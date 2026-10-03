// web/lib/idioma.ts
//
// The Home's languages and the rule that picks one of them per request. Pure on
// purpose: it runs on the server (the dashboard layout resolves it before the
// first byte, without the page starting in Portuguese and switching later) and
// in tests.
//
// The order of the decision, from the strongest signal to the weakest:
//   1. the person's explicit choice (Preferences → `idioma` cookie);
//   2. the browser's language (`Accept-Language`) — the most faithful signal of
//      what the person READS: a Brazilian woman with her browser in English
//      chose English, and an American tourist in Brazil does not want the
//      screen in Portuguese;
//   3. the connection's country (`CF-IPCountry`, when Cloudflare sends it) — but
//      ONLY when the browser sent an `Accept-Language` we do not support;
//   4. the default: Portuguese if the request carried no `Accept-Language`;
//      English if it did, but with none of our languages (someone who reads
//      French reads English better than Portuguese).
//
// Without `Accept-Language` the request did not come from a browser — every
// browser sends it. It comes from a search crawler or a script, and the
// connection's country would only say where its server is: Googlebot comes
// from the US and would index the Home in English.

export const LANGUAGES = ["pt-BR", "en", "es"] as const
export type Idioma = (typeof LANGUAGES)[number]

export const DEFAULT_LANGUAGE: Idioma = "pt-BR"

/** The explicit-choice cookie — same model as `theme` (ThemeContext). */
export const LANGUAGE_COOKIE = "idioma"

/** Each language's name in itself: that is how people recognize it in a list. */
export const LANGUAGE_NAME: Record<Idioma, string> = {
  "pt-BR": "Português (Brasil)",
  en: "English",
  es: "Español",
}

export function ehIdioma(valor: unknown): valor is Idioma {
  return typeof valor === "string" && (LANGUAGES as readonly string[]).includes(valor)
}

function _languageFromTag(etiqueta: string): Idioma | null {
  const base = etiqueta.trim().toLowerCase().split(/[-_]/)[0]
  if (base === "pt") return "pt-BR"
  if (base === "en") return "en"
  if (base === "es") return "es"
  return null
}

/**
 * The first of our languages in the browser's preference, honoring the `q`
 * weights (`q=0` is an explicit refusal). `"fr-FR,fr;q=0.9,en;q=0.8"` → `"en"`.
 */
export function idiomaDoAcceptLanguage(cabecalho: string | null | undefined): Idioma | null {
  if (!cabecalho) return null
  const itens = cabecalho
    .split(",")
    .map((parte, ordem) => {
      const [etiqueta, ...params] = parte.trim().split(";")
      const q = params
        .map((p) => p.trim())
        .find((p) => p.startsWith("q="))
      const peso = q ? Number(q.slice(2)) : 1
      return { etiqueta: etiqueta.trim(), peso: Number.isFinite(peso) ? peso : 0, ordem }
    })
    .filter((item) => item.etiqueta && item.peso > 0)
    // Highest weight first; on a tie, the header's order wins.
    .sort((a, b) => b.peso - a.peso || a.ordem - b.ordem)
  for (const { etiqueta } of itens) {
    const idioma = _languageFromTag(etiqueta)
    if (idioma) return idioma
  }
  return null
}

const PORTUGUESE_SPEAKING_COUNTRIES = new Set(["BR", "PT", "AO", "MZ", "CV", "GW", "ST", "TL"])
const SPANISH_SPEAKING_COUNTRIES = new Set([
  "ES", "MX", "GT", "HN", "SV", "NI", "CR", "PA", "CU", "DO", "PR",
  "CO", "VE", "EC", "PE", "BO", "CL", "AR", "PY", "UY", "GQ",
])

/**
 * The language by the connection's country (ISO 3166-1 alpha-2). `XX` (unknown)
 * and `T1` (Tor) are Cloudflare codes that say nothing — they become `null`.
 */
export function idiomaDoPais(pais: string | null | undefined): Idioma | null {
  const codigo = (pais ?? "").trim().toUpperCase()
  if (!/^[A-Z]{2}$/.test(codigo) || codigo === "XX" || codigo === "T1") return null
  if (PORTUGUESE_SPEAKING_COUNTRIES.has(codigo)) return "pt-BR"
  if (SPANISH_SPEAKING_COUNTRIES.has(codigo)) return "es"
  return "en"
}

export interface ResolvedLanguage {
  /** What the screen uses: the choice, or the detected one when there is no choice. */
  idioma: Idioma
  /** What automatic detection would give — Preferences shows it under "Automático". */
  detectado: Idioma
  /** The explicit choice (cookie), or `null` when on automatic. */
  escolhido: Idioma | null
}

export function resolverIdioma(sinais: {
  cookie?: string | null
  acceptLanguage?: string | null
  pais?: string | null
}): ResolvedLanguage {
  const escolhido = ehIdioma(sinais.cookie) ? sinais.cookie : null
  const cabecalho = sinais.acceptLanguage?.trim()
  const detectado = cabecalho
    ? idiomaDoAcceptLanguage(cabecalho) ?? idiomaDoPais(sinais.pais) ?? "en"
    : DEFAULT_LANGUAGE
  return { idioma: escolhido ?? detectado, detectado, escolhido }
}
