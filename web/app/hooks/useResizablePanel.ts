"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export interface ResizablePanelOptions {
  /** localStorage key. Without it the width does not survive closing the panel. */
  storageKey?: string
  defaultWidth?: number
  /**
   * Fraction of the window the panel takes when it opens (0–1), when that is more
   * than `defaultWidth` — it is what keeps "open at half the screen" holding on
   * both a laptop and a large monitor. It only governs the opening: a width the
   * user has already chosen wins, and dragging to less than the fraction is
   * allowed.
   */
  defaultRatio?: number
  minWidth?: number
  maxWidth?: number
  /** Edge the panel is anchored to — defines which direction dragging grows it. */
  side?: "left" | "right"
  /**
   * False does not only turn off dragging: the hook stops reading storage and
   * listening to the window's `resize`. Callers that always call it (every
   * `SheetContent`, even the ones that don't resize) pay nothing for it.
   */
  enabled?: boolean
}

/** Minimum gap between the panel and the opposite edge of the window. */
const VIEWPORT_MARGIN = 48
const KEY_STEP = 16
const KEY_STEP_LARGE = 64

/**
 * Draggable width for a panel anchored to an edge of the window.
 *
 * Dragging uses pointer capture instead of listeners on `window`: the pointer
 * keeps delivering events to the handle even after leaving it, and releasing
 * outside the window still fires `pointerup`/`pointercancel` — with global
 * listeners the panel would get stuck to the cursor.
 */
export function useResizablePanel({
  storageKey,
  defaultWidth = 640,
  defaultRatio,
  minWidth = 360,
  maxWidth = 1280,
  side = "right",
  enabled = true,
}: ResizablePanelOptions = {}) {
  const [width, setWidth] = useState(defaultWidth)
  const [isResizing, setIsResizing] = useState(false)

  // `width` in a ref so the handlers read the current value without entering the
  // dependencies (an `onPointerMove` recreated on every dragged pixel would be
  // swapped in the middle of the gesture).
  const widthRef = useRef(defaultWidth)
  // The width the user chose, before the viewport clamp: narrowing the window and
  // widening it back restores the requested width instead of what was left.
  const preferredRef = useRef(defaultWidth)
  const dragRef = useRef<{ startX: number; startWidth: number } | null>(null)

  const clamp = useCallback((w: number) => {
    const ceiling = Math.max(minWidth, Math.min(maxWidth, window.innerWidth - VIEWPORT_MARGIN))
    return Math.round(Math.min(Math.max(w, minWidth), ceiling))
  }, [minWidth, maxWidth])

  const apply = useCallback((w: number) => {
    const next = clamp(w)
    widthRef.current = next
    setWidth(next)
  }, [clamp])

  const persist = useCallback(() => {
    preferredRef.current = widthRef.current
    if (!storageKey) return
    // localStorage throws in private mode/with a full quota — the width is a
    // preference, not worth bringing the panel down over.
    try {
      window.localStorage.setItem(storageKey, String(widthRef.current))
    } catch { /* disposable preference */ }
  }, [storageKey])

  // Depends on the viewport, so it only exists on the client.
  const resolveDefault = useCallback(() => {
    const porFracao = defaultRatio ? window.innerWidth * defaultRatio : 0
    return Math.max(defaultWidth, porFracao)
  }, [defaultWidth, defaultRatio])

  // Opening width, on mount (not on render: `window` does not exist on the
  // server). What the user dragged before wins over the fraction — they have
  // already said what they wanted.
  useEffect(() => {
    if (!enabled) return
    let saved = NaN
    if (storageKey) {
      try {
        saved = Number(window.localStorage.getItem(storageKey))
      } catch { /* no readable storage: falls back to the default */ }
    }
    const inicial = Number.isFinite(saved) && saved > 0 ? saved : resolveDefault()
    preferredRef.current = inicial
    apply(inicial)
  }, [enabled, storageKey, apply, resolveDefault])

  useEffect(() => {
    if (!enabled) return
    function onWindowResize() {
      apply(preferredRef.current)
    }
    window.addEventListener("resize", onWindowResize)
    return () => window.removeEventListener("resize", onWindowResize)
  }, [enabled, apply])

  // While dragging, the cursor and selection suppression must apply to the whole
  // page: the pointer passes over text and other elements.
  useEffect(() => {
    if (!isResizing) return
    const { body } = document
    const prevCursor = body.style.cursor
    const prevSelect = body.style.userSelect
    body.style.cursor = "col-resize"
    body.style.userSelect = "none"
    return () => {
      body.style.cursor = prevCursor
      body.style.userSelect = prevSelect
    }
  }, [isResizing])

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLElement>) => {
    if (e.button !== 0) return
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragRef.current = { startX: e.clientX, startWidth: widthRef.current }
    setIsResizing(true)
  }, [])

  const onPointerMove = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const drag = dragRef.current
    if (!drag) return
    // A delta instead of "width = edge to cursor": grabbing the handle in the middle
    // does not teleport the edge under the cursor on the first move.
    const delta = side === "right" ? drag.startX - e.clientX : e.clientX - drag.startX
    apply(drag.startWidth + delta)
  }, [apply, side])

  const endDrag = useCallback((e: React.PointerEvent<HTMLElement>) => {
    if (!dragRef.current) return
    dragRef.current = null
    setIsResizing(false)
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId)
    }
    persist()
  }, [persist])

  const onKeyDown = useCallback((e: React.KeyboardEvent<HTMLElement>) => {
    const step = e.shiftKey ? KEY_STEP_LARGE : KEY_STEP
    const grow = side === "right" ? -1 : 1
    let next: number
    if (e.key === "ArrowLeft") next = widthRef.current + step * grow
    else if (e.key === "ArrowRight") next = widthRef.current - step * grow
    else if (e.key === "Home") next = minWidth
    else if (e.key === "End") next = maxWidth
    else return
    e.preventDefault()
    // The handle lives inside a Radix Dialog, which listens to arrow keys.
    e.stopPropagation()
    apply(next)
    persist()
  }, [apply, persist, side, minWidth, maxWidth])

  const onDoubleClick = useCallback(() => {
    apply(resolveDefault())
    persist()
  }, [apply, persist, resolveDefault])

  return {
    width,
    isResizing,
    /** Spread onto the handle element. */
    resizeHandleProps: {
      role: "separator",
      "aria-orientation": "vertical",
      "aria-label": "Redimensionar painel",
      "aria-valuenow": width,
      "aria-valuemin": minWidth,
      "aria-valuemax": maxWidth,
      tabIndex: 0,
      title: "Arraste para redimensionar · duplo clique para restaurar",
      onPointerDown,
      onPointerMove,
      onPointerUp: endDrag,
      onPointerCancel: endDrag,
      onKeyDown,
      onDoubleClick,
    } as const,
  }
}
