/**
 * The WebSocket event envelope and the per-frame buffer.
 *
 * The server sends historical replay and the LIVE stream in the SAME format
 * (`{"type":"events","events":[...],"dropped":N}`), so what decides whether the run
 * is over is the batch's CONTENT — not the envelope. While the client relied on the
 * envelope, a run that finished with the tab in the background stayed stuck on
 * "Executando": `requestAnimationFrame` does not run in a hidden document, and
 * `completeExecution` and `ws.close()` live inside the flush.
 *
 * The tests below freeze rAF on purpose (exactly what the browser does with a
 * hidden tab) and demand the correct behavior from the hook without it.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { MAX_RUN_EVENTS, useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"

const RUN_A = "run-a"
const RUN_B = "run-b"

// --- Minimal environment around the hook ------------------------------------

let currentWorkflow = "wf-a"
const runsByWorkflow: Record<string, { run_id: string; status: string }[]> = {}

const canvasNodes = [
  { id: "n1", position: { x: 0, y: 0 }, data: {} },
  { id: "n2", position: { x: 0, y: 0 }, data: {} },
]

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: currentWorkflow }),
}))

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null }),
}))

vi.mock("@/app/hooks/workflow/useSaveWorkflow", () => ({
  useSaveWorkflow: () => ({ saveWorkflow: vi.fn(async () => ({ error: null })) }),
}))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getObservabilityRuns: vi.fn(async ({ workflow_id }: { workflow_id: string }) => ({
      data: { runs: runsByWorkflow[workflow_id] ?? [] },
    })),
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

/** Fake socket: keeps the handlers so the test can push frames. */
class FakeSocket {
  static abertos: FakeSocket[] = []
  onopen: (() => void) | null = null
  onmessage: ((ev: { data: string }) => void) | null = null
  onerror: ((err: unknown) => void) | null = null
  onclose: ((ev: { code: number }) => void) | null = null
  fechadoCom: number | null = null

  constructor(public url: string) {
    FakeSocket.abertos.push(this)
  }
  send() {}
  close(code = 1000) {
    this.fechadoCom = code
    this.onclose?.({ code })
  }
  entregar(frame: object) {
    this.onmessage?.({ data: JSON.stringify(frame) })
  }
}

/** rAF queue under the test's control — with no callback running, it is the
 *  hidden tab; running the queue by hand, it is the visible tab. */
const quadros = new Map<number, FrameRequestCallback>()
let nextFrame = 1

function runFrames() {
  const pendentes = [...quadros.entries()]
  quadros.clear()
  for (const [, cb] of pendentes) cb(performance.now())
}

async function importHook() {
  const mod = await import("@/app/hooks/workflow/useExecuteWorkflow")
  return mod.useExecuteWorkflow
}

function eventsFrame(events: object[], dropped = 0) {
  return dropped > 0 ? { type: "events", events, dropped } : { type: "events", events }
}

function nodeEvent(node: string, status: string, over: object = {}) {
  return { node, status, kind: "lifecycle", level: "info", timestamp: 1_700_000_000, ...over }
}

function endEvent(status = "completed") {
  return { node: "__workflow_complete__", status, kind: "lifecycle", level: "info", duration_ms: 1200, timestamp: 1_700_000_001 }
}

/** Mounts the hook already attached to a live run (the re-attach path). */
async function anexar(runId: string) {
  const useExecuteWorkflow = await importHook()
  const view = renderHook(() => useExecuteWorkflow())
  await waitFor(() => expect(FakeSocket.abertos.length).toBeGreaterThan(0))
  const ws = FakeSocket.abertos.find(s => s.url.endsWith(runId))!
  expect(ws).toBeDefined()
  return { view, ws }
}

