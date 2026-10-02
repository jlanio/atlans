// web/app/components/home/agendamentos/resumo.ts
//
// O resumo de um agendamento na lista da Home ("todo dia às 06:00 · amanhã,
// 06:00") no idioma de quem lê.
//
// Em português é `resumirAgendamento` de projects/gatilho TAL E QUAL — a mesma
// função do painel de administração, que segue em português —, e a Home em
// português não muda um byte. Nos outros idiomas o ESTADO continua vindo de lá
// (ativo, pausado, calculando e o motivo da pausa são regra de negócio, não
// texto) e só as frases são refeitas com o dicionário da Home: a cadência pelo
// MESMO reconhecimento de cron do gatilho (o que ele deixa cru segue cru nos
// três idiomas — é a expressão que a pessoa escreveu) e a próxima execução
// pelo `quando` da Home, com "amanhã" nomeado como em `formatarProxima`.

import { resumirAgendamento, type ResumoDoAgendamento } from "@/app/components/projects/gatilho"
import { dayjs, fromBackend } from "@/lib/dayjs"
import type { Idioma } from "@/lib/idioma"
import type { IWorkflowSchedule } from "@/service/types"
import { textosDaCascaDe, type TextosDaCasca } from "../i18n/da-casca"
import { FORMATOS } from "../i18n/formatos"

type Frases = TextosDaCasca["listas"]["agendamentos"]["resumo"]

/** O resumo com o motivo da pausa já no idioma (o gatilho o tipa como o texto em português). */
export type ResumoNoIdioma = Omit<ResumoDoAgendamento, "motivoPausa"> & { motivoPausa: string | null }

export function resumirNoIdioma(
  schedule: IWorkflowSchedule | null | undefined,
  flagAtive: boolean,
  idioma: Idioma,
  agora: Date = new Date(),
): ResumoNoIdioma | null {
  const resumo = resumirAgendamento(schedule, flagAtive, agora)
  if (idioma === "pt-BR" || !resumo || !schedule) return resumo
  return traduzirResumo(resumo, schedule, idioma, agora)
}

/**
 * As frases de um resumo do gatilho refeitas num idioma. Exportada para o teste
 * do molde: em português ela devolve exatamente o que o gatilho devolveu.
 */
export function traduzirResumo(
  resumo: ResumoDoAgendamento,
  schedule: IWorkflowSchedule,
  idioma: Idioma,
  agora: Date = new Date(),
): ResumoNoIdioma {
  const t = textosDaCascaDe(idioma).listas.agendamentos.resumo
  return {
    ...resumo,
    descricao: resumo.descricaoCrua ? resumo.descricao : descrever(schedule, idioma, t),
    proxima: resumo.proxima == null ? null : proximaExecucao(schedule.next_run_at, idioma, t, agora),
    motivoPausa: resumo.motivoPausa == null ? null : MOTIVO_DA_PAUSA[resumo.motivoPausa](t),
  }
}

// Um motivo novo no gatilho vira erro de tipo aqui — e não um motivo em
// português numa tela em inglês.
const MOTIVO_DA_PAUSA: Record<NonNullable<ResumoDoAgendamento["motivoPausa"]>, (t: Frases) => string> = {
  "workflow inativo": (t) => t.workflowInativo,
}

// A hora de relógio de cada idioma: o português com os dois dígitos de sempre
// ("06:00", como o gatilho); inglês e espanhol com as opções do `quando` da
// Home ("6:00 AM", "6:00" — ver i18n/formatos).
const OPCOES_DA_HORA: Record<Idioma, Intl.DateTimeFormatOptions> = {
  "pt-BR": { hour: "2-digit", minute: "2-digit" },
  en: { hour: "numeric", minute: "2-digit" },
  es: { hour: "numeric", minute: "2-digit" },
}

const RELOGIOS = new Map<string, Intl.DateTimeFormat>()

