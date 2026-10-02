"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IRunSummary } from "@/service/types"
import { inicioDaJanela, type EstadoDoHistorico } from "./historico-url"

export const TAMANHO_DA_PAGINA = 20

export interface Execucoes {
  runs: IRunSummary[]
  /** Só a primeira página conta (COUNT é a parte cara); nulo até ela chegar. */
  total: number | null
  hasMore: boolean
  carregando: boolean
  carregandoMais: boolean
  falhou: boolean
  carregarMais: () => void
  recarregar: () => void
}

/**
 * Lista paginada de execuções recortada pelo estado da URL (spec §4.3).
 *
 * Herdeiro do `useRunsQuery` da página antiga, com as mesmas defesas: carimbo
 * de sequência (trocar de filtro dispara uma busca antes de a anterior
 * responder, e a mais lenta não pode vencer), `with_total` só na primeira
 * página, offset em ref para o `carregarMais` não trocar de identidade a cada
 * página, e erro como booleano — a tabela decide o texto.
 *
 * Qualquer mudança de filtro (período, status, workspace, workflow, executor,
 * origem, assistente, busca) recomeça da primeira página. A visão e a execução aberta não
 * entram: trocar de aba ou abrir o painel não refaz a lista.
 */
export function useExecucoes(estado: EstadoDoHistorico, { habilitado }: { habilitado: boolean }): Execucoes {
  const [runs, setRuns] = useState<IRunSummary[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [carregando, setCarregando] = useState(true)
  const [carregandoMais, setCarregandoMais] = useState(false)
  const [falhou, setFalhou] = useState(false)
  const seq = useRef(0)
  const offsetRef = useRef(0)

  const { periodo, status, workspace, workflow, executor, origem, assistente } = estado
  const q = estado.q.trim()

  const buscar = useCallback(async (offset: number, acumular: boolean) => {
    const meu = ++seq.current
    if (acumular) setCarregandoMais(true)
    else setCarregando(true)
    const res = await GisFlowService.getObservabilityRuns({
      date_from: inicioDaJanela(periodo),
      status: status ?? undefined,
      workspace_id: workspace ?? undefined,
      workflow_id: workflow ?? undefined,
      worker_host: executor ?? undefined,
      trigger_source: origem ?? undefined,
      // Chip "Assistente": recorta pelo FLUXO, e não pelo disparo — combina
      // com `trigger_source` em vez de competir com ele.
      workflow_origem: assistente ? "assistente" : undefined,
      q: q || undefined,
      limit: TAMANHO_DA_PAGINA,
      offset,
      with_total: acumular ? undefined : true,
    })
    if (meu !== seq.current) return
    const dados = res?.data
    setFalhou(!dados)
    if (dados) {
      if (!acumular && typeof dados.total === "number") setTotal(dados.total)
      setHasMore(!!dados.has_more)
      // Uma execução que começa entre a página 1 e a 2 desloca o offset e o
      // último item da página anterior volta na seguinte: fica só a primeira.
      setRuns(prev => {
        if (!acumular) return dados.runs
        const vistos = new Set(prev.map(r => r.run_id))
        return [...prev, ...dados.runs.filter(r => !vistos.has(r.run_id))]
      })
      offsetRef.current = offset + dados.runs.length
    }
    setCarregando(false)
    setCarregandoMais(false)
  }, [periodo, status, workspace, workflow, executor, origem, assistente, q])

  useEffect(() => {
    if (!habilitado) return
    // Zera antes de buscar: a lista do filtro anterior não pode ficar na tela
    // sob o chip do novo enquanto a resposta não chega.
    setRuns([])
    setTotal(null)
    setHasMore(false)
    offsetRef.current = 0
    buscar(0, false)
  }, [habilitado, buscar])

  const recarregar = useCallback(() => { buscar(0, false) }, [buscar])
  const carregarMais = useCallback(() => { buscar(offsetRef.current, true) }, [buscar])

  return useMemo(
    () => ({ runs, total, hasMore, carregando, carregandoMais, falhou, carregarMais, recarregar }),
    [runs, total, hasMore, carregando, carregandoMais, falhou, carregarMais, recarregar],
  )
}
