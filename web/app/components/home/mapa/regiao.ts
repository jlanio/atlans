// web/app/components/home/mapa/regiao.ts
//
// Where the Home globe starts — and where it returns to when the answer
// arrives. It used to be always South America; now it is the region of whoever
// opens the page, without asking anyone for location permission:
//
//   1. the browser's TIME ZONE (`Intl…timeZone`) → the zone's reference city
//      (IANA table in `fusos.gerado.ts`). It is the finest signal: it tells
//      the eastern from the western US, and Manaus from São Paulo;
//   2. the connection's COUNTRY (`CF-IPCountry`, when Cloudflare sends it) →
//      the center of that country's time zones. Covers the browser that hides
//      the zone (the "UTC", or Iceland's zone, of privacy modes — below);
//   3. the CONTINENT in the zone name (`Europe/…`, `Asia/…`) for a zone the
//      table does not know;
//   4. a neutral center (the Greenwich meridian, at 20° N).
//
// The globe follows the REGION, not the language: a Brazilian woman with her
// screen in English still sees Brazil.

import { FUSOS, PAISES } from "./fusos.gerado"

/**
 * The fallback when no signal tells the region: neutral, with no preferred
 * country. At the hero zoom, the Greenwich meridian at 20° N shows Europe,
 * Africa and the Atlantic. (It used to be Brazil, the country of the first
 * installation.)
 */
export const CENTRO_PADRAO_DO_GLOBO: [number, number] = [0, 20]

// At the hero zoom the whole globe shows; centered on a pole it would show
// almost nothing but ice. The latitude is clamped to a strip in which the
// person's continent stays in frame (Oslo, Helsinki and Moscow fall at 50° N).
const LATITUDE_MAXIMA = 50
const LATITUDE_MINIMA = -45

const CONTINENTES: Readonly<Record<string, readonly [number, number]>> = {
  Europe: [15, 50],
  Africa: [20, 5],
  Asia: [90, 30],
  Australia: [134, -25],
  Pacific: [170, -15],
  Atlantic: [-30, 30],
  Indian: [70, -10],
  America: [-75, 10],
}

// Browsers that resist fingerprinting (Firefox with
// `privacy.resistFingerprinting`, Tor Browser, Mullvad Browser) do not say
// "UTC": they say Iceland's time zone, which has zero offset all year. For them
// the zone is no signal at all — without this, every user of those browsers
// opened the globe over the North Atlantic, and the connection's country was
// never consulted. Only Iceland itself (by connection country) keeps the zone;
// with no country, the neutral center applies, as for "UTC".
const FUSOS_DOS_MODOS_DE_PRIVACIDADE = new Set(["Atlantic/Reykjavik", "Iceland"])

/** The browser's time zone, or `null` where there is none (`Intl` missing, exotic SSR). */
export function fusoDoNavegador(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null
  } catch {
    return null
  }
}

export function centroDaRegiao(sinais: { fuso?: string | null; pais?: string | null }): [number, number] {
  const pais = sinais.pais?.trim().toUpperCase() || null
  const informado = sinais.fuso?.trim() || null
  const fuso = informado && FUSOS_DOS_MODOS_DE_PRIVACIDADE.has(informado) && pais !== "IS" ? null : informado
  const alvo =
    (fuso ? FUSOS[fuso] : undefined)
    ?? (pais ? PAISES[pais] : undefined)
    ?? (fuso ? CONTINENTES[fuso.split("/")[0]] : undefined)
    ?? CENTRO_PADRAO_DO_GLOBO
  const [lon, lat] = alvo
  return [lon, Math.min(LATITUDE_MAXIMA, Math.max(LATITUDE_MINIMA, lat))]
}
