"use client"

import { useCallback, useEffect, useMemo, useRef } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { DEFAULT_STATE, escreverEstado, lerEstado, type ProjectsState } from "./projetos-url"

export interface ProjectsUrl {
  estado: ProjectsState
  /** Merges what changed with the current state and writes it to the URL. */
  atualizar: (parcial: Partial<ProjectsState>) => void
  /** Resets search and chip; the sort stays, because it does not slice the list. */
  limparFiltros: () => void
}

/**
 * Projects state read from and written to the URL (spec §3.6). The URL is the
 * only source: F5, the back button and a pasted link reopen the same shelf.
 *
 * `router.replace` (not `push`: each search keystroke must not become an
 * entry in the browser history) is asynchronous: between the write and
 * `useSearchParams` reflecting the change there is at least one render. A click
 * on the attention strip followed by a search keystroke would both start from
 * the old state and the second would erase the first. That is why the last
 * written state is kept and serves as the base until the URL catches up — the
 * same mechanism as `observability/use-historico-url.ts`.
 */
export function useProjetosUrl(): ProjectsUrl {
  const router = useRouter()
  const pathname = usePathname()
  const sp = useSearchParams()
  const estado = useMemo(() => lerEstado(sp), [sp])
  const pendente = useRef<ProjectsState | null>(null)

  // When the URL reaches ANY state — the one we wrote or an external
  // navigation (back/forward, link) —, `pendente` has done its job and must
  // reset. Without this it was only cleared when `base()` was called again and
  // matched the URL; a `pendente` left over after a back/forward becomes the base
  // of a future write and resurrects the old state (losing the external navigation).
  useEffect(() => { pendente.current = null }, [estado])

  const gravar = useCallback((proximo: ProjectsState) => {
    pendente.current = proximo
    const qs = escreverEstado(proximo)
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }, [router, pathname])

  const base = useCallback((): ProjectsState => {
    const p = pendente.current
    if (p && escreverEstado(p) !== escreverEstado(estado)) return p
    pendente.current = null
    return estado
  }, [estado])

  const atualizar = useCallback((parcial: Partial<ProjectsState>) => {
    gravar({ ...base(), ...parcial })
  }, [base, gravar])

  const limparFiltros = useCallback(() => {
    const atual = base()
    if (atual.q === DEFAULT_STATE.q && atual.filtro === DEFAULT_STATE.filtro) return
    gravar({ ...atual, q: DEFAULT_STATE.q, filtro: DEFAULT_STATE.filtro })
  }, [base, gravar])

  return useMemo(() => ({ estado, atualizar, limparFiltros }), [estado, atualizar, limparFiltros])
}
