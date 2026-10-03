import type { IWorkflow } from "@/service/types"
import type { IWorkflowMetricsRow } from "@/service/types"
import type { RunningRun } from "@/context/ActiveRunsContext"
import { fromBackend, dayjs } from "@/lib/dayjs"
import { formatarDecorridoGrosso, formatarQuando, originLabel } from "@/lib/formatos"

/**
 * "Como anda" (how it is going): a workflow's last run (docs/specs/projects.md
 * §3.5). Pure — crosses the metrics row (30-day window, 45 s cache) with the
 * live run from `ActiveRunsContext` (10 s), which wins for being fresher.
 * Returns ready-made strings where the screen only displays ("quando",
 * "desde") and raw numbers where it formats ("61 execuções em 30 d · 3 falhas").
 */

/** Window of the listing metrics (`days=30`), the same one that separates "nunca" (never) from "sem execuções" (no runs). */
export const WINDOW_IN_DAYS = 30

export type HowItsGoing =
  | {
      tipo: "executando"
      /** "há 4 min"; empty when the run has no `started_at` yet. */
      desde: string
      /** Start instant (ms), to sort by run; now when unknown. */
      instante: number
      origem: string | null
      executor: string | null
      /** Median (s) of the runs in the window: "costuma levar 7 min". */
      tipica: number | null
    }
  | {
      tipo: "concluida" | "falhou" | "cancelada"
      /** "há 3 h" / "hoje, 18:00" / "ontem, 06:00" / "4 set, 03:00". */
      quando: string
      /** Instant (ms) of the last run, for sorting. */
      instante: number
      /** Only in `falhou`; null in the others. */
      erro: string | null
      total: number
      falhas: number
      mediana: number | null
    }
  /** No metrics row in the window (or `last_run_at` null) and the workflow is older than 30 days. */
  | { tipo: "sem-execucoes" }
  /** `total_runs` 0 and created less than 30 days ago: "execute uma vez para validar" (run once to validate). */
  | { tipo: "nunca" }
  /** The metrics failed. */
  | { tipo: "indisponivel" }

export function derivarComoAnda(
  wf: Pick<IWorkflow, "created_at">,
  metrica: IWorkflowMetricsRow | undefined,
  emExecucao: RunningRun | undefined,
  metricasIndisponiveis: boolean,
  agora: Date = new Date(),
): HowItsGoing {
  // The live run beats everything, including missing metrics: it comes from
  // another endpoint, at a 10 s cadence, and it is what the person is waiting to see.
  if (emExecucao) {
    const inicio = fromBackend(emExecucao.startedAt)
    return {
      tipo: "executando",
      desde: inicio ? formatarDecorridoGrosso(Math.max(0, dayjs(agora).diff(inicio, "second"))) : "",
      instante: inicio ? inicio.valueOf() : agora.getTime(),
      origem: originLabel(emExecucao.triggerSource),
      executor: emExecucao.executorName,
      tipica: metrica?.p50_seconds ?? null,
    }
  }

  if (metricasIndisponiveis) return { tipo: "indisponivel" }

  const ultima = fromBackend(metrica?.last_run_at)
  if (!metrica || !ultima || !metrica.last_status) return neverOrNoRuns(wf, metrica, agora)

  // Metrics say "running" but the context does not have the run: either the
  // context has not done its first poll yet, or the run ended less than 45 s
  // ago (cache). Showing "em execução" (running) with what is known is more
  // honest than guessing a final status nobody reported.
  if (metrica.last_status === "running" || metrica.last_status === "pending") {
    return {
      tipo: "executando",
      desde: formatarDecorridoGrosso(Math.max(0, dayjs(agora).diff(ultima, "second"))),
      instante: ultima.valueOf(),
      origem: null,
      executor: null,
      tipica: metrica.p50_seconds ?? null,
    }
  }

  const base = {
    quando: formatarQuando(metrica.last_run_at, agora),
    instante: ultima.valueOf(),
    erro: null,
    total: metrica.total_runs ?? 0,
    falhas: metrica.failed_runs ?? 0,
    mediana: metrica.p50_seconds ?? null,
  }
  switch (metrica.last_status) {
    case "failed":
    case "error":
      return { ...base, tipo: "falhou", erro: metrica.last_error?.trim() || null }
    case "cancelled":
      return { ...base, tipo: "cancelada" }
    default:
      // `success` and any terminal status the backend may come to create: the
      // run ended with no error recorded.
      return { ...base, tipo: "concluida" }
  }
}

function neverOrNoRuns(
  wf: Pick<IWorkflow, "created_at">,
  metrica: IWorkflowMetricsRow | undefined,
  agora: Date,
): HowItsGoing {
  // "Nunca" (never) is the invitation for the new workflow ("execute uma vez
  // para validar"); past the window, there is no way to know whether it ran
  // before it — and the text becomes the neutral "sem execuções em 30 dias".
  // Without `created_at` there is no way to claim it is new.
  const criado = fromBackend(wf.created_at)
  const noRuns = (metrica?.total_runs ?? 0) === 0
  const recente = criado != null && dayjs(agora).diff(criado, "day") < WINDOW_IN_DAYS
  return noRuns && recente ? { tipo: "nunca" } : { tipo: "sem-execucoes" }
}
