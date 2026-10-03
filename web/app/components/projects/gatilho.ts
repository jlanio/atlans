import type { IWorkflow, IWorkflowSchedule } from "@/service/types"
import { fromBackend, dayjs } from "@/lib/dayjs"
import { formatarInicio } from "@/lib/formatos"

/**
 * "What it is": a workflow's trigger and schedule (docs/specs/projects.md
 * §3.4). Pure — takes the booleans and the summary the listing already carries
 * and returns type, label and text; the icon belongs to the component, which is
 * the one that knows about color and size.
 */

export type TriggerKind = "agendado" | "webhook" | "arquivo" | "geofence" | "manual" | "subfluxo"

export interface Gatilho {
  /** The main one, in this precedence: sub-workflow > scheduled > webhook > file > geofence > manual. */
  tipo: TriggerKind
  /** "Agendado", "Agendado + webhook", "Só manual", "Chamado por outros workflows"… */
  rotulo: string
  /** Other triggers present, in the same precedence. */
  extras: TriggerKind[]
}

export const TRIGGER_LABEL: Record<TriggerKind, string> = {
  agendado: "Agendado",
  webhook: "Webhook",
  arquivo: "Por arquivo",
  geofence: "Por geofence",
  manual: "Só manual",
  subfluxo: "Chamado por outros workflows",
}

// How the trigger appears when it is the second in the list ("Agendado + webhook"):
// no preposition and in lowercase, so it reads as a single phrase.
const EXTRA_LABEL: Record<TriggerKind, string> = {
  agendado: "agendado",
  webhook: "webhook",
  arquivo: "arquivo",
  geofence: "geofence",
  manual: "manual",
  subfluxo: "sub-fluxo",
}

type TriggerFields = Pick<
  IWorkflow,
  "is_subworkflow" | "has_schedule_trigger" | "has_webhook_trigger" | "has_file_trigger" | "has_geofence_trigger"
>

export function derivarGatilho(wf: TriggerFields): Gatilho {
  // Sub-workflow comes first even with its own trigger: its nature is to be
  // called by another workflow, and that is what changes how the person runs it.
  const presentes: TriggerKind[] = []
  if (wf.is_subworkflow) presentes.push("subfluxo")
  if (wf.has_schedule_trigger) presentes.push("agendado")
  if (wf.has_webhook_trigger) presentes.push("webhook")
  if (wf.has_file_trigger) presentes.push("arquivo")
  if (wf.has_geofence_trigger) presentes.push("geofence")
  if (presentes.length === 0) return { tipo: "manual", rotulo: TRIGGER_LABEL.manual, extras: [] }

  const [tipo, ...extras] = presentes
  const rotulo = [TRIGGER_LABEL[tipo], ...extras.map(e => EXTRA_LABEL[e])].join(" + ")
  return { tipo, rotulo, extras }
}

export interface ScheduleSummary {
  /** pausado = `schedule.active` false (or inactive workflow); calculando = active without `next_run_at`. */
  estado: "ativo" | "pausado" | "calculando"
  /** "todo dia às 06:00" · "a cada 6 h" · raw cron when not recognized · "recorrência (RRULE)". */
  descricao: string
  /** `descricao` is the untranslated cron expression — the component shows it in `code`. */
  descricaoCrua: boolean
  /** "hoje, 18:00" / "amanhã, 06:00" / "1 out, 08:00"; null when paused or calculating. */
  proxima: string | null
  /** When paused because the workflow itself is inactive. */
  motivoPausa: "workflow inativo" | null
}

export function resumirAgendamento(
  schedule: IWorkflowSchedule | null | undefined,
  flagActive: boolean,
  agora: Date = new Date(),
): ScheduleSummary | null {
  if (!schedule) return null

  // An inactive workflow counts as paused even if the schedule row still
  // says `active`: the backend aligns the two on deactivation, but the list does
  // the optimistic switch before reloading — and what the person needs to know
  // is that it will not run.
  //
  // `next_run_at` in the past is "calculando", not "ativo": the scheduler has
  // not advanced the mark yet (it runs every ~30 s). Without this the row would
  // say "próxima há 3 h" or "próxima hoje, 06:00" for a time that already passed.
  const proxima = fromBackend(schedule.next_run_at)
  const nextInFuture = proxima != null && proxima.isAfter(dayjs(agora))
  const estado: ScheduleSummary["estado"] =
    !schedule.active || !flagActive ? "pausado" : nextInFuture ? "ativo" : "calculando"

  const { descricao, descricaoCrua } = describeStrategy(schedule)
  return {
    estado,
    descricao,
    descricaoCrua,
    proxima: estado === "ativo" ? formatarProxima(schedule.next_run_at, agora) : null,
    motivoPausa: estado === "pausado" && !flagActive ? "workflow inativo" : null,
  }
}

