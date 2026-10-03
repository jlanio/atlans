"use client"

import { TbKey, TbPlus } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * States of the Credentials screen (contract screen-patterns.md §3): loading,
 * load error, first use and no results. Each one says what happened and what
 * to do next. The skeleton and the screen's sentences live here; each state's
 * frame is the one from `shared/estados.tsx`.
 */

/**
 * First load: the real header sits on top (`index` always renders it, with
 * the subtitle as a skeleton), and here goes the outline of the toolbar and
 * rows — with the same heights as the real list, so the swap doesn't jump.
 */
export function SkeletonDeCredenciais() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Carregando as credenciais"
      className="flex flex-col gap-4"
    >
      {/* Ghost of the search/filter/sort/group bar. */}
      <div className="flex flex-wrap items-center gap-2">
        <Skeleton className="h-9 min-w-[12rem] flex-1 rounded-md max-md:h-10" />
        <Skeleton className="h-9 w-36 rounded-md max-md:h-10" />
        <Skeleton className="h-9 w-36 rounded-md max-md:h-10" />
        <Skeleton className="h-9 w-40 rounded-md max-md:h-10" />
      </div>
      <div className="flex flex-col gap-3">
        {[0, 1, 2].map(i => <LinhaFantasma key={i} />)}
      </div>
    </div>
  )
}

/**
 * Taller on phones: there the EntityCard stacks the badges on a second line,
 * and a short skeleton made the list shrink the instant the data arrived.
 */
function LinhaFantasma() {
  return (
    <div className="flex h-[86px] items-center gap-3 rounded-lg border bg-card px-3 shadow-xs sm:h-[58px]">
      <Skeleton className="size-8 shrink-0 rounded-md" />
      <div className="flex flex-1 flex-col gap-1.5">
        <Skeleton className="h-3.5 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="hidden h-5 w-24 rounded-full sm:block" />
      <Skeleton className="size-7 rounded-full" />
    </div>
  )
}

/**
 * The spine source (the listing) failed on the 1st load. It only takes over the
 * screen when there was never an accepted load — a reload that fails over a
 * ready list keeps what was there and warns via toast (see `index`). `mensagem`
 * is the server's; without it, the usual guidance.
 */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem?: string | null; onTentar: () => void }) {
  return (
    <Estado.ErroDeCarga
      titulo="Não foi possível carregar as credenciais."
      mensagem={mensagem || "Verifique a conexão e tente novamente."}
      onTentar={onTentar}
    />
  )
}

/**
 * No credentials at all: the screen teaches what a credential is and where to
 * start. Creating is a personal action (owner-only by nature), so the CTA
 * appears for whoever can; the fallback exists by contract.
 */
export function VazioPrimeiroUso({ canEdit, onCriar }: { canEdit: boolean; onCriar: () => void }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbKey}
      titulo="Comece pela primeira credencial"
      descricao={
        <>
          Credenciais guardam as conexões privadas — bancos, APIs e serviços — que seus workflows
          reutilizam nos nós, sem repetir segredos em cada um.
        </>
      }
      cta={{ rotulo: "Criar credencial", icone: TbPlus, onClick: onCriar }}
      podeCriar={canEdit}
      pedirA="criar a primeira credencial"
    />
  )
}

/** "Nenhuma credencial com "q"" / "…com este filtro" / "…com "q" e este filtro". */
export function textoDeSemResultado(q: string, comFiltro: boolean): string {
  return Estado.textoDeSemResultado({
    nada: "Nenhuma credencial",
    termo: q,
    comFiltro,
    semRecorte: "Nenhuma credencial corresponde ao filtro",
  })
}

/** Search or type filter with no rows: the obvious way out is to clear the slice. */
export function SemResultado({ q, comFiltro, onLimpar }: {
  q: string
  comFiltro: boolean
  onLimpar: () => void
}) {
  return <Estado.SemResultado texto={textoDeSemResultado(q, comFiltro)} onLimpar={onLimpar} />
}
