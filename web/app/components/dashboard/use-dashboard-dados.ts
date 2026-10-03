"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IResponse } from "@/service/types"
import type { IWorkflow } from "@/service/types"
import type {
  IExecutorMetrics, IObservabilityMetrics, IRunSummary, IRunsByDay,
} from "@/service/types"

/**
 * Dashboard data (docs/specs/dashboard.md §3.3).
 *
 * Five scoped sources start together per scope (`Promise.allSettled`):
 * metrics (the SPINE — health + attention + indicators), runs per day
 * (chart), recent runs (activity), executors ("at ceiling" item of
 * attention) and the workflow listing (upcoming runs).
 *
 * Only `metrics` blocks: if it fails on the scope's 1st load, `erroEspinha` takes
 * over the screen; on reloads with data on screen it degrades per section
 * (`falhas.metrics`), like the others. `executores` is the only one that doesn't
 * become a warning — failure → `[]`, and attention only loses the "executor at
 * ceiling" item. The instant (`now`) comes only from `metrics` (not from
 * `ActiveRunsContext`, which belongs to the active workspace and doesn't serve
 * the "todos" scope): a 30 s poll renews only the metrics, without flashing the screen.
 *
 * The scope already arrives resolved in `scopeWorkspaceId` (`null` = "todos");
 * changing scope restarts that scope's 1st load (skeleton). The one that decides
 * the id from `?escopo=` and the active workspace is `index` — so the hook doesn't
 * reload when `current` changes while the scope is "todos".
 *
 * The window arrives in `dias` (7/30/90, from `?periodo=`) and scales the three
 * period sources — metrics, runs per day and executors. Changing only the period
 * is a RELOAD (the button spins, the screen stays and updates when the new data
 * arrives), like History's selector; only a scope change shows the skeleton.
 */

export interface DashboardData {
  metrics: IObservabilityMetrics | null
  dias: IRunsByDay[]
  runs: IRunSummary[]
  executores: IExecutorMetrics[]
  workflows: IWorkflow[]
  /** 1st load of the current scope (skeleton). */
  carregando: boolean
  /** Subsequent reloads (the button spins, the screen stays). */
  atualizando: boolean
  /** Per section that failed on the last load; what was already there stays on screen. */
  falhas: { metrics: boolean; dias: boolean; runs: boolean; workflows: boolean }
  /** Only when `metrics` fails on the 1st load of the current scope (including a scope change): blocks the screen. */
  erroEspinha: string | null
  /** "Atualizar" passes `force: true` to bypass the metrics cache in the backend. */
  recarregar: (opts?: { force?: boolean }) => void
}

/** Health renews every 30 s while the tab is visible (spec §3.3); the instant is not a window. */
export const HEALTH_INTERVAL_MS = 30_000
/** Few rows: recent activity is a summary, not a table (spec §3.7). */
export const RUNS_LIMIT = 6

const DEFAULT_BACKBONE_ERROR = "Não foi possível carregar o painel."

const NO_FAILURES = { metrics: false, dias: false, runs: false, workflows: false }

/** `allSettled` never rejects; neither does the service — but an unexpected `throw` must not bring down the screen. */
function resposta<T>(r: PromiseSettledResult<IResponse<T> | null>): IResponse<T> | null {
  return r.status === "fulfilled" ? r.value : null
}

function fusoDoNavegador(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  } catch {
    return "UTC"
  }
}

