"use client"

import type React from "react"
import {
  TbMapPin, TbFileCode, TbFileTypeZip, TbDatabase, TbClock, TbCloudUp, TbPinFilled,
  TbPhoto, TbFileTypePdf,
} from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"
import { formatLocal, fromBackend, dayjs } from "@/lib/dayjs"
import { plural } from "@/lib/formatos"

/**
 * Artifact badges and hints, extracted from the page to fit the screen
 * contract. Hard rule from §6: format is NOT status, so no literal emerald/blue/
 * orange/purple here — the icon tells the formats apart, the neutral token
 * paints them all the same. Only the portal states (§6 allows the status pairs
 * with dark) and imminent retention (warning red/amber) get color.
 */

// Only the ICON varies by format — the color is always neutral. Before, each
// format had its own color (emerald/blue/orange/purple), which made the format
// compete visually with the rows' real status.
const FORMAT_ICONS: Record<string, React.ElementType> = {
  geojson:    TbMapPin,
  json:       TbFileCode,
  shapefile:  TbFileTypeZip,
  geoparquet: TbDatabase,
  // The image map (CartaImagem node): a file to download, not a layer.
  png:        TbPhoto,
  jpg:        TbPhoto,
  jpeg:       TbPhoto,
  pdf:        TbFileTypePdf,
}

export function FormatBadge({ format }: { format: string | null }) {
  if (!format) return null
  const Icon = FORMAT_ICONS[format] ?? TbFileCode
  return (
    <Badge variant="secondary" className="gap-1 bg-muted text-[10px] text-muted-foreground">
      <Icon size={10} aria-hidden="true" />
      {format.toUpperCase()}
    </Badge>
  )
}

/** Portal serving this layer now: success (sanctioned green pair + dark). */
export function PortalAtivoBadge() {
  return (
    <span className="flex items-center gap-0.5 rounded-full border border-green-500/20 bg-green-100 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-green-700 dark:bg-green-500/15 dark:text-green-400">
      <TbCloudUp size={9} aria-hidden="true" /> Ativo
    </span>
  )
}

/** Publication superseded by another: neutral, neither failure nor success. */
export function PortalAnteriorBadge() {
  return (
    <span className="flex items-center gap-0.5 rounded-full bg-muted px-1.5 py-0.5 text-[9px] text-muted-foreground">
      <TbCloudUp size={9} aria-hidden="true" /> Anterior
    </span>
  )
}

/** Output pinned in the cache: amber notice (sanctioned pair + dark). */
export function CachePinBadge() {
  return (
    <span
      className="flex items-center gap-0.5 rounded-full border border-amber-500/20 bg-amber-100 px-1.5 py-0.5 text-[9px] font-medium text-amber-700 dark:bg-amber-500/15 dark:text-amber-400"
      title="Cache de output fixado (pin)"
    >
      <TbPinFilled size={9} aria-hidden="true" /> Cache Pin
    </span>
  )
}

/**
 * The sentences of the retention hint. The default is the usual Portuguese; the
 * Home, which speaks three languages, passes those of its language (the Artifacts
 * table passes nothing and stays the same).
 */
export interface TextosDaRetencao {
  expirado: string
  expiraHoje: string
  /** `dias` ≥ 1: "expira em 3 dias". */
  expiraEm: (dias: number) => string
  /** O `title`: "Removido automaticamente em 20/10/2026 14:03". */
  removidoEm: (expiresAt: string | null) => string
}

export const RETENCAO_EM_PORTUGUES: TextosDaRetencao = {
  expirado: "expirado",
  expiraHoje: "expira hoje",
  // `plural` covers the pt-BR "1 dia"/"2 dias" with the same thousands formatter
  // as the other screens.
  expiraEm: (dias) => `expira em ${plural(dias, "dia")}`,
  removidoEm: (expiresAt) => `Removido automaticamente em ${formatLocal(expiresAt)}`,
}

// Retention: when the artifact will be removed by the automatic cleanup
// (`artifact_cleanup` purges by `expires_at`). `null` = no expiration — renders
// nothing, the absence already says "permanent". Brings the red/amber closer as
// expiry approaches so the user is not caught off guard by an artifact that vanishes.
function infoRetencao(
  expiresAt: string | null,
  textos: TextosDaRetencao,
): { texto: string; classe: string } | null {
  const exp = fromBackend(expiresAt)
  if (!exp) return null
  const agora = dayjs()
  const horas = exp.diff(agora, "hour")
  if (horas < 0)  return { texto: textos.expirado,   classe: "text-red-600 dark:text-red-400" }
  if (horas < 24) return { texto: textos.expiraHoje, classe: "text-red-600 dark:text-red-400" }
  const dias = exp.diff(agora, "day")
  return {
    texto: textos.expiraEm(dias),
    classe: dias < 3 ? "text-amber-600 dark:text-amber-400" : "text-muted-foreground",
  }
}

export function RetencaoHint({
  expiresAt,
  textos = RETENCAO_EM_PORTUGUES,
}: {
  expiresAt: string | null
  textos?: TextosDaRetencao
}) {
  const r = infoRetencao(expiresAt, textos)
  if (!r) return null
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] tabular-nums ${r.classe}`}
      title={textos.removidoEm(expiresAt)}
    >
      <TbClock size={10} aria-hidden="true" /> {r.texto}
    </span>
  )
}
