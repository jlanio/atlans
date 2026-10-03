"use client"

import { useEffect } from "react"
import { useStore } from "@xyflow/react"
import { useCanvasViewStore } from "@/app/stores/canvasViewStore"
import { buildFocusCss } from "./utils/focus-css"

/** Applies the path highlight and the zoom level of detail to the canvas.
 *
 * It draws nothing: it only maintains the mode classes on the `.react-flow`
 * container and the stylesheet with the allow-list of the focused path. It's the
 * only component that re-renders when the focus or the zoom changes — no node or
 * edge is reconciled. Render as a child of `<ReactFlow>`.
 */
const CanvasViewLayer = () => {

  const domNode = useStore(s => s.domNode)

  const focusNodeId = useCanvasViewStore(s => s.focusNodeId)
  const focusNodeIds = useCanvasViewStore(s => s.focusNodeIds)
  const focusEdgeIds = useCanvasViewStore(s => s.focusEdgeIds)
  const lod = useCanvasViewStore(s => s.lod)

  // Deleting the focused node (clicking the trash can on the node toolbar also pins
  // the highlight, because it bubbles up to `onNodeClick`) would leave the canvas
  // stuck half-faded around an anchor that no longer exists. The selector returns
  // a boolean, so it only re-renders when the answer changes.
  const anchorExists = useStore(s => focusNodeId === null || s.nodeLookup.has(focusNodeId))

  useEffect(() => {
    if (!anchorExists) useCanvasViewStore.getState().clearFocus()
  }, [anchorExists])

  useEffect(() => {
    if (!domNode) return
    domNode.classList.toggle("rf-focus", focusNodeId !== null)
  }, [domNode, focusNodeId])

  useEffect(() => {
    if (!domNode) return
    const className = `rf-lod-${lod}`
    domNode.classList.add(className)
    return () => domNode.classList.remove(className)
  }, [domNode, lod])

  return <style>{buildFocusCss(focusNodeIds, focusEdgeIds, focusNodeId)}</style>
}

export default CanvasViewLayer
