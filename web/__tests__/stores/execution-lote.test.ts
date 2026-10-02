/**
 * O caminho quente do run: lote de eventos, índice por nó e ramos perdedores.
 *
 * Cada mensagem do WebSocket disparava três trabalhos proporcionais ao tamanho
 * do grafo (mapa de todos os nós, BFS sobre todas as arestas, cópia do array de
 * eventos). O que estes testes protegem é o inverso disso: uma cópia por lote,
 * um índice pronto na store e IDENTIDADE preservada quando nada mudou — é a
 * identidade que corta o re-render de nós e arestas.
 */
import { describe, it, expect, beforeEach } from "vitest"
import { Edge } from "@xyflow/react"
import { RunEvent, useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { INodeStatusWorkFlow } from "@/context/useFlowContext"

const T0 = 1_700_000_000_000

function no(id: string, status: INodeStatusWorkFlow["status"], extra: Partial<INodeStatusWorkFlow> = {}) {
  return { id, status, position: { x: 0, y: 0 }, data: {}, ...extra } as INodeStatusWorkFlow
}

function evento(index: number, over: Partial<RunEvent> = {}): RunEvent {
  return {
    seq: 0,
    ts: T0 + index,
    node: "a",
    kind: "lifecycle",
    level: "info",
    status: "completed",
    raw: {},
    ...over,
  }
}

describe("workflowExecutionStore — lote de eventos", () => {
  beforeEach(() => {
    useWorkflowExecutionStore.getState().resetExecution()
  })

  it("numera os eventos com um seq monotônico que sobrevive à rotação", () => {
    const store = useWorkflowExecutionStore.getState()
    store.appendEvents([evento(0), evento(1), evento(2)])
    expect(useWorkflowExecutionStore.getState().events.map(e => e.seq)).toEqual([0, 1, 2])

    // A rotação descarta stdout do MEIO da lista: as keys das linhas que
    // sobrevivem não podem mudar por causa disso.
    const stdout = Array.from({ length: 2_500 }, (_, i) => evento(i + 3, { kind: "stdout", status: "log" }))
    useWorkflowExecutionStore.getState().appendEvents(stdout)

    const events = useWorkflowExecutionStore.getState().events
    expect(events.length).toBeLessThanOrEqual(2_000)
    // Estritamente crescente e sem repetição.
    for (let i = 1; i < events.length; i++) {
      expect(events[i].seq).toBeGreaterThan(events[i - 1].seq)
    }
  })

  it("um lote grande respeita o teto com uma única passada", () => {
    const lote = Array.from({ length: 5_000 }, (_, i) => evento(i, { kind: "stdout", status: "log" }))
    useWorkflowExecutionStore.getState().appendEvents(lote)
    const state = useWorkflowExecutionStore.getState()
    expect(state.events.length).toBeLessThanOrEqual(2_000)
    expect(state.droppedEvents).toBeGreaterThan(0)
    expect(state.runStartedTs).toBe(T0)
  })

  it("o replay histórico usa o mesmo teto do caminho ao vivo", () => {
    // O endpoint devolve até 5000 eventos; renderizá-los todos travava a aba.
    const events = Array.from({ length: 5_000 }, (_, i) => evento(i, { kind: "stdout", status: "log" }))
    useWorkflowExecutionStore.getState().loadHistoricalEvents("run-1", events)
    const state = useWorkflowExecutionStore.getState()
    expect(state.events.length).toBeLessThanOrEqual(2_000)
    expect(state.droppedEvents).toBeGreaterThan(0)
    expect(state.events[0].seq).toBe(0)
    // O início do run continua sendo o do PRIMEIRO evento, não o do sobrevivente
    // mais antigo — senão todos os offsets "+Xs" do painel se deslocavam.
    expect(state.runStartedTs).toBe(T0)
  })

  it("guarda o desfecho do run a O(1), sem reconstruir a linha do tempo", () => {
    useWorkflowExecutionStore.getState().appendEvents([
      evento(0),
      evento(1, { node: "__workflow_complete__", status: "failed", duration_ms: 1234, message: "estourou" }),
    ])
    expect(useWorkflowExecutionStore.getState().runOutcome).toEqual({
      status: "failed",
      durationMs: 1234,
      error: "estourou",
      category: null,
      retryable: null,
    })
  })
})

describe("workflowExecutionStore — índice por nó e ramos perdedores", () => {
  beforeEach(() => {
    useWorkflowExecutionStore.getState().resetExecution()
  })

  it("indexa os nós por id já no startExecution", () => {
    useWorkflowExecutionStore.getState().startExecution([no("a", "idle"), no("b", "idle")])
    const { statusById } = useWorkflowExecutionStore.getState()
    expect(statusById.get("a")?.status).toBe("idle")
    expect(statusById.get("b")?.status).toBe("idle")
  })

  it("o índice aponta para o MESMO objeto do nó não alterado", () => {
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([no("a", "idle"), no("b", "idle")])
    const nodes = useWorkflowExecutionStore.getState().statusWorkflow!.nodes
    const bAntes = useWorkflowExecutionStore.getState().statusById.get("b")

    // Só "a" muda; "b" é devolvido por identidade, como faz o flush do WS.
    const atualizados = nodes.map(n => (n.id === "a" ? { ...n, status: "started" as const } : n))
    useWorkflowExecutionStore.getState().updateNodeStatuses(atualizados, [])

    // É isto que faz o seletor por id do card de "b" não re-renderizar.
    expect(useWorkflowExecutionStore.getState().statusById.get("b")).toBe(bAntes)
    expect(useWorkflowExecutionStore.getState().statusById.get("a")?.status).toBe("started")
  })

  it("reaproveita os Sets de ramo perdedor quando nenhum branch_result mudou", () => {
    const arestas: Edge[] = [
      { id: "e1", source: "cond", target: "x", sourceHandle: "true" },
      { id: "e2", source: "cond", target: "y", sourceHandle: "false" },
      { id: "e3", source: "y", target: "z" },
    ]
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([no("cond", "idle"), no("x", "idle"), no("y", "idle"), no("z", "idle")])

    const decidido = [
      no("cond", "completed", { branch_result: true }),
      no("x", "idle"), no("y", "idle"), no("z", "idle"),
    ]
    useWorkflowExecutionStore.getState().updateNodeStatuses(decidido, arestas)
    const primeiros = useWorkflowExecutionStore.getState()
    // O ramo "false" perdeu: a aresta e2 e tudo que ela alcança.
    expect([...primeiros.losingEdgeIds!].sort()).toEqual(["e2", "e3"])
    expect([...primeiros.losingNodeIds!].sort()).toEqual(["y", "z"])

    // Um evento qualquer depois disso (um print, o término de outro nó) não
    // pode recriar os Sets: recriá-los re-renderizava todo nó e toda aresta.
    useWorkflowExecutionStore.getState().updateNodeStatuses(
      decidido.map(n => (n.id === "x" ? { ...n, status: "completed" as const } : n)),
      arestas,
    )
    const depois = useWorkflowExecutionStore.getState()
    expect(depois.losingNodeIds).toBe(primeiros.losingNodeIds)
    expect(depois.losingEdgeIds).toBe(primeiros.losingEdgeIds)
  })

  it("recalcula quando a topologia muda durante o run", () => {
    const antes: Edge[] = [{ id: "e1", source: "cond", target: "y", sourceHandle: "false" }]
    const decidido = [no("cond", "completed", { branch_result: true }), no("y", "idle")]
    useWorkflowExecutionStore.getState().startExecution([no("cond", "idle"), no("y", "idle")])
    useWorkflowExecutionStore.getState().updateNodeStatuses(decidido, antes)
    expect([...useWorkflowExecutionStore.getState().losingEdgeIds!]).toEqual(["e1"])

    // Aresta apagada: o curto-circuito por assinatura não pode segurar o
    // resultado velho só porque nenhum Conditional decidiu de novo.
    useWorkflowExecutionStore.getState().updateNodeStatuses(decidido, [])
    expect([...useWorkflowExecutionStore.getState().losingEdgeIds!]).toEqual([])
  })
})
