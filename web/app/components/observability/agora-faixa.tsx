"use client"

import type { ReactNode } from "react"
import { TbArrowRight } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { INowBlock } from "@/service/types"
import { formatarDuracao, formatarInteiro } from "@/lib/formatos"

interface Props {
  now: INowBlock | null | undefined
  carregando: boolean
  /** "Ver em andamento →" (see in progress): applies `status=running` to the table. */
  onVerEmAndamento: () => void
  /** Click on "N presa(s)" (N stuck): opens the oldest one in the panel. */
  onAbrirPresa: (runId: string) => void
}

/**
 * "Agora" (Now) strip (spec §4.3): the instant, not the window. One line, not
 * cards — it changes every 30 s and must not make the period numbers flicker.
 * Whatever is zero is hidden, except "em andamento" (in progress): zero in
 * progress is information ("nothing running"); zero stuck is normal and does
 * not deserve space.
 */
export function AgoraFaixa({ now, carregando, onVerEmAndamento, onAbrirPresa }: Props) {
  return (
    <section
      className="flex flex-wrap items-center gap-x-3.5 gap-y-2 rounded-lg border bg-card px-4 py-2.5 text-sm shadow-xs"
      aria-labelledby="agora-titulo"
      aria-busy={carregando && !now}
    >
      <h2 id="agora-titulo" className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Agora</h2>
      {!now ? (
        carregando
          ? <Skeleton className="h-4 w-56" />
          : <span className="text-muted-foreground">Sem leitura do instante.</span>
      ) : (
        <ItensAgora now={now} onAbrirPresa={onAbrirPresa} />
      )}
      <button
        type="button"
        onClick={onVerEmAndamento}
        aria-label="Ver execuções em andamento"
        className="ml-auto inline-flex items-center gap-1 rounded-sm text-xs font-medium text-primary underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        Ver em andamento <TbArrowRight size={13} aria-hidden="true" />
      </button>
    </section>
  )
}

/**
 * The line of instant items ("3 em andamento · 1 presa há X · Executores N
 * de M online"), without the strip's envelope or the "Ver em andamento". Named
 * export so the Dashboard reuses the SAME line inside the Health strip
 * (docs/specs/dashboard.md §3.4), without duplicating the "hide what is zero" logic.
 */
export function ItensAgora({ now, onAbrirPresa }: { now: INowBlock; onAbrirPresa: (runId: string) => void }) {
  const presas = now.stuck_count ?? 0
  const maisAntiga = now.stuck?.[0]
  const { online, total } = now.executors ?? { online: 0, total: 0 }
  const confirmacoes = now.overdue_acks

  return (
    <>
      <Item>
        <Ponto className={cn("bg-blue-500", now.running > 0 && "motion-safe:animate-pulse")} />
        <N>{formatarInteiro(now.running)}</N> em andamento
      </Item>
      {now.pending > 0 && (
        <Item className="text-muted-foreground"><N>{formatarInteiro(now.pending)}</N> na fila</Item>
      )}
      {presas > 0 && (
        <>
          <Separador />
          <button
            type="button"
            onClick={maisAntiga ? () => onAbrirPresa(maisAntiga.run_id) : undefined}
            disabled={!maisAntiga}
            aria-label={presas === 1
              ? `Abrir a execução presa há ${formatarDuracao(maisAntiga?.elapsed_seconds)}`
              : `Abrir a mais antiga das ${presas} execuções presas`}
            className="inline-flex items-center gap-1.5 rounded-sm text-amber-700 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:no-underline dark:text-amber-400"
          >
            <Ponto className="bg-amber-500" />
            <span>
              <N>{formatarInteiro(presas)}</N> {presas === 1 ? "presa" : "presas"}
              {maisAntiga && ` há ${formatarDuracao(maisAntiga.elapsed_seconds)}`}
            </span>
          </button>
        </>
      )}
      {total > 0 && (
        <>
          <Separador />
          <Item>
            <Ponto className={online === 0 ? "bg-red-500" : online < total ? "bg-amber-500" : "bg-green-500"} />
            Executores <N>{online} de {total}</N> online
          </Item>
        </>
      )}
      {confirmacoes != null && confirmacoes > 0 && (
        <>
          <Separador />
          <Item className="text-amber-700 dark:text-amber-400">
            <N>{formatarInteiro(confirmacoes)}</N> {confirmacoes === 1 ? "confirmação atrasada" : "confirmações atrasadas"}
          </Item>
        </>
      )}
    </>
  )
}

function Item({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("inline-flex items-center gap-1.5", className)}>{children}</span>
}
function N({ children }: { children: ReactNode }) {
  return <span className="font-semibold tabular-nums">{children}</span>
}
function Ponto({ className }: { className?: string }) {
  return <span aria-hidden="true" className={cn("inline-block size-2 shrink-0 rounded-full", className)} />
}
function Separador() {
  return <span aria-hidden="true" className="hidden h-4 w-px bg-border sm:inline-block" />
}
