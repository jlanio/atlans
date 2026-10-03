"use client"

import { TbActivity, TbPlus } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * States of the Dashboard screen (docs/specs/dashboard.md §3.10): 1st-load
 * skeleton, spine error, first-use empty state and the amber per-section
 * partial-failure warning. Each one says what happened and what to do next;
 * the skeleton and the sentences live here, with the frame from `shared/estados.tsx`.
 */

/**
 * First load of the scope: the real header sits on top (`index` always
 * renders it) and here goes the outline of the blocks at their real height,
 * so the swap to the content doesn't make the page jump.
 */
export function SkeletonDoDashboard() {
  return (
    <div role="status" aria-busy="true" aria-label="Carregando o painel" className="flex flex-col gap-4 sm:gap-6">
      {/* Health: the thin line of the calm state. */}
      <Skeleton className="h-11 w-full rounded-lg" />
      {/* Attention | Upcoming. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Skeleton className="h-48 w-full rounded-lg" />
        <Skeleton className="h-48 w-full rounded-lg" />
      </div>
      {/* Period summary: 4 indicators + chart. */}
      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full rounded-lg" />)}
        </div>
        <Skeleton className="h-56 w-full rounded-lg" />
      </div>
    </div>
  )
}

/**
 * The spine (`metrics`) failed on the 1st load: without it there is no health,
 * attention or indicators, so the whole dashboard gives way to the error block.
 * On a reload with data on screen the hook keeps what was there and this does
 * not appear.
 */
export function ErroDoPainel({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar o painel" mensagem={mensagem} onTentar={onTentar} />
}

/**
 * First-use empty state (§3.10): nothing has run and there is no workflow in
 * the scope. Only the invitation to create the first one; the other blocks
 * don't appear — there is nothing to summarize or route yet.
 */
export function VazioDePrimeiroUso({ canEdit, onCriar }: { canEdit: boolean; onCriar: () => void }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbActivity}
      titulo="Nada rodou ainda"
      descricao={
        <>
          Quando um workflow rodar — na mão, num horário, ou por um webhook ou arquivo — o
          painel passa a mostrar a saúde, o que precisa de você e como o período andou.
        </>
      }
      cta={{ rotulo: "Criar workflow", icone: TbPlus, onClick: onCriar }}
      podeCriar={canEdit}
      pedirA="criar o primeiro workflow"
    />
  )
}

/**
 * Partial failure of a section (§3.10): that block's source failed, but the
 * rest of the dashboard carries on. The amber line from `shared/estados.tsx`,
 * with the "Tentar de novo" (try again) that redoes the load (`index` wires it
 * to `recarregar`).
 */
export { AvisoAmbar as AvisoDeSecao } from "@/app/components/shared/estados"
