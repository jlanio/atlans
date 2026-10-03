"use client"

import { useEffect, useRef, useState } from "react"
import { useStore } from "@xyflow/react"
import { READ_ONLY_LAYER } from "./canvas-layers"

/** Wait before showing the animation: a load that finishes before this doesn't
 *  deserve an indicator — it would only blink. */
export const SHOW_DELAY_MS = 150

/** Once it has appeared, it stays at least this long. Disappearing right after
 *  appearing is the same blink, seen from the other side. */
export const MIN_DISPLAY_MS = 450

/** How long the reveal class stays on the canvas (covers the graph's entrance
 *  animation, in globals.css). */
const REVEAL_DURATION_MS = 700

/**
 * Translates "the canvas is loading" into "the animation is visible", with the two
 * margins above. If the load becomes pending again while the animation is still
 * on air (quick workflow switch), it simply continues.
 */
export function useVisibleLoading(carregando: boolean): boolean {
  const [visivel, setVisible] = useState(false)
  const shownAt = useRef(0)

  useEffect(() => {
    if (carregando) {
      if (visivel) return
      const timer = setTimeout(() => {
        shownAt.current = Date.now()
        setVisible(true)
      }, SHOW_DELAY_MS)
      return () => clearTimeout(timer)
    }
    if (!visivel) return
    const restante = Math.max(0, MIN_DISPLAY_MS - (Date.now() - shownAt.current))
    const timer = setTimeout(() => setVisible(false), restante)
    return () => clearTimeout(timer)
  }, [carregando, visivel])

  return visivel
}

interface Props {
  /** The route has an id and the graph hasn't been hydrated on the canvas yet. */
  carregando: boolean
}

/**
 * What the canvas shows while the workflow hasn't arrived.
 *
 * Before, nothing: the page opened with an empty canvas, the breadcrumb saying
 * "Sem nome" (untitled) and the add-node button pulsing as if the workflow were
 * new — during the fetch, the screen asserted things that weren't true.
 *
 * A mini workflow of three nodes in the center: a packet in the brand color
 * travels the links and each node lights up when reached. It's a piece of the
 * editor, not a spinner on top of it. The styles live in globals.css
 * ("Canvas em espera").
 *
 * It also marks the `.react-flow` container with `rf-carregando` — which is what
 * fades the button columns without each one needing to know about the load — and,
 * when done, with `rf-revelando`, which makes the graph fade in instead of cut in.
 * Same mechanism as CanvasViewLayer for the path highlight.
 *
 * Render as a child of `<ReactFlow>`.
 */
export default function CanvasLoading({ carregando }: Props) {
  const domNode = useStore(s => s.domNode)
  const visivel = useVisibleLoading(carregando)
  const wasLoading = useRef(false)

  useEffect(() => {
    if (!domNode) return
    domNode.classList.toggle("rf-carregando", carregando)

    if (carregando) {
      wasLoading.current = true
      return
    }
    // Only reveals what actually waited: opening the create screen, or switching
    // workflows with the graph already in hand, isn't an arrival of anything.
    if (!wasLoading.current) return
    wasLoading.current = false
    domNode.classList.add("rf-revelando")
    const timer = setTimeout(() => domNode.classList.remove("rf-revelando"), REVEAL_DURATION_MS)
    return () => {
      clearTimeout(timer)
      domNode.classList.remove("rf-revelando")
    }
  }, [domNode, carregando])

  if (!visivel) return null

  return (
    <div
      role="status"
      aria-live="polite"
      data-role="canvas-loading"
      className={`${READ_ONLY_LAYER} inset-0 flex items-center justify-center`}
    >
      <div className="canvas-carregando -mt-6 flex flex-col items-center gap-3.5">
        <svg viewBox="0 0 232 64" width="232" height="64" aria-hidden="true">
          <path className="lig" d="M52 32H88" />
          <path className="lig" d="M144 32H180" />
          <rect className="no" x="8" y="20" width="44" height="24" rx="6" />
          <rect className="no" x="94" y="20" width="44" height="24" rx="6" />
          <rect className="no" x="180" y="20" width="44" height="24" rx="6" />
          <circle className="pk" r="3.5">
            <animateMotion dur="1.8s" repeatCount="indefinite" path="M30 32H202" />
          </circle>
        </svg>
        <span className="text-xs text-muted-foreground">Carregando workflow…</span>
      </div>
    </div>
  )
}
