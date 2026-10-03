// service/dominios/observabilidade.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post } from "../http"
import type {
  IExecutorMetrics, IObservabilityMetrics, IRunDetail, IRunEventsResponse, IRunSummary, IRunsByDay, IWorkflowMetrics, IWorkflowMetricsRow,
} from "../types"

// ── Observabilidade ────────────────────────────────────────────────────────

/**
 * Aggregated metrics for the requested window.
 *
 * `days` is actually sent (the panel let the backend fall back to the default
 * of 90 while the screen announced another window) and `force` bypasses the
 * ~45s Redis cache — that is what makes the Refresh button bring new numbers
 * instead of repeating the same memoized response. The names are those of the
 * Query in app/api/routers/observability_router.py (`days`, `force`).
 */
/**
 * Common History filters (docs/specs/metrics-history.md §3):
 * `workspace_id` and `workflow_id` slice the window; `tz` only matters for
 * `runs-by-day`, which cuts the day in the user's timezone.
 */
export function getObservabilityMetrics(
  days = 90, force = false, filtros: { workspace_id?: string; workflow_id?: string } = {},
) {
  return get<IObservabilityMetrics>(
    `/observability/metrics${qs({ days, force: force || undefined, ...filtros })}`,
  )
}

/** "By workflow" view: every accessible workflow with the window's numbers. */
export function getWorkflowMetricsList(days = 30, force = false, filtros: { workspace_id?: string } = {}) {
  return get<{ period_days: number; workflows: IWorkflowMetricsRow[] }>(
    `/observability/metrics/workflows${qs({ days, force: force || undefined, ...filtros })}`,
  )
}

export function getWorkflowMetrics(id: string, limit = 20) {
  return get<IWorkflowMetrics>(`/observability/metrics/workflow/${id}${qs({ limit })}`)
}

/** Same window and same cache as `getObservabilityMetrics` — see there. */
export function getExecutorMetrics(days = 90, force = false, filtros: { workspace_id?: string } = {}) {
  return get<{ executores: IExecutorMetrics[] }>(
    `/observability/metrics/executores${qs({ days, force: force || undefined, ...filtros })}`,
  )
}

export function getRunsByDay(days = 7, filtros: { workspace_id?: string; workflow_id?: string; tz?: string } = {}) {
  return get<{ days: IRunsByDay[] }>(`/observability/runs-by-day${qs({ days, ...filtros })}`)
}

export function getObservabilityRuns(params: {
  workflow_id?: string; status?: string; date_from?: string; date_to?: string;
  workspace_id?: string; trigger_source?: string; tier?: string
  /** Origin of the WORKFLOW ("assistente"), not of the trigger — that one is `trigger_source`. */
  workflow_origem?: string
  /** Searches in `error_message` and in the workflow name. */
  q?: string
  /** Executor hostname. The name has to match the backend's Query —
   *  `agent_host` was silently discarded by FastAPI. */
  worker_host?: string; limit?: number; offset?: number
  /** Requests the full COUNT. The COUNT over filtered `runs` is the expensive
   *  part of the listing and only the first page needs it — on the following
   *  ones `has_more` is enough, which the backend answers for free. */
  with_total?: boolean
} = {}) {
  return get<{
    total: number; limit: number; offset: number; runs: IRunSummary[]
    /** There is at least one more page after this one. Comes instead of a
     *  `total` recomputed on every "see more". */
    has_more?: boolean
  }>(
    `/observability/runs${qs(params)}`,
  )
}

export function getRunDetail(runId: string) { return get<IRunDetail>(`/observability/runs/${runId}`) }

/** Interrupts a run in progress. The final status arrives through the usual
 *  path (the executor's job_result → `__workflow_complete__`). */
export function cancelRun(runId: string) {
  return post<{ run_id: string; outcome: string }>(`/workflows/runs/${runId}/cancel`, {})
}

/** Triggers a NEW run of this run's workflow (the current definition; it is
 *  not a replay — `WorkflowRun` does not store the inputs). The backend
 *  validates that the run belongs to the workflow and records
 *  `trigger_source="retry"`. 403 when the role does not allow executing or the
 *  workflow is disabled. */
export function retryRun(workflowId: string, runId: string) {
  return post<{ task_id: string; message: string }>(`/workflows/${workflowId}/runs/${runId}/retry`, {})
}

/** Raw events of a run — the same replay the WebSocket delivers on
 *  connecting, exposed over HTTP to reopen the log of finished runs.
 *  The history lives in Redis with a 1h TTL (`expired` signals it has expired). */
export function getRunEvents(runId: string) {
  return get<IRunEventsResponse>(`/observability/runs/${runId}/events`)
}
