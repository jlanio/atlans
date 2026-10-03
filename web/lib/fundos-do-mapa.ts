// web/lib/fundos-do-mapa.ts
//
// The map's basemaps: streets, satellite and satellite with labels.
//
// The code ships no tile server other than OpenStreetMap (the streets):
// satellite imagery requires a provider and its terms, and each installation
// picks its own. The URLs come from the web server's environment — the SAME
// variables the API uses for the Carta nodes (`app/core/config.py`, MAPA_*) —
// read by the root layout on every request and passed to the client via
// context (`app/components/share/fundos-do-mapa.tsx`). NEXT_PUBLIC_* would not
// work: the value would be baked in at build time, and the image is the same
// for every installation.
//
// Without satellite configured, the portal does not offer the switcher, and
// the Home (which starts on hybrid) falls back to satellite and, without it,
// to streets.

/** The three basemaps the map knows. */
export type Basemap = "streets" | "satellite" | "hybrid"

export interface MapBasemap {
  /** Template com {z}, {x} e {y}. */
  url: string
  /** The attribution required by the provider, in plain text. */
  credito: string
}

export interface MapBasemaps {
  ruas: MapBasemap
  satelite?: MapBasemap
  hibrido?: MapBasemap
}

export const RUAS_PADRAO: MapBasemap = {
  url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  credito: "© OpenStreetMap contributors",
}

export const DEFAULT_BASEMAPS: MapBasemaps = { ruas: RUAS_PADRAO }

function readBasemap(env: Record<string, string | undefined>, prefixo: string): MapBasemap | undefined {
  const url = (env[`MAPA_${prefixo}_URL`] ?? "").trim()
  if (!url) return undefined
  if (!/^https?:\/\//.test(url) || !["{z}", "{x}", "{y}"].every(m => url.includes(m))) {
    console.error(`MAPA_${prefixo}_URL não é um template de tiles (https://…/{z}/{x}/{y}…) — ignorada.`)
    return undefined
  }
  return { url, credito: (env[`MAPA_${prefixo}_CREDITO`] ?? "").trim() }
}

/** This installation's basemaps, from the server's environment (MAPA_*). */
export function lerFundosDoAmbiente(env: Record<string, string | undefined>): MapBasemaps {
  const fundos: MapBasemaps = { ruas: readBasemap(env, "RUAS") ?? RUAS_PADRAO }
  const satelite = readBasemap(env, "SATELITE")
  const hibrido = readBasemap(env, "HIBRIDO")
  if (satelite) fundos.satelite = satelite
  if (hibrido) fundos.hibrido = hibrido
  return fundos
}

/** The credit goes as HTML in MapLibre's attribution control: escaped. */
function escapeText(texto: string): string {
  return texto.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!)
}

/**
 * The basemap the map uses for a requested basemap: hybrid falls back to
 * satellite, and satellite to streets, when the installation has not
 * configured them.
 */
export function conjuntoDoFundo(fundos: MapBasemaps, basemap: Basemap): { tiles: string[]; attribution: string } {
  const fundo =
    basemap === "hybrid" ? fundos.hibrido ?? fundos.satelite ?? fundos.ruas
    : basemap === "satellite" ? fundos.satelite ?? fundos.ruas
    : fundos.ruas
  return { tiles: [fundo.url], attribution: escapeText(fundo.credito) }
}
