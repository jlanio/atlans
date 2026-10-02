"use client"

import type { IDriveFile } from "@/service/types"
import { formatLocal } from "@/lib/dayjs"
import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { isLocalDoExecutor } from "@/app/components/local-badge"
import { formatBytes } from "@/utils/formatters"
import { formatarInteiro } from "@/lib/formatos"
import { ExtIcon } from "./ext"
import { cn } from "@/lib/utils"

type DriveFile = IDriveFile

/** Data da última escrita de conteúdo — chave por que o backend ordena a lista. */
export function lastWrite(file: DriveFile): string {
  return file.content_written_at ?? file.created_at
}

/** Houve reescrita depois do envio original? (guarda as duas datas). */
export function foiReescrito(file: DriveFile): boolean {
  const escrita = file.content_written_at
  return Boolean(escrita && formatLocal(escrita) !== formatLocal(file.created_at))
}

/** Os textos do diálogo. Padrão: o português do Drive; a Home traduzida passa os dela. */
export interface TextosDosMetadados {
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
    /** O bbox — em português, "Extensão" como a do arquivo. */
    extensaoEspacial: string
  }
  semNuvemTitulo: string
  semNuvemTexto: string
  executor: (id: string) => string
  fechar: string
  inteiro: (n: number) => string
  /** Data e hora exatas — o dado EXATO, não o relativo do resumo. */
  dataEHora: (iso: string | null | undefined) => string
}

export const TEXTOS_DOS_METADADOS_PT: TextosDosMetadados = {
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
  inteiro: formatarInteiro,
  dataEHora: (iso) => formatLocal(iso),
}

/**
 * Linhas de metadados espaciais extraídos pelo GeoSync (CRS, bbox, contagem).
 * Só aparecem quando existem: o upload comum não os extrai, e mostrar "—" para
 * cinco campos vazios em todo arquivo pioraria o diálogo no caso normal.
 */
function metadadosEspaciais(file: DriveFile, textos: TextosDosMetadados): Array<[string, string]> {
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
    // Arredondado: o bbox cru tem 6 casas e estoura a largura do diálogo sem
    // acrescentar nada a quem só quer situar a área.
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
  /** A Home passa `home-portal`: o conteúdo é portado ao <body>, fora da paleta dela. */
  className?: string
  textos?: TextosDosMetadados
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
            // O diálogo de metadados existe para expor o dado EXATO — data e
            // hora completas, não o relativo "há 3 min" do resumo.
            [r.enviadoEm, textos.dataEHora(file.created_at)],
            // Só aparece quando o conteúdo foi de fato reescrito depois do envio.
            ...(foiReescrito(file) ? [[r.atualizadoEm, textos.dataEHora(lastWrite(file))]] : []),
            [r.id, file.id_hash],
            // No modo catálogo estes são os ÚNICOS dados que a plataforma tem
            // sobre o conteúdo — sem eles o arquivo seria só um nome.
            ...metadadosEspaciais(file, textos),
            // A chave é a posição: em português a extensão do arquivo e a do
            // bbox têm o mesmo rótulo.
          ] as Array<[string, string]>).map(([label, value], i) => (
            <div key={i} className="flex justify-between gap-4">
              <span className="shrink-0 text-muted-foreground">{label}</span>
              {/* Quebra em vez de cortar: em mono o bbox arredondado e um MIME
                  como application/geopackage+sqlite3 passam de 200px, e o
                  pedaço cortado era justamente a informação. */}
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
