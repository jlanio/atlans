"use client"

import { useReactFlow, MiniMap, type Edge } from "@xyflow/react"
import { useState, useCallback } from "react"
import { TbZoomIn, TbZoomOut, TbFocus2, TbMap, TbLayoutDistributeVertical, TbArrowBackUp, TbArrowForwardUp, TbRoute } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { cn } from "@/lib/utils"
import { INodeContext } from "@/context/useFlowContext"
import { useRunDockHeight } from "@/app/stores/runPanelStore"
import { useCanvasViewStore } from "@/app/stores/canvasViewStore"
import { computeAutoLayout } from "./utils/auto-layout"
import { LAYER_ABOVE_CANVAS } from "./canvas-layers"
import { useCanvasReadOnly } from "./canvas-interaction"

// 44px is the recommended minimum touch target (iOS HIG and Material). On desktop
// it stays 32px: with a fine pointer the bigger button only steals canvas area.
const BUTTON = "h-11 w-11 sm:h-8 sm:w-8"

interface CanvasToolbarProps {
  onUndo?: () => void
  onRedo?: () => void
  canUndo?: boolean
  canRedo?: boolean
  onSaveSnapshot?: () => void
}

const CanvasToolbar = ({ onUndo, onRedo, canUndo, canRedo, onSaveSnapshot }: CanvasToolbarProps) => {
  // Imperative read: the graph is only used inside "Organizar nós". Subscribing to
  // `useNodes()`/`useEdges()` reconciled the 9 buttons and the minimap on every
  // pointermove of a drag, and also recreated `handleAutoLayout` per frame.
  const { zoomIn, zoomOut, fitView, setNodes, getNodes, getEdges } = useReactFlow<INodeContext, Edge>()
  const [minimapOpen, setMinimapOpen] = useState(false)
  const readOnly = useCanvasReadOnly()
  const focusEnabled = useCanvasViewStore(s => s.focusEnabled)
  const toggleFocusEnabled = useCanvasViewStore(s => s.toggleFocusEnabled)
  // Rises together with the run panel dock — anchored at a fixed `bottom-4`,
  // the zoom toolbar and the minimap sat under the panel's bar.
  const dockHeight = useRunDockHeight()

  const handleAutoLayout = useCallback(() => {
    // Two snapshots: the first lets Ctrl+Z go back to the manual layout; the
    // second prevents the next edit from being merged with the layout step.
    // The second has to go in the setTimeout because `saveSnapshot` reads
    // `getNodes()` at call time — before the commit it would capture the old positions.
    onSaveSnapshot?.()

    const positions = computeAutoLayout(getNodes(), getEdges())
    setNodes(prev => prev.map(node => ({
      ...node,
      position: positions.get(node.id) ?? node.position,
    })))

    setTimeout(() => {
      fitView({ padding: 0.1, duration: 400 })
      onSaveSnapshot?.()
    }, 50)
  }, [getNodes, getEdges, setNodes, fitView, onSaveSnapshot])

  return (
    <>
      {/* Minimap */}
      {minimapOpen && (
        <MiniMap
          className="!right-4 !rounded-lg !border !border-border !shadow-md"
          // Colors derived from the tokens instead of raw hex: they follow dark/light
          // on their own. ReactFlow applies `nodeColor` as an inline style `fill`
          // and `maskColor` as a CSS custom property — both resolve `var()`/
          // `color-mix()`. Node = neutral surface; mask = faded background.
          nodeColor="var(--muted)"
          maskColor="color-mix(in oklab, var(--background) 55%, transparent)"
          style={{ zIndex: 10, bottom: dockHeight + 48 }}
        />
      )}

      {/* Floating toolbar.
          On the phone only the NAVIGATION controls remain. The nine stacked
          buttons added up to ~336px of height — half the usable screen — and at
          32px they fell well short of the 44px touch target. Undo, redo and
          organize go because the canvas there doesn't edit; the path highlight
          goes because it's triggered by hover, which doesn't exist on touch. */}
      <div
        data-canvas-chrome=""
        className={`${LAYER_ABOVE_CANVAS} right-2 sm:right-4 pr-safe flex flex-col gap-1.5 transition-[bottom] duration-150`}
        style={{ bottom: dockHeight + 16 }}
      >
        {!readOnly && (
          <>
            <Button
              variant="outline"
              size="icon"
              onClick={onUndo}
              disabled={!canUndo}
              title="Desfazer (Ctrl+Z)"
              className={BUTTON}
            >
              <TbArrowBackUp size={15} />
            </Button>

            <Button
              variant="outline"
              size="icon"
              onClick={onRedo}
              disabled={!canRedo}
              title="Refazer (Ctrl+Y)"
              className={BUTTON}
            >
              <TbArrowForwardUp size={15} />
            </Button>

            <div className="h-px bg-border mx-1" />

            <Button
              variant="outline"
              size="icon"
              onClick={handleAutoLayout}
              title="Organizar nós automaticamente"
              className={BUTTON}
            >
              <TbLayoutDistributeVertical size={15} />
            </Button>

            <Button
              variant="outline"
              size="icon"
              onClick={toggleFocusEnabled}
              title={focusEnabled ? "Desativar realce de caminho (F)" : "Realçar caminho ao passar o mouse (F)"}
              className={cn(BUTTON, focusEnabled && "border-primary text-primary")}
            >
              <TbRoute size={15} />
            </Button>
          </>
        )}

        <Button
          variant="outline"
          size="icon"
          onClick={() => setMinimapOpen(v => !v)}
          title={minimapOpen ? "Fechar minimapa" : "Abrir minimapa"}
          className={cn(BUTTON, minimapOpen && "border-primary text-primary")}
        >
          <TbMap size={17} />
        </Button>

        <div className="h-px bg-border mx-1" />

        <Button
          variant="outline"
          size="icon"
          onClick={() => fitView({ padding: 0.1, duration: 400 })}
          title="Ajustar à tela"
          className={BUTTON}
        >
          <TbFocus2 size={17} />
        </Button>

        <Button
          variant="outline"
          size="icon"
          onClick={() => zoomIn({ duration: 200 })}
          title="Zoom in"
          className={BUTTON}
        >
          <TbZoomIn size={17} />
        </Button>

        <Button
          variant="outline"
          size="icon"
          onClick={() => zoomOut({ duration: 200 })}
          title="Zoom out"
          className={BUTTON}
        >
          <TbZoomOut size={17} />
        </Button>
      </div>
    </>
  )
}

export default CanvasToolbar
