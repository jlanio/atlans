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
    // O executor interrompe a task e não emite evento de término para o nó em
    // curso; sem tratar aqui ele giraria para sempre no canvas.
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
    // O botão Executar limpa o run anterior antes de disparar o novo. Quando
    // resetExecution zerava debugMode, o toggle apagava no exato clique em que
    // o debug deveria valer.
    const store = useWorkflowExecutionStore.getState()
    store.setDebugMode(true)
    useWorkflowExecutionStore.getState().resetExecution()
    expect(useWorkflowExecutionStore.getState().debugMode).toBe(true)
    expect(useWorkflowExecutionStore.getState().statusWorkflow).toBeNull()
  })
})
