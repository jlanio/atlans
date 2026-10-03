import { useCallback, useEffect, useRef } from "react"
import { useOnViewportChange, useStoreApi } from "@xyflow/react"
import { LodTier, useCanvasViewStore } from "@/app/stores/canvasViewStore"

/**
 * Boundaries with hysteresis: each tier is only left when crossing a threshold
 * farther away than the one that made it enter. Without this, hovering right on
 * top of a threshold makes the canvas flicker.
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
 * Publishes the detail tier according to the zoom.
 *
 * Uses `useOnViewportChange` because it stores the callback in the React Flow
 * store and is called straight from the pan/zoom handler — no re-render.
 * `useViewport()` would re-render on every frame, and `useStore(s => s.transform[2])`
 * on every zoom frame. The comparison with `tierRef` is the filter that reduces a
 * whole zoom session to half a dozen state updates.
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

  // `defaultViewport` does not go through d3-zoom, so opening the canvas at a
  // saved zoom would emit no event — classify once on mount.
  useEffect(() => { publish(store.getState().transform[2]) }, [publish, store])

  useOnViewportChange({ onChange: ({ zoom }) => publish(zoom) })
}
