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
 * Selos e dicas dos artefatos, extraídos da página para caber no contrato de
 * telas. Regra dura de §6: formato NÃO é status, então nada de emerald/blue/
 * orange/purple literais aqui — o ícone distingue os formatos, o token neutro
 * pinta todos igual. Só os estados de portal (§6 permite os pares de status com
 * dark) e a retenção iminente (vermelho/âmbar de aviso) ganham cor.
 */

// Só o ÍCONE varia por formato — a cor é sempre neutra. Antes cada formato
// tinha uma cor própria (emerald/blue/orange/purple), o que fazia o formato
// competir visualmente com o status de verdade das linhas.
const FORMAT_ICONS: Record<string, React.ElementType> = {
  geojson:    TbMapPin,
  json:       TbFileCode,
  shapefile:  TbFileTypeZip,
  geoparquet: TbDatabase,
  // A carta imagem (nó CartaImagem): um arquivo para baixar, não uma camada.
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

/** Portal servindo esta camada agora: sucesso (par verde sancionado + dark). */
export function PortalAtivoBadge() {
  return (
    <span className="flex items-center gap-0.5 rounded-full border border-green-500/20 bg-green-100 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-green-700 dark:bg-green-500/15 dark:text-green-400">
      <TbCloudUp size={9} aria-hidden="true" /> Ativo
    </span>
  )
}

/** Publicação superada por outra: neutro, não é falha nem sucesso. */
export function PortalAnteriorBadge() {
  return (
    <span className="flex items-center gap-0.5 rounded-full bg-muted px-1.5 py-0.5 text-[9px] text-muted-foreground">
      <TbCloudUp size={9} aria-hidden="true" /> Anterior
    </span>
  )
}

/** Output fixado no cache: aviso âmbar (par sancionado + dark). */
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
 * As frases da dica de retenção. O padrão é o português de sempre; a Home, que
 * fala três idiomas, passa as do idioma dela (a tabela de Artefatos não passa
 * nada e continua igual).
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
  // `plural` cobre o "1 dia"/"2 dias" pt-BR com o mesmo formatador de milhar
  // das demais telas.
  expiraEm: (dias) => `expira em ${plural(dias, "dia")}`,
  removidoEm: (expiresAt) => `Removido automaticamente em ${formatLocal(expiresAt)}`,
}

// Retenção: quando o artefato será removido pela limpeza automática
// (`artifact_cleanup` purga por `expires_at`). `null` = sem expiração — não
// renderiza nada, a ausência já diz "permanente". Aproxima o vermelho/âmbar do
// vencimento para o usuário não ser pego de surpresa por um artefato que some.
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
