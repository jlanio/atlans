"use client"

import { useCallback, useEffect, useMemo, useRef } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { ESTADO_PADRAO, escreverEstado, lerEstado, type EstadoDeProjetos } from "./projetos-url"

export interface ProjetosUrl {
  estado: EstadoDeProjetos
  /** Funde o que mudou com o estado atual e grava na URL. */
  atualizar: (parcial: Partial<EstadoDeProjetos>) => void
  /** Zera busca e chip; a ordenação fica, porque não recorta a lista. */
  limparFiltros: () => void
}

/**
 * Estado de Projetos lido e gravado na URL (spec §3.6). A URL é a única
 * fonte: F5, o botão voltar e um link colado reabrem a mesma estante.
 *
 * `router.replace` (não `push`: cada tecla na busca não pode virar uma
 * entrada no histórico do navegador) é assíncrono: entre a escrita e o
 * `useSearchParams` refletir a mudança há pelo menos um render. Um clique na
 * faixa de atenção seguido de uma tecla na busca partiriam ambos do estado
 * velho e o segundo apagaria o primeiro. Por isso o último estado escrito
 * fica guardado e serve de base enquanto a URL não o alcança — o mesmo
 * mecanismo de `observability/use-historico-url.ts`.
 */
export function useProjetosUrl(): ProjetosUrl {
  const router = useRouter()
  const pathname = usePathname()
  const sp = useSearchParams()
  const estado = useMemo(() => lerEstado(sp), [sp])
  const pendente = useRef<EstadoDeProjetos | null>(null)

  // Quando a URL alcança QUALQUER estado — o que gravamos ou uma navegação
  // externa (voltar/avançar, link) —, `pendente` cumpriu seu papel e tem de
  // zerar. Sem isto ele só era limpo quando `base()` era chamado de novo e batia
  // com a URL; um `pendente` que sobra depois de um voltar/avançar vira base de
  // uma escrita futura e ressuscita o estado antigo (perde a navegação externa).
  useEffect(() => { pendente.current = null }, [estado])

  const gravar = useCallback((proximo: EstadoDeProjetos) => {
    pendente.current = proximo
    const qs = escreverEstado(proximo)
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }, [router, pathname])

  const base = useCallback((): EstadoDeProjetos => {
    const p = pendente.current
    if (p && escreverEstado(p) !== escreverEstado(estado)) return p
    pendente.current = null
    return estado
  }, [estado])

  const atualizar = useCallback((parcial: Partial<EstadoDeProjetos>) => {
    gravar({ ...base(), ...parcial })
  }, [base, gravar])

  const limparFiltros = useCallback(() => {
    const atual = base()
    if (atual.q === ESTADO_PADRAO.q && atual.filtro === ESTADO_PADRAO.filtro) return
    gravar({ ...atual, q: ESTADO_PADRAO.q, filtro: ESTADO_PADRAO.filtro })
  }, [base, gravar])

  return useMemo(() => ({ estado, atualizar, limparFiltros }), [estado, atualizar, limparFiltros])
}
