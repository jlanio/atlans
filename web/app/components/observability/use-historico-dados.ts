"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type {
  IExecutorMetrics, IObservabilityMetrics, IRunsByDay, IWorkflowMetricsRow,
} from "@/service/types"
import type { EstadoDoHistorico, Periodo } from "./historico-url"

/**
 * Dados do topo do Histórico (docs/specs/historico-metricas.md §4.3 "Dados").
 *
 * Quatro chamadas em paralelo por (período, filtros): métricas, execuções por
 * dia, executores e workflows. As duas últimas só se recortam por workspace —
 * escolher um workflow não muda a frota nem a lista de workflows, então elas
 * têm chave de cache própria e não voltam à rede quando só o workflow muda.
 *
 * O cache é POR PARTE, e só o que respondeu entra nele. É a mesma lição do
 * `metrics-cache.ts` da página antiga (uma resposta faltando não pode virar
 * lista vazia memorizada), resolvida no grão da parte em vez de tudo-ou-nada:
 * uma falha em `/metrics/executores` não obriga a refazer as outras três na
 * próxima visita ao mesmo período.
 */

export type ParteDosDados = "metrics" | "dias" | "executores" | "workflows"

export type FalhasDosDados = Partial<Record<ParteDosDados, string>>

export interface HistoricoDados {
  metrics: IObservabilityMetrics | null
  dias: IRunsByDay[]
  executores: IExecutorMetrics[]
  workflows: IWorkflowMetricsRow[]
  /** Alguma parte está em voo (o poll silencioso da faixa Agora não conta). */
  carregando: boolean
  /** Janela a que pertence o que está NA TELA — muda quando o dado chega, não no clique. */
  periodoDosDados: Periodo
  /** Mensagem por parte que falhou na última carga; o que já havia continua na tela. */
  falhas: FalhasDosDados
  /** Fura o cache local e manda `force=true` para o backend furar o Redis. */
  recarregar: () => void
}

export const TTL_DO_CACHE_MS = 60_000
/** A faixa "Agora" atualiza a cada 30 s com a aba visível (spec §4.3). */
export const INTERVALO_DO_AGORA_MS = 30_000

const MENSAGENS: Record<ParteDosDados, string> = {
  metrics: "Não foi possível carregar os indicadores.",
  dias: "Não foi possível carregar as execuções por dia.",
  executores: "Não foi possível carregar os executores.",
  workflows: "Não foi possível carregar os workflows.",
}

type Entrada<T> = { valor: T; ts: number }

/** Fuso do navegador para `/runs-by-day` cortar o dia onde a pessoa está. */
export function fusoDoNavegador(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  } catch {
    return "UTC"
  }
}

/** Chaves de cache: métricas e dias por (período, workspace, workflow); frota e workflows só por (período, workspace). */
export function chavesDeCache(estado: Pick<EstadoDoHistorico, "periodo" | "workspace" | "workflow">, tz: string) {
  const ws = estado.workspace ?? ""
  const wf = estado.workflow ?? ""
  return {
    metrics: `metrics|${estado.periodo}|${ws}|${wf}`,
    dias: `dias|${estado.periodo}|${ws}|${wf}|${tz}`,
    executores: `executores|${estado.periodo}|${ws}`,
    workflows: `workflows|${estado.periodo}|${ws}`,
  }
}

function filtrosDeJanela(estado: Pick<EstadoDoHistorico, "workspace" | "workflow">) {
  return {
    workspace_id: estado.workspace ?? undefined,
    workflow_id: estado.workflow ?? undefined,
  }
}

