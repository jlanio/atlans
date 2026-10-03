"use client"

import { TbFolders } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"
import type { ArtifactTab } from "@/app/(dashboard)/artifacts/use-artifacts-query"

/**
 * States of the Artifacts screen (contract §3): 1st-load skeleton, spine error
 * in a card, first-use empty vs no result, and the amber notice for a reload
 * that failed over an already-ready list. The precedence (loading → error only
 * if there was never a load → first use → content) lives in the page; the
 * skeleton and the sentences live here, with the frame from `shared/estados.tsx`.
 */

/**
 * First load: the real header stays on top (the page always renders it) and
 * here goes the table's outline — the same frame, the same five row blocks at
 * the real height — so the swap to the content does not make the page jump.
 */
export function SkeletonDeArtefatos() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Carregando os artefatos"
      className="overflow-hidden rounded-lg border bg-card shadow-xs"
    >
      <div className="flex flex-col gap-2 p-4">
        {[0, 1, 2, 3, 4].map(i => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="size-4 shrink-0 rounded" />
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="hidden h-4 w-24 sm:block" />
            <Skeleton className="hidden h-4 w-20 md:block" />
            <Skeleton className="h-7 w-20 rounded-md" />
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * The listing went down on the 1st load (no `atualizadoEm` yet): without it
 * there is no table, so the error card takes its place. A reload that fails over
 * a ready list does NOT get here — it becomes the amber notice and the table stays.
 */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar os artefatos" mensagem={mensagem} onTentar={onTentar} />
}

/**
 * First use: the workspace/tab has no artifacts and there is no active slice.
 * Different from "no result" — here there is nothing to clear, only the
 * explanation of where artifacts come from.
 */
export function VazioPrimeiroUso({ tab }: { tab: ArtifactTab }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbFolders}
      titulo={tab === "execution" ? "Nenhum artefato ainda" : "Nenhuma publicação ainda"}
      descricao={tab === "execution"
        ? "Quando um workflow rodar e gerar uma saída, o arquivo aparece aqui — pronto para baixar."
        : "Quando um workflow publicar uma camada num portal, a versão servida aparece aqui."}
    />
  )
}

/**
 * Search or format chip with no rows. Unlike first use, there is a slice to
 * undo — the obvious way out is "Limpar filtros", and the screen offers it.
 */
export function SemResultado({ q, formato, tab, onLimpar }: {
  q: string
  formato: string | null
  tab: ArtifactTab
  onLimpar: () => void
}) {
  return <Estado.SemResultado texto={textoDeSemResultado(q, formato, tab)} onLimpar={onLimpar} />
}

/** "Nenhum artefato com «q»" / "Nenhuma publicação em GEOJSON" — the noun
 *  follows the tab (execution → artifact; publication → publication). */
export function textoDeSemResultado(termo: string, formato: string | null, tab: ArtifactTab): string {
  const nada = tab === "execution" ? "Nenhum artefato" : "Nenhuma publicação"
  const fmt = formato && formato !== "all" ? formato.toUpperCase() : null
  return Estado.textoDeSemResultado({
    nada,
    termo,
    comFiltro: fmt != null,
    sufixoFiltro: fmt ? `em ${fmt}` : undefined,
    semRecorte: `${nada} com este filtro`,
  })
}

/**
 * A reload that failed with the list already on screen (§3.4): a discreet amber
 * line, it does not bring down the table. It also covers a "Ver mais" that
 * errored — the button stays there to try again.
 */
export function AvisoDeRecarga({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.AvisoAmbar onTentar={onTentar}>{mensagem}</Estado.AvisoAmbar>
}
