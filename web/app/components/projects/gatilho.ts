import type { IWorkflow, IWorkflowSchedule } from "@/service/types"
import { fromBackend, dayjs } from "@/lib/dayjs"
import { formatarInicio } from "@/lib/formatos"

/**
 * "O que ele é": gatilho e agendamento de um workflow (docs/specs/projetos.md
 * §3.4). Puro — recebe os booleanos e o resumo que a listagem já traz e
 * devolve tipo, rótulo e texto; o ícone é do componente, que é quem sabe de
 * cor e tamanho.
 */

export type TipoDeGatilho = "agendado" | "webhook" | "arquivo" | "geofence" | "manual" | "subfluxo"

export interface Gatilho {
  /** O principal, nesta precedência: subfluxo > agendado > webhook > arquivo > geofence > manual. */
  tipo: TipoDeGatilho
  /** "Agendado", "Agendado + webhook", "Só manual", "Chamado por outros workflows"… */
  rotulo: string
  /** Demais gatilhos presentes, na mesma precedência. */
  extras: TipoDeGatilho[]
}

export const ROTULO_DO_GATILHO: Record<TipoDeGatilho, string> = {
  agendado: "Agendado",
  webhook: "Webhook",
  arquivo: "Por arquivo",
  geofence: "Por geofence",
  manual: "Só manual",
  subfluxo: "Chamado por outros workflows",
}

// Como o gatilho aparece quando é o segundo da lista ("Agendado + webhook"):
// sem preposição e em caixa baixa, para ler como uma frase só.
const ROTULO_DE_EXTRA: Record<TipoDeGatilho, string> = {
  agendado: "agendado",
  webhook: "webhook",
  arquivo: "arquivo",
  geofence: "geofence",
  manual: "manual",
  subfluxo: "sub-fluxo",
}

type CamposDoGatilho = Pick<
  IWorkflow,
  "is_subworkflow" | "has_schedule_trigger" | "has_webhook_trigger" | "has_file_trigger" | "has_geofence_trigger"
>

export function derivarGatilho(wf: CamposDoGatilho): Gatilho {
  // Sub-fluxo vem primeiro mesmo com gatilho próprio: a natureza dele é ser
  // chamado por outro workflow, e é isso que muda como a pessoa o executa.
  const presentes: TipoDeGatilho[] = []
  if (wf.is_subworkflow) presentes.push("subfluxo")
  if (wf.has_schedule_trigger) presentes.push("agendado")
  if (wf.has_webhook_trigger) presentes.push("webhook")
  if (wf.has_file_trigger) presentes.push("arquivo")
  if (wf.has_geofence_trigger) presentes.push("geofence")
  if (presentes.length === 0) return { tipo: "manual", rotulo: ROTULO_DO_GATILHO.manual, extras: [] }

  const [tipo, ...extras] = presentes
  const rotulo = [ROTULO_DO_GATILHO[tipo], ...extras.map(e => ROTULO_DE_EXTRA[e])].join(" + ")
  return { tipo, rotulo, extras }
}

export interface ResumoDoAgendamento {
  /** pausado = `schedule.active` false (ou workflow inativo); calculando = ativo sem `next_run_at`. */
  estado: "ativo" | "pausado" | "calculando"
  /** "todo dia às 06:00" · "a cada 6 h" · cron cru quando não reconhecido · "recorrência (RRULE)". */
  descricao: string
  /** `descricao` é a expressão cron sem tradução — o componente a mostra em `code`. */
  descricaoCrua: boolean
  /** "hoje, 18:00" / "amanhã, 06:00" / "1 out, 08:00"; nulo quando pausado ou calculando. */
  proxima: string | null
  /** Quando pausado porque o próprio workflow está inativo. */
  motivoPausa: "workflow inativo" | null
}

