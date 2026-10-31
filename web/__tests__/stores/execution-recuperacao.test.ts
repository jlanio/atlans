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
import { useWorkflowExecutionStore, RUN_TERMINAL, toRunEvent } from "@/app/stores/workflowExecutionStore"
import type { INodeStatusWorkFlow } from "@/context/useFlowContext"

const RUN = "run-x"

let currentWorkflow = "wf-a"
const runsByWorkflow: Record<string, { run_id: string; status: string }[]> = {}
/** Status the API returns for the run — what `onclose` will query. */
let statusNaApi = "running"

const canvasNodes = [
  { id: "n1", position: { x: 0, y: 0 }, data: {} },
  { id: "n2", position: { x: 0, y: 0 }, data: {} },
]

/** The session SessionProvider holds, and the one /api/auth/session answers now. */
let sessaoNoProvider: unknown = null
const getSession = vi.fn(async (): Promise<unknown> => null)
/** `useSession().update()` — what /api/auth/session answers now (null = the fetch failed). */
const atualizarSessao = vi.fn(async (): Promise<unknown> => null)

vi.mock("next/navigation", () => ({ useParams: () => ({ id: currentWorkflow }) }))
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: sessaoNoProvider, update: atualizarSessao }),
  getSession: () => getSession(),
}))
vi.mock("@/app/hooks/workflow/useSaveWorkflow", () => ({
  useSaveWorkflow: () => ({ saveWorkflow: vi.fn(async () => ({ error: null })) }),
}))

const getRunDetail = vi.fn(async () => ({ data: { status: statusNaApi } }))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getObservabilityRuns: vi.fn(async ({ workflow_id }: { workflow_id: string }) => ({
      data: { runs: runsByWorkflow[workflow_id] ?? [] },
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
  useNodes: () => canvasNodes,
  useEdges: () => [],
  useReactFlow: () => ({ getNodes: () => canvasNodes }),
}))

class FakeSocket {
  static abertos: FakeSocket[] = []
  onopen: (() => void) | null = null
  onmessage: ((ev: { data: string }) => void) | null = null
  onerror: ((err: unknown) => void) | null = null
  onclose: ((ev: { code: number }) => void) | null = null
  fechadoCom: number | null = null
  enviados: string[] = []

