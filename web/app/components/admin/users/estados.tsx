"use client"

import { TbShield, TbUsers } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/*
 * The four states of the Admin › Users screen (contract §3): 1st-load skeleton
 * mirroring the table, error only when there was never a load, first-use empty
 * × no result, and the no-access card. The composition and precedence live in
 * `page.tsx`; the skeleton and the sentences live here, with the frame from
 * `shared/estados.tsx`.
 */

/**
 * First load: the real header and toolbar stay on top (`page.tsx` always
 * renders them) and here goes the table's outline — five rows with the real
 * height — so the swap to the content does not make the page jump.
 */
export function SkeletonDeUsuarios() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Carregando os usuários"
      className="overflow-hidden rounded-lg border bg-card shadow-xs"
    >
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 border-b px-3 py-3 last:border-b-0">
          <Skeleton className="size-4 shrink-0 rounded" />
          <div className="flex flex-1 flex-col gap-1.5">
            <Skeleton className="h-3.5 w-40" />
            <Skeleton className="h-3 w-56" />
          </div>
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="hidden h-5 w-16 rounded-full sm:block" />
          <Skeleton className="hidden h-3.5 w-24 md:block" />
          <Skeleton className="size-8 shrink-0 rounded-md" />
        </div>
      ))}
    </div>
  )
}

/**
 * The listing went down on the 1st load: without it there is no table, so the
 * error block takes its place. On a reload that fails over an already-ready list
 * this does NOT appear — `page.tsx` keeps what was there and only shows a toast
 * (contract §3.2).
 */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar os usuários" mensagem={mensagem} onTentar={onTentar} />
}

/**
 * No users and no slice: the instance's first use. Rare on an admin screen
 * (there is always at least the admin themself), but the contract asks for the
 * distinction between "there is nothing" and "the filter hid everything".
 */
export function VazioPrimeiroUso() {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbUsers}
      titulo="Nenhum usuário ainda"
      descricao="Assim que as primeiras contas forem criadas, elas aparecem aqui para gestão."
    />
  )
}

/**
 * Search or filter with no rows: the obvious way out is clearing the slice, and
 * the screen says so (contract §3.3, `TbFilterOff` icon). The page only passes
 * the search: with no term, what zeroed the list is the status and role slice.
 */
export function SemResultado({ q, onLimpar }: { q: string; onLimpar: () => void }) {
  return (
    <Estado.SemResultado
      texto={Estado.textoDeSemResultado({ nada: "Nenhum usuário", termo: q, comFiltro: q.trim() === "" })}
      dica="Ajuste a busca ou o recorte de status e role."
      onLimpar={onLimpar}
    />
  )
}

/** Non-admin: the whole screen gives way to the centered no-access card. */
export function SemAcesso() {
  return (
    <Estado.CartaoDeEstado
      icone={TbShield}
      tamanho="amplo"
      titulo="Acesso restrito"
      descricao="Esta área é exclusiva de administradores da plataforma."
    />
  )
}
