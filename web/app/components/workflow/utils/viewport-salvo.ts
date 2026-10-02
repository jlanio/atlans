import type { Viewport } from "@xyflow/react"

/** Tolerâncias abaixo das quais dois viewports são "o mesmo": ruído de ponto
 *  flutuante do d3-zoom não vira PUT. Meio pixel e um milésimo de zoom não
 *  são distinguíveis na tela. */
const TOLERANCIA_PX = 0.5
const TOLERANCIA_ZOOM = 0.001

/** Viewport que veio da `definition` salva e que dá para restaurar. */
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
