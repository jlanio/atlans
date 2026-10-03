import { useCallback, useEffect, useRef, useState } from "react"

const BOTTOM_TOLERANCE_PX = 40

/**
 * Auto-scroll that only follows someone already at the end.
 *
 * The old panel called `scrollIntoView` on every new event, without checking
 * the position: scrolling up to read anything during the run was impossible —
 * the list pulled the user back once per line.
 */
export function useStickyScroll(deps: unknown[], scrollToEnd?: () => void) {
  const containerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const [stuck, setStuck] = useState(true)
  const [showJump, setShowJump] = useState(false)

  // Ref to the callback: `onScroll` is registered once, but the virtualizer
  // (and therefore `scrollToEnd`) changes on every render.
  const scrollToEndRef = useRef(scrollToEnd)
  scrollToEndRef.current = scrollToEnd

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    function onScroll() {
      const node = containerRef.current
      if (!node) return
      const atBottom = node.scrollHeight - node.scrollTop - node.clientHeight <= BOTTOM_TOLERANCE_PX
      setStuck(atBottom)
      // The button's authority lives here: with virtualization, dynamic measurement
      // can move the scroll off the end AFTER the auto-scroll effect runs (which
      // does not re-fire on a finished run). Without this, the user was left
      // without the "↓" button to get back to the end.
      setShowJump(!atBottom)
    }
    el.addEventListener("scroll", onScroll, { passive: true })
    return () => el.removeEventListener("scroll", onScroll)
  }, [])

  // `scrollTop = scrollHeight` instead of `scrollIntoView`: this effect runs on
  // every panel flush (every 120ms in a live run) and scrollIntoView measured
  // the position of an element at the end of a list of thousands of freshly
  // rendered rows — forced synchronous layout, eight times per second. The
  // adjustment also goes into a single frame, so two consecutive flushes do
  // not pay for the work twice.
  const frameRef = useRef<number | null>(null)
  useEffect(() => {
    if (!stuck) {
      setShowJump(true)
      return
    }
    if (frameRef.current != null) cancelAnimationFrame(frameRef.current)
    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null
      // Virtualized: delegates to the virtualizer, whose readjustment loop
      // compensates for dynamic measurement (scrollTop=scrollHeight would use the
      // ESTIMATED height and stop midway). Without virtualization, the raw
      // scroll is still correct.
      if (scrollToEndRef.current) {
        scrollToEndRef.current()
        return
      }
      const el = containerRef.current
      if (el) el.scrollTop = el.scrollHeight
    })
    return () => {
      if (frameRef.current != null) {
        cancelAnimationFrame(frameRef.current)
        frameRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  const jumpToBottom = useCallback(() => {
    setStuck(true)
    setShowJump(false)
    if (scrollToEndRef.current) {
      scrollToEndRef.current()
      return
    }
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [])

  return { containerRef, bottomRef, showJump, jumpToBottom }
}
