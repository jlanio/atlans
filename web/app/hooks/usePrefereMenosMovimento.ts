"use client"

import { useEffect, useState } from "react"

/**
 * `prefers-reduced-motion: reduce`, for code that decides in JS what CSS cannot
 * reach (unmounting after a transition, typing letter by letter).
 *
 * `false` in SSR and on the first render, on purpose: reading `matchMedia` in
 * the state initializer would make the client render differently from the
 * server and break hydration. The real value comes in the effect, one frame
 * later — and follows changes in real time, since the system allows changing it
 * without reloading.
 */
export function usePrefereMenosMovimento(): boolean {
  const [reduz, setReduz] = useState(false)
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return
    const consulta = window.matchMedia("(prefers-reduced-motion: reduce)")
    setReduz(consulta.matches)
    const aoMudar = (e: MediaQueryListEvent) => setReduz(e.matches)
    consulta.addEventListener?.("change", aoMudar)
    return () => consulta.removeEventListener?.("change", aoMudar)
  }, [])
  return reduz
}
