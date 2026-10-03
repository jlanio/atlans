"use client"

import type { IDriveFile } from "@/service/types"
import { formatLocal } from "@/lib/dayjs"
import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { isLocalDoExecutor } from "@/app/components/local-badge"
import { formatBytes } from "@/utils/formatters"
import { formatInteger } from "@/lib/formatos"
import { ExtIcon } from "./ext"
import { cn } from "@/lib/utils"

type DriveFile = IDriveFile

/** Date of the last content write — the key the backend sorts the list by. */
export function lastWrite(file: DriveFile): string {
  return file.content_written_at ?? file.created_at
}

/** Was there a rewrite after the original upload? (keeps both dates). */
export function wasRewritten(file: DriveFile): boolean {
  const escrita = file.content_written_at
  return Boolean(escrita && formatLocal(escrita) !== formatLocal(file.created_at))
}

/** The dialog's texts. Default: the Drive's Portuguese; the translated Home passes its own. */
export interface MetadataTexts {
  descricao: string
  rotulos: {
    extensao: string
    tamanho: string
    mime: string
    enviadoEm: string
    atualizadoEm: string
    id: string
    geometria: string
    crs: string
    feicoes: string
    colunas: string
    /** The bbox — in Portuguese, "Extensão" like the file's extension. */
    extensaoEspacial: string
  }
  semNuvemTitulo: string
  semNuvemTexto: string
  executor: (id: string) => string
  fechar: string
  inteiro: (n: number) => string
  /** Exact date and time — the EXACT value, not the summary's relative one. */
  dataEHora: (iso: string | null | undefined) => string
}

export const TEXTOS_DOS_METADADOS_PT: MetadataTexts = {
  descricao: "Metadados do arquivo",
  rotulos: {
    extensao: "Extensão",
    tamanho: "Tamanho",
    mime: "MIME type",
    enviadoEm: "Enviado em",
    atualizadoEm: "Atualizado em",
    id: "ID",
    geometria: "Geometria",
    crs: "CRS",
    feicoes: "Feições",
    colunas: "Colunas",
    extensaoEspacial: "Extensão",
  },
  semNuvemTitulo: "O conteúdo não está na nuvem.",
  semNuvemTexto:
    "Este arquivo foi catalogado por um executor e os bytes nunca saíram daquela máquina. " +
    "A plataforma conhece os metadados acima, mas não o conteúdo — por isso não há download. " +
    "Workflows que rodem nesse executor conseguem lê-lo normalmente.",
  executor: (id) => `executor ${id}`,
  fechar: "Fechar",
  inteiro: formatInteger,
  dataEHora: (iso) => formatLocal(iso),
}

/**
 * Rows of spatial metadata extracted by GeoSync (CRS, bbox, count).
 * They only appear when they exist: a regular upload doesn't extract them, and
 * showing "—" for five empty fields on every file would make the dialog worse in
 * the normal case.
 */
function spatialMetadata(file: DriveFile, textos: MetadataTexts): Array<[string, string]> {
  const m = file.spatial_metadata
  if (!m) return []

  const linhas: Array<[string, string]> = []
  const texto = (v: unknown) => (v === null || v === undefined ? "" : String(v))

  const r = textos.rotulos
  if (m.geometry_type) linhas.push([r.geometria, texto(m.geometry_type)])
  if (m.crs)           linhas.push([r.crs, texto(m.crs)])
  if (typeof m.feature_count === "number") {
    linhas.push([r.feicoes, textos.inteiro(m.feature_count)])
  }
  if (Array.isArray(m.columns) && m.columns.length > 0) {
    linhas.push([r.colunas, textos.inteiro(m.columns.length)])
  }
  if (Array.isArray(m.bbox) && m.bbox.length === 4) {
    // Rounded: the raw bbox has 6 decimal places and overflows the dialog width
    // without adding anything for someone who just wants to locate the area.
    linhas.push([r.extensaoEspacial, (m.bbox as number[]).map(n => n.toFixed(3)).join(", ")])
  }
  return linhas
}

export function MetadataDialog({
  file, open, onClose, className, textos = TEXTOS_DOS_METADADOS_PT,
}: {
  file: DriveFile | null
  open: boolean
  onClose: () => void
  /** The Home passes `home-portal`: the content is portaled to <body>, outside its palette. */
  className?: string
  textos?: MetadataTexts
}) {
  if (!file) return null
  const r = textos.rotulos
  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className={cn("max-w-sm", className)} closeLabel={textos.fechar}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-sm">
            <ExtIcon ext={file.extension} />
            <span className="truncate">«{file.original_name}»</span>
          </DialogTitle>
          <DialogDescription>{textos.descricao}</DialogDescription>
        </DialogHeader>
        <div className="space-y-2 text-sm">
          {([
            [r.extensao,  file.extension.toUpperCase()],
            [r.tamanho,   formatBytes(file.size)],
            [r.mime,      file.mime_type ?? "—"],
            // The metadata dialog exists to expose the EXACT value — full date
            // and time, not the summary's relative "há 3 min".
            [r.enviadoEm, textos.dataEHora(file.created_at)],
            // Only appears when the content was actually rewritten after the upload.
            ...(wasRewritten(file) ? [[r.atualizadoEm, textos.dataEHora(lastWrite(file))]] : []),
            [r.id, file.id_hash],
            // In catalog mode these are the ONLY data the platform has about
            // the content — without them the file would be just a name.
            ...spatialMetadata(file, textos),
            // The key is the position: in Portuguese the file's extension and the
            // bbox's extent have the same label.
          ] as Array<[string, string]>).map(([label, value], i) => (
            <div key={i} className="flex justify-between gap-4">
              <span className="shrink-0 text-muted-foreground">{label}</span>
              {/* Wrap instead of truncating: in mono the rounded bbox and a MIME
                  like application/geopackage+sqlite3 exceed 200px, and the
                  truncated piece was precisely the information. */}
              <span className="min-w-0 text-right font-mono text-xs tabular-nums wrap-anywhere" title={value}>{value}</span>
            </div>
          ))}
        </div>

        {isLocalDoExecutor(file) && (
          <div className="rounded-md border border-amber-500/40 bg-amber-500/5 p-3 text-xs">
            <p className="font-medium">{textos.semNuvemTitulo}</p>
            <p className="mt-1 text-muted-foreground">{textos.semNuvemTexto}</p>
            {file.content_executor_id && (
              <p className="mt-1.5 font-mono text-muted-foreground">{textos.executor(file.content_executor_id)}</p>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>{textos.fechar}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
