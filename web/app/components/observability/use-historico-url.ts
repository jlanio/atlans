"use client"

import { useCallback, useEffect, useMemo, useRef } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { escreverEstado, lerEstado, type EstadoDoHistorico } from "./historico-url"

export interface HistoricoUrl {
  estado: EstadoDoHistorico
  /** Funde o que mudou com o estado atual e grava na URL. Trocar de visão fecha o painel. */
  atualizar: (parcial: Partial<EstadoDoHistorico>) => void
  abrirExecucao: (runId: string) => void
  fecharExecucao: () => void
}

/**
 * Estado do Histórico lido e gravado na URL (spec §4.1). A URL é a única
 * fonte: F5, o botão voltar e um link colado reabrem exatamente a mesma tela.
 *
 * `router.replace` é assíncrono: entre a escrita e o `useSearchParams`
 * refletir a mudança há pelo menos um render. Dois cliques seguidos (chip de
 * status e, logo depois, um workflow na lista de atenção) partiriam ambos do
 * estado velho e o segundo apagaria o primeiro. Por isso o último estado
 * escrito fica guardado e serve de base enquanto a URL não o alcança.
 */
export function useHistoricoUrl(): HistoricoUrl {
  const router = useRouter()
  const pathname = usePathname()
  const sp = useSearchParams()
  const estado = useMemo(() => lerEstado(sp), [sp])
  const pendente = useRef<EstadoDoHistorico | null>(null)

  // Quando a URL alcança QUALQUER estado — o que gravamos ou uma navegação
  // externa (voltar/avançar, link) —, `pendente` cumpriu seu papel e tem de
  // zerar. Sem isto ele só era limpo quando `base()` era chamado de novo e batia
  // com a URL; um `pendente` que sobra depois de um voltar/avançar vira base de
  // uma escrita futura e ressuscita o estado antigo (perde a navegação externa).
  useEffect(() => { pendente.current = null }, [estado])

  const gravar = useCallback((proximo: EstadoDoHistorico) => {
    pendente.current = proximo
    const qs = escreverEstado(proximo)
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }, [router, pathname])

  const base = useCallback((): EstadoDoHistorico => {
    const p = pendente.current
    if (p && escreverEstado(p) !== escreverEstado(estado)) return p
    pendente.current = null
    return estado
  }, [estado])

  const atualizar = useCallback((parcial: Partial<EstadoDoHistorico>) => {
    const atual = base()
    const proximo: EstadoDoHistorico = { ...atual, ...parcial }
    // Mudar de visão troca o assunto da tela; o painel aberto era da visão
    // anterior. Período e filtros não mexem na execução aberta — a pessoa
    // pode estar lendo um erro enquanto ajusta a lista atrás do painel.
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
