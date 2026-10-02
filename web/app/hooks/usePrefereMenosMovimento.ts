"use client"

import { useEffect, useState } from "react"

/**
 * `prefers-reduced-motion: reduce`, para quem decide em JS o que o CSS não
 * alcança (desmontar depois de uma transição, digitar letra a letra).
 *
 * `false` no SSR e no primeiro render, de propósito: ler `matchMedia` no
 * inicializador do estado faria o cliente renderizar diferente do servidor e
 * descasar a hidratação. O valor real entra no efeito, um quadro depois — e
 * acompanha a troca em tempo real, que o sistema permite mudar sem recarregar.
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