// `scopeWorkspaceId`: `null` = "todos"; an id = that workspace; `undefined` =
// scope not defined yet (the active workspace is loading) — do NOT fetch, the
// skeleton stays. Without this third state, the "ativo" scope fetched "todos"
// for an instant (id still null) and flashed the wrong dashboard before reloading.
export function useDashboardDados(scopeWorkspaceId: string | null | undefined, periodo: number): DashboardData {
  const [metrics, setMetrics] = useState<IObservabilityMetrics | null>(null)
  const [dias, setDays] = useState<IRunsByDay[]>([])
  const [runs, setRuns] = useState<IRunSummary[]>([])
  const [executores, setExecutors] = useState<IExecutorMetrics[]>([])
  const [workflows, setWorkflows] = useState<IWorkflow[]>([])
  const [carregando, setLoading] = useState(true)
  const [atualizando, setRefreshing] = useState(false)
  const [falhas, setFailures] = useState(NO_FAILURES)
  const [erroEspinha, setBackboneError] = useState<string | null>(null)

  // Sequence stamp: changing scope twice in a row fires two loads, and the
  // slower one may answer last. Only the last load requested writes to the
  // screen.
  const seq = useRef(0)
  // Scope whose data is ON SCREEN (`undefined` = never loaded with the spine;
  // `null` = "todos"). Separates skeleton (scope's 1st load) from "the button spins".
  const scopeOnScreen = useRef<string | null | undefined>(undefined)
  // The current scope, read by `recarregar` and by the poll without changing
  // identity on every render. (`undefined` = not defined yet — doesn't fetch.)
  const scopeRef = useRef<string | null | undefined>(scopeWorkspaceId)
  scopeRef.current = scopeWorkspaceId
  // The current window (number of days), read by `recarregar` and by the health
  // poll without changing identity on every render. (`dias`, the state, is the
  // chart series — hence the name `periodo` here.)
  const periodRef = useRef(periodo)
  periodRef.current = periodo
  // When an "Atualizar" (force) wrote fresh metrics. A background tick that
  // started BEFORE fetches the cache and, arriving later, would overwrite the
  // fresh data with the stale — the two don't change the sequence. The tick
  // checks this stamp and gives up (same pattern as `use-projetos-dados`).
  const forcedAt = useRef(0)
  const tz = useMemo(fusoDoNavegador, [])

  const carregar = useCallback(async (alvo: string | null, periodo: number, force: boolean) => {
    const mine = ++seq.current
    // `primeira` is per SCOPE: a scope's 1st load shows the skeleton and empties
    // the section that fails. Changing only the period doesn't change `alvo` → it
    // is a reload (the button spins, the screen stays), like History's selector.
    const primeira = scopeOnScreen.current !== alvo
    if (primeira) setLoading(true)
    else setRefreshing(true)

    const workspace_id = alvo ?? undefined
    const [rMetrics, rDays, rRuns, rExecutors, rWorkflows] = await Promise.allSettled([
      GisFlowService.getObservabilityMetrics(periodo, force, { workspace_id }),
      GisFlowService.getRunsByDay(periodo, { workspace_id, tz }),
      GisFlowService.getObservabilityRuns({ limit: RUNS_LIMIT, workspace_id }),
      GisFlowService.getExecutorMetrics(periodo, force, { workspace_id }),
      // Including the assistant's ones: the dashboard summarizes what exists, and
      // "Próximas execuções" without them would hide precisely what runs on its own.
      GisFlowService.getWorkflows(workspace_id, { incluirDoAssistente: true }),
    ])
    if (mine !== seq.current) return

    const metricsRes = resposta(rMetrics)
    const daysRes = resposta(rDays)
    const runsRes = resposta(rRuns)
    const execRes = resposta(rExecutors)
    const workflowsRes = resposta(rWorkflows)

    const newFailures = { ...NO_FAILURES }

    // Spine. Success clears the error. Failure only blocks on the scope's 1st load
    // (`primeira`, which a scope change also fires): then the screen shows "não
    // foi possível carregar" and the previous scope's data doesn't leak. On a
    // reload of the same scope, it degrades per section and the rest carries on.
    if (metricsRes?.data) {
      if (force) forcedAt.current = Date.now()
      setMetrics(metricsRes.data)
      setBackboneError(null)
      scopeOnScreen.current = alvo
    } else {
      newFailures.metrics = true
      if (primeira) {
        setBackboneError(metricsRes?.error?.message ?? DEFAULT_BACKBONE_ERROR)
        setMetrics(null)
      }
    }

    // The others degrade per section. On a RELOAD of the same scope, what was
    // there stays (§3.3, "nunca zerar a tela"); on a scope CHANGE
    // (`primeira`), the section that fails is emptied — showing the previous
    // workspace's data under the new scope would confuse the reading (§3.10).
    if (daysRes?.data?.days) setDays(daysRes.data.days)
    else { newFailures.dias = true; if (primeira) setDays([]) }

    if (runsRes?.data?.runs) setRuns(runsRes.data.runs)
    else { newFailures.runs = true; if (primeira) setRuns([]) }

    if (workflowsRes?.data) setWorkflows(workflowsRes.data)
    else { newFailures.workflows = true; if (primeira) setWorkflows([]) }

    // Executors is the only optional source that doesn't become a warning: failure → `[]`.
    setExecutors(execRes?.data?.executores ?? [])

    setFailures(newFailures)
    setLoading(false)
    setRefreshing(false)
  }, [tz])

  // Reloads when the scope changes. Since `index` only changes `scopeWorkspaceId`
  // when the scope is "ativo" and `current` changes (in "todos" it is always
  // `null`), this already covers the spec's rule without the hook knowing the context.
  //
  // `undefined` = active scope still without an id (workspace loading): doesn't
  // fetch, the skeleton (initial state `carregando=true`) stays until the id is known.
  useEffect(() => {
    if (scopeWorkspaceId === undefined) return
    carregar(scopeWorkspaceId, periodo, false)
  }, [scopeWorkspaceId, periodo, carregar])

  // Silent health poll: only the metrics (where `now` lives), without turning on
  // `carregando`/`atualizando`. Doesn't increment the sequence: a full load
  // requested in the middle wins.
  useEffect(() => {
    if (HEALTH_INTERVAL_MS <= 0) return
    let ultimo = Date.now()
    async function refreshHealth() {
      const alvo = scopeRef.current
      if (alvo === undefined) return   // escopo ainda indefinido: nada a renovar
      const mine = seq.current
      const inicio = Date.now()
      ultimo = inicio
      const res = await GisFlowService.getObservabilityMetrics(periodRef.current, false, { workspace_id: alvo ?? undefined })
      // Failed, arrived late (another load took over), or an "Atualizar" wrote
      // fresh data while this tick was fetching the cache: what was there stays.
      if (mine !== seq.current || forcedAt.current > inicio || !res.data) return
      setMetrics(res.data)
      setBackboneError(null)
      // If the scope's health recovers through here (its 1st load had
      // failed), the scope becomes "on screen" — a later "Tentar de novo"
      // doesn't repeat the skeleton for nothing.
      scopeOnScreen.current = alvo
    }
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") refreshHealth()
    }, HEALTH_INTERVAL_MS)
    // Coming back to the tab after a long time away renews right away, but not on every alt-tab.
    const onVisibility = () => {
      if (document.visibilityState === "visible" && Date.now() - ultimo >= HEALTH_INTERVAL_MS) refreshHealth()
    }
    document.addEventListener("visibilitychange", onVisibility)
    return () => {
      clearInterval(timer)
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [])

  const recarregar = useCallback((opts: { force?: boolean } = {}) => {
    if (scopeRef.current === undefined) return   // scope not defined yet
    carregar(scopeRef.current, periodRef.current, opts.force ?? false)
  }, [carregar])

  return useMemo(() => ({
    metrics, dias, runs, executores, workflows,
    carregando, atualizando, falhas, erroEspinha, recarregar,
  }), [metrics, dias, runs, executores, workflows, carregando, atualizando, falhas, erroEspinha, recarregar])
}
