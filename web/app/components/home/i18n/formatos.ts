// web/app/components/home/i18n/formatos.ts
//
// The formatters the Home uses, one set per language. Portuguese DELEGATES to
// the `lib/formatos` functions — the Home in Portuguese stays byte for byte what
// it was, and the formatting rule for the rest of the app keeps a single owner.
// English and Spanish mirror the SAME granularity ("agora" → "now"/"ahora",
// "há 5 min" → "5 min ago"/"hace 5 min", "ontem, 14:03" → "yesterday, 2:03
// PM"/"ayer, 14:03"), with month and time via each language's `Intl`.

import { dayjs, formatLocal, fromBackend } from "@/lib/dayjs"
import { formatarDuracao, formatInteger, formatarQuando } from "@/lib/formatos"
import type { Idioma } from "@/lib/idioma"

export interface Formatos {
  /** Integer with the language's thousands separator: 1284 → "1.284" / "1,284". */
  inteiro: (n: number | null | undefined) => string
  /** Duration "31 s", "4 min 02 s", "2 h 14 min" — the units hold in all three languages. */
  duracao: (segundos: number | null | undefined) => string
  /** When something happened: relative within 24 h, calendar after that. */
  quando: (iso: string | null | undefined, agora?: Date) => string
  /**
   * The EXACT date and time, in the browser's time zone: "20/10/2026 14:03" (the
   * usual `formatLocal`) / "Oct 20, 2026, 2:03 PM" / "20/10/2026, 14:03".
   * In English with the month spelled out: "09/01/2026" is September 1 for an
   * en-US reader and January 9 for an en-GB, en-AU or en-IN reader.
   */
  dataEHora: (iso: string | null | undefined) => string
}

interface WhenWords {
  agora: string
  haMinutos: (m: number) => string
  haHoras: (h: number) => string
  hoje: string
  ontem: string
}

function _whenFor(idioma: Idioma, p: WhenWords) {
  const hora = new Intl.DateTimeFormat(idioma, { hour: "numeric", minute: "2-digit" })
  const dia = new Intl.DateTimeFormat(idioma, { day: "numeric", month: "short" })
  const dayWithYear = new Intl.DateTimeFormat(idioma, { day: "numeric", month: "short", year: "numeric" })
  return (iso: string | null | undefined, agora: Date = new Date()): string => {
    const d = fromBackend(iso)
    // An invalid one becomes "—": `Intl` THROWS on an invalid date, and one
    // unreadable date in a row took down the whole list (in Portuguese, text comes out).
    if (!d || !d.isValid()) return "—"
    const ref = dayjs(agora)
    const minutos = ref.diff(d, "minute")
    if (minutos >= 0 && minutos < 60) return minutos < 1 ? p.agora : p.haMinutos(minutos)
    if (minutos >= 60 && minutos < 24 * 60) return p.haHoras(Math.floor(minutos / 60))
    const data = d.toDate()
    const h = hora.format(data)
    if (d.isSame(ref, "day")) return `${p.hoje}, ${h}`
    if (d.isSame(ref.subtract(1, "day"), "day")) return `${p.ontem}, ${h}`
    const quando = d.year() === ref.year() ? dia.format(data) : dayWithYear.format(data)
    return `${quando}, ${h}`
  }
}

function _dateTimeFor(idioma: Idioma, opcoes: Intl.DateTimeFormatOptions) {
  const formato = new Intl.DateTimeFormat(idioma, opcoes)
  return (iso: string | null | undefined): string => {
    const d = fromBackend(iso)
    return d && d.isValid() ? formato.format(d.toDate()) : "—"
  }
}

function _integerFor(idioma: Idioma) {
  const numero = new Intl.NumberFormat(idioma)
  return (n: number | null | undefined): string =>
    n == null || !Number.isFinite(n) ? "—" : numero.format(Math.round(n))
}

export const FORMATOS: Record<Idioma, Formatos> = {
  "pt-BR": {
    inteiro: formatInteger,
    duracao: formatarDuracao,
    quando: formatarQuando,
    dataEHora: (iso) => formatLocal(iso),
  },
  en: {
    inteiro: _integerFor("en"),
    duracao: formatarDuracao,
    quando: _whenFor("en", {
      agora: "now",
      haMinutos: (m) => `${m} min ago`,
      haHoras: (h) => `${h} h ago`,
      hoje: "today",
      ontem: "yesterday",
    }),
    dataEHora: _dateTimeFor("en", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" }),
  },
  es: {
    inteiro: _integerFor("es"),
    duracao: formatarDuracao,
    quando: _whenFor("es", {
      agora: "ahora",
      haMinutos: (m) => `hace ${m} min`,
      haHoras: (h) => `hace ${h} h`,
      hoje: "hoy",
      ontem: "ayer",
    }),
    dataEHora: _dateTimeFor("es", { day: "2-digit", month: "2-digit", year: "numeric", hour: "numeric", minute: "2-digit" }),
  },
}
