// service/dominios/observabilidade.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post } from "../http"
import type {
  IExecutorMetrics, IObservabilityMetrics, IRunDetail, IRunEventsResponse, IRunSummary, IRunsByDay, IWorkflowMetrics, IWorkflowMetricsRow,
} from "../types"

// ── Observabilidade ────────────────────────────────────────────────────────

/**
 * Métricas agregadas da janela pedida.
 *
 * `days` viaja de verdade (o painel deixava o backend cair no default de 90
 * enquanto a tela anunciava outra janela) e `force` ignora o cache Redis de
 * ~45s — é o que faz o botão Atualizar trazer números novos em vez de repetir
 * a mesma resposta memorizada. Os nomes são os do Query em
 * app/api/routers/observability_router.py (`days`, `force`).
 */
/**
 * Filtros comuns do Histórico (docs/specs/metrics-history.md §3):
 * `workspace_id` e `workflow_id` recortam a janela; `tz` só importa para
 * `runs-by-day`, que corta o dia no fuso do usuário.
 */
export function getObservabilityMetrics(
  days = 90, force = false, filtros: { workspace_id?: string; workflow_id?: string } = {},
) {
  return get<IObservabilityMetrics>(
    `/observability/metrics${qs({ days, force: force || undefined, ...filtros })}`,
  )
}

/** Visão "Por workflow": todos os workflows acessíveis com números da janela. */
export function getWorkflowMetricsList(days = 30, force = false, filtros: { workspace_id?: string } = {}) {
  return get<{ period_days: number; workflows: IWorkflowMetricsRow[] }>(
    `/observability/metrics/workflows${qs({ days, force: force || undefined, ...filtros })}`,
  )
}

export function getWorkflowMetrics(id: string, limit = 20) {
  return get<IWorkflowMetrics>(`/observability/metrics/workflow/${id}${qs({ limit })}`)
}

/** Mesma janela e mesmo cache de `getObservabilityMetrics` — ver ali. */
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
  /** Origem do FLUXO ("assistente"), não do disparo — este é `trigger_source`. */
  workflow_origem?: string
  /** Busca em `error_message` e no nome do workflow. */
  q?: string
  /** Hostname do executor. O nome tem de bater com o Query do backend —
   *  `agent_host` era descartado em silêncio pelo FastAPI. */
  worker_host?: string; limit?: number; offset?: number
  /** Pede o COUNT completo. O COUNT sobre `runs` filtrado é a parte cara da
   *  listagem e só a primeira página precisa dele — nas seguintes basta
   *  `has_more`, que o backend responde de graça. */
  with_total?: boolean
} = {}) {
  return get<{
    total: number; limit: number; offset: number; runs: IRunSummary[]
    /** Existe pelo menos mais uma página depois desta. Vem no lugar de um
     *  `total` recalculado a cada "ver mais". */
    has_more?: boolean
  }>(
    `/observability/runs${qs(params)}`,
  )
}

export function getRunDetail(runId: string) { return get<IRunDetail>(`/observability/runs/${runId}`) }

/** Interrompe uma execução em andamento. O status final chega pelo mesmo
 *  caminho de sempre (job_result do executor → `__workflow_complete__`). */
export function cancelRun(runId: string) {
  return post<{ run_id: string; outcome: string }>(`/workflows/runs/${runId}/cancel`, {})
}

/** Dispara uma execução NOVA do workflow desta run (a definição atual; não
 *  é replay — `WorkflowRun` não guarda as entradas). O backend valida que a
 *  run pertence ao workflow e grava `trigger_source="retry"`. 403 quando o
 *  papel não permite executar ou o workflow está desativado. */
export function retryRun(workflowId: string, runId: string) {
  return post<{ task_id: string; message: string }>(`/workflows/${workflowId}/runs/${runId}/retry`, {})
}

/** Eventos brutos de um run — o mesmo replay que o WebSocket entrega ao
 *  conectar, exposto por HTTP para reabrir o log de execuções concluídas.
 *  O histórico vive no Redis com TTL de 1h (`expired` sinaliza vencido). */
export function getRunEvents(runId: string) {
  return get<IRunEventsResponse>(`/observability/runs/${runId}/events`)
}
