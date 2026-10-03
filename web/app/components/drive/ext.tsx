"use client"

import {
  TbFile, TbFileCode, TbFileSpreadsheet, TbFileTypeCsv, TbFileTypeZip, TbMap,
  TbPhoto, TbFileTypePdf,
} from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"

/**
 * File extension badge (icon + abbreviation).
 *
 * The colors moved from loose literals (`text-emerald-500 bg-emerald-500/10`,
 * `text-orange-500`) to the status PAIRS sanctioned by the contract (§6):
 * each brings the light pair (`bg-*-100 text-*-700`) and the dark pair
 * (`dark:bg-*-500/15 dark:text-*-400`), so the abbreviation reads well in both
 * themes. The palette was restricted to green/blue/amber/yellow/purple — the
 * brand orange is `primary`, it doesn't become a category color; teal/emerald
 * are not in the set.
 */
const EXT_STYLE: Record<string, string> = {
  geojson: "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400",
  json:    "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400",
  csv:     "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400",
  xlsx:    "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400",
  zip:     "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400",
  kml:     "bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400",
  gpkg:    "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400",
  shp:     "bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-400",
}

/** Extension icon — the spatial formats share the map. */
export function ExtIcon({ ext }: { ext: string }) {
  switch (ext) {
    case "csv":  return <TbFileTypeCsv size={14} aria-hidden="true" />
    case "zip":  return <TbFileTypeZip size={14} aria-hidden="true" />
    case "xlsx": return <TbFileSpreadsheet size={14} aria-hidden="true" />
    case "geojson":
    case "kml":
    case "gpkg":
    case "shp":  return <TbMap size={14} aria-hidden="true" />
    case "json": return <TbFileCode size={14} aria-hidden="true" />
    // The image map (CartaImagem node) arrives as a png/jpg/pdf artifact.
    case "png":
    case "jpg":
    case "jpeg": return <TbPhoto size={14} aria-hidden="true" />
    case "pdf":  return <TbFileTypePdf size={14} aria-hidden="true" />
    default:     return <TbFile size={14} aria-hidden="true" />
  }
}

export function ExtBadge({ ext }: { ext: string }) {
  const cls = EXT_STYLE[ext] ?? "bg-muted text-muted-foreground"
  return (
    <Badge variant="secondary" className={`gap-1 font-mono text-[10px] uppercase ${cls}`}>
      <ExtIcon ext={ext} />
      {ext}
    </Badge>
  )
}
