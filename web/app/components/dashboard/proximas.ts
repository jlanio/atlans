import type { IWorkflow } from "@/service/types"
import { dayjs, fromBackend } from "@/lib/dayjs"

/**
 * "Próximas execuções" agendadas (docs/specs/dashboard.md §3.6) — a única tela
 * que responde "o que vai rodar". Puro: recebe a listagem que o hook já buscou
 * e devolve, por horário, os até 5 workflows que efetivamente vão rodar em
 * seguida. A UI (`proximas-lista.tsx`) cuida de ícone, nome e texto do
 * agendamento com `projects/gatilho.ts`.
 */

export const MAXIMO_DE_PROXIMAS = 5

export function proximas(workflows: IWorkflow[], agora: Date = new Date()): IWorkflow[] {
  const ref = dayjs(agora)
  return workflows
    // `next_run_at` no passado é "calculando" (o agendador ainda não avançou a
    // marca), não uma próxima execução — e pausado/inativo não vai rodar.
    .map(wf => ({ wf, proxima: fromBackend(wf.schedule?.next_run_at) }))
    .filter(({ wf, proxima }) =>
      Boolean(wf.schedule?.active) && wf.flag_ative && proxima != null && proxima.isAfter(ref))
    .sort((a, b) => a.proxima!.valueOf() - b.proxima!.valueOf())
    .slice(0, MAXIMO_DE_PROXIMAS)
    .map(({ wf }) => wf)
}
