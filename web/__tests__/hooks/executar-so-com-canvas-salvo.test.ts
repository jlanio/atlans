/**
 * Executar saves silently before dispatching, and the run executes what is
 * STORED. It used to stop only on a save `error`: every save that wrote
 * nothing — a Ctrl+S still in flight, a canvas not loaded yet, a missing name —
 * answered `undefined` or an empty envelope and the POST /execute went out
 * anyway, running the previous definition while the canvas showed another,
 * with nothing said. Now the run only goes out when the save says `saved`.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import type { SaveResult } from "@/app/hooks/workflow/useSaveWorkflow"

const canvasNodes = [{ id: "n1", position: { x: 0, y: 0 }, data: {} }]

let resultadoDoSave: SaveResult = { outcome: "saved", data: null, error: null }
const executeWorkflow = vi.fn(async () => ({ data: { task_id: "run-1" }, error: null }))
const toasts = vi.hoisted(() => ({ info: vi.fn(), error: vi.fn(), success: vi.fn() }))

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "wf-a" }) }))
vi.mock("next-auth/react", () => ({ useSession: () => ({ data: null }), getSession: async () => null }))
vi.mock("@/app/hooks/workflow/useSaveWorkflow", () => ({
  useSaveWorkflow: () => ({ saveWorkflow: async () => resultadoDoSave }),
}))
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    // No live run: the re-attach on mount stays out of the way.
    getObservabilityRuns: vi.fn(async () => ({ data: { runs: [] } })),
    getRunDetail: vi.fn(async () => ({ data: { status: "running" } })),
    executeWorkflow: () => executeWorkflow(),
  },
}))
vi.mock("@/utils/createToast", () => ({ createToast: toasts }))
vi.mock("@/utils/env", () => ({ getWsUrl: () => "ws://teste" }))
vi.mock("@xyflow/react", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  useNodes: () => canvasNodes,
  useEdges: () => [],
  useReactFlow: () => ({ getNodes: () => canvasNodes }),
}))

class FakeSocket {
  static abertos: FakeSocket[] = []
  onopen = null; onmessage = null; onerror = null; onclose = null
  constructor(public url: string) { FakeSocket.abertos.push(this) }
  send() {}
  close() {}
}

async function executar() {
  const { useExecuteWorkflow } = await import("@/app/hooks/workflow/useExecuteWorkflow")
  const view = renderHook(() => useExecuteWorkflow())
  await act(async () => { await view.result.current.executeWorkflow() })
  return view
}

describe("Executar só despacha com o canvas salvo", () => {
  beforeEach(() => {
    FakeSocket.abertos = []
    executeWorkflow.mockClear()
    toasts.info.mockClear()
    toasts.error.mockClear()
    vi.stubGlobal("WebSocket", FakeSocket)
    vi.stubGlobal("requestAnimationFrame", () => 0)
    vi.stubGlobal("cancelAnimationFrame", () => {})
    useWorkflowExecutionStore.getState().resetExecution()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it.each([
    ["in_flight", "Salvamento em andamento"],
    ["not_hydrated", "Aguarde o workflow carregar para executar"],
    ["needs_name", "Dê um nome ao workflow para executar"],
    ["empty_graph", "Workflow não executado"],
  ] as const)("save pulado (%s): não executa e diz por quê", async (skipReason, titulo) => {
    resultadoDoSave = { outcome: "skipped", skipReason, data: null, error: null }
    const view = await executar()

    expect(executeWorkflow).not.toHaveBeenCalled()
    expect(FakeSocket.abertos).toHaveLength(0)
    expect(toasts.info).toHaveBeenCalledTimes(1)
    expect(toasts.info.mock.calls[0][0]).toBe(titulo)
    // The canvas does not stay "queued" for a run that never left.
    const estado = useWorkflowExecutionStore.getState()
    expect(estado.isExecuting).toBe(false)
    expect(estado.statusWorkflow).toBeNull()
    view.unmount()
  })

  it("save com erro: não executa, e não repete o aviso que o save já deu", async () => {
    resultadoDoSave = { outcome: "error", data: null, error: { name: "AxiosError", message: "boom" } }
    const view = await executar()

    expect(executeWorkflow).not.toHaveBeenCalled()
    expect(toasts.info).not.toHaveBeenCalled()
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(false)
    view.unmount()
  })

  it("canvas salvo (ou já igual ao do servidor): executa e acompanha o run", async () => {
    resultadoDoSave = { outcome: "saved", data: null, error: null }
    const view = await executar()

    expect(executeWorkflow).toHaveBeenCalledTimes(1)
    expect(FakeSocket.abertos.map(s => s.url)).toEqual(["ws://teste/ws/workflow/run-1"])
    view.unmount()
  })
})
