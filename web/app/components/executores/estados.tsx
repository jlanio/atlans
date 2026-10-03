"use client"

import type { ReactNode } from "react"
import { TbServerOff } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * States of the Executors screen (contract §3): 1st-load skeleton, spine
 * error, first-use empty state × no results and the amber warning for a
 * partial failure of the metrics. Each one says what happened and what to do
 * next; the skeleton and the sentences live here, with the frame from
 * `shared/estados.tsx`.
 *
 * Here the "content" is the RAIL — a dense table, a deliberate variant — so the
 * skeleton draws exactly that: column header + rows at the real height
 * (h-11), so the swap to the list doesn't make the page jump.
 */

/** First load: the real header sits on top (`index` always renders it). */
export function SkeletonDeExecutores() {
  return (
    <section
      role="status"
      aria-busy="true"
      aria-label="Carregando os executores"
      className="flex min-w-0 flex-col overflow-hidden rounded-lg border bg-card shadow-xs"
    >
      {/* Column header — hidden on phones, where the row has no columns. */}
      <div className="hidden items-center gap-3 border-b border-border bg-muted/50 px-3 py-1.5 md:flex">
        <Skeleton className="h-3 w-4" />
        <Skeleton className="h-3 w-24" />
        <Skeleton className="ml-auto h-3 w-14" />
        <Skeleton className="h-3 w-16" />
      </div>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex h-11 items-center gap-3 border-b border-border/60 px-3 last:border-b-0">
          <Skeleton className="size-2 shrink-0 rounded-full" />
          <Skeleton className="h-3.5 w-40" />
          <Skeleton className="ml-auto hidden h-3 w-16 md:block" />
          <Skeleton className="hidden h-3 w-20 md:block" />
        </div>
      ))}
    </section>
  )
}

/**
 * The spine (the listing) failed on the 1st load: without it there is no rail,
 * so the error block takes its place. Only appears when `data == null` — a
 * reload that fails over an already ready list keeps what was there (see `index`).
 */
export function ErroDosExecutores({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar os executores" mensagem={mensagem} onTentar={onTentar} />
}

/**
 * First-use empty state (contract §3.3): distinguishes "no executor" from "no
 * results". The message changes with the role — an admin registers the first
 * one; a regular user asks for access. `acao` is the primary CTA (the creation
 * dialog), rendered only when the viewer can create.
 */
export function VazioDeExecutores({ isAdmin, acao }: { isAdmin: boolean; acao?: ReactNode }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbServerOff}
      titulo={isAdmin ? "Nenhum executor ainda" : "Nenhum executor disponível para você"}
      descricao={isAdmin
        ? "Executores são as máquinas que rodam seus workflows de forma distribuída. Registre o primeiro para começar a despachar execuções."
        : "Os workflows precisam de um executor para rodar. Peça a um administrador acesso a um executor dedicado ou ao pool compartilhado."}
      acao={acao}
      podeCriar={isAdmin}
    />
  )
}

/**
 * Active slice with no rows (contract §3.3): the obvious way out is to clear the
 * filter, and the screen says so — the `TbFilterOff` icon sets it apart from a
 * real empty state.
 */
export function SemResultado({ onLimpar }: { onLimpar: () => void }) {
  return <Estado.SemResultado texto="Nenhum executor com este filtro" onLimpar={onLimpar} />
}

/**
 * Partial failure (contract §3.4): only the execution metrics failed; the rail
 * stays whole, without the history numbers. A discreet amber line with the
 * "Tentar de novo" (try again) that redoes the metrics load.
 */
export function AvisoDeMetricas({ onTentar }: { onTentar: () => void }) {
  return (
    <Estado.AvisoAmbar onTentar={onTentar}>
      Sem dados de execução agora — a lista continua completa.
    </Estado.AvisoAmbar>
  )
}
