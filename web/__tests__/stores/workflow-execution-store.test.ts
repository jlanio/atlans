import { describe, it, expect, beforeEach } from "vitest"
import { RunEvent, useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"

const T0 = 1_700_000_000_000

function event(kind: RunEvent["kind"], index: number): RunEvent {
  return {
    seq: 0,
    ts: T0 + index,
    node: `n${index % 5}`,
    kind,
    level: "info",
    status: kind === "stdout" ? "log" : "completed",
    message: `linha ${index}`,
    raw: {},
  }
}

describe("workflowExecutionStore — rotação de eventos", () => {
  beforeEach(() => {
    useWorkflowExecutionStore.getState().resetExecution()
  })

  it("fixa o início do run no primeiro evento e não o move depois", () => {
    const store = useWorkflowExecutionStore.getState()
    store.appendEvents([event("lifecycle", 0)])
    store.appendEvents([event("stdout", 1)])
    expect(useWorkflowExecutionStore.getState().runStartedTs).toBe(T0)
  })

  it("preserva eventos de ciclo de vida ao estourar o teto, descartando stdout", () => {
    const store = useWorkflowExecutionStore.getState()
    // 40 de ciclo de vida no começo, depois muito stdout até passar do teto.
    for (let i = 0; i < 40; i++) store.appendEvents([event("lifecycle", i)])
    for (let i = 40; i < 2_400; i++) store.appendEvents([event("stdout", i)])

    const state = useWorkflowExecutionStore.getState()
    const lifecycleKept = state.events.filter(e => e.kind === "lifecycle").length
    expect(lifecycleKept).toBe(40)
    expect(state.droppedEvents).toBeGreaterThan(0)
    expect(state.events.length).toBeLessThanOrEqual(2_000)
    // O início do run continua sendo o primeiro evento de verdade.
    expect(state.runStartedTs).toBe(T0)
  })

  it("cai no descarte cronológico quando não há stdout para liberar", () => {
    const store = useWorkflowExecutionStore.getState()
    for (let i = 0; i < 2_100; i++) store.appendEvents([event("lifecycle", i)])
    const state = useWorkflowExecutionStore.getState()
    expect(state.events.length).toBeLessThanOrEqual(2_000)
    expect(state.droppedEvents).toBeGreaterThan(0)
  })

  it("resetExecution zera eventos, contador de descarte e início do run", () => {
    const store = useWorkflowExecutionStore.getState()
    store.appendEvents([event("stdout", 0)])
    useWorkflowExecutionStore.getState().resetExecution()
    const state = useWorkflowExecutionStore.getState()
    expect(state.events).toHaveLength(0)
    expect(state.droppedEvents).toBe(0)
    expect(state.runStartedTs).toBeNull()
  })

  it("queda de conexão preserva os eventos já recebidos", () => {
    // failExecution (e não resetExecution) no fechamento inesperado: apagar o
    // log no momento em que a conexão cai é exatamente quando ele importa.
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([])
    store.appendEvents([event("lifecycle", 0)])
    useWorkflowExecutionStore.getState().failExecution()
    const state = useWorkflowExecutionStore.getState()
    expect(state.events).toHaveLength(1)
    expect(state.isExecuting).toBe(false)
    expect(state.wsState).toBe("closed")
  })
})
