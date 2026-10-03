"use client"

import { useCallback, useEffect, useMemo, useRef } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import {
  escreverEstado, lerEstado, type DashboardState, type ScopeState, type Period,
} from "./dashboard-url"

export interface DashboardUrl {
  escopo: ScopeState
  setEscopo: (escopo: ScopeState) => void
  periodo: Period
  setPeriodo: (periodo: Period) => void
}

/**
 * Dashboard scope and period read from and written to the URL (docs/specs/dashboard.md §3.9).
 *
 * `router.replace` (not `push`): changing scope or period is filtering the same
 * screen, not navigating — it must not push an entry onto the browser history,
 * as in `use-projetos-url.ts`.
 *
 * `replace` is asynchronous: between the write and `useSearchParams` reflecting
 * the change there is at least one render. Changing the scope and the period in
 * a row would both start from the stale state and the second would erase the
 * first. That is why the last written state is kept (`pendente`) and serves as
 * the base while the URL hasn't caught up — the same mechanism as `use-projetos-url.ts`.
 */
export function useDashboardUrl(): DashboardUrl {
  const router = useRouter()
  const pathname = usePathname()
  const sp = useSearchParams()
  const estado = useMemo(() => lerEstado(sp), [sp])
  const pendente = useRef<DashboardState | null>(null)

  // When the URL reaches ANY state — the one we wrote or an external navigation
  // (back/forward, link) —, `pendente` has done its job and must be reset.
  // Without this it was only cleared when `base()` was called again and matched
  // the URL; a `pendente` left over after a back/forward becomes the base of a
  // future write and resurrects the old state (losing the external navigation).
  useEffect(() => { pendente.current = null }, [estado])

  const gravar = useCallback((proximo: DashboardState) => {
    pendente.current = proximo
    const qs = escreverEstado(proximo)
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }, [router, pathname])

  const base = useCallback((): DashboardState => {
    const p = pendente.current
    if (p && escreverEstado(p) !== escreverEstado(estado)) return p
    pendente.current = null
    return estado
  }, [estado])

  const setEscopo = useCallback((escopo: ScopeState) => gravar({ ...base(), escopo }), [base, gravar])
  const setPeriodo = useCallback((periodo: Period) => gravar({ ...base(), periodo }), [base, gravar])

  return useMemo(
    () => ({ escopo: estado.escopo, setEscopo, periodo: estado.periodo, setPeriodo }),
    [estado, setEscopo, setPeriodo],
  )
}