  constructor(public url: string) {
    FakeSocket.abertos.push(this)
  }
  send(msg: string) { this.enviados.push(msg) }
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
let nextFrame = 1

async function anexar() {
  const { useExecuteWorkflow } = await import("@/app/hooks/workflow/useExecuteWorkflow")
  const view = renderHook(() => useExecuteWorkflow())
  await waitFor(() => expect(FakeSocket.abertos.length).toBeGreaterThan(0))
  return { view, ws: FakeSocket.abertos[0] }
}

describe("recuperação do stream de execução", () => {
  beforeEach(() => {
    currentWorkflow = "wf-a"
    statusNaApi = "running"
    runsByWorkflow["wf-a"] = [{ run_id: RUN, status: "running" }]
    FakeSocket.abertos = []
    quadros.clear()
    nextFrame = 1
    getRunDetail.mockClear()
    sessaoNoProvider = null
    getSession.mockReset()
    getSession.mockResolvedValue(null)
    atualizarSessao.mockReset()
    atualizarSessao.mockResolvedValue(null)
    vi.stubGlobal("WebSocket", FakeSocket)
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      const id = nextFrame++
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
    expect(FakeSocket.abertos).toHaveLength(1)

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

    expect(FakeSocket.abertos.length).toBeGreaterThan(1)
    expect(FakeSocket.abertos[1].url).toContain(RUN)
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

    expect(FakeSocket.abertos).toHaveLength(1)
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
    await waitFor(() => expect(FakeSocket.abertos).toHaveLength(1))

    const carona = renderHook(() => useExecuteWorkflow())
    // REAL time for the async re-attach chain (API query + waiting for the
    // canvas hydration) to complete. With an `await
    // Promise.resolve()` the test would pass even WITHOUT the fix, because the
    // second socket would not have been opened yet when the assertion ran.
    await act(async () => { await new Promise(r => setTimeout(r, 60)) })

    expect(FakeSocket.abertos).toHaveLength(1)

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

  function runPendingFrames() {
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
    act(() => { runPendingFrames() })

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
      expect(RUN_TERMINAL.has(estado.statusWorkflow?.status ?? "")).toBe(false)
    })

    view.unmount()
  })

  // ── 7. The token goes out at open time, not from the attach's closure ───

  it("o token sai da sessão do momento do onopen, não do render que anexou", async () => {
    sessaoNoProvider = { user: { access_token: "T1" } }
    const { view, ws } = await anexar()
    // SessionProvider refetched (poll, focus) before the socket opened.
    sessaoNoProvider = { user: { access_token: "T2" } }
    view.rerender()

    act(() => { ws.onopen?.() })
    expect(ws.enviados).toEqual(["T2"])
    view.unmount()
  })

  it("reconectar renova a sessão antes e manda o token novo", async () => {
    // Past the API's 30 min TTL the server refuses the token (4401). The tab
    // kept focus, so the provider still holds the old one; reconnecting with
    // the attach's token failed the same way until giving up.
    sessaoNoProvider = { user: { access_token: "TOKEN-DO-ANEXO" } }
    const { view, ws } = await anexar()
    act(() => { ws.onopen?.() })
    expect(ws.enviados).toEqual(["TOKEN-DO-ANEXO"])

    // `update()`: keeps the session if the fetch fails (getSession turned the
    // tab anonymous) and tells the provider, so a dead refresh signs out.
    atualizarSessao.mockResolvedValue({ user: { access_token: "TOKEN-RENOVADO" } })
    vi.useFakeTimers()
    await act(async () => { ws.cairDoServidor(4401) })
    await act(async () => { await vi.advanceTimersByTimeAsync(1_100) })

    const ws2 = FakeSocket.abertos[1]
    act(() => { ws2.onopen?.() })
    expect(atualizarSessao).toHaveBeenCalled()
    expect(getSession).not.toHaveBeenCalled()
    expect(ws2.enviados).toEqual(["TOKEN-RENOVADO"])
    view.unmount()
  })

  it("com o refresh token morto, para de reconectar", async () => {
    // /api/auth/session answers 200 with `error: RefreshTokenExpired`: the
    // token will never be accepted. Reconnecting looped forever — the API
    // accepts the socket before the token, and the attempt counter reset on
    // every open (round-2 review).
    sessaoNoProvider = { user: { access_token: "VELHO" } }
    const { view, ws } = await anexar()
    act(() => { ws.onopen?.() })
    atualizarSessao.mockResolvedValue({ user: { access_token: "VELHO" }, error: "RefreshTokenExpired" })

    vi.useFakeTimers()
    await act(async () => { ws.cairDoServidor(4401) })
    await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })

    expect(FakeSocket.abertos).toHaveLength(1)
    view.unmount()
  })

  it("um token recusado em todo socket esgota as tentativas", async () => {
    // Open → 4401 → open… with no frame ever arriving: the backoff must still
    // count (it reset on `onopen`, before the refusal).
    sessaoNoProvider = { user: { access_token: "RECUSADO" } }
    atualizarSessao.mockResolvedValue({ user: { access_token: "RECUSADO" } })
    const { view } = await anexar()
    vi.useFakeTimers()
    for (let i = 0; i < 12; i++) {
      const atual = FakeSocket.abertos.at(-1)!
      act(() => { atual.onopen?.() })
      await act(async () => { atual.cairDoServidor(4401) })
      await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
    }
    expect(FakeSocket.abertos.length).toBeLessThanOrEqual(9)
    view.unmount()
  })

  // ── 8. Reconnecting does not replay the history on top of the panel ─────
  //
  // The server replays the run's WHOLE history on every connect (Redis
  // `LRANGE 0 -1`) and the store only appends. A reconnect used to append the
  // replay after the events already shown: every print() line twice (three
  // times after the next drop), and the "Saída" count, Copiar/Baixar with it.

  const historico = [
    { node: "n1", status: "started",   kind: "lifecycle", timestamp: 1 },
    { node: "n1", status: "log",       kind: "stdout", extra: { lines: ["a", "b"] }, timestamp: 2 },
    { node: "n1", status: "completed", kind: "lifecycle", timestamp: 3 },
    { node: "n2", status: "started",   kind: "lifecycle", timestamp: 4 },
  ]
  const quadro = (events: object[], dropped = 0) =>
    ({ data: JSON.stringify({ type: "events", events, dropped }) })

  it("reconectar não duplica as linhas que já estão no painel", async () => {
    const { view, ws } = await anexar()
    // The live stream lost 3 stdout events to server back-pressure.
    act(() => { ws.onopen?.(); ws.onmessage?.(quadro(historico, 3)) })
    act(() => { runPendingFrames() })
    expect(useWorkflowExecutionStore.getState().events).toHaveLength(4)
    expect(useWorkflowExecutionStore.getState().droppedEvents).toBe(3)

    vi.useFakeTimers()
    await act(async () => { ws.cairDoServidor(1006) })
    await act(async () => { await vi.advanceTimersByTimeAsync(1_100) })
    const ws2 = FakeSocket.abertos[1]
    expect(ws2?.url).toContain(RUN)

    // Reconnected, replay not here yet: nothing on screen is lost meanwhile —
    // neither the log nor the canvas. (A reconnect refused before any frame,
    // a 4401 for one, must not leave the panel empty.)
    act(() => { ws2.onopen?.() })
    let estado = useWorkflowExecutionStore.getState()
    expect(estado.events).toHaveLength(4)
    expect(estado.statusById.get("n1")?.status).toBe("completed")
    expect(estado.statusById.get("n2")?.status).toBe("started")

    // The server sends the COMPLETE history again, plus what happened in the gap.
    const novo = { node: "n2", status: "log", kind: "stdout", extra: { lines: ["c"] }, timestamp: 5 }
    act(() => { ws2.onmessage?.(quadro([...historico, novo])) })
    // The fake clock also owns requestAnimationFrame now: one frame drains.
    await act(async () => { await vi.advanceTimersByTimeAsync(20) })

    estado = useWorkflowExecutionStore.getState()
    expect(estado.events).toHaveLength(5)
    expect(estado.events.flatMap(e => e.lines ?? [])).toEqual(["a", "b", "c"])
    expect(estado.events.map(e => e.seq)).toEqual([0, 1, 2, 3, 4])
    expect(estado.runStartedTs).toBe(1_000)
    // The replay comes from the Redis history, which still has what the live
    // queue dropped: the old discard count would now be a lie.
    expect(estado.droppedEvents).toBe(0)
    // The canvas was not reset along with the log.
    expect(estado.statusById.get("n1")?.status).toBe("completed")
    expect(estado.statusById.get("n2")?.status).toBe("started")
    expect(estado.isExecuting).toBe(true)

    view.unmount()
  })

  it("re-anexar a um run cujo log já está no store também troca o log pelo replay", async () => {
    // A second mount of the owner (or a re-run effect) re-attaches WITHOUT
    // `startExecution`, to keep the progress painted: same replay, same doubling.
    const store = useWorkflowExecutionStore.getState()
    store.startExecution(canvasNodes.map(n => ({ ...n, status: "idle" })) as unknown as INodeStatusWorkFlow[])
    store.setTaskId(RUN)
    store.appendEvents(historico.map(toRunEvent))

    const { view, ws } = await anexar()
    act(() => { ws.onmessage?.(quadro(historico)) })
    act(() => { runPendingFrames() })

    expect(useWorkflowExecutionStore.getState().events).toHaveLength(4)
    view.unmount()
  })

  it("o replay é reconhecido pelo conteúdo, não pelo relógio do executor", async () => {
    // The executor's clock stepped back: the replay's events carry the same
    // timestamps as the panel's, but a NEW live event before them has an
    // older time. Judged by clock, the batch looked new and doubled the log.
    const store = useWorkflowExecutionStore.getState()
    store.startExecution(canvasNodes.map(n => ({ ...n, status: "idle" })) as unknown as INodeStatusWorkFlow[])
    store.setTaskId(RUN)
    store.appendEvents(historico.map(toRunEvent))

    const { view, ws } = await anexar()
    act(() => { ws.onmessage?.(quadro(historico)) })
    act(() => { runPendingFrames() })

    expect(useWorkflowExecutionStore.getState().events).toHaveLength(4)
    view.unmount()
  })

  it("um quadro ilegível antes do replay mantém o aviso de descarte", async () => {
    const store = useWorkflowExecutionStore.getState()
    store.startExecution(canvasNodes.map(n => ({ ...n, status: "idle" })) as unknown as INodeStatusWorkFlow[])
    store.setTaskId(RUN)
    store.appendEvents(historico.map(toRunEvent))

    const { view, ws } = await anexar()
    act(() => { ws.onmessage?.({ data: "{corrompido" }) })
    act(() => { ws.onmessage?.(quadro(historico)) })
    act(() => { runPendingFrames() })

    expect(useWorkflowExecutionStore.getState().droppedEvents).toBe(1)
    view.unmount()
  })

  it("um primeiro lote mais novo que o painel não é replay: o log fica", async () => {
    // The server's history expired (or was lost): the reconnect delivers only
    // live events. Clearing then wiped the whole log for a handful of lines.
    const store = useWorkflowExecutionStore.getState()
    store.startExecution(canvasNodes.map(n => ({ ...n, status: "idle" })) as unknown as INodeStatusWorkFlow[])
    store.setTaskId(RUN)
    store.appendEvents(historico.map(toRunEvent))

    const { view, ws } = await anexar()
    const ao_vivo = { node: "n2", status: "log", kind: "stdout", extra: { lines: ["z"] }, timestamp: 9 }
    act(() => { ws.onmessage?.(quadro([ao_vivo])) })
    act(() => { runPendingFrames() })

    const estado = useWorkflowExecutionStore.getState()
    expect(estado.events).toHaveLength(5)
    expect(estado.events.flatMap(e => e.lines ?? [])).toEqual(["a", "b", "z"])
    view.unmount()
  })

  it("o replay de um run longo mantém o início e os grupos de subfluxo", async () => {
    // The server keeps only the last 5000 events: a long run's replay no longer
    // carries the start or the sub-workflow's first events.
    const store = useWorkflowExecutionStore.getState()
    store.startExecution(canvasNodes.map(n => ({ ...n, status: "idle" })) as unknown as INodeStatusWorkFlow[])
    store.setTaskId(RUN)
    store.appendEvents([
      { node: "sub", status: "started", kind: "lifecycle", timestamp: 1, extra: { subworkflow_parent_node: "n1" } },
      ...historico.slice(1),
    ].map(toRunEvent))
    const antes = useWorkflowExecutionStore.getState()
    expect(antes.runStartedTs).toBe(1_000)
    expect(antes.subflowRoots.has("n1")).toBe(true)

    const { view, ws } = await anexar()
    // The replay starts at timestamp 3: the first two aged out of the history.
    act(() => { ws.onmessage?.(quadro(historico.slice(2))) })
    act(() => { runPendingFrames() })

    const estado = useWorkflowExecutionStore.getState()
    expect(estado.events).toHaveLength(2)
    expect(estado.runStartedTs).toBe(1_000)
    expect(estado.subflowRoots.has("n1")).toBe(true)
    view.unmount()
  })

  // ── 9. Reconciling one run never closes another ─────────────────────────

  it("reconciliar o run X depois de trocar para o run Y não encerra Y", async () => {
    const { view, ws } = await anexar()
    // X dropped and its reconciliation is waiting on a slow API.
    type Detalhe = { data: { status: string } }
    let responder: (v: Detalhe) => void = () => {}
    getRunDetail.mockImplementationOnce(() => new Promise<Detalhe>(r => { responder = r }))
    await act(async () => { ws.cairDoServidor(1006) })
    expect(getRunDetail).toHaveBeenCalledTimes(1)

    // Meanwhile the user opens workflow B, whose live run Y is re-attached.
    currentWorkflow = "wf-b"
    runsByWorkflow["wf-b"] = [{ run_id: "run-y", status: "running" }]
    view.rerender()
    await waitFor(() => expect(FakeSocket.abertos.at(-1)?.url).toContain("run-y"))

    // X's answer: finished. It is about X, not about the panel on screen.
    await act(async () => { responder({ data: { status: "success" } }) })

    const estado = useWorkflowExecutionStore.getState()
    expect(estado.viewingRunId).toBe("run-y")
    expect(estado.isExecuting).toBe(true)
    expect(RUN_TERMINAL.has(estado.statusWorkflow?.status ?? "")).toBe(false)
    // Nor does anything reconnect to X.
    expect(FakeSocket.abertos.filter(s => s.url.endsWith(`/${RUN}`))).toHaveLength(1)

    delete runsByWorkflow["wf-b"]
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
