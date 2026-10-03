"use client"

import { TbKey, TbPlus } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * States of the Access tokens screen (contract screen-patterns.md §3):
 * loading, load error and first use. There is no search or filter here, so
 * the "no results" state doesn't exist. This holds the skeleton and the screen's
 * sentences; the frame of each state is the one from `shared/estados.tsx`.
 */

/**
 * First load: the real header stays on top (`index` always renders it, with the
 * subtitle as a skeleton), and here goes the drawing of the rows — with the
 * height of the real card (name, prefix and the scopes line), so the swap
 * doesn't jump.
 */
export function SkeletonDeTokens() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Carregando os tokens de acesso"
      className="flex flex-col gap-3"
    >
      {[0, 1, 2].map(i => <GhostRow key={i} />)}
    </div>
  )
}

/**
 * Taller on the phone: there the EntityCard stacks the "Revogar" button on a
 * second line, and a short skeleton shrank the list when the data arrived.
 */
function GhostRow() {
  return (
    <div className="flex h-[132px] items-center gap-3 rounded-lg border bg-card px-3 shadow-xs sm:h-[92px]">
      <Skeleton className="size-8 shrink-0 rounded-md" />
      <div className="flex flex-1 flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <Skeleton className="h-3.5 w-1/3" />
          <Skeleton className="h-4 w-14 rounded-full" />
        </div>
        <Skeleton className="h-3 w-24" />
        <div className="flex items-center gap-1.5">
          <Skeleton className="h-4 w-20 rounded-full" />
          <Skeleton className="h-4 w-28 rounded-full" />
          <Skeleton className="hidden h-3 w-40 sm:block" />
        </div>
      </div>
      <Skeleton className="hidden h-8 w-20 rounded-md sm:block" />
    </div>
  )
}

/**
 * The listing failed on the 1st load. It only takes over the screen when there
 * was never an accepted load — a reload that fails over a ready list keeps what
 * was there and warns via toast (see `index`). `mensagem` is the server's;
 * without it, the usual guidance.
 */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem?: string | null; onTentar: () => void }) {
  return (
    <Estado.ErroDeCarga
      titulo="Não foi possível carregar os tokens de acesso."
      mensagem={mensagem || "Verifique a conexão e tente novamente."}
      onTentar={onTentar}
    />
  )
}

/**
 * No tokens at all: the screen teaches what a token is and that it inherits the
 * account's permissions. Creating is a personal action — everyone can, so the CTA
 * is unconditional (there's no "peça a um editor" here).
 */
export function VazioPrimeiroUso({ onCriar }: { onCriar: () => void }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbKey}
      titulo="Crie o primeiro token de acesso"
      descricao={
        <>
          Um token deixa um agente de IA ou uma integração usar o Atlans em seu nome — pela API ou
          pelo servidor MCP. Ele herda as permissões da sua conta e nunca vai além delas: você
          escolhe o que ele pode fazer, em quais workspaces e por quanto tempo.
        </>
      }
      cta={{ rotulo: "Criar o primeiro token", icone: TbPlus, onClick: onCriar }}
    />
  )
}
