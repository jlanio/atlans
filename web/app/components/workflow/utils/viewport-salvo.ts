import type { Viewport } from "@xyflow/react"

/** Tolerances below which two viewports are "the same": d3-zoom floating-point
 *  noise does not turn into a PUT. Half a pixel and a thousandth of zoom are
 *  not distinguishable on screen. */
const TOLERANCIA_PX = 0.5
const TOLERANCIA_ZOOM = 0.001

/** Viewport that came from the saved `definition` and can be restored. */
export function viewportSalvoValido(v: Partial<Viewport> | null | undefined): v is Viewport {
  if (!v) return false
  return [v.x, v.y, v.zoom].every(n => typeof n === "number" && Number.isFinite(n))
}

export function viewportsIguais(a: Viewport | null | undefined, b: Viewport | null | undefined): boolean {
  if (!a || !b) return a === b
  return Math.abs(a.x - b.x) < TOLERANCIA_PX
    && Math.abs(a.y - b.y) < TOLERANCIA_PX
    && Math.abs(a.zoom - b.zoom) < TOLERANCIA_ZOOM
}
