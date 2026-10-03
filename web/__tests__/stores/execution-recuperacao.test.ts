/**
 * Recovery of the execution stream.
 *
 * The executor→server→browser channel is lossy at EVERY layer (executor
 * queue, server inbox, viewer buffer, rate limit), and the server closes
 * the socket with code 1000 even when the Redis subscription ends without
 * `__workflow_complete__`. The client treated that 1000 as a normal
 * shutdown and did nothing: the nodes kept spinning and the panel said
 * "Executando" forever, with the run already finished in the database and in
 * the executor log.
 *
 * These tests demand the three defenses that close that hole:
 *   1. no node outlives the end of the run in `started`;
 *   2. a drop with the run open reconciles through the API;
 *   3. a still-live run makes the client reconnect, and an intentional close does not.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { useWorkflowExecutionStore, RUN_ENCERRADO } from "@/app/stores/workflowExecutionStore"
import type { INodeStatusWorkFlow } from "@/context/useFlowContext"

const RUN = "run-x"

let workflowAtual = "wf-a"
const runsPorWorkflow: Record<string, { run_id: string; status: string }[]> = {}
/** Status the API returns for the run — what `onclose` will query. */
let statusNaApi = "running"

const nosDoCanvas = [
  { id: "n1", position: { x: 0, y: 0 }, data: {} },
  { id: "n2", position: { x: 0, y: 0 }, data: {} },
]

vi.mock("next/navigation", () => ({ useParams: () => ({ id: workflowAtual }) }))
vi.mock("next-auth/react", () => ({ useSession: () => ({ data: null }) }))
vi.mock("@/app/hooks/workflow/useSaveWorkflow", () => ({
  useSaveWorkflow: () => ({ saveWorkflow: vi.fn(async () => ({ error: null })) }),
}))

const getRunDetail = vi.fn(async () => ({ data: { status: statusNaApi } }))

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
  fechadoCom: number | null = null

  constructor(public url: string) {
    SocketFalso.abertos.push(this)
  }
  send() {}
  /** Close requested by the CODE (intentional). */
  close(code = 1000) {
    this.fechadoCom = code
    this.onclose?.({ code })
  }
  /** Drop coming from the SERVER — the case that needs recovery. */
  cairDoServidor(code = 1000) {
    this.onclose?.({ code })
  }
}

const quadros = new Map<number, FrameRequestCallback>()
let proximoQuadro = 1

async function anexar() {
  const { useExecuteWorkflow } = await import("@/app/hooks/workflow/useExecuteWorkflow")
  const view = renderHook(() => useExecuteWorkflow())
  await waitFor(() => expect(SocketFalso.abertos.length).toBeGreaterThan(0))
  return { view, ws: SocketFalso.abertos[0] }
}

