"use client"

import type React from "react"
import {
  TbAlertTriangle, TbCircleCheck, TbFileOff, TbLock, TbWeight, TbX,
} from "react-icons/tb"
import { plural } from "@/lib/formatos"
import type { UploadErrorCode } from "@/service/types"

// ── Upload failure classification ─────────────────────────────────────────────

export type UploadErrorType = "extension" | "size" | "empty" | "permission" | "other"

export interface UploadError {
  fileName: string
  detail:   string
  type:     UploadErrorType
}

/** The category of each Drive rejection code (`error` in the body). */
const TYPE_BY_CODE: Record<UploadErrorCode, UploadErrorType> = {
  extension_not_allowed:     "extension",
  dangerous_inner_extension: "extension",
  empty_file:                "empty",
  file_too_large:            "size",
}

/**
 * Classifies the failure by what the backend returned: the status and the CODE
 * (`error` in the body, which `GisFlowService` delivers in `IResponse.error.code`).
 * Never by the sentence — the old rule looked for "extensão"/"não permitida" in
 * the text, and the backend writes without accents: the extension rejection
 * fell into "other".
 *
 * The status counts before the code: the role 403 and the ceiling 413 read by
 * the router are `HTTPException`, with no domain code.
 */
export function classifyUploadError(status: number | undefined, codigo: string | undefined): UploadErrorType {
  if (status === 403) return "permission"
  if (status === 413) return "size"
  // `hasOwn`, not the raw index: a code like "constructor" would find the prototype's.
  return codigo && Object.hasOwn(TYPE_BY_CODE, codigo) ? TYPE_BY_CODE[codigo as UploadErrorCode] : "other"
}

/**
 * Icon, label and color of each failure type. The colors moved from the
 * `text-orange-500`/`text-yellow-500` literals to status pairs with a dark pair
 * (§6), so the label reads in both themes instead of vanishing on the dark background.
 */
const ERROR_META: Record<UploadErrorType, { icon: React.ElementType; color: string }> = {
  extension:  { icon: TbFileOff,       color: "text-amber-600 dark:text-amber-400" },
  size:       { icon: TbWeight,        color: "text-yellow-600 dark:text-yellow-400" },
  empty:      { icon: TbFileOff,       color: "text-muted-foreground" },
  permission: { icon: TbLock,          color: "text-destructive" },
  other:      { icon: TbAlertTriangle, color: "text-destructive" },
}

/** The panel's texts. Default: the Drive's Portuguese; the translated Home passes its own. */
export interface ResultTexts {
  enviados: (n: number) => string
  falhas: (n: number) => string
  fechar: string
  tipos: Record<UploadErrorType, string>
}

export const TEXTOS_DO_RESULTADO_PT: ResultTexts = {
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

/** Result panel of the last upload: how many went through, what failed and why. */
export function UploadResult({
  sucessos, erros, onFechar, textos = TEXTOS_DO_RESULTADO_PT,
}: { sucessos: number; erros: UploadError[]; onFechar: () => void; textos?: ResultTexts }) {
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
