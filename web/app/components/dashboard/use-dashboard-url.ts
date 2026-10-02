"use client"

import { useCallback, useEffect, useMemo, useRef } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import {
  escreverEstado, lerEstado, type EstadoDoDashboard, type EstadoDoEscopo, type Periodo,
} from "./dashboard-url"

export interface DashboardUrl {
  escopo: EstadoDoEscopo
  setEscopo: (escopo: EstadoDoEscopo) => void
  periodo: Periodo
  setPeriodo: (periodo: Periodo) => void
}

/**
 * Escopo e período do Dashboard lidos e gravados na URL (docs/specs/dashboard.md §3.9).
 *
 * `router.replace` (não `push`): trocar escopo ou período é filtrar a mesma
 * tela, não navegar — não deve empilhar entrada no histórico do navegador,
 * como em `use-projetos-url.ts`.
 *
 * O `replace` é assíncrono: entre a escrita e o `useSearchParams` refletir a
 * mudança há ao menos um render. Trocar o escopo e o período em sequência
 * partiriam ambos do estado velho e o segundo apagaria o primeiro. Por isso o
 * último estado escrito fica guardado (`pendente`) e serve de base enquanto a
 * URL não o alcança — o mesmo mecanismo de `use-projetos-url.ts`.
 */
export function useDashboardUrl(): DashboardUrl {
  const router = useRouter()
  const pathname = usePathname()
  const sp = useSearchParams()
  const estado = useMemo(() => lerEstado(sp), [sp])
  const pendente = useRef<EstadoDoDashboard | null>(null)

  // Quando a URL alcança QUALQUER estado — o que gravamos ou uma navegação
  // externa (voltar/avançar, link) —, `pendente` cumpriu seu papel e tem de
  // zerar. Sem isto ele só era limpo quando `base()` era chamado de novo e batia
  // com a URL; um `pendente` que sobra depois de um voltar/avançar vira base de
  // uma escrita futura e ressuscita o estado antigo (perde a navegação externa).
  useEffect(() => { pendente.current = null }, [estado])

  const gravar = useCallback((proximo: EstadoDoDashboard) => {
    pendente.current = proximo
    const qs = escreverEstado(proximo)
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }, [router, pathname])

  const base = useCallback((): EstadoDoDashboard => {
    const p = pendente.current
    if (p && escreverEstado(p) !== escreverEstado(estado)) return p
    pendente.current = null
    return estado
  }, [estado])

  const setEscopo = useCallback((escopo: EstadoDoEscopo) => gravar({ ...base(), escopo }), [base, gravar])
  const setPeriodo = useCallback((periodo: Periodo) => gravar({ ...base(), periodo }), [base, gravar])

  return useMemo(
    () => ({ escopo: estado.escopo, setEscopo, periodo: estado.periodo, setPeriodo }),
    [estado, setEscopo, setPeriodo],
  )
}