function describeStrategy(schedule: IWorkflowSchedule): { descricao: string; descricaoCrua: boolean } {
  switch (schedule.strategy) {
    case "cron": {
      const expr = schedule.cron_expression?.trim() ?? ""
      if (!expr) return { descricao: "agendamento", descricaoCrua: false }
      const traduzido = translateCron(expr)
      return { descricao: traduzido ?? expr, descricaoCrua: traduzido == null }
    }
    case "interval":
      return { descricao: descreverIntervalo(schedule.interval, schedule.unit), descricaoCrua: false }
    case "rrule":
      return { descricao: "recorrência (RRULE)", descricaoCrua: false }
    default:
      return { descricao: "agendamento", descricaoCrua: false }
  }
}

/**
 * Next run for the person looking at the list today: "amanhã, 06:00" is the
 * most common case of a daily schedule, and `formatarInicio` (made for the
 * past) would show it as "8 set, 06:00". The other cases are its own.
 */
export function formatarProxima(iso: string | null | undefined, agora: Date = new Date()): string {
  const d = fromBackend(iso)
  if (!d) return "—"
  if (d.isSame(dayjs(agora).add(1, "day"), "day")) return `amanhã, ${d.format("HH:mm")}`
  return formatarInicio(iso, agora)
}

// ── Cron ──────────────────────────────────────────────────────────────────

// Weekday as it is spoken: "às segundas", "aos domingos". 7 is Sunday
// too (both spellings are valid in cron).
const WEEKDAYS = ["aos domingos", "às segundas", "às terças", "às quartas", "às quintas", "às sextas", "aos sábados", "aos domingos"]

function inteiro(campo: string, min: number, max: number): number | null {
  if (!/^\d+$/.test(campo)) return null
  const n = Number(campo)
  return n >= min && n <= max ? n : null
}

function hora(h: number, m: number): string {
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
}

/**
 * Forms the screen translates — the ones the editor offers as presets and the
 * ones people write by hand without thinking. The hour is the cron's, in the
 * schedule's time zone, unconverted: it is what the person wrote. Returns null
 * for the rest.
 */
function translateCron(expr: string): string | null {
  const partes = expr.trim().split(/\s+/)
  if (partes.length !== 5) return null
  const [min, hor, dia, mes, sem] = partes
  const todos = (...campos: string[]) => campos.every(c => c === "*")

  if (todos(min, hor, dia, mes, sem)) return "a cada 1 min"

  const everyMin = /^\*\/(\d+)$/.exec(min)
  if (everyMin && todos(hor, dia, mes, sem)) {
    const n = Number(everyMin[1])
    return n > 0 ? `a cada ${n} min` : null
  }

  if (min === "0" && todos(dia, mes, sem)) {
    if (hor === "*") return "a cada 1 h"
    const everyHour = /^\*\/(\d+)$/.exec(hor)
    if (everyHour) {
      const n = Number(everyHour[1])
      return n > 0 ? `a cada ${n} h` : null
    }
  }

  const m = inteiro(min, 0, 59)
  const h = inteiro(hor, 0, 23)
  if (m == null || h == null || mes !== "*") return null
  const as = hora(h, m)

  if (dia === "*") {
    if (sem === "*") return `todo dia às ${as}`
    if (sem === "1-5") return `seg–sex às ${as}`
    const d = inteiro(sem, 0, 7)
    if (d != null) return `${WEEKDAYS[d]} às ${as}`
    return null
  }
  if (sem === "*") {
    const d = inteiro(dia, 1, 31)
    if (d != null) return `dia ${d} às ${as}`
  }
  return null
}

/** "a cada 15 min" / "a cada 6 h" / "a cada 2 dias" — scheduler units (`seconds|minutes|hours|days`). */
export function descreverIntervalo(interval: number | null | undefined, unit: string | null | undefined): string {
  if (interval == null || !Number.isFinite(interval) || interval <= 0) return "intervalo"
  const n = Math.round(interval)
  switch (unit) {
    case "seconds": return `a cada ${n} s`
    case "minutes": return `a cada ${n} min`
    case "hours": return `a cada ${n} h`
    case "days": return `a cada ${n} ${n === 1 ? "dia" : "dias"}`
    default: return unit ? `a cada ${n} ${unit}` : `a cada ${n}`
  }
}