describe("useExecuteWorkflow — envelope único de eventos", () => {
  beforeEach(() => {
    currentWorkflow = "wf-a"
    runsByWorkflow["wf-a"] = [{ run_id: RUN_A, status: "running" }]
    runsByWorkflow["wf-b"] = []
    FakeSocket.abertos = []
    quadros.clear()
    nextFrame = 1
    vi.stubGlobal("WebSocket", FakeSocket)
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      const id = nextFrame++
      quadros.set(id, cb)
      return id
    })
    vi.stubGlobal("cancelAnimationFrame", (id: number) => { quadros.delete(id) })
    useWorkflowExecutionStore.getState().resetExecution()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("um lote com __workflow_complete__ encerra o run na hora, sem esperar quadro", async () => {
    const { view, ws } = await anexar(RUN_A)

    act(() => {
      ws.entregar(eventsFrame([
        nodeEvent("n1", "started"),
        nodeEvent("n1", "completed", { duration_ms: 10 }),
        endEvent(),
      ]))
    })

    // No frame ran — this is the background-tab scenario.
    const estado = useWorkflowExecutionStore.getState()
    expect(estado.isExecuting).toBe(false)
    expect(estado.statusWorkflow?.status).toBe("completed")
    expect(estado.events).toHaveLength(3)
    expect(ws.fechadoCom).not.toBeNull()

    view.unmount()
  })

  it("os eventos comuns continuam agrupados por quadro (um flush por rAF)", async () => {
    const { view, ws } = await anexar(RUN_A)

    act(() => {
      ws.entregar(eventsFrame([nodeEvent("n1", "started")]))
      ws.entregar(eventsFrame([nodeEvent("n2", "started")]))
    })
    // Nothing in the store yet: per-frame grouping is what avoids a render
    // cycle of the whole canvas per message.
    expect(useWorkflowExecutionStore.getState().events).toHaveLength(0)
    expect(quadros.size).toBe(1)

    act(() => { runFrames() })
    expect(useWorkflowExecutionStore.getState().events).toHaveLength(2)

    view.unmount()
  })

  it("o `dropped` do frame entra em droppedEvents", async () => {
    const { view, ws } = await anexar(RUN_A)

    act(() => {
      ws.entregar(eventsFrame([nodeEvent("n1", "started")], 7))
      ws.entregar(eventsFrame([nodeEvent("n1", "completed")], 5))
    })

    // The server-side drop is what the user has no way to notice alone:
    // without this the panel claims to be complete with 12 lines missing.
    expect(useWorkflowExecutionStore.getState().droppedEvents).toBe(12)

    view.unmount()
  })

  it("com a aba oculta o buffer não passa do teto de eventos", async () => {
    const { view, ws } = await anexar(RUN_A)

    act(() => {
      for (let i = 0; i < MAX_RUN_EVENTS + 10; i++) {
        ws.entregar(eventsFrame([{ node: "n1", status: "log", kind: "stdout", level: "info", extra: { lines: [`linha ${i}`] } }]))
      }
    })

    // No frame ran; even so the batch was drained on its own when it hit the
    // ceiling — the store's rotation only acts AFTER the drain.
    expect(useWorkflowExecutionStore.getState().events.length).toBeGreaterThan(0)
    expect(useWorkflowExecutionStore.getState().events.length).toBeLessThanOrEqual(MAX_RUN_EVENTS)

    view.unmount()
  })

  it("esconder a aba drena o lote pendente", async () => {
    const { view, ws } = await anexar(RUN_A)

    act(() => { ws.entregar(eventsFrame([nodeEvent("n1", "started")])) })
    expect(useWorkflowExecutionStore.getState().events).toHaveLength(0)

    act(() => {
      Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true })
      document.dispatchEvent(new Event("visibilitychange"))
    })

    expect(useWorkflowExecutionStore.getState().events).toHaveLength(1)
    // The pending frame was canceled — otherwise the same batch would be applied twice.
    expect(quadros.size).toBe(0)

    Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true })
    view.unmount()
  })
})

describe("useExecuteWorkflow — isolamento entre runs", () => {
  beforeEach(() => {
    currentWorkflow = "wf-a"
    runsByWorkflow["wf-a"] = [{ run_id: RUN_A, status: "running" }]
    runsByWorkflow["wf-b"] = []
    FakeSocket.abertos = []
    quadros.clear()
    nextFrame = 1
    vi.stubGlobal("WebSocket", FakeSocket)
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      const id = nextFrame++
      quadros.set(id, cb)
      return id
    })
    vi.stubGlobal("cancelAnimationFrame", (id: number) => { quadros.delete(id) })
    useWorkflowExecutionStore.getState().resetExecution()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("mensagem atrasada do workflow A não cai na store do workflow B", async () => {
    const useExecuteWorkflow = await importHook()
    const view = renderHook(() => useExecuteWorkflow())
    await waitFor(() => expect(FakeSocket.abertos.length).toBe(1))
    const wsA = FakeSocket.abertos[0]

    // Workflow switch: /workflow/A → /workflow/B does NOT remount the component.
    currentWorkflow = "wf-b"
    await act(async () => {
      view.rerender()
      await Promise.resolve()
    })
    act(() => { useWorkflowExecutionStore.getState().resetExecution() })

    // Messages already queued in the event loop keep being delivered after
    // close(1000) — including the end of A's run, which closed B's panel
    // with "Concluído · 0 nós" for a workflow that never ran.
    act(() => {
      wsA.entregar(eventsFrame([nodeEvent("n1", "completed"), endEvent()]))
      runFrames()
    })

    const estado = useWorkflowExecutionStore.getState()
    expect(estado.events).toHaveLength(0)
    expect(estado.statusWorkflow).toBeNull()
    expect(estado.isExecuting).toBe(false)

    view.unmount()
  })

  it("desmontar descarta o lote pendente", async () => {
    const useExecuteWorkflow = await importHook()
    const view = renderHook(() => useExecuteWorkflow())
    await waitFor(() => expect(FakeSocket.abertos.length).toBe(1))
    const wsA = FakeSocket.abertos[0]

    act(() => { wsA.entregar(eventsFrame([nodeEvent("n1", "started")])) })
    view.unmount()

    act(() => { runFrames() })
    expect(useWorkflowExecutionStore.getState().events).toHaveLength(0)
  })
})