describe("recuperação do stream de execução", () => {
  beforeEach(() => {
    workflowAtual = "wf-a"
    statusNaApi = "running"
    runsPorWorkflow["wf-a"] = [{ run_id: RUN, status: "running" }]
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
    // Deterministic jitter: the backoff becomes exactly the base.
    vi.spyOn(Math, "random").mockReturnValue(1)
    useWorkflowExecutionStore.getState().resetExecution()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  // ── 1. No node outlives the end of the run spinning ─────────────────────

  it("nó preso em 'started' vira 'unknown' quando o run conclui", () => {
    const store = useWorkflowExecutionStore.getState()
    const nos = [
      { id: "n1", status: "completed" },
      { id: "n2", status: "started" },
    ] as INodeStatusWorkFlow[]
    store.startExecution(nos)
    store.completeExecution("completed", nos, [])

    const final = useWorkflowExecutionStore.getState()
    expect(final.statusById.get("n2")?.status).toBe("unknown")
    // What actually completed must not be downgraded along with it.
    expect(final.statusById.get("n1")?.status).toBe("completed")
    expect(final.isExecuting).toBe(false)
  })

  it("cancelamento continua devolvendo o nó a 'idle', não a 'unknown'", () => {
    // These are different outcomes: canceling really interrupted the work;
    // `unknown` is work that probably finished and whose news got lost.
    const store = useWorkflowExecutionStore.getState()
    const nos = [{ id: "n1", status: "started" }] as INodeStatusWorkFlow[]
    store.startExecution(nos)
    store.completeExecution("cancelled", nos, [])

    expect(useWorkflowExecutionStore.getState().statusById.get("n1")?.status).toBe("idle")
  })

  // ── 2. A drop with the run open reconciles through the API ──────────────

  it("queda com código 1000 e run já concluído fecha o painel com o desfecho real", async () => {
    const { view, ws } = await anexar()
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(true)

    statusNaApi = "success"
    await act(async () => { ws.cairDoServidor(1000) })

    await waitFor(() => {
      const estado = useWorkflowExecutionStore.getState()
      expect(estado.isExecuting).toBe(false)
      expect(estado.statusWorkflow?.status).toBe("completed")
    })
    expect(getRunDetail).toHaveBeenCalled()
    // Reconciled: it makes no sense to reconnect to a run that already ended.
    expect(SocketFalso.abertos).toHaveLength(1)

    view.unmount()
  })

  // ── 3. Run still live → reconnects; intentional → does not ─────────────

  it("queda com o run ainda em andamento reconecta com backoff", async () => {
    const { view, ws } = await anexar()
    statusNaApi = "running"

    vi.useFakeTimers()
    await act(async () => { ws.cairDoServidor(1000) })
    // The API query is asynchronous; let the microtask resolve before the timer.
    await act(async () => { await vi.advanceTimersByTimeAsync(1_100) })

    expect(SocketFalso.abertos.length).toBeGreaterThan(1)
    expect(SocketFalso.abertos[1].url).toContain(RUN)
    // The panel was NOT closed: the run is still live.
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(true)

    view.unmount()
  })

  it("fechamento intencional (sair do workflow) não reconecta", async () => {
    const { view } = await anexar()
    statusNaApi = "running"

    vi.useFakeTimers()
    // Unmounting closes the socket through the code's own path.
    await act(async () => { view.unmount() })
    await act(async () => { await vi.advanceTimersByTimeAsync(5_000) })

    expect(SocketFalso.abertos).toHaveLength(1)
    // And it did not go ask the API about a run the user left behind.
    expect(getRunDetail).not.toHaveBeenCalled()
  })

  // ── 4. A single owner for the socket ────────────────────────────────────

  it("uma segunda instância do hook não abre um socket concorrente", async () => {
    // The hook is mounted on the Run button AND on the Webhook node's "Testar"
    // tab. Since the execution store is global, the second instance opened a
    // parallel WebSocket to the same run and, on mount, called
    // `startExecution` — which wipes the canvas of whoever was already
    // following. In production logs this showed up as three connections to the
    // same run within 25 seconds.
    const { useExecuteWorkflow } = await import("@/app/hooks/workflow/useExecuteWorkflow")

    const dono = renderHook(() => useExecuteWorkflow())
    await waitFor(() => expect(SocketFalso.abertos).toHaveLength(1))

    const carona = renderHook(() => useExecuteWorkflow())
    // REAL time for the async re-attach chain (API query + waiting for the
    // canvas hydration) to complete. With an `await
    // Promise.resolve()` the test would pass even WITHOUT the fix, because the
    // second socket would not have been opened yet when the assertion ran.
    await act(async () => { await new Promise(r => setTimeout(r, 60)) })

    expect(SocketFalso.abertos).toHaveLength(1)

    carona.unmount()
    dono.unmount()
  })

  // ── 5. An unreadable frame does not bring down the batch ───────────────

  it("frame com JSON inválido é contabilizado e não lança", async () => {
    const { view, ws } = await anexar()
    const antes = useWorkflowExecutionStore.getState().droppedEvents

    expect(() => {
      act(() => { ws.onmessage?.({ data: '{"type":"events","events":[{bro' }) })
    }).not.toThrow()

    expect(useWorkflowExecutionStore.getState().droppedEvents).toBeGreaterThan(antes)
    view.unmount()
  })

  // ── 5b. A mute socket (Safari) is recovered without relying on onclose ──
  //
  // On Safari an idle WebSocket is dropped silently, WITHOUT firing
  // `onclose`. Since reconnection lived entirely in `onclose`, the drop went
  // unnoticed: the panel spun forever, with the run already finished on the
  // server. The inactivity watchdog closes that hole — it detects the silence
  // and recovers through the API/replay, even if `onclose` never comes.

  it("socket mudo além do limite recupera mesmo sem onclose (caso Safari)", async () => {
    const { view, ws } = await anexar()
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(true)
    // The API knows the run finished — Safari just never received the events.
    statusNaApi = "success"

    vi.useFakeTimers()
    // Arms the watchdog on the fake clock (the fake socket does not fire onopen by itself).
    act(() => { ws.onopen?.() })
    // TOTAL silence: no onmessage and — on purpose — no onclose.
    await act(async () => { await vi.advanceTimersByTimeAsync(70_000) })

    // O watchdog assumiu o socket morto e reconciliou pela API.
    expect(getRunDetail).toHaveBeenCalled()
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(false)
    expect(useWorkflowExecutionStore.getState().statusWorkflow?.status).toBe("completed")

    view.unmount()
  })

  it("heartbeat (frame vazio) mantém o socket vivo e NÃO dispara o watchdog", async () => {
    const { view, ws } = await anexar()
    statusNaApi = "success"

    vi.useFakeTimers()
    act(() => { ws.onopen?.() })
    // A heartbeat (empty batch) arrives every 20s. Silence never accumulates, so
    // the watchdog must not mistake a healthy connection for a dead socket.
    for (let t = 0; t < 90_000; t += 20_000) {
      await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
      act(() => { ws.onmessage?.({ data: '{"type":"events","dropped":0,"events":[]}' }) })
    }

    expect(getRunDetail).not.toHaveBeenCalled()
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(true)

    view.unmount()
  })

  // ── 6. A late batch does not resurrect an already-settled run ───────────
  //
  // The client applies events per `requestAnimationFrame` frame. With the tab in
  // the background the frame does NOT run, but the WebSocket keeps delivering: the
  // batch stays pending while the run finishes and is settled. On returning to the
  // tab, the late frame fired and reapplied old events on top of the outcome —
  // the node went back to `started` and kept spinning forever, now with no socket,
  // no `isExecuting` and nobody to settle it again. It was what remained of the
  // symptom after the two earlier fixes closed the LOSS paths.

  function rodarQuadrosPendentes() {
    const pendentes = [...quadros.values()]
    quadros.clear()
    for (const cb of pendentes) cb(0)
  }

  it("quadro atrasado que roda depois da liquidação não devolve o nó a 'started'", async () => {
    const { view, ws } = await anexar()

    // Events arrive, but the frame stays pending (tab in the background).
    act(() => {
      ws.onmessage?.({ data: JSON.stringify({
        type: "events",
        events: [
          { run_id: RUN, node: "n1", status: "completed", kind: "lifecycle" },
          { run_id: RUN, node: "n2", status: "started",   kind: "lifecycle" },
        ],
      }) })
    })
    expect(quadros.size).toBeGreaterThan(0)

    // O run termina e o socket cai sem o `__workflow_complete__`.
    statusNaApi = "success"
    await act(async () => { ws.cairDoServidor(1000) })
    await waitFor(() => {
      expect(useWorkflowExecutionStore.getState().isExecuting).toBe(false)
    })

    // The user returns to the tab: what was scheduled fires now.
    act(() => { rodarQuadrosPendentes() })

    const final = useWorkflowExecutionStore.getState()
    expect(final.statusById.get("n2")?.status).toBe("unknown")
    expect(final.statusById.get("n2")?.status).not.toBe("started")
    // Draining BEFORE settling preserves what actually arrived: n1's `completed`
    // is legitimate information and must not be thrown away with the batch.
    expect(final.statusById.get("n1")?.status).toBe("completed")
    expect(final.statusWorkflow?.status).toBe("completed")

    view.unmount()
  })

  it("updateNodeStatuses é inerte depois de o run ter desfecho", () => {
    const store = useWorkflowExecutionStore.getState()
    const nos = [{ id: "n1", status: "completed" }] as INodeStatusWorkFlow[]
    store.startExecution(nos)
    store.completeExecution("completed", nos, [])

    // The store's safety belt: even if some future path escapes the hook's
    // guards, the outcome is final.
    useWorkflowExecutionStore.getState().updateNodeStatuses(
      [{ id: "n1", status: "started" }] as INodeStatusWorkFlow[], [],
    )

    const final = useWorkflowExecutionStore.getState()
    expect(final.statusById.get("n1")?.status).toBe("completed")
    expect(final.statusWorkflow?.status).toBe("completed")
    expect(final.isExecuting).toBe(false)
  })

  it("re-anexar a um run que o servidor diz vivo desfaz um encerramento precipitado", async () => {
    // The `updateNodeStatuses` guard makes the outcome final — which would be
    // wrong if the outcome had been our mistake. Here the client settled the
    // run (racing reconciliation / giving up) but the API reports it as in
    // progress: the re-attach must re-seed, otherwise the replay is discarded
    // by the guard and the canvas freezes on the wrong outcome.
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([{ id: "n1", status: "started" }] as INodeStatusWorkFlow[])
    store.setTaskId(RUN)
    store.completeExecution("failed", store.statusWorkflow?.nodes ?? [], [])
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(false)

    const { view } = await anexar()
    await waitFor(() => {
      const estado = useWorkflowExecutionStore.getState()
      expect(estado.isExecuting).toBe(true)
      expect(RUN_ENCERRADO.has(estado.statusWorkflow?.status ?? "")).toBe(false)
    })

    view.unmount()
  })

  it("failExecution também liquida nó preso em 'started'", () => {
    const store = useWorkflowExecutionStore.getState()
    const nos = [
      { id: "n1", status: "completed" },
      { id: "n2", status: "started" },
    ] as INodeStatusWorkFlow[]
    store.startExecution(nos)
    store.updateNodeStatuses(nos, [])
    useWorkflowExecutionStore.getState().failExecution()

    const final = useWorkflowExecutionStore.getState()
    expect(final.statusById.get("n2")?.status).toBe("unknown")
    expect(final.statusById.get("n1")?.status).toBe("completed")
    expect(final.isExecuting).toBe(false)
  })
})
