// web/lib/formatos.ts
//
// A casa ÚNICA de formatação de apresentação do web: durações, datas, números,
// dinheiro, percentuais e os rótulos pt-BR dos vocabulários de execução.
// Nasceu em components/observability/ e foi promovida na F2 da simplificação
// (docs/specs/simplificacao.md, A8) quando 40+ arquivos de todas as áreas já
// importavam de lá — cópias locais divergem, e duas telas mostrando a mesma
// grandeza em formatos diferentes é defeito, não estilo.

import { fromBackend, dayjs } from "@/lib/dayjs"
import type { DispatchTier, ErrorCategory, TriggerSource } from "@/service/types"

/**
 * Duração em segundos por extenso, na unidade que a pessoa usa: "31 s",
 * "4 min 02 s", "2 h 14 min". Nunca "834.12s".
 */
export function formatarDuracao(segundos: number | null | undefined): string {
  if (segundos == null || !Number.isFinite(segundos) || segundos < 0) return "—"
  if (segundos < 1) return "< 1 s"
  const s = Math.round(segundos)
  if (s < 60) return `${s} s`
  if (s < 3600) {
    const m = Math.floor(s / 60)
    const r = s % 60
    return r === 0 ? `${m} min` : `${m} min ${String(r).padStart(2, "0")} s`
  }
  const h = Math.floor(s / 3600)
  const m = Math.round((s % 3600) / 60)
  if (m === 60) return `${h + 1} h`
  return m === 0 ? `${h} h` : `${h} h ${m} min`
}

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

/**
 * Início de uma execução como se lê numa lista: relativo quando é recente,
 * "hoje"/"ontem" com a hora, e a data curta depois disso.
 */
export function formatarInicio(iso: string | null | undefined, agora: Date = new Date()): string {
  const d = fromBackend(iso)
  if (!d) return "—"
  const ref = dayjs(agora)
  const minutos = ref.diff(d, "minute")
  if (minutos >= 0 && minutos < 60) return minutos < 1 ? "agora" : `há ${minutos} min`
  const hora = d.format("HH:mm")
  if (d.isSame(ref, "day")) return `hoje, ${hora}`
  if (d.isSame(ref.subtract(1, "day"), "day")) return `ontem, ${hora}`
  const dia = `${d.date()} ${MESES[d.month()]}`
  if (d.year() === ref.year()) return `${dia}, ${hora}`
  return `${dia} ${d.year()}, ${hora}`
}

/**
 * Duração "grossa", para ler de relance numa lista: "31 s", "6 min",
 * "2 h 14 min". A partir de 1 min os segundos somem — "6 min 09 s" ao lado
 * do nome de um workflow é precisão que ninguém usa.
 */
export function formatarDuracaoGrossa(segundos: number | null | undefined): string {
  if (segundos == null || !Number.isFinite(segundos) || segundos < 0) return "—"
  if (segundos < 1) return "< 1 s"
  const s = Math.round(segundos)
  if (s < 60) return `${s} s`
  const minutos = Math.round(s / 60)
  if (minutos < 60) return `${minutos} min`
  const h = Math.floor(minutos / 60)
  const m = minutos % 60
  return m === 0 ? `${h} h` : `${h} h ${m} min`
}

/** "há 6 min" com a mesma granularidade de `formatarDuracaoGrossa`. */
export function formatarDecorridoGrosso(segundos: number | null | undefined): string {
  const d = formatarDuracaoGrossa(segundos)
  return d === "—" ? d : `há ${d}`
}

/**
 * Quando algo aconteceu, para a coluna "como anda" de Projetos: relativo
 * dentro de 24 h ("há 40 min", "há 3 h" — mesmo atravessando a meia-noite,
 * que é quando "ontem, 23:23" mais engana), e daí em diante o calendário de
 * `formatarInicio` ("ontem, 18:12", "1 set, 08:04").
 */
