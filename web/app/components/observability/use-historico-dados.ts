"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type {
  IExecutorMetrics, IObservabilityMetrics, IRunsByDay, IWorkflowMetricsRow,
} from "@/service/types"
import type { EstadoDoHistorico, Periodo } from "./historico-url"

/**
 * Data for the top of History (docs/specs/metrics-history.md §4.3 "Dados").
 *
 * Four calls in parallel per (period, filters): metrics, runs per day,
 * executors and workflows. The last two are sliced only by workspace —
 * picking a workflow changes neither the fleet nor the workflow list, so they
 * have their own cache key and do not go back to the network when only the
 * workflow changes.
 *
 * The cache is PER PART, and only what responded goes into it. It is the same
 * lesson as the old page's `metrics-cache.ts` (a missing response must not
 * become a memorized empty list), solved at the part's grain instead of
 * all-or-nothing: a failure in `/metrics/executores` does not force redoing the
 * other three on the next visit to the same period.
 */

export type ParteDosDados = "metrics" | "dias" | "executores" | "workflows"

export type FalhasDosDados = Partial<Record<ParteDosDados, string>>

export interface HistoricoDados {
  metrics: IObservabilityMetrics | null
  dias: IRunsByDay[]
  executores: IExecutorMetrics[]
  workflows: IWorkflowMetricsRow[]
  /** Some part is in flight (the Now strip's silent poll does not count). */
  carregando: boolean
  /** Window that what is ON SCREEN belongs to — changes when the data arrives, not on click. */
  periodoDosDados: Periodo
  /** Message per part that failed in the last load; what was already there stays on screen. */
  falhas: FalhasDosDados
  /** Fura o cache local e manda `force=true` para o backend furar o Redis. */
  recarregar: () => void
}

export const TTL_DO_CACHE_MS = 60_000
/** The "Agora" (Now) strip refreshes every 30 s while the tab is visible (spec §4.3). */
export const INTERVALO_DO_AGORA_MS = 30_000

const MENSAGENS: Record<ParteDosDados, string> = {
  metrics: "Não foi possível carregar os indicadores.",
  dias: "Não foi possível carregar as execuções por dia.",
  executores: "Não foi possível carregar os executores.",
  workflows: "Não foi possível carregar os workflows.",
}

type Entrada<T> = { valor: T; ts: number }

/** Browser time zone so `/runs-by-day` cuts the day where the person is. */
export function fusoDoNavegador(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  } catch {
    return "UTC"
  }
}

/** Cache keys: metrics and days by (period, workspace, workflow); fleet and workflows only by (period, workspace). */
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

  // Sequence stamp: switching periods twice in a row fires two loads, and the
  // slower one may respond last. Only the last load requested writes to the
  // screen.
  const seq = useRef(0)
  const cache = useRef(new Map<string, Entrada<unknown>>())
  // The state read by `recarregar` and by the poll is always the current one,
  // without them having to change identity on every render (they go down to buttons).
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

    // What the cache has goes in right away: switching periods and back does not flicker.
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

    // The window label follows the data that arrived: if only the metrics
    // came, the cards are already for the new period and the chart is not yet —
    // the chart is flagged by the failure notice, not by the label.
    if ((rMetrics?.data || rDias?.data?.days) || doCache.metrics || doCache.dias) setPeriodoDosDados(alvo.periodo)
    setFalhas(novasFalhas)
    setCarregando(false)
  }, [tz, lerCache])

  useEffect(() => {
    if (!habilitado) return
    carregar(estadoRef.current, false)
    // Only (period, workspace, workflow) slice these four calls; the other
    // state fields (status, search, view) belong to the table.
  }, [habilitado, estado.periodo, estado.workspace, estado.workflow, carregar])

  // Silent poll of the "Agora" strip: only the metrics (that is where `now`
  // lives), without turning on `carregando` — otherwise the indicators would
  // become a skeleton every 30 s. It does not bump the sequence: a full load
  // requested in the middle wins.
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
    // Returning to the tab after a long time away: refreshes right away instead of
    // waiting for the next tick — but not on every alt-tab.
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
