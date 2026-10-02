// web/app/components/home/i18n/formatos.ts
//
// Os formatadores que a Home usa, um jogo por idioma. O português DELEGA às
// funções de `lib/formatos` — a Home em português continua byte a byte a de
// antes, e a regra de formatação do resto do app segue com um dono só. Inglês e
// espanhol espelham a MESMA granularidade ("agora" → "now"/"ahora", "há 5 min"
// → "5 min ago"/"hace 5 min", "ontem, 14:03" → "yesterday, 2:03 PM"/"ayer,
// 14:03"), com mês e hora pelo `Intl` de cada idioma.

import { dayjs, formatLocal, fromBackend } from "@/lib/dayjs"
import { formatarDuracao, formatarInteiro, formatarQuando } from "@/lib/formatos"
import type { Idioma } from "@/lib/idioma"

export interface Formatos {
  /** Inteiro com o separador de milhar do idioma: 1284 → "1.284" / "1,284". */
  inteiro: (n: number | null | undefined) => string
  /** Duração "31 s", "4 min 02 s", "2 h 14 min" — as unidades valem nos três idiomas. */
  duracao: (segundos: number | null | undefined) => string
  /** Quando algo aconteceu: relativo em 24 h, calendário depois. */
  quando: (iso: string | null | undefined, agora?: Date) => string
  /**
   * A data e hora EXATAS, no fuso do navegador: "20/10/2026 14:03" (o
   * `formatLocal` de sempre) / "Oct 20, 2026, 2:03 PM" / "20/10/2026, 14:03".
   * Em inglês com o mês por extenso: "09/01/2026" é 1º de setembro para quem
   * lê en-US e 9 de janeiro para quem lê en-GB, en-AU ou en-IN.
   */
  dataEHora: (iso: string | null | undefined) => string
}

interface PalavrasDoQuando {
  agora: string
  haMinutos: (m: number) => string
  haHoras: (h: number) => string
  hoje: string
  ontem: string
}

function _quandoPor(idioma: Idioma, p: PalavrasDoQuando) {
  const hora = new Intl.DateTimeFormat(idioma, { hour: "numeric", minute: "2-digit" })
  const dia = new Intl.DateTimeFormat(idioma, { day: "numeric", month: "short" })
  const diaComAno = new Intl.DateTimeFormat(idioma, { day: "numeric", month: "short", year: "numeric" })
  return (iso: string | null | undefined, agora: Date = new Date()): string => {
    const d = fromBackend(iso)
    // Inválida vira "—": o `Intl` LANÇA com uma data inválida, e uma data
    // ilegível numa linha derrubava a lista inteira (em português sai texto).
    if (!d || !d.isValid()) return "—"
    const ref = dayjs(agora)
    const minutos = ref.diff(d, "minute")
    if (minutos >= 0 && minutos < 60) return minutos < 1 ? p.agora : p.haMinutos(minutos)
    if (minutos >= 60 && minutos < 24 * 60) return p.haHoras(Math.floor(minutos / 60))
    const data = d.toDate()
    const h = hora.format(data)
    if (d.isSame(ref, "day")) return `${p.hoje}, ${h}`
    if (d.isSame(ref.subtract(1, "day"), "day")) return `${p.ontem}, ${h}`
    const quando = d.year() === ref.year() ? dia.format(data) : diaComAno.format(data)
    return `${quando}, ${h}`
  }
}

function _dataEHoraPor(idioma: Idioma, opcoes: Intl.DateTimeFormatOptions) {
  const formato = new Intl.DateTimeFormat(idioma, opcoes)
  return (iso: string | null | undefined): string => {
    const d = fromBackend(iso)
    return d && d.isValid() ? formato.format(d.toDate()) : "—"
  }
}

function _inteiroPor(idioma: Idioma) {
  const numero = new Intl.NumberFormat(idioma)
  return (n: number | null | undefined): string =>
    n == null || !Number.isFinite(n) ? "—" : numero.format(Math.round(n))
}

export const FORMATOS: Record<Idioma, Formatos> = {
  "pt-BR": {
    inteiro: formatarInteiro,
    duracao: formatarDuracao,
    quando: formatarQuando,
    dataEHora: (iso) => formatLocal(iso),
  },
  en: {
    inteiro: _inteiroPor("en"),
    duracao: formatarDuracao,
    quando: _quandoPor("en", {
      agora: "now",
      haMinutos: (m) => `${m} min ago`,
      haHoras: (h) => `${h} h ago`,
      hoje: "today",
      ontem: "yesterday",
    }),
    dataEHora: _dataEHoraPor("en", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" }),
  },
  es: {
    inteiro: _inteiroPor("es"),
    duracao: formatarDuracao,
    quando: _quandoPor("es", {
      agora: "ahora",
      haMinutos: (m) => `hace ${m} min`,
      haHoras: (h) => `hace ${h} h`,
      hoje: "hoy",
      ontem: "ayer",
    }),
    dataEHora: _dataEHoraPor("es", { day: "2-digit", month: "2-digit", year: "numeric", hour: "numeric", minute: "2-digit" }),
  },
}
