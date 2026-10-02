import { useCallback, useEffect, useRef } from "react"
import { useOnViewportChange, useStoreApi } from "@xyflow/react"
import { LodTier, useCanvasViewStore } from "@/app/stores/canvasViewStore"

/**
 * Fronteiras com histerese: cada degrau só é abandonado ao cruzar um limiar
 * mais distante do que o que o fez entrar. Sem isso, ficar oscilando em cima
 * de um limiar faz o canvas piscar.
 */
const FAR_ENTER = 0.42
const FAR_EXIT = 0.50
const NEAR_ENTER = 0.80
const NEAR_EXIT = 0.72

export function classifyZoom(zoom: number, current: LodTier): LodTier {
  if (current === "far") return zoom >= FAR_EXIT ? (zoom >= NEAR_ENTER ? "near" : "mid") : "far"
  if (current === "near") return zoom < NEAR_EXIT ? (zoom < FAR_ENTER ? "far" : "mid") : "near"
  // mid
  if (zoom < FAR_ENTER) return "far"
  if (zoom >= NEAR_ENTER) return "near"
  return "mid"
}

/**
 * Publica o degrau de detalhe conforme o zoom.
 *
 * Usa `useOnViewportChange` porque ele grava o callback na store do React Flow
 * e é chamado direto do handler de pan/zoom — sem re-render. `useViewport()`
 * re-renderizaria a cada frame, e `useStore(s => s.transform[2])` a cada frame
 * de zoom. A comparação com `tierRef` é o filtro que reduz uma sessão inteira
 * de zoom a meia dúzia de atualizações de estado.
 */
export function useZoomLod() {

  const store = useStoreApi()
  const tier = useRef<LodTier>(useCanvasViewStore.getState().lod)

  const publish = useCallback((zoom: number) => {
    const next = classifyZoom(zoom, tier.current)
    if (next === tier.current) return
    tier.current = next
    useCanvasViewStore.getState().setLod(next)
  }, [])

  // `defaultViewport` não passa pelo d3-zoom, então a abertura do canvas num
  // zoom salvo não emitiria nenhum evento — classifica uma vez na montagem.
  useEffect(() => { publish(store.getState().transform[2]) }, [publish, store])

  useOnViewportChange({ onChange: ({ zoom }) => publish(zoom) })
}