export function resumirAgendamento(
  schedule: IWorkflowSchedule | null | undefined,
  flagAtive: boolean,
  agora: Date = new Date(),
): ResumoDoAgendamento | null {
  if (!schedule) return null

  // Workflow inativo conta como pausado mesmo que a linha do schedule ainda
  // diga `active`: o backend alinha os dois ao desativar, mas a lista faz a
  // troca otimista antes de recarregar — e o que a pessoa precisa saber é
  // que não vai rodar.
  //
  // `next_run_at` no passado é "calculando", não "ativo": o agendador ainda
  // não avançou a marca (roda a cada ~30 s). Sem isto a linha diria "próxima
  // há 3 h" ou "próxima hoje, 06:00" para um horário que já passou.
  const proxima = fromBackend(schedule.next_run_at)
  const proximaNoFuturo = proxima != null && proxima.isAfter(dayjs(agora))
  const estado: ResumoDoAgendamento["estado"] =
    !schedule.active || !flagAtive ? "pausado" : proximaNoFuturo ? "ativo" : "calculando"

  const { descricao, descricaoCrua } = descreverEstrategia(schedule)
  return {
    estado,
    descricao,
    descricaoCrua,
    proxima: estado === "ativo" ? formatarProxima(schedule.next_run_at, agora) : null,
    motivoPausa: estado === "pausado" && !flagAtive ? "workflow inativo" : null,
  }
}

function descreverEstrategia(schedule: IWorkflowSchedule): { descricao: string; descricaoCrua: boolean } {
  switch (schedule.strategy) {
    case "cron": {
      const expr = schedule.cron_expression?.trim() ?? ""
      if (!expr) return { descricao: "agendamento", descricaoCrua: false }
      const traduzido = traduzirCron(expr)
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
 * Próxima execução para a pessoa que olha a lista hoje: "amanhã, 06:00" é o
 * caso mais comum de um agendamento diário e `formatarInicio` (feito para o
 * passado) o mostraria como "8 set, 06:00". Os demais casos são os dele.
 */
export function formatarProxima(iso: string | null | undefined, agora: Date = new Date()): string {
  const d = fromBackend(iso)
  if (!d) return "—"
  if (d.isSame(dayjs(agora).add(1, "day"), "day")) return `amanhã, ${d.format("HH:mm")}`
  return formatarInicio(iso, agora)
}

// ── Cron ──────────────────────────────────────────────────────────────────

// Dia da semana como se fala: "às segundas", "aos domingos". O 7 é domingo
// também (as duas grafias valem no cron).
const DIAS_DA_SEMANA = ["aos domingos", "às segundas", "às terças", "às quartas", "às quintas", "às sextas", "aos sábados", "aos domingos"]

function inteiro(campo: string, min: number, max: number): number | null {
  if (!/^\d+$/.test(campo)) return null
  const n = Number(campo)
  return n >= min && n <= max ? n : null
}

function hora(h: number, m: number): string {
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
}

/**
 * Formas que a tela traduz — as que o editor oferece como preset e as que se
 * escrevem à mão sem pensar. A hora é a do cron no fuso do agendamento, sem
 * converter: é o que a pessoa escreveu. Devolve nulo para o resto.
 */
function traduzirCron(expr: string): string | null {
  const partes = expr.trim().split(/\s+/)
  if (partes.length !== 5) return null
  const [min, hor, dia, mes, sem] = partes
  const todos = (...campos: string[]) => campos.every(c => c === "*")

  if (todos(min, hor, dia, mes, sem)) return "a cada 1 min"

  const aCadaMin = /^\*\/(\d+)$/.exec(min)
  if (aCadaMin && todos(hor, dia, mes, sem)) {
    const n = Number(aCadaMin[1])
    return n > 0 ? `a cada ${n} min` : null
  }

  if (min === "0" && todos(dia, mes, sem)) {
    if (hor === "*") return "a cada 1 h"
    const aCadaHora = /^\*\/(\d+)$/.exec(hor)
    if (aCadaHora) {
      const n = Number(aCadaHora[1])
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
    if (d != null) return `${DIAS_DA_SEMANA[d]} às ${as}`
    return null
  }
  if (sem === "*") {
    const d = inteiro(dia, 1, 31)
    if (d != null) return `dia ${d} às ${as}`
  }
  return null
}

/** "a cada 15 min" / "a cada 6 h" / "a cada 2 dias" — unidades do agendador (`seconds|minutes|hours|days`). */
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
