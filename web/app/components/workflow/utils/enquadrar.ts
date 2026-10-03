// web/app/components/workflow/utils/enquadrar.ts
//
// When the canvas should move to follow the workflow being built.
//
// The decision is pure on purpose. React Flow's `fitView` is easy to call and
// hard to calibrate: calling it at every step reframes the WHOLE graph, and the
// zoom changes with it — what you see is not the screen following the workflow
// grow, it is the screen jumping in scale with every node. The rule of when NOT
// to move is what avoids that, and testing it inside a fake React Flow would
// measure React Flow.

export interface Caixa {
  x: number
  y: number
  width: number
  height: number
}

/**
 * Slack, in graph units, before considering that the drawing has left the
 * frame.
 *
 * Exists because the auto-layout repositions the nodes at every step: without
 * it, a variation of a few pixels in the box would trigger a new reframe on
 * every draw, which is the jump we are trying to remove. Smaller than a node, so
 * that a real node coming in always counts.
 */
export const FIT_PADDING = 40

/** How long the camera movement lasts, in ms. */
export const FIT_DURATION = 700

/** Zoom ceiling when framing the whole workflow. */
export const FIT_MAX_ZOOM = 1

/**
 * Does the new drawing fit within what was already framed?
 *
 * A null `anterior` means we have not framed anything yet — so it needs to.
 *
 * The comparison is against the LAST framed box, and not against the current
 * viewport, and that is a decision, not a shortcut: if the person dragged the
 * canvas to look at a node and the workflow did not grow, pulling them back
 * would take control out of their hands mid-read. As long as the drawing does
 * not exceed what was already framed, nothing moves.
 */
export function cabeNoEnquadrado(
  nova: Caixa,
  anterior: Caixa | null,
  folga: number = FIT_PADDING,
): boolean {
  if (!anterior) return false
  return (
    nova.x >= anterior.x - folga &&
    nova.y >= anterior.y - folga &&
    nova.x + nova.width <= anterior.x + anterior.width + folga &&
    nova.y + nova.height <= anterior.y + anterior.height + folga
  )
}

/**
 * Did the person ask for reduced motion?
 *
 * The camera movement is animated by JS, so CSS `prefers-reduced-motion` does
 * not reach it — it has to be read here. Someone who asked for reduced motion is
 * still taken to the new workflow; what goes away is the path there.
 */
export function semMovimento(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
}
