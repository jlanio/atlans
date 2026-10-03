// web/app/components/home/agendamentos/resumo.ts
//
// The summary of a schedule in the Home list ("todo dia às 06:00 · amanhã,
// 06:00") in the reader's language.
//
// In Portuguese it is `resumirAgendamento` from projects/gatilho AS IS — the same
// function as the administration panel, which stays in Portuguese —, and the
// Portuguese Home doesn't change a byte. In the other languages the STATE still
// comes from there (active, paused, calculating and the pause reason are
// business rules, not text) and only the sentences are rebuilt with the Home's
// dictionary: the cadence through the SAME cron recognition as the trigger (what
// it leaves raw stays raw in all three languages — it is the expression the
// person wrote) and the next run through the Home's `quando`, with "amanhã"
// (tomorrow) named as in `formatarProxima`.

import { resumirAgendamento, type ScheduleSummary } from "@/app/components/projects/gatilho"
import { dayjs, fromBackend } from "@/lib/dayjs"
import type { Idioma } from "@/lib/idioma"
import type { IWorkflowSchedule } from "@/service/types"
import { shellTextsFor, type ShellTexts } from "../i18n/da-casca"
import { FORMATOS } from "../i18n/formatos"

type Phrases = ShellTexts["listas"]["agendamentos"]["resumo"]

/** The summary with the pause reason already in the language (the trigger types it as the Portuguese text). */
export type LocalizedSummary = Omit<ScheduleSummary, "motivoPausa"> & { motivoPausa: string | null }

export function resumirNoIdioma(
  schedule: IWorkflowSchedule | null | undefined,
  flagActive: boolean,
  idioma: Idioma,
  agora: Date = new Date(),
): LocalizedSummary | null {
  const resumo = resumirAgendamento(schedule, flagActive, agora)
  if (idioma === "pt-BR" || !resumo || !schedule) return resumo
  return translateSummary(resumo, schedule, idioma, agora)
}

/**
 * The sentences of a trigger summary rebuilt in a language. Exported for the
 * template test: in Portuguese it returns exactly what the trigger returned.
 */
export function translateSummary(
  resumo: ScheduleSummary,
  schedule: IWorkflowSchedule,
  idioma: Idioma,
  agora: Date = new Date(),
): LocalizedSummary {
  const t = shellTextsFor(idioma).listas.agendamentos.resumo
  return {
    ...resumo,
    descricao: resumo.descricaoCrua ? resumo.descricao : descrever(schedule, idioma, t),
    proxima: resumo.proxima == null ? null : nextRun(schedule.next_run_at, idioma, t, agora),
    motivoPausa: resumo.motivoPausa == null ? null : PAUSE_REASON[resumo.motivoPausa](t),
  }
}

// A new reason in the trigger becomes a type error here — and not a
// Portuguese reason on an English screen.
const PAUSE_REASON: Record<NonNullable<ScheduleSummary["motivoPausa"]>, (t: Phrases) => string> = {
  "workflow inativo": (t) => t.workflowInativo,
}

// The clock time for each language: Portuguese with the usual two digits
// ("06:00", like the trigger); English and Spanish with the options of the
// Home's `quando` ("6:00 AM", "6:00" — see i18n/formatos).
const TIME_OPTIONS: Record<Idioma, Intl.DateTimeFormatOptions> = {
  "pt-BR": { hour: "2-digit", minute: "2-digit" },
  en: { hour: "numeric", minute: "2-digit" },
  es: { hour: "numeric", minute: "2-digit" },
}

const CLOCKS = new Map<string, Intl.DateTimeFormat>()

/** In the browser's time zone (the next run) or in UTC (the cron time, which is a clock time and isn't converted). */
function relogio(idioma: Idioma, fuso?: "UTC"): Intl.DateTimeFormat {
  const chave = `${idioma}|${fuso ?? ""}`
  let formato = CLOCKS.get(chave)
  if (!formato) {
    formato = new Intl.DateTimeFormat(idioma, { ...TIME_OPTIONS[idioma], timeZone: fuso })
    CLOCKS.set(chave, formato)
  }
  return formato
}

