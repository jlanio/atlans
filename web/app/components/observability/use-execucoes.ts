"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IRunSummary } from "@/service/types"
import { inicioDaJanela, type EstadoDoHistorico } from "./historico-url"

export const TAMANHO_DA_PAGINA = 20

export interface Execucoes {
  runs: IRunSummary[]
  /** Only the first page counts (COUNT is the expensive part); null until it arrives. */
  total: number | null
  hasMore: boolean
  carregando: boolean
  carregandoMais: boolean
  falhou: boolean
  carregarMais: () => void
  recarregar: () => void
}

/**
 * Paginated list of runs sliced by the URL state (spec §4.3).
 *
 * Heir of the old page's `useRunsQuery`, with the same defenses: a sequence
 * stamp (switching filters fires a fetch before the previous one responds,
 * and the slower one must not win), `with_total` only on the first page,
 * offset in a ref so `carregarMais` does not change identity on every page,
 * and the error as a boolean — the table decides the text.
 *
 * Any filter change (period, status, workspace, workflow, executor, origin,
 * assistant, search) restarts from the first page. The view and the open run
 * are not included: switching tabs or opening the panel does not redo the list.
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
      // "Assistente" chip: slices by WORKFLOW, not by trigger — it combines
      // with `trigger_source` instead of competing with it.
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
      // A run that starts between page 1 and page 2 shifts the offset and the
      // last item of the previous page comes back in the next: keep only the first.
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
    // Reset before fetching: the previous filter's list must not stay on screen
    // under the new chip while the response has not arrived.
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
