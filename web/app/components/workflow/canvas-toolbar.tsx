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
import { CAMADA_SOBRE_O_CANVAS } from "./canvas-layers"
import { useCanvasReadOnly } from "./canvas-interaction"

// 44px é o alvo de toque mínimo recomendado (iOS HIG e Material). No desktop
// segue 32px: com ponteiro fino o botão maior só rouba área do canvas.
const BOTAO = "h-11 w-11 sm:h-8 sm:w-8"

interface CanvasToolbarProps {
  onUndo?: () => void
  onRedo?: () => void
  canUndo?: boolean
  canRedo?: boolean
  onSaveSnapshot?: () => void
}

const CanvasToolbar = ({ onUndo, onRedo, canUndo, canRedo, onSaveSnapshot }: CanvasToolbarProps) => {
  // Leitura imperativa: o grafo só é usado dentro do "Organizar nós". Assinar
  // `useNodes()`/`useEdges()` reconciliava os 9 botões e o minimapa a cada
  // pointermove de um arraste, e ainda recriava `handleAutoLayout` por quadro.
  const { zoomIn, zoomOut, fitView, setNodes, getNodes, getEdges } = useReactFlow<INodeContext, Edge>()
  const [minimapOpen, setMinimapOpen] = useState(false)
  const somenteLeitura = useCanvasReadOnly()
  const focusEnabled = useCanvasViewStore(s => s.focusEnabled)
  const toggleFocusEnabled = useCanvasViewStore(s => s.toggleFocusEnabled)
  // Sobe junto com o dock do painel de execução — ancorados em `bottom-4` fixo,
  // a toolbar de zoom e o minimapa ficavam por baixo da barra do painel.
  const dockHeight = useRunDockHeight()

  const handleAutoLayout = useCallback(() => {
    // Dois snapshots: o primeiro deixa o Ctrl+Z voltar ao layout manual; o
    // segundo impede que a próxima edição seja mesclada com o passo de layout.
    // O segundo precisa ir no setTimeout porque `saveSnapshot` lê `getNodes()`
    // no momento da chamada — antes do commit ele capturaria as posições antigas.
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
          // Cores derivadas dos tokens em vez de hex cru: seguem dark/light
          // sozinhas. O ReactFlow aplica `nodeColor` como `fill` de estilo inline
          // e `maskColor` como custom property CSS — ambos resolvem `var()`/
          // `color-mix()`. Nó = superfície neutra; máscara = fundo esmaecido.
          nodeColor="var(--muted)"
          maskColor="color-mix(in oklab, var(--background) 55%, transparent)"
          style={{ zIndex: 10, bottom: dockHeight + 48 }}
        />
      )}

      {/* Toolbar flutuante.
          No telefone sobram só os controles de NAVEGAÇÃO. Os nove botões
          empilhados somavam ~336px de altura — metade da tela útil — e a 32px
          ficavam bem abaixo do alvo de toque de 44px. Desfazer, refazer e
          organizar saem porque o canvas ali não edita; o realce de caminho sai
          porque é acionado por hover, que não existe no toque. */}
      <div
        data-canvas-chrome=""
        className={`${CAMADA_SOBRE_O_CANVAS} right-2 sm:right-4 pr-safe flex flex-col gap-1.5 transition-[bottom] duration-150`}
        style={{ bottom: dockHeight + 16 }}
      >
        {!somenteLeitura && (
          <>
            <Button
              variant="outline"
              size="icon"
              onClick={onUndo}
              disabled={!canUndo}
              title="Desfazer (Ctrl+Z)"
              className={BOTAO}
            >
              <TbArrowBackUp size={15} />
            </Button>

            <Button
              variant="outline"
              size="icon"
              onClick={onRedo}
              disabled={!canRedo}
              title="Refazer (Ctrl+Y)"
              className={BOTAO}
            >
              <TbArrowForwardUp size={15} />
            </Button>

            <div className="h-px bg-border mx-1" />

            <Button
              variant="outline"
              size="icon"
              onClick={handleAutoLayout}
              title="Organizar nós automaticamente"
              className={BOTAO}
            >
              <TbLayoutDistributeVertical size={15} />
            </Button>

            <Button
              variant="outline"
              size="icon"
              onClick={toggleFocusEnabled}
              title={focusEnabled ? "Desativar realce de caminho (F)" : "Realçar caminho ao passar o mouse (F)"}
              className={cn(BOTAO, focusEnabled && "border-primary text-primary")}
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
          className={cn(BOTAO, minimapOpen && "border-primary text-primary")}
        >
          <TbMap size={17} />
        </Button>

        <div className="h-px bg-border mx-1" />

        <Button
          variant="outline"
          size="icon"
          onClick={() => fitView({ padding: 0.1, duration: 400 })}
          title="Ajustar à tela"
          className={BOTAO}
        >
          <TbFocus2 size={17} />
        </Button>

        <Button
          variant="outline"
          size="icon"
          onClick={() => zoomIn({ duration: 200 })}
          title="Zoom in"
          className={BOTAO}
        >
          <TbZoomIn size={17} />
        </Button>

        <Button
          variant="outline"
          size="icon"
          onClick={() => zoomOut({ duration: 200 })}
          title="Zoom out"
          className={BOTAO}
        >
          <TbZoomOut size={17} />
        </Button>
      </div>
    </>
  )
}

export default CanvasToolbar
