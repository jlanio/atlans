import { useCallback, useEffect, useRef } from "react"
import { Edge, useStoreApi, type NodeMouseHandler } from "@xyflow/react"
import { INodeContext } from "@/context/useFlowContext"
import { useCanvasViewStore } from "@/app/stores/canvasViewStore"
import { FocusGraph, buildFocusGraph, collectPath } from "@/app/components/workflow/utils/graph-traversal"

/** Delay before highlighting — avoids flicker when dragging the cursor across the canvas. */
const ENTER_DELAY = 90
/** Delay before clearing — asymmetric on purpose: leaving too fast makes the
 *  graph flicker when crossing the border between two neighboring cards. */
const LEAVE_DELAY = 140

/**
 * Path highlight: hovering over a node highlights everything that feeds it and
 * everything it feeds; clicking pins the highlight until a click on the canvas
 * or pressing Escape. `F` toggles the mode.
 *
 * Called only once in the canvas root component — not per node.
 *
 * PERF: the four handlers have a stable identity forever. They are passed to
 * `<ReactFlow>`, and `NodeRenderer` is `memo` receiving them as props — a new
 * handler on every render would re-render ALL nodes on the canvas. That is why
 * edges are read from the store at event time (via `getState()`) instead of
 * via `useEdges()`: nothing here enters the dependency list.
 */
export function useCanvasFocus() {

  const store = useStoreApi()
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const graphCache = useRef<{ source: Edge[]; graph: FocusGraph } | null>(null)

  const schedule = useCallback((delay: number, run: () => void) => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(run, delay)
  }, [])

  const cancel = useCallback(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = null
  }, [])

  useEffect(() => cancel, [cancel])

  const focus = useCallback((nodeId: string, origin: "hover" | "pin") => {
    const edges = store.getState().edges
    // Memo by array identity: the graph is only rebuilt when the topology actually
    // changes, not on every hover.
    if (graphCache.current?.source !== edges) {
      graphCache.current = { source: edges, graph: buildFocusGraph(edges) }
    }

    const { nodes, edges: touched } = collectPath(graphCache.current.graph, nodeId)
    useCanvasViewStore.getState().applyFocus(nodeId, origin, nodes, touched)
  }, [store])

  const onNodeMouseEnter = useCallback<NodeMouseHandler<INodeContext>>((event, node) => {
    const { focusEnabled, focusOrigin } = useCanvasViewStore.getState()
    if (!focusEnabled) return
    // The pin is deliberate — hovering over something does not replace it.
    if (focusOrigin === "pin") return
    // Dragging a node or pulling a connection: dimming the graph gets in the way of aiming.
    if (event.buttons !== 0) return
    if (store.getState().connection.inProgress) return

    schedule(ENTER_DELAY, () => focus(node.id, "hover"))
  }, [focus, schedule, store])

  const onNodeMouseLeave = useCallback<NodeMouseHandler<INodeContext>>(() => {
    schedule(LEAVE_DELAY, () => useCanvasViewStore.getState().clearFocus("hover"))
  }, [schedule])

  /** Composed with the canvas's existing click handler — it only toggles the pin. */
  const onNodeClick = useCallback<NodeMouseHandler<INodeContext>>((_, node) => {
    const { focusEnabled, focusNodeId, focusOrigin, clearFocus } = useCanvasViewStore.getState()
    if (!focusEnabled) return

    cancel()

    if (focusOrigin === "pin" && focusNodeId === node.id) clearFocus("pin")
    else focus(node.id, "pin")
  }, [cancel, focus])

  const onPaneClick = useCallback(() => {
    cancel()
    useCanvasViewStore.getState().clearFocus("pin")
  }, [cancel])

  // Escape releases the pin; F toggles the mode. Same text-field guard used by
  // the undo/redo shortcuts.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null
      const tag = target?.tagName
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target?.isContentEditable) return
      if (event.ctrlKey || event.metaKey || event.altKey) return

      if (event.key === "Escape") {
        useCanvasViewStore.getState().clearFocus("pin")
        return
      }

      // No `preventDefault`: a bare letter outside a text field has no default
      // action to cancel, and canceling it would break the typeahead of
      // components like Radix's Select.
      if (event.key === "f" || event.key === "F") {
        useCanvasViewStore.getState().toggleFocusEnabled()
      }
    }

    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  return { onNodeMouseEnter, onNodeMouseLeave, onNodeClick, onPaneClick }
}
