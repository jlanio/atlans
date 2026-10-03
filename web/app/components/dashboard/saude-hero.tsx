"use client"

import { TbAlertTriangle, TbArrowRight, TbCircleCheck } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { INowBlock } from "@/service/types"
import { NowItems } from "../observability/agora-faixa"
import type { ScopeState } from "./dashboard-url"
import { type AttentionSummary, type HealthTone, veredito } from "./saude"

interface Props {
  now: INowBlock | null | undefined
  tom: HealthTone
  /** Count per type of the "Precisa de atenção" list (via `montarAtencao` in `index`); the verdict cites "N workflows falhando" without reimplementing `top_failing`. */
  resumo: AttentionSummary
  /** Scope has workflows but no run: the calm state becomes "nada rodando ainda" (§3.10). */
  semExecucoes: boolean
  escopo: ScopeState
  /** Active workspace when scoped; `null` in "todos". `index` uses it when routing. */
  workspaceId: string | null
  /** 1st load: with no `now` yet, the line becomes a skeleton instead of "sem leitura". */
  carregando: boolean
  onVerEmAndamento: () => void
  onAbrirPresa: (runId: string) => void
}

/**
 * Color per tone, with the SAME classes that `StatusBadge` and `agora-faixa`
 * already use — no loose hex, so both themes stay consistent: green
 * (calm), amber (attention), red (critical).
 */
const COLORS: Record<HealthTone, { friso: string; texto: string }> = {
  calmo: { friso: "bg-green-500", texto: "text-green-700 dark:text-green-400" },
  atencao: { friso: "bg-amber-500", texto: "text-amber-700 dark:text-amber-400" },
  critico: { friso: "bg-red-500", texto: "text-red-700 dark:text-red-400" },
}

/**
 * Health strip at the top of the Dashboard (docs/specs/dashboard.md §3.4). What
 * the screen answers first: "is everything fine right now?".
 *
 * In CALM, a thin green line (4px stripe + check + verdict + the same "agora"
 * line as History) — not a big card, which would shout for attention that
 * isn't needed. In ATTENTION/CRITICAL, the `rounded-xl` envelope gets the
 * thick stripe and the diffuse glow of `workspace-hero`, and the verdict comes
 * in two parts ("Precisa de você:" + the 1–2 most serious reasons).
 *
 * The item line ("N em andamento · 1 presa há X · Executores N de M") is the
 * `NowItems` extracted from `agora-faixa.tsx`: the same "hide what is zero"
 * logic, without duplicating it. "Ver em andamento" and the clickable stuck run
 * bubble up as callbacks — the one that routes (with `&workspace=` when scoped)
 * is `index`.
 */
export function SaudeHero({ now, tom, resumo, semExecucoes, carregando, onVerEmAndamento, onAbrirPresa }: Props) {
  const cor = COLORS[tom]
  const frase = veredito(now, tom, resumo, semExecucoes)
  const calmo = tom === "calmo"

  // Body shared by both states: the items of the moment and the shortcut to
  // the table filtered by "em andamento" (in progress).
  const corpo = (
    <div className="flex flex-1 flex-wrap items-center gap-x-3.5 gap-y-2">
      {now ? (
        <NowItems now={now} onAbrirPresa={onAbrirPresa} />
      ) : carregando ? (
        <Skeleton className="h-4 w-56" />
      ) : (
        <span className="text-muted-foreground">Sem leitura do instante.</span>
      )}
      <button
        type="button"
        onClick={onVerEmAndamento}
        aria-label="Ver execuções em andamento"
        className="ml-auto inline-flex items-center gap-1 rounded-sm text-xs font-medium text-primary underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
      >
        Ver em andamento <TbArrowRight size={13} aria-hidden="true" />
      </button>
    </div>
  )

  if (calmo) {
    // Thin line: the 4px stripe on the left, the check and the verdict in a single sentence.
    return (
      <section
        aria-labelledby="saude-titulo"
        aria-busy={carregando && !now}
        className="relative flex flex-wrap items-center gap-x-3.5 gap-y-2 overflow-hidden rounded-lg border bg-card py-2.5 pr-4 pl-5 text-sm shadow-xs"
      >
        <h2 id="saude-titulo" className="sr-only">Saúde · agora</h2>
        <span aria-hidden="true" className={cn("absolute inset-y-0 left-0 w-1", cor.friso)} />
        <span className={cn("inline-flex items-center gap-2 font-medium", cor.texto)}>
          <TbCircleCheck size={17} className="shrink-0" aria-hidden="true" />
          {frase}
        </span>
        {corpo}
      </section>
    )
  }

  // Attention/critical: the big envelope, with a thick stripe and the verdict in
  // two parts. The identity color only comes in as the stripe — without the diffuse glow.
  const [prefixo, motivos] = verdictParts(frase)
  return (
    <section
      aria-labelledby="saude-titulo"
      className="relative overflow-hidden rounded-xl border bg-card shadow-xs motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-1 motion-safe:duration-300"
    >
      <span aria-hidden="true" className={cn("absolute inset-y-0 left-0 w-1.5", cor.friso)} />
      <div className="relative flex flex-col gap-2.5 p-4 pl-6 sm:p-5 sm:pl-7">
        <div className="flex items-start gap-2.5">
          <TbAlertTriangle size={20} className={cn("mt-0.5 shrink-0", cor.texto)} aria-hidden="true" />
          <div className="min-w-0">
            <h2 id="saude-titulo" className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
              Saúde · agora
            </h2>
            <p className="text-[15px] leading-snug font-medium text-balance">
              <span className={cor.texto}>{prefixo}</span>
              {motivos && <span className="text-foreground">{motivos}</span>}
            </p>
          </div>
        </div>
        {corpo}
      </div>
    </section>
  )
}

/**
 * Splits the verdict at the first ": " — "Precisa de você:" is painted in the
 * tone's color, the reasons stay in normal text. Without the separator (a
 * single sentence), everything goes into the prefix.
 */
function verdictParts(frase: string): [string, string | null] {
  const i = frase.indexOf(": ")
  if (i === -1) return [frase, null]
  return [frase.slice(0, i + 1), frase.slice(i + 1)]
}
