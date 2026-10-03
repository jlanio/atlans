"use client"

import type { IconType } from "react-icons"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * States of the Admin › Settings screen (contract §3): per-section 1st-load
 * skeleton, error card when the section's source goes down before there is any
 * read, empty states with icon-in-circle and the amber partial-failure notice.
 * The skeletons and the sentences live here; the frame is that of
 * `shared/estados.tsx`.
 *
 * Since each section lives inside a `<section>` shell that already draws the
 * frame (border + `bg-card`) and the header, the skeletons here are only the
 * BODY — they do not repeat the border, otherwise the section would have two.
 */

// ── 1st-load skeletons (section body) ───────────────────────────────────────

/**
 * Overview: the four indicators (real height `h-24`) and the pending-items
 * block. `aria-busy` on the wrapper so the screen reader announces the wait.
 */
export function SkeletonVisaoGeral() {
  return (
    <div role="status" aria-busy="true" aria-label="Carregando a visão geral" className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full rounded-lg" />)}
      </div>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-4 w-28" />
        {[0, 1, 2].map(i => <Skeleton key={i} className="h-12 w-full rounded-md" />)}
      </div>
    </div>
  )
}

/**
 * Stackable table (Storage, Trash, Isolation): a header strip and a few rows
 * with the real height, so the swap to the content does not make the page jump.
 */
export function SkeletonDeTabela({ linhas = 4, rotulo }: { linhas?: number; rotulo: string }) {
  return (
    <div role="status" aria-busy="true" aria-label={rotulo} className="flex flex-col gap-2.5">
      <Skeleton className="h-8 w-full rounded-md" />
      {Array.from({ length: linhas }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-md" />
      ))}
    </div>
  )
}

/**
 * Short form (Whitelist, Retention, Drive): the label, the field + button
 * row and the help note.
 */
export function SkeletonDeFormulario({ rotulo }: { rotulo: string }) {
  return (
    <div role="status" aria-busy="true" aria-label={rotulo} className="flex flex-col gap-3">
      <Skeleton className="h-3 w-40" />
      <div className="flex gap-2">
        <Skeleton className="h-9 w-32 rounded-md" />
        <Skeleton className="h-9 w-24 rounded-md" />
      </div>
      <Skeleton className="h-3 w-full max-w-md" />
    </div>
  )
}

/**
 * Nodes: a linha de resumo + busca e alguns grupos recolhidos.
 */
export function SkeletonDeNodes() {
  return (
    <div role="status" aria-busy="true" aria-label="Carregando os nodes" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <Skeleton className="h-3 w-48" />
        <Skeleton className="h-8 w-40 rounded-md" />
      </div>
      {[0, 1, 2].map(i => <Skeleton key={i} className="h-9 w-full rounded-md" />)}
    </div>
  )
}

// ── Error (the section's source went down before there was a read) ───────────

/**
 * A section's read failed and there is nothing on screen: the body gives way to
 * the error card. Before, `useFetchData`'s `error` was ignored and the section
 * simply stayed blank — without saying it failed or how to try again.
 *
 * On a RELOAD with data already on screen this does not appear (the hook keeps
 * what was there); `AvisoDeSecao` is what covers that partial failure.
 */
export function CartaoDeErro({
  mensagem, onTentar,
}: {
  mensagem?: string
  onTentar: () => void
}) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar as configurações" mensagem={mensagem} onTentar={onTentar} />
}

// ── Empty (the read went fine, but there is nothing to list) ─────────────────

/**
 * A section's empty state — Storage with no files, empty Trash, Drive with no
 * extensions. Icon-in-circle and a sentence; replaces the loose `<p italic>`
 * that was there before, which could not be told apart from any label.
 */
export function VazioEmCirculo({
  icone, titulo, descricao,
}: {
  icone: IconType
  titulo: string
  descricao?: string
}) {
  return <Estado.CartaoDeEstado icone={icone} titulo={titulo} descricao={descricao} />
}

// ── Amber notice (partial failure of a section, without bringing down the block) ─

/**
 * Per-section partial failure (§3.4): that block's source went down on a
 * reload, but there was data on screen. The amber line from `shared/estados.tsx`,
 * with the inline "Tentar de novo".
 */
export { AvisoAmbar as AvisoDeSecao } from "@/app/components/shared/estados"
