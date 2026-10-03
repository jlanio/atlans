import { describe, it, expect, beforeEach } from "vitest"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { INodeStatusWorkFlow } from "@/context/useFlowContext"

function node(id: string, status: INodeStatusWorkFlow["status"]) {
  return { id, status, position: { x: 0, y: 0 }, data: {} } as INodeStatusWorkFlow
}

describe("workflowExecutionStore — cancelamento e modo debug", () => {
  beforeEach(() => {
    useWorkflowExecutionStore.getState().resetExecution()
    useWorkflowExecutionStore.getState().setDebugMode(false)
  })

  it("cancelar tira do ar o nó que estava em execução", () => {
    // The executor interrupts the task and doesn't emit an end event for the
    // node in progress; without handling it here it would spin forever on the canvas.
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([node("a", "idle"), node("b", "idle")])
    store.updateNodeStatuses([node("a", "completed"), node("b", "started")], [])

    useWorkflowExecutionStore.getState().completeExecution("cancelled", [
      node("a", "completed"), node("b", "started"),
    ], [])

    const nodes = useWorkflowExecutionStore.getState().statusWorkflow!.nodes
    expect(nodes.find(n => n.id === "a")!.status).toBe("completed")
    expect(nodes.find(n => n.id === "b")!.status).toBe("idle")
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(false)
  })

  it("conclusão normal não mexe no estado dos nós", () => {
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([node("a", "idle")])
    useWorkflowExecutionStore.getState().completeExecution("completed", [node("a", "completed")], [])
    expect(useWorkflowExecutionStore.getState().statusWorkflow!.nodes[0].status).toBe("completed")
  })

  it("limpar o run preserva o modo debug", () => {
    // The Run button clears the previous run before firing the new one. When
    // resetExecution zeroed debugMode, the toggle switched off on the very
    // click in which debug was supposed to take effect.
    const store = useWorkflowExecutionStore.getState()
    store.setDebugMode(true)
    useWorkflowExecutionStore.getState().resetExecution()
    expect(useWorkflowExecutionStore.getState().debugMode).toBe(true)
    expect(useWorkflowExecutionStore.getState().statusWorkflow).toBeNull()
  })
})