export function formatarQuando(iso: string | null | undefined, agora: Date = new Date()): string {
  const d = fromBackend(iso)
  if (!d) return "—"
  const minutos = dayjs(agora).diff(d, "minute")
  if (minutos >= 0 && minutos < 60) return minutos < 1 ? "agora" : `há ${minutos} min`
  if (minutos >= 60 && minutos < 24 * 60) return `há ${Math.floor(minutos / 60)} h`
  return formatarInicio(iso, agora)
}

/** Data curta para eixos de gráfico: "8 ago". */
export function formatarDiaCurto(isoDia: string): string {
  const [ano, mes, dia] = isoDia.split("-").map(Number)
  if (!ano || !mes || !dia) return isoDia
  return `${dia} ${MESES[mes - 1] ?? ""}`.trim()
}

export function rotuloDaOrigem(origem: TriggerSource | string | null | undefined): string | null {
  switch (origem) {
    case "manual": return "manual"
    case "retry": return "reexecução"
    case "webhook": return "webhook"
    case "schedule": return "agendado"
    case "mcp": return "agente"
    default: return null
  }
}

export function rotuloDaCategoria(categoria: ErrorCategory | string | null | undefined): string | null {
  switch (categoria) {
    case "timeout": return "tempo esgotado"
    case "no_executor": return "sem executor"
    case "executor_lost": return "executor caiu"
    case "isolation": return "isolamento"
    case "user": return "erro do fluxo"
    case "validation": return "validação"
    case "resource": return "recursos"
    case "transient": return "transitório"
    case "internal": return "interno"
    case "dispatch": return "despacho"
    default: return null
  }
}

/** O nível normal (principal) não se marca; os outros sim. */
export function rotuloDoNivel(nivel: DispatchTier | string | null | undefined): string | null {
  if (nivel === "fallback") return "reserva"
  if (nivel === "pool") return "pool"
  return null
}

export type Variacao = { pct: number | null; delta: number; direcao: "sobe" | "desce" | "igual" }

/**
 * Variação entre o período e o anterior. `pct` é nulo quando o anterior é
 * zero (não há base); `delta` é a diferença absoluta. "Igual" abaixo de 0,5%.
 */
export function variacao(atual: number | null | undefined, anterior: number | null | undefined): Variacao | null {
  if (atual == null || anterior == null) return null
  const delta = atual - anterior
  const pct = anterior === 0 ? null : (delta / anterior) * 100
  const direcao: Variacao["direcao"] =
    pct == null ? (delta === 0 ? "igual" : delta > 0 ? "sobe" : "desce")
      : Math.abs(pct) < 0.5 ? "igual" : pct > 0 ? "sobe" : "desce"
  return { pct, delta, direcao }
}

/** Percentual com uma casa e vírgula: 0.964 → "96,4%". */
export function formatarPercentual(fracao: number | null | undefined, casas = 1): string {
  if (fracao == null || !Number.isFinite(fracao)) return "—"
  return `${(fracao * 100).toFixed(casas).replace(".", ",")}%`
}

/** Inteiro com separador de milhar pt-BR: 1284 → "1.284". */
export function formatarInteiro(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—"
  return new Intl.NumberFormat("pt-BR").format(Math.round(n))
}

/** Pontos percentuais com sinal: 0.964 vs 0.975 → "−1,1 pt". */
export function formatarPontos(delta: number): string {
  const pts = Math.abs(delta * 100).toFixed(1).replace(".", ",")
  return `${delta < 0 ? "−" : "+"}${pts} pt`
}

/** Plural simples: `plural(1, "presa")` → "1 presa"; `plural(2, "presa")` → "2 presas". */
export function plural(n: number, singular: string, pluralForma = `${singular}s`): string {
  return `${formatarInteiro(n)} ${n === 1 ? singular : pluralForma}`
}

// ── Dinheiro ─────────────────────────────────────────────────────────────────
// Uma honestidade que este formatador existe para manter: **preço
// desconhecido não vira zero**. `null` vira «—». Zero leria como «de graça», e
// é essa leitura que faria escolher errado numa tela de dinheiro.

/** «US$ 12,34». `null` vira «—». */
export function formatarDolar(v: number | null | undefined): string {
  if (v == null) return "—"
  return `US$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