export function useHistoricoDados(
  estado: EstadoDoHistorico,
  opts: { habilitado: boolean; intervaloDoAgoraMs?: number },
): HistoricoDados {
  const { habilitado, intervaloDoAgoraMs = INTERVALO_DO_AGORA_MS } = opts
  const [metrics, setMetrics] = useState<IObservabilityMetrics | null>(null)
  const [dias, setDias] = useState<IRunsByDay[]>([])
  const [executores, setExecutores] = useState<IExecutorMetrics[]>([])
  const [workflows, setWorkflows] = useState<IWorkflowMetricsRow[]>([])
  const [carregando, setCarregando] = useState(true)
  const [periodoDosDados, setPeriodoDosDados] = useState<Periodo>(estado.periodo)
  const [falhas, setFalhas] = useState<FalhasDosDados>({})

  // Carimbo de sequência: trocar de período duas vezes seguidas dispara duas
  // cargas, e a mais lenta pode responder por último. Só a última carga
  // pedida escreve na tela.
  const seq = useRef(0)
  const cache = useRef(new Map<string, Entrada<unknown>>())
  // O estado lido pelo `recarregar` e pelo poll é sempre o corrente, sem que
  // eles precisem trocar de identidade a cada render (descem para botões).
  const estadoRef = useRef(estado)
  estadoRef.current = estado
  const tz = useMemo(fusoDoNavegador, [])

  const lerCache = useCallback(<T,>(chave: string, agora: number): T | undefined => {
    const e = cache.current.get(chave)
    if (!e || agora - e.ts >= TTL_DO_CACHE_MS) return undefined
    return e.valor as T
  }, [])

  const carregar = useCallback(async (alvo: EstadoDoHistorico, force: boolean) => {
    const mine = ++seq.current
    const agora = Date.now()
    const chaves = chavesDeCache(alvo, tz)
    const doCache = force ? {} : {
      metrics: lerCache<IObservabilityMetrics>(chaves.metrics, agora),
      dias: lerCache<IRunsByDay[]>(chaves.dias, agora),
      executores: lerCache<IExecutorMetrics[]>(chaves.executores, agora),
      workflows: lerCache<IWorkflowMetricsRow[]>(chaves.workflows, agora),
    }

    // O que o cache tem entra na hora: trocar de período e voltar não pisca.
    if (doCache.metrics) setMetrics(doCache.metrics)
    if (doCache.dias) setDias(doCache.dias)
    if (doCache.executores) setExecutores(doCache.executores)
    if (doCache.workflows) setWorkflows(doCache.workflows)
    if (doCache.metrics || doCache.dias) setPeriodoDosDados(alvo.periodo)

    const faltam = (["metrics", "dias", "executores", "workflows"] as ParteDosDados[])
      .filter(p => !doCache[p])
    if (faltam.length === 0) {
      setFalhas({})
      setCarregando(false)
      return
    }

    setCarregando(true)
    const janela = filtrosDeJanela(alvo)
    const soWorkspace = { workspace_id: janela.workspace_id }
    const [rMetrics, rDias, rExecutores, rWorkflows] = await Promise.all([
      faltam.includes("metrics") ? GisFlowService.getObservabilityMetrics(alvo.periodo, force, janela) : null,
      faltam.includes("dias") ? GisFlowService.getRunsByDay(alvo.periodo, { ...janela, tz }) : null,
      faltam.includes("executores") ? GisFlowService.getExecutorMetrics(alvo.periodo, force, soWorkspace) : null,
      faltam.includes("workflows") ? GisFlowService.getWorkflowMetricsList(alvo.periodo, force, soWorkspace) : null,
    ])
    if (mine !== seq.current) return

    const ts = Date.now()
    const novasFalhas: FalhasDosDados = {}
    const guardar = (chave: string, valor: unknown) => {
      cache.current.set(chave, { valor, ts })
    }

    if (rMetrics) {
      if (rMetrics.data) { setMetrics(rMetrics.data); guardar(chaves.metrics, rMetrics.data) }
      else novasFalhas.metrics = MENSAGENS.metrics
    }
    if (rDias) {
      if (rDias.data?.days) { setDias(rDias.data.days); guardar(chaves.dias, rDias.data.days) }
      else novasFalhas.dias = MENSAGENS.dias
    }
    if (rExecutores) {
      if (rExecutores.data?.executores) { setExecutores(rExecutores.data.executores); guardar(chaves.executores, rExecutores.data.executores) }
      else novasFalhas.executores = MENSAGENS.executores
    }
    if (rWorkflows) {
      if (rWorkflows.data?.workflows) { setWorkflows(rWorkflows.data.workflows); guardar(chaves.workflows, rWorkflows.data.workflows) }
      else novasFalhas.workflows = MENSAGENS.workflows
    }

    // O rótulo da janela acompanha o dado que chegou: se só as métricas
    // vieram, os cards já são do período novo e o gráfico ainda não — o
    // gráfico se marca pelo aviso de falha, não pelo rótulo.
    if ((rMetrics?.data || rDias?.data?.days) || doCache.metrics || doCache.dias) setPeriodoDosDados(alvo.periodo)
    setFalhas(novasFalhas)
    setCarregando(false)
  }, [tz, lerCache])

  useEffect(() => {
    if (!habilitado) return
    carregar(estadoRef.current, false)
    // Só (período, workspace, workflow) recortam estas quatro chamadas; os
    // demais campos do estado (status, busca, visão) são da tabela.
  }, [habilitado, estado.periodo, estado.workspace, estado.workflow, carregar])

  // Poll silencioso da faixa "Agora": só as métricas (é onde `now` vive), sem
  // ligar `carregando` — senão os indicadores virariam skeleton a cada 30 s.
  // Não incrementa a sequência: uma carga completa pedida no meio vence.
  useEffect(() => {
    if (!habilitado || intervaloDoAgoraMs <= 0) return
    let ultimo = Date.now()
    async function atualizarAgora() {
      const alvo = estadoRef.current
      const mine = seq.current
      ultimo = Date.now()
      const res = await GisFlowService.getObservabilityMetrics(alvo.periodo, false, filtrosDeJanela(alvo))
      if (mine !== seq.current || !res.data) return
      const ts = Date.now()
      cache.current.set(chavesDeCache(alvo, tz).metrics, { valor: res.data, ts })
      setMetrics(res.data)
    }
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") atualizarAgora()
    }, intervaloDoAgoraMs)
    // Voltar para a aba depois de um tempo longe: atualiza na hora em vez de
    // esperar o próximo tick — mas não a cada alt-tab.
    const onVisibility = () => {
      if (document.visibilityState === "visible" && Date.now() - ultimo >= intervaloDoAgoraMs) atualizarAgora()
    }
    document.addEventListener("visibilitychange", onVisibility)
    return () => {
      clearInterval(timer)
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [habilitado, intervaloDoAgoraMs, tz])

  const recarregar = useCallback(() => { carregar(estadoRef.current, true) }, [carregar])

  return useMemo(() => ({
    metrics, dias, executores, workflows, carregando, periodoDosDados, falhas, recarregar,
  }), [metrics, dias, executores, workflows, carregando, periodoDosDados, falhas, recarregar])
}
