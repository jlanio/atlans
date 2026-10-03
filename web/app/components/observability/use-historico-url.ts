"use client"

import { useCallback, useEffect, useMemo, useRef } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { escreverEstado, lerEstado, type HistoryState } from "./historico-url"

export interface HistoryUrl {
  estado: HistoryState
  /** Merges what changed with the current state and writes it to the URL. Switching views closes the panel. */
  atualizar: (parcial: Partial<HistoryState>) => void
  abrirExecucao: (runId: string) => void
  fecharExecucao: () => void
}

/**
 * History state read from and written to the URL (spec §4.1). The URL is the
 * only source: F5, the back button and a pasted link reopen exactly the same
 * screen.
 *
 * `router.replace` is asynchronous: between the write and `useSearchParams`
 * reflecting the change there is at least one render. Two clicks in a row
 * (a status chip and, right after, a workflow in the attention list) would both
 * start from the old state and the second would erase the first. That is why
 * the last written state is kept and serves as the base until the URL catches up.
 */
export function useHistoricoUrl(): HistoryUrl {
  const router = useRouter()
  const pathname = usePathname()
  const sp = useSearchParams()
  const estado = useMemo(() => lerEstado(sp), [sp])
  const pendente = useRef<HistoryState | null>(null)

  // When the URL reaches ANY state — the one we wrote or an external
  // navigation (back/forward, link) —, `pendente` has done its job and must
  // reset. Without this it was only cleared when `base()` was called again and
  // matched the URL; a `pendente` left over after a back/forward becomes the base
  // of a future write and resurrects the old state (losing the external navigation).
  useEffect(() => { pendente.current = null }, [estado])

  const gravar = useCallback((proximo: HistoryState) => {
    pendente.current = proximo
    const qs = escreverEstado(proximo)
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }, [router, pathname])

  const base = useCallback((): HistoryState => {
    const p = pendente.current
    if (p && escreverEstado(p) !== escreverEstado(estado)) return p
    pendente.current = null
    return estado
  }, [estado])

  const atualizar = useCallback((parcial: Partial<HistoryState>) => {
    const atual = base()
    const proximo: HistoryState = { ...atual, ...parcial }
    // Changing views changes the screen's subject; the open panel belonged to
    // the previous view. Period and filters do not touch the open run — the
    // person may be reading an error while adjusting the list behind the panel.
    if (parcial.visao !== undefined && parcial.visao !== atual.visao && parcial.execucao === undefined) {
      proximo.execucao = null
    }
    gravar(proximo)
  }, [base, gravar])

  const abrirExecucao = useCallback((runId: string) => {
    gravar({ ...base(), execucao: runId })
  }, [base, gravar])

  const fecharExecucao = useCallback(() => {
    const atual = base()
    if (atual.execucao == null) return
    gravar({ ...atual, execucao: null })
  }, [base, gravar])

  return useMemo(
    () => ({ estado, atualizar, abrirExecucao, fecharExecucao }),
    [estado, atualizar, abrirExecucao, fecharExecucao],
  )
}
