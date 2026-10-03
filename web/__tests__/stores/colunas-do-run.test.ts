/**
 * How the known columns ENTER the store — the two real paths:
 *
 *   1. Re-hydration: opening a workflow whose last run has already finished
 *      fetches the persisted `node_stats` and seeds the suggestions WITHOUT
 *      executing anything. It's what kills "F5 wipes everything" — before,
 *      the columns only existed while the run's session was alive.
 *   2. Live: each node's `completed` event writes the columns with
 *      `fresh: true`; and `completed` WITHOUT the key REMOVES the entry —
 *      keeping the old value would assert columns the last run didn't produce.
 *
 * Uses the same socket/frame harness as the stream recovery: the live path
 * goes through the per-frame batch (`drenarLote`), not through a direct call.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { useKnownColumnsStore } from "@/app/stores/knownColumnsStore"

const RUN = "run-x"

let workflowAtual = "wf-a"
const runsPorWorkflow: Record<string, { run_id: string; status: string }[]> = {}
/** What `getRunDetail` returns — the detail with `node_stats` for hydration. */
let detalheNaApi: Record<string, unknown> = {}

const nosDoCanvas = [
  { id: "n1", position: { x: 0, y: 0 }, data: {} },
  { id: "n2", position: { x: 0, y: 0 }, data: {} },
]

vi.mock("next/navigation", () => ({ useParams: () => ({ id: workflowAtual }) }))
vi.mock("next-auth/react", () => ({ useSession: () => ({ data: null }) }))
vi.mock("@/app/hooks/workflow/useSaveWorkflow", () => ({
  useSaveWorkflow: () => ({ saveWorkflow: vi.fn(async () => ({ error: null })) }),
}))

const getRunDetail = vi.fn(async () => ({ data: detalheNaApi }))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getObservabilityRuns: vi.fn(async ({ workflow_id }: { workflow_id: string }) => ({
      data: { runs: runsPorWorkflow[workflow_id] ?? [] },
    })),
    getRunDetail: (...args: unknown[]) => getRunDetail(...(args as [])),
    executeWorkflow: vi.fn(),
  },
}))

vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), info: vi.fn(), success: vi.fn() },
}))
vi.mock("@/utils/env", () => ({ getWsUrl: () => "ws://teste" }))
vi.mock("@xyflow/react", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  useNodes: () => nosDoCanvas,
  useEdges: () => [],
  useReactFlow: () => ({ getNodes: () => nosDoCanvas }),
}))

class SocketFalso {
  static abertos: SocketFalso[] = []
  onopen: (() => void) | null = null
  onmessage: ((ev: { data: string }) => void) | null = null
  onerror: ((err: unknown) => void) | null = null
  onclose: ((ev: { code: number }) => void) | null = null
  constructor(public url: string) {
    SocketFalso.abertos.push(this)
  }
  send() {}
  close() {
    this.onclose?.({ code: 1000 })
  }
}

const quadros = new Map<number, FrameRequestCallback>()
let proximoQuadro = 1

/** Runs the pending frames — it's what applies the batch to the store. */
function rodarQuadros() {
  const cbs = [...quadros.values()]
  quadros.clear()
  for (const cb of cbs) cb(0)
}

async function montar() {
  const { useExecuteWorkflow } = await import("@/app/hooks/workflow/useExecuteWorkflow")
  return renderHook(() => useExecuteWorkflow())
}

