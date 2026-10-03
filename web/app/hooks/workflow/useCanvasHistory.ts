import { useCallback, useRef, useEffect, useReducer } from "react"
import { Edge, useReactFlow } from "@xyflow/react"
import { INodeContext } from "@/context/useFlowContext"

interface Snapshot {
  nodes: INodeContext[]
  edges: Edge[]
}

const MAX_HISTORY = 50

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

  /** Saves the current state to history (discards future entries after the pointer). */
  const saveSnapshot = useCallback(() => {
    if (isTravelingRef.current) return

    const snapshot: Snapshot = {
      nodes: getNodes() as INodeContext[],
      edges: getEdges(),
    }

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
