"use client"

// web/app/components/home/assistente/uso-da-cota.tsx
//
// The meter for the assistant's daily token quota: a thin donut with the
// percentage, on the meta line RIGHT BELOW the field — the design and placement
// are those of Claude Code's context indicator, which was the owner's reference.
//
// It does not talk to the network: it reads `estado.cota` (`GET /assistente/estado` /
// `GET /assistente/editor/estado`), which the three surfaces already receive as a prop,
// raise during the turn via the stream's `cota` frame and reread when it closes.
// Without `cota` (Redis down, assistant
// disabled), the component simply does not exist — the same "fail open" as
// the backend. The quota-exceeded pill stays where it always was; here, in the
// same state, the donut closes and the label becomes the reopening countdown.
//
// Bands: terracotta (`--primary`) up to 79%, amber from 80% on — raw Tailwind
// amber because it is the house precedent for "approaching the limit" (the
// pill and the executors' LoadBar use the same). The full detail (spend,
// ceiling, percentage and deadline) goes in the tooltip and the aria-label. The
// bucket being the same for the Home and the editor (app/mcp/cotas.py) stays out
// of the text: it is noise to someone reading a meter.

import { DEFAULT_LANGUAGE, type Idioma } from "@/lib/idioma"
import { textosDe, useScreenLanguage } from "../i18n"
import { FORMATOS } from "../i18n/formatos"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/app/components/ui/tooltip"
import { cn } from "@/lib/utils"
import type { IAssistantQuota } from "@/service/types"

export type QuotaBand = "normal" | "alerta" | "cheia"

/** 0–100, already clamped: `gasto` CAN exceed the ceiling (the server check is
 *  once per conversation), and a 133% donut would be a visual lie. */
export function quotaPercentage(cota: IAssistantQuota): number {
  if (!cota.teto || cota.teto <= 0) return 0
  return Math.max(0, Math.min(100, Math.round((cota.gasto / cota.teto) * 100)))
}

export function quotaBand(cota: IAssistantQuota): QuotaBand {
  if (cota.gasto >= cota.teto) return "cheia"
  return quotaPercentage(cota) >= 80 ? "alerta" : "normal"
}

/** The tooltip and aria-label text — exported for the tests. */
export function detalheDaCota(cota: IAssistantQuota, idioma: Idioma = DEFAULT_LANGUAGE): string {
  const t = textosDe(idioma).assistente.cota
  const f = FORMATOS[idioma]
  const pct = quotaPercentage(cota)
  const cheia = cota.gasto >= cota.teto
  const prazo = cota.reabre_em_segundos != null
    ? t.janela(cheia, f.duracao(cota.reabre_em_segundos))
    : ""
  return t.detalhe(f.inteiro(cota.gasto), f.inteiro(cota.teto), pct, prazo)
}

const RING_COLOR: Record<QuotaBand, string> = {
  normal: "text-primary",
  alerta: "text-amber-400",
  cheia: "text-amber-500",
}

// 16 px donut, 2.6 stroke — the reference's geometry.
const DIAMETER = 16
const RADIUS = DIAMETER / 2 - 1.6
const VOLTA = 2 * Math.PI * RADIUS

interface Props {
  cota?: IAssistantQuota | null
  /** The editor respects the light/dark theme; the Home is always dark and the
   *  tooltip's portaled content needs its palette (`.home-portal`). */
  superficie?: "home" | "editor"
  className?: string
}

export default function QuotaUsage({ cota, superficie = "home", className }: Props) {
  const idioma = useScreenLanguage()
  if (!cota || !cota.teto || cota.teto <= 0) return null
  const t = textosDe(idioma).assistente.cota

  const pct = quotaPercentage(cota)
  const faixa = quotaBand(cota)
  const cheia = faixa === "cheia"
  const detalhe = detalheDaCota(cota, idioma)
  const rotulo = cheia
    ? cota.reabre_em_segundos != null
      ? t.reabreEmCurto(FORMATOS[idioma].duracao(cota.reabre_em_segundos))
      : t.usada
    : `${pct}%`

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            tabIndex={0}
            data-testid="uso-da-cota"
            data-faixa={faixa}
            aria-label={t.rotulo(detalhe)}
            className={cn(
              "inline-flex cursor-help items-center gap-1.5 rounded-full text-[11px] tabular-nums",
              "text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              className,
            )}
          >
            <svg
              width={DIAMETER}
              height={DIAMETER}
              viewBox={`0 0 ${DIAMETER} ${DIAMETER}`}
              aria-hidden="true"
              className={cn("shrink-0", RING_COLOR[faixa])}
            >
              <circle
                cx={DIAMETER / 2} cy={DIAMETER / 2} r={RADIUS}
                fill="none" strokeWidth="2.6" stroke="currentColor"
                className="text-muted-foreground/30"
              />
              <circle
                cx={DIAMETER / 2} cy={DIAMETER / 2} r={RADIUS}
                fill="none" strokeWidth="2.6" stroke="currentColor" strokeLinecap="round"
                strokeDasharray={VOLTA.toFixed(2)}
                strokeDashoffset={(VOLTA * (1 - pct / 100)).toFixed(2)}
                transform={`rotate(-90 ${DIAMETER / 2} ${DIAMETER / 2})`}
              />
            </svg>
            <span
              className={cn(
                cheia && (superficie === "editor"
                  ? "text-amber-700 dark:text-amber-400"
                  : "text-amber-400"),
              )}
            >
              {rotulo}
            </span>
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className={cn("max-w-60 text-center", superficie === "home" && "home-portal")}>
          {detalhe}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