describe("colunas do run → knownColumnsStore", () => {
  beforeEach(() => {
    workflowAtual = "wf-a"
    runsPorWorkflow["wf-a"] = []
    detalheNaApi = {}
    SocketFalso.abertos = []
    quadros.clear()
    proximoQuadro = 1
    getRunDetail.mockClear()
    vi.stubGlobal("WebSocket", SocketFalso)
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      const id = proximoQuadro++
      quadros.set(id, cb)
      return id
    })
    vi.stubGlobal("cancelAnimationFrame", (id: number) => { quadros.delete(id) })
    useWorkflowExecutionStore.getState().resetExecution()
    useKnownColumnsStore.setState({ workflowId: null, porNo: new Map() })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  // ── 1. Re-hydration of the last persisted run ───────────────────────────

  it("último run concluído semeia as colunas do node_stats, sem abrir socket", async () => {
    runsPorWorkflow["wf-a"] = [{ run_id: RUN, status: "success" }]
    detalheNaApi = {
      status: "success",
      node_stats: {
        n1: { node_name: "Ler camada", output_columns: { output: ["cod", "nome"] } },
        // Without the key (old executor, 8KB cut): it simply doesn't seed.
        n2: { node_name: "Filtro" },
      },
    }

    const view = await montar()
    await waitFor(() => {
      expect(useKnownColumnsStore.getState().porNo.get("n1")).toEqual({
        porPorta: { output: ["cod", "nome"] }, runId: RUN, fresh: false, parciais: false,
      })
    })
    expect(useKnownColumnsStore.getState().workflowId).toBe("wf-a")
    expect(useKnownColumnsStore.getState().porNo.has("n2")).toBe(false)
    // A dead run has nothing to re-attach.
    expect(SocketFalso.abertos).toHaveLength(0)
    // And hydration doesn't touch the execution state (clean canvas).
    expect(useWorkflowExecutionStore.getState().statusWorkflow).toBeNull()

    view.unmount()
  })

  it("stats sem coluna nenhuma não chama a store à toa", async () => {
    runsPorWorkflow["wf-a"] = [{ run_id: RUN, status: "failed" }]
    detalheNaApi = { status: "failed", node_stats: { n1: { node_name: "x" } } }

    const view = await montar()
    await waitFor(() => expect(getRunDetail).toHaveBeenCalled())
    expect(useKnownColumnsStore.getState().porNo.size).toBe(0)

    view.unmount()
  })

  // ── 2. Live write, through the per-frame batch ──────────────────────────

  it("completed com colunas grava fresh=true; sem colunas, remove a entrada", async () => {
    runsPorWorkflow["wf-a"] = [{ run_id: RUN, status: "running" }]

    const view = await montar()
    await waitFor(() => expect(SocketFalso.abertos.length).toBeGreaterThan(0))
    const ws = SocketFalso.abertos[0]

    const frame = (eventos: object[]) =>
      JSON.stringify({ type: "events", events: eventos })

    await act(async () => {
      ws.onmessage?.({
        data: frame([{
          node: "n1", status: "completed", kind: "lifecycle", timestamp: 1,
          extra: { output_columns: { output: ["x", "y"] } },
        }]),
      })
      rodarQuadros()
    })
    expect(useKnownColumnsStore.getState().porNo.get("n1")).toEqual({
      porPorta: { output: ["x", "y"] }, runId: RUN, fresh: true,
    })

    // The same node completes again, now without publishing columns
    // (non-tabular output): it becomes a tombstone — nothing to suggest, and
    // the previous run's late seeding doesn't resurrect the denied data.
    await act(async () => {
      ws.onmessage?.({
        data: frame([{ node: "n1", status: "completed", kind: "lifecycle", timestamp: 2, extra: {} }]),
      })
      rodarQuadros()
    })
    expect(useKnownColumnsStore.getState().porNo.get("n1")).toEqual({
      porPorta: {}, runId: RUN, fresh: true,
    })

    view.unmount()
  })

  it("evento que não é completed não mexe na memória de colunas", async () => {
    runsPorWorkflow["wf-a"] = [{ run_id: RUN, status: "running" }]
    useKnownColumnsStore.getState().semearDoHistorico("wf-a", "run-antigo", {
      n1: { porPorta: { output: ["antiga"] } },
    })

    const view = await montar()
    await waitFor(() => expect(SocketFalso.abertos.length).toBeGreaterThan(0))
    const ws = SocketFalso.abertos[0]

    await act(async () => {
      ws.onmessage?.({
        data: JSON.stringify({
          type: "events",
          events: [{ node: "n1", status: "started", kind: "lifecycle", timestamp: 1 }],
        }),
      })
      rodarQuadros()
    })
    // `started` (and stdout, debug…) assert nothing about columns.
    expect(useKnownColumnsStore.getState().porNo.get("n1")).toMatchObject({
      porPorta: { output: ["antiga"] }, fresh: false,
    })

    view.unmount()
  })
})
