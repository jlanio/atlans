/**
 * The snapshot must not reallocate everything on every window.
 *
 * `buildTimeline` is pure and creates a new `NodeRun` for each node on every
 * call. Since the panel rows are memoized by prop identity, this made ALL of
 * them re-render eight times per second even when a single node changed. And,
 * with the panel collapsed, that rebuild happened for nobody: the 34px bar only
 * needs counts and status.
 */
import { describe, it, expect, beforeEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"

import { useRunSnapshot } from "@/app/components/workflow/run-panel/use-run-snapshot"
import { RunEvent, useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { INodeStatusWorkFlow } from "@/context/useFlowContext"

const T0 = 1_700_000_000_000

function no(id: string, status: INodeStatusWorkFlow["status"]) {
  return { id, status, position: { x: 0, y: 0 }, data: { alias: `Nó ${id}` } } as INodeStatusWorkFlow
}

function evento(node: string, status: string, atMs = 0): RunEvent {
  return { seq: 0, ts: T0 + atMs, node, kind: "lifecycle", level: "info", status, raw: {} }
}

describe("useRunSnapshot — identidade e custo", () => {
  beforeEach(() => {
    useWorkflowExecutionStore.getState().resetExecution()
  })

  it("preserva a instância das linhas que não mudaram entre janelas", async () => {
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([no("a", "idle"), no("b", "idle")])
    store.appendEvents([evento("a", "started")])

    const { result, unmount } = renderHook(() => useRunSnapshot(true))
    await waitFor(() => expect(result.current.timeline.nodes).toHaveLength(2))
    const rowB = result.current.timeline.nodes.find(n => n.nodeId === "b")!

    act(() => {
      useWorkflowExecutionStore.getState().appendEvents([evento("a", "completed", 500)])
    })
    await waitFor(() => {
      expect(result.current.timeline.nodes.find(n => n.nodeId === "a")!.status).toBe("completed")
    })

    // "b" wasn't touched by any event: its row has to be the SAME object,
    // otherwise NodeRow's `memo` holds nothing back.
    expect(result.current.timeline.nodes.find(n => n.nodeId === "b")).toBe(rowB)
    unmount()
  })

  it("com a barra recolhida não monta a linha do tempo por evento", async () => {
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([no("a", "idle")])
    store.appendEvents([
      evento("a", "started"),
      { seq: 0, ts: T0 + 10, node: "a", kind: "stdout", level: "info", status: "log", lines: ["oi"], raw: {} },
    ])

    const { result, unmount } = renderHook(() => useRunSnapshot(false))
    // The summary still answers "what's happening": counts and status come
    // from the canvas's per-node state, without walking the events.
    expect(result.current.timeline.counts.total).toBe(1)
    expect(result.current.timeline.workflow.status).toBe("running")
    // Prints are a detail of the open panel — nobody draws them while it's closed.
    expect(result.current.timeline.totalPrints).toBe(0)
    unmount()
  })

  it("abrir o painel passa a entregar a linha do tempo completa", async () => {
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([no("a", "idle")])
    store.appendEvents([
      evento("a", "started"),
      { seq: 0, ts: T0 + 10, node: "a", kind: "stdout", level: "info", status: "log", lines: ["oi"], raw: {} },
    ])

    const { result, rerender, unmount } = renderHook(
      ({ aberto }: { aberto: boolean }) => useRunSnapshot(aberto),
      { initialProps: { aberto: false } },
    )
    expect(result.current.timeline.totalPrints).toBe(0)

    rerender({ aberto: true })
    await waitFor(() => expect(result.current.timeline.totalPrints).toBe(1))
    unmount()
  })
})