/** No fuso do navegador (a próxima execução) ou em UTC (a hora do cron, que é de relógio e não se converte). */
function relogio(idioma: Idioma, fuso?: "UTC"): Intl.DateTimeFormat {
  const chave = `${idioma}|${fuso ?? ""}`
  let formato = RELOGIOS.get(chave)
  if (!formato) {
    formato = new Intl.DateTimeFormat(idioma, { ...OPCOES_DA_HORA[idioma], timeZone: fuso })
    RELOGIOS.set(chave, formato)
  }
  return formato
}

/** "06:00" / "6:00 AM" — a hora que a pessoa escreveu no cron, sem conversão de fuso. */
function horaDoCron(idioma: Idioma, h: number, m: number): string {
  return relogio(idioma, "UTC").format(new Date(Date.UTC(2000, 0, 1, h, m)))
}

function proximaExecucao(iso: string | null, idioma: Idioma, t: Frases, agora: Date): string {
  const d = fromBackend(iso)
  if (!d) return "—"
  if (d.isSame(dayjs(agora).add(1, "day"), "day")) return `${t.amanha}, ${relogio(idioma).format(d.toDate())}`
  // No futuro o `quando` é o calendário ("hoje, 18:00", "1 out, 08:00") — o
  // mesmo `formatarInicio` que `formatarProxima` usa em português.
  return FORMATOS[idioma].quando(iso, agora)
}

function descrever(schedule: IWorkflowSchedule, idioma: Idioma, t: Frases): string {
  switch (schedule.strategy) {
    case "cron": {
      const expr = schedule.cron_expression?.trim() ?? ""
      if (!expr) return t.agendamento
      return traduzirCron(expr, idioma, t) ?? expr
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
 * As formas que o gatilho traduz (`traduzirCron` em projects/gatilho), na mesma
 * ordem e com as mesmas recusas. Um teste confere que o que o gatilho traduz,
 * esta também traduz; o sentido contrário não tem como aparecer, porque um cron
 * que o gatilho não traduz é mostrado cru antes de chegar aqui. Nulo para o resto.
 */
function traduzirCron(expr: string, idioma: Idioma, t: Frases): string | null {
  const partes = expr.trim().split(/\s+/)
  if (partes.length !== 5) return null
  const [min, hor, dia, mes, sem] = partes
  const todos = (...campos: string[]) => campos.every((c) => c === "*")

  if (todos(min, hor, dia, mes, sem)) return t.aCadaMinutos(1)

  const aCadaMin = /^\*\/(\d+)$/.exec(min)
  if (aCadaMin && todos(hor, dia, mes, sem)) {
    const n = Number(aCadaMin[1])
    return n > 0 ? t.aCadaMinutos(n) : null
  }

  if (min === "0" && todos(dia, mes, sem)) {
    if (hor === "*") return t.aCadaHoras(1)
    const aCadaHora = /^\*\/(\d+)$/.exec(hor)
    if (aCadaHora) {
      const n = Number(aCadaHora[1])
      return n > 0 ? t.aCadaHoras(n) : null
    }
  }

  const m = inteiro(min, 0, 59)
  const h = inteiro(hor, 0, 23)
  if (m == null || h == null || mes !== "*") return null
  const as = horaDoCron(idioma, h, m)

  if (dia === "*") {
    if (sem === "*") return t.todoDia(as)
    if (sem === "1-5") return t.segASex(as)
    const d = inteiro(sem, 0, 7)
    // O 7 também é domingo no cron.
    if (d != null) return t.naSemana(d % 7, as)
    return null
  }
  if (sem === "*") {
    const d = inteiro(dia, 1, 31)
    if (d != null) return t.noDia(d, as)
  }
  return null
}

/** O `descreverIntervalo` do gatilho, com as unidades do agendador (`seconds|minutes|hours|days`). */
function descreverIntervalo(interval: number | null | undefined, unit: string | null | undefined, t: Frases): string {
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
