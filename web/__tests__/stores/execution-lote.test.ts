/**
 * The run's hot path: event batch, per-node index and losing branches.
 *
 * Every WebSocket message triggered three jobs proportional to the size of
 * the graph (a map of all nodes, a BFS over all edges, a copy of the events
 * array). What these tests protect is the inverse: one copy per batch, a
 * ready index in the store and IDENTITY preserved when nothing changed — it is
 * identity that cuts the re-render of nodes and edges.
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

    // Rotation drops stdout from the MIDDLE of the list: the keys of the lines
    // that survive must not change because of it.
    const stdout = Array.from({ length: 2_500 }, (_, i) => evento(i + 3, { kind: "stdout", status: "log" }))
    useWorkflowExecutionStore.getState().appendEvents(stdout)

    const events = useWorkflowExecutionStore.getState().events
    expect(events.length).toBeLessThanOrEqual(2_000)
    // Strictly increasing and without repeats.
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
    // The endpoint returns up to 5000 events; rendering them all froze the tab.
    const events = Array.from({ length: 5_000 }, (_, i) => evento(i, { kind: "stdout", status: "log" }))
    useWorkflowExecutionStore.getState().loadHistoricalEvents("run-1", events)
    const state = useWorkflowExecutionStore.getState()
    expect(state.events.length).toBeLessThanOrEqual(2_000)
    expect(state.droppedEvents).toBeGreaterThan(0)
    expect(state.events[0].seq).toBe(0)
    // The run's start is still that of the FIRST event, not of the oldest
    // survivor — otherwise every "+Xs" offset in the panel would shift.
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

    // Only "a" changes; "b" is returned by identity, as the WS flush does.
    const atualizados = nodes.map(n => (n.id === "a" ? { ...n, status: "started" as const } : n))
    useWorkflowExecutionStore.getState().updateNodeStatuses(atualizados, [])

    // This is what keeps the by-id selector of "b"'s card from re-rendering.
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
    // The "false" branch lost: edge e2 and everything it reaches.
    expect([...primeiros.losingEdgeIds!].sort()).toEqual(["e2", "e3"])
    expect([...primeiros.losingNodeIds!].sort()).toEqual(["y", "z"])

    // Any event after that (a print, another node finishing) must not
    // recreate the Sets: recreating them re-rendered every node and every edge.
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

    // Deleted edge: the signature short-circuit must not hold on to the
    // old result just because no Conditional decided again.
    useWorkflowExecutionStore.getState().updateNodeStatuses(decidido, [])
    expect([...useWorkflowExecutionStore.getState().losingEdgeIds!]).toEqual([])
  })
})
