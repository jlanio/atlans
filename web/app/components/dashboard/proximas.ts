import type { IWorkflow } from "@/service/types"
import { dayjs, fromBackend } from "@/lib/dayjs"

/**
 * Scheduled "Próximas execuções" (docs/specs/dashboard.md §3.6) — the only
 * screen that answers "what is going to run". Pure: receives the listing the
 * hook already fetched and returns, by time, the up to 5 workflows that will
 * actually run next. The UI (`proximas-lista.tsx`) takes care of the icon,
 * name and schedule text with `projects/gatilho.ts`.
 */

export const MAXIMO_DE_PROXIMAS = 5

export function proximas(workflows: IWorkflow[], agora: Date = new Date()): IWorkflow[] {
  const ref = dayjs(agora)
  return workflows
    // A `next_run_at` in the past is "calculating" (the scheduler hasn't advanced
    // the mark yet), not an upcoming run — and paused/inactive won't run.
    .map(wf => ({ wf, proxima: fromBackend(wf.schedule?.next_run_at) }))
    .filter(({ wf, proxima }) =>
      Boolean(wf.schedule?.active) && wf.flag_ative && proxima != null && proxima.isAfter(ref))
    .sort((a, b) => a.proxima!.valueOf() - b.proxima!.valueOf())
    .slice(0, MAXIMO_DE_PROXIMAS)
    .map(({ wf }) => wf)
}
