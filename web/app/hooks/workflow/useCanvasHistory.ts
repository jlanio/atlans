import { useCallback, useRef, useEffect, useReducer } from "react"
import { Edge, useReactFlow } from "@xyflow/react"
import { INodeContext } from "@/context/useFlowContext"

interface Snapshot {
  nodes: INodeContext[]
  edges: Edge[]
}

const MAX_HISTORY = 50

/** Equal by reference or, failing that, by serialized content. */
function sameContent(a: unknown, b: unknown): boolean {
  if (a === b) return true
  try {
    return JSON.stringify(a) === JSON.stringify(b)
  } catch {
    return false
  }
}

/**
 * Same workflow on both sides: nodes with the same id, type, position and data;
 * edges with the same id, ends, handles and data. Selection, measured size and
 * the assistant's entrance classes are left out on purpose — they change with
 * nobody editing anything.
 */
function sameGraph(a: Snapshot, b: Snapshot): boolean {
  if (a.nodes.length !== b.nodes.length || a.edges.length !== b.edges.length) return false

  const nodesOfB = new Map(b.nodes.map(node => [node.id, node]))
  for (const node of a.nodes) {
    const other = nodesOfB.get(node.id)
    if (!other || other.type !== node.type) return false
    // Optional access: a node without a position must not make the history
    // throw — at worst, the step is recorded.
    if (other.position?.x !== node.position?.x || other.position?.y !== node.position?.y) return false
    if (!sameContent(other.data, node.data)) return false
  }

  const edgesOfB = new Map(b.edges.map(edge => [edge.id, edge]))
  for (const edge of a.edges) {
    const other = edgesOfB.get(edge.id)
    if (!other || other.source !== edge.source || other.target !== edge.target) return false
    // React Flow uses `null` for an anonymous handle and a loaded edge may carry
    // `undefined`: the same handle either way.
    if ((other.sourceHandle ?? null) !== (edge.sourceHandle ?? null)) return false
    if ((other.targetHandle ?? null) !== (edge.targetHandle ?? null)) return false
    if (!sameContent(other.data, edge.data)) return false
  }
  return true
}

/**
 * Undo/redo hook for the ReactFlow canvas.
 * - Call `saveSnapshot()` after each operation that should be undoable (add/remove node, etc.)
 * - Registers Ctrl+Z / Ctrl+Y automatically.
 */
export function useCanvasHistory() {
  const { getNodes, getEdges, setNodes, setEdges } = useReactFlow<INodeContext, Edge>()

  const history = useRef<Snapshot[]>([])
  const pointer = useRef(-1)  // -1 = no snapshot yet
  const isTravelingRef = useRef(false)  // evita salvar durante undo/redo

  // `history`/`pointer` are refs so the canvas does not re-render on every
  // snapshot, but `canUndo`/`canRedo` derive from them — without this bump the
  // toolbar buttons stayed stuck at `disabled` until something *else* re-rendered
  // the canvas.
  const [, bumpVersion] = useReducer((v: number) => v + 1, 0)

  /**
   * Saves the current state to history (discards future entries after the pointer).
   * `state` records one the caller has just handed to the canvas: until React
   * commits it, `getNodes()`/`getEdges()` still return the previous one.
   */
  const saveSnapshot = useCallback((state?: Snapshot) => {
    if (isTravelingRef.current) return

    const snapshot: Snapshot = state ?? {
      nodes: getNodes() as INodeContext[],
      edges: getEdges(),
    }

    // The canvas already IS the step under the pointer: nothing new to record.
    // This is what keeps undo/redo from writing over its own future. Restoring
    // goes through React Flow's setNodes/setEdges, which a controlled flow turns
    // into add/remove/replace changes — and the editor answers those with a
    // snapshot 300 ms later. By then `isTravelingRef` (reset on the next tick) no
    // longer held it back: the restored canvas went in as a new step, the redo
    // was discarded, and the next Ctrl+Z landed on that duplicate. Comparing
    // content instead of timing holds however late the snapshot arrives.
    const atPointer = history.current[pointer.current]
    if (atPointer && sameGraph(atPointer, snapshot)) return

    // Removes "future" snapshots (after undoing and then changing)
    history.current = history.current.slice(0, pointer.current + 1)
    history.current.push(snapshot)

    // Limits the history size
    if (history.current.length > MAX_HISTORY) {
      history.current = history.current.slice(-MAX_HISTORY)
    }

    pointer.current = history.current.length - 1
    bumpVersion()
  }, [getNodes, getEdges])

  /**
   * Resets the history with the CURRENT canvas state as baseline (pointer=0).
   * Call ONCE after a workflow is hydrated. Without a baseline, the history
   * starts empty (pointer=-1) and the first snapshot is the POST-edit state; since
   * `undo()` guards `pointer <= 0`, the FIRST edge edit (delete / from_key change)
   * got stuck and was never undone (F10). Resetting also keeps one workflow's
   * history from leaking into the next when switching workflows.
   */
  const captureBaseline = useCallback(() => {
    history.current = [{ nodes: getNodes() as INodeContext[], edges: getEdges() }]
    pointer.current = 0
    bumpVersion()
  }, [getNodes, getEdges])

  const undo = useCallback(() => {
    if (pointer.current <= 0) return
    pointer.current -= 1
    const snap = history.current[pointer.current]
    isTravelingRef.current = true
    setNodes(snap.nodes)
    setEdges(snap.edges)
    bumpVersion()
    setTimeout(() => { isTravelingRef.current = false }, 0)
  }, [setNodes, setEdges])

  const redo = useCallback(() => {
    if (pointer.current >= history.current.length - 1) return
    pointer.current += 1
    const snap = history.current[pointer.current]
    isTravelingRef.current = true
    setNodes(snap.nodes)
    setEdges(snap.edges)
    bumpVersion()
    setTimeout(() => { isTravelingRef.current = false }, 0)
  }, [setNodes, setEdges])

  const canUndo = pointer.current > 0
  const canRedo = pointer.current < history.current.length - 1

  // Registers global keyboard shortcuts on the canvas
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Ignores when focus is on an input/textarea
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement)?.isContentEditable) return

      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === "z") {
        e.preventDefault()
        undo()
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.shiftKey && e.key === "z"))) {
        e.preventDefault()
        redo()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [undo, redo])

  return { saveSnapshot, captureBaseline, undo, redo, canUndo, canRedo }
}