/** "06:00" / "6:00 AM" — the time the person wrote in the cron, without time zone conversion. */
function cronTime(idioma: Idioma, h: number, m: number): string {
  return relogio(idioma, "UTC").format(new Date(Date.UTC(2000, 0, 1, h, m)))
}

function nextRun(iso: string | null, idioma: Idioma, t: Phrases, agora: Date): string {
  const d = fromBackend(iso)
  if (!d) return "—"
  if (d.isSame(dayjs(agora).add(1, "day"), "day")) return `${t.amanha}, ${relogio(idioma).format(d.toDate())}`
  // In the future `quando` is the calendar ("hoje, 18:00", "1 out, 08:00") — the
  // same `formatarInicio` that `formatarProxima` uses in Portuguese.
  return FORMATOS[idioma].quando(iso, agora)
}

function descrever(schedule: IWorkflowSchedule, idioma: Idioma, t: Phrases): string {
  switch (schedule.strategy) {
    case "cron": {
      const expr = schedule.cron_expression?.trim() ?? ""
      if (!expr) return t.agendamento
      return translateCron(expr, idioma, t) ?? expr
    }
    case "interval":
      return descreverIntervalo(schedule.interval, schedule.unit, t)
    case "rrule":
      return t.recorrencia
    default:
      return t.agendamento
  }
}

function inteiro(campo: string, min: number, max: number): number | null {
  if (!/^\d+$/.test(campo)) return null
  const n = Number(campo)
  return n >= min && n <= max ? n : null
}

/**
 * The forms the trigger translates (`translateCron` in projects/gatilho), in the
 * same order and with the same refusals. A test checks that what the trigger
 * translates, this one translates too; the reverse can't happen, because a cron
 * the trigger doesn't translate is shown raw before reaching here. Null for the rest.
 */
function translateCron(expr: string, idioma: Idioma, t: Phrases): string | null {
  const partes = expr.trim().split(/\s+/)
  if (partes.length !== 5) return null
  const [min, hor, dia, mes, sem] = partes
  const todos = (...campos: string[]) => campos.every((c) => c === "*")

  if (todos(min, hor, dia, mes, sem)) return t.aCadaMinutos(1)

  const everyMin = /^\*\/(\d+)$/.exec(min)
  if (everyMin && todos(hor, dia, mes, sem)) {
    const n = Number(everyMin[1])
    return n > 0 ? t.aCadaMinutos(n) : null
  }

  if (min === "0" && todos(dia, mes, sem)) {
    if (hor === "*") return t.aCadaHoras(1)
    const everyHour = /^\*\/(\d+)$/.exec(hor)
    if (everyHour) {
      const n = Number(everyHour[1])
      return n > 0 ? t.aCadaHoras(n) : null
    }
  }

  const m = inteiro(min, 0, 59)
  const h = inteiro(hor, 0, 23)
  if (m == null || h == null || mes !== "*") return null
  const as = cronTime(idioma, h, m)

  if (dia === "*") {
    if (sem === "*") return t.todoDia(as)
    if (sem === "1-5") return t.segASex(as)
    const d = inteiro(sem, 0, 7)
    // 7 is also Sunday in cron.
    if (d != null) return t.naSemana(d % 7, as)
    return null
  }
  if (sem === "*") {
    const d = inteiro(dia, 1, 31)
    if (d != null) return t.noDia(d, as)
  }
  return null
}

/** The trigger's `descreverIntervalo`, with the scheduler's units (`seconds|minutes|hours|days`). */
function descreverIntervalo(interval: number | null | undefined, unit: string | null | undefined, t: Phrases): string {
  if (interval == null || !Number.isFinite(interval) || interval <= 0) return t.intervalo
  const n = Math.round(interval)
  switch (unit) {
    case "seconds": return t.aCadaSegundos(n)
    case "minutes": return t.aCadaMinutos(n)
    case "hours": return t.aCadaHoras(n)
    case "days": return t.aCadaDias(n)
    default: return unit ? t.aCadaUnidade(n, unit) : t.aCada(n)
  }
}
