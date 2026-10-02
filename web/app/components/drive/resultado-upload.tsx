"use client"

import type React from "react"
import {
  TbAlertTriangle, TbCircleCheck, TbFileOff, TbLock, TbWeight, TbX,
} from "react-icons/tb"
import { plural } from "@/lib/formatos"
import type { UploadErrorCode } from "@/service/types"

// ── Classificação da falha de upload ──────────────────────────────────────────

export type UploadErrorType = "extension" | "size" | "empty" | "permission" | "other"

export interface UploadError {
  fileName: string
  detail:   string
  type:     UploadErrorType
}

/** A categoria de cada código de recusa do Drive (`error` do corpo). */
const TIPO_DO_CODIGO: Record<UploadErrorCode, UploadErrorType> = {
  extension_not_allowed:     "extension",
  dangerous_inner_extension: "extension",
  empty_file:                "empty",
  file_too_large:            "size",
}

/**
 * Classifica a falha pelo que o backend devolveu: o status e o CÓDIGO (`error`
 * do corpo, que o `GisFlowService` entrega em `IResponse.error.code`). Nunca
 * pela frase — a regra antiga procurava "extensão"/"não permitida" no texto, e
 * o backend escreve sem acento: a recusa por extensão caía em "other".
 *
 * O status vale antes do código: o 403 do papel e o 413 do teto lido pelo
 * router são `HTTPException`, sem código de domínio.
 */
export function classifyUploadError(status: number | undefined, codigo: string | undefined): UploadErrorType {
  if (status === 403) return "permission"
  if (status === 413) return "size"
  // `hasOwn`, e não o índice cru: um código como "constructor" acharia o do protótipo.
  return codigo && Object.hasOwn(TIPO_DO_CODIGO, codigo) ? TIPO_DO_CODIGO[codigo as UploadErrorCode] : "other"
}

/**
 * Ícone, rótulo e cor de cada tipo de falha. As cores saíram dos literais
 * `text-orange-500`/`text-yellow-500` para pares de status com par escuro (§6),
 * então o rótulo lê nos dois temas em vez de sumir no fundo escuro.
 */
const ERROR_META: Record<UploadErrorType, { icon: React.ElementType; color: string }> = {
  extension:  { icon: TbFileOff,       color: "text-amber-600 dark:text-amber-400" },
  size:       { icon: TbWeight,        color: "text-yellow-600 dark:text-yellow-400" },
  empty:      { icon: TbFileOff,       color: "text-muted-foreground" },
  permission: { icon: TbLock,          color: "text-destructive" },
  other:      { icon: TbAlertTriangle, color: "text-destructive" },
}

/** Os textos do painel. Padrão: o português do Drive; a Home traduzida passa os dela. */
export interface TextosDoResultado {
  enviados: (n: number) => string
  falhas: (n: number) => string
  fechar: string
  tipos: Record<UploadErrorType, string>
}

export const TEXTOS_DO_RESULTADO_PT: TextosDoResultado = {
  enviados: (n) => plural(n, "enviado"),
  falhas: (n) => plural(n, "falha"),
  fechar: "Fechar o resultado do envio",
  tipos: {
    extension: "Extensão não permitida",
    size: "Arquivo muito grande",
    empty: "Arquivo vazio",
    permission: "Sem permissão",
    other: "Falha no envio",
  },
}

/** Painel de resultado do último envio: quantos foram, o que falhou e por quê. */
export function ResultadoDoUpload({
  sucessos, erros, onFechar, textos = TEXTOS_DO_RESULTADO_PT,
}: { sucessos: number; erros: UploadError[]; onFechar: () => void; textos?: TextosDoResultado }) {
  return (
    <div className="overflow-hidden rounded-lg border bg-card shadow-xs">
      <div className="flex items-center justify-between border-b bg-muted/40 px-4 py-2.5">
        <div className="flex items-center gap-3">
          {sucessos > 0 && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-green-700 tabular-nums dark:text-green-400">
              <TbCircleCheck size={14} aria-hidden="true" />
              {textos.enviados(sucessos)}
            </span>
          )}
          {erros.length > 0 && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-destructive tabular-nums">
              <TbAlertTriangle size={14} aria-hidden="true" />
              {textos.falhas(erros.length)}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onFechar}
          aria-label={textos.fechar}
          className="rounded-sm text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <TbX size={13} aria-hidden="true" />
        </button>
      </div>

      {erros.map((err, i) => {
        const meta = ERROR_META[err.type]
        const Icon = meta.icon
        return (
          <div
            key={i}
            className={`flex items-start gap-3 px-4 py-3 text-sm ${i < erros.length - 1 ? "border-b border-border/60" : ""}`}
          >
            <div className={`mt-0.5 shrink-0 ${meta.color}`}>
              <Icon size={15} aria-hidden="true" />
            </div>
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="max-w-[220px] truncate font-medium text-foreground">«{err.fileName}»</span>
                <span className={`rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium ${meta.color}`}>
                  {textos.tipos[err.type]}
                </span>
              </div>
              <p className="text-xs leading-snug text-muted-foreground">{err.detail}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
