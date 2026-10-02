"use client"

import { useEffect } from "react"
import { useStore } from "@xyflow/react"
import { useCanvasViewStore } from "@/app/stores/canvasViewStore"
import { buildFocusCss } from "./utils/focus-css"

/** Aplica ao canvas o realce de caminho e o nível de detalhe do zoom.
 *
 * Não desenha nada: só mantém as classes de modo no container `.react-flow` e
 * a folha de estilo com a allow-list do caminho em foco. É o único componente
 * que re-renderiza quando o foco ou o zoom mudam — nenhum nó ou aresta é
 * reconciliado. Renderizar como filho de `<ReactFlow>`.
 */
const CanvasViewLayer = () => {

  const domNode = useStore(s => s.domNode)

  const focusNodeId = useCanvasViewStore(s => s.focusNodeId)
  const focusNodeIds = useCanvasViewStore(s => s.focusNodeIds)
  const focusEdgeIds = useCanvasViewStore(s => s.focusEdgeIds)
  const lod = useCanvasViewStore(s => s.lod)

  // Excluir o nó em foco (o clique na lixeira da toolbar do nó também fixa o
  // realce, porque borbulha para `onNodeClick`) deixaria o canvas travado
  // meio-esmaecido em volta de uma âncora que não existe mais. O selector
  // devolve booleano, então só re-renderiza quando a resposta muda.
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
