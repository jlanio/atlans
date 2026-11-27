/**
 * Data sample of a node's outputs, as the executor sends it in the `sample`
 * event (flow/executor/sample.py, docs/specs/node-data-panels.md §4.4).
 */

export interface AmostraColuna {
  name: string
  /** `int` | `float` | `bool` | `datetime` | `str` | `object` | `geometry:<Tipo>` */
  type: string
  geometry?: boolean
}

/** Geometry cell: summarized, never the whole geometry. */
export interface AmostraGeometria {
  type: string
  vertices: number | null
  wkt: string | null
}

export type AmostraCelula = string | number | boolean | null | AmostraGeometria

export interface AmostraTabela {
  kind: "table"
  rows_total: number
  crs?: string
  columns: AmostraColuna[]
  rows: AmostraCelula[][]
  truncated: { rows: boolean; columns: boolean; cells: boolean }
  /** The sample's geometries drawn small, for the Mapa view (absent when the
   *  table has no geometry, or the map did not fit in the event). */
  map?: AmostraMapa
}

/** SVG preview of the sample's geometries: coordinates already scaled into
 *  `0..w` × `0..h` (y pointing down), in the layer's own CRS. */
export interface AmostraMapa {
  w: number
  h: number
  /** `d`: an SVG path (`area` = filled polygon, else a line); `p`: a point. */
  features: Array<{ d: string; area: boolean } | { p: [number, number] }>
}

export interface AmostraJson {
  kind: "json"
  value: unknown
  truncated: boolean
}

export interface AmostraOmitida {
  kind: "omitted"
  reason: "too_large" | "error" | string
}

export type AmostraSaida = AmostraTabela | AmostraJson | AmostraOmitida

export interface AmostraDoNo {
  version: number
  outputs: Record<string, AmostraSaida>
  skipped?: string[]
}

export function isGeometria(valor: unknown): valor is AmostraGeometria {
  return !!valor && typeof valor === "object" && "type" in valor && "wkt" in valor
}

/** One line for the raw log: `amostra: output (20 de 1.284 linhas), metadata (objeto)`. */
export function resumoDaAmostra(sample: unknown): string {
  const outputs = (sample as AmostraDoNo | null)?.outputs
  if (!outputs || typeof outputs !== "object") return "amostra indisponível"
  const partes = Object.entries(outputs).map(([chave, saida]) => {
    if (saida?.kind === "table") {
      return `${chave} (${saida.rows.length} de ${saida.rows_total.toLocaleString("pt-BR")} linhas)`
    }
    if (saida?.kind === "json") return `${chave} (objeto)`
    return `${chave} (omitida)`
  })
  return partes.length ? `amostra: ${partes.join(", ")}` : "amostra: nenhuma saída"
}
