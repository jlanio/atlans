"use client"

import { TbPlus, TbSitemap } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"
import { formatInteger } from "@/lib/formatos"
import { DEFAULT_STATE, type Filtro } from "./projetos-url"

/**
 * States of the Projects screen (docs/specs/projects.md §3.10): loading,
 * first-use empty, no results, load error and metrics unavailable. Each one
 * says what happened and what to do next. The skeleton and the sentences live
 * here; the frame is the one from `shared/estados.tsx`.
 */

/**
 * First load: the real header stays on top (the page composer renders it),
 * and here goes the shape of the list — a group with three rows and two
 * loose ones, at the real row height, so the swap does not jump.
 */
export function SkeletonDeProjetos() {
  return (
    <div role="status" aria-busy="true" aria-label="Carregando projetos" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5 rounded-lg border bg-muted/30 p-2.5">
        <div className="flex items-center gap-2 px-1 py-1.5">
          <Skeleton className="size-4 rounded" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-24" />
        </div>
        {[0, 1, 2].map(i => <GhostRow key={i} />)}
      </div>
      <div className="flex flex-col gap-1.5">
        {[0, 1].map(i => <GhostRow key={i} />)}
      </div>
    </div>
  )
}

function GhostRow() {
  return (
    <div className="flex h-14 items-center gap-3 rounded-lg border bg-card px-3 shadow-xs">
      <Skeleton className="size-[34px] shrink-0 rounded-lg" />
      <div className="flex flex-1 flex-col gap-1.5">
        <Skeleton className="h-3.5 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="hidden h-3.5 w-40 md:block" />
      <Skeleton className="size-8 rounded-md" />
    </div>
  )
}

const STEPS: { titulo: string; detalhe: string }[] = [
  { titulo: "Desenhe", detalhe: "Ligue os nós de leitura, processamento e saída no editor." },
  { titulo: "Execute uma vez", detalhe: "Rode pela lista e confira o resultado." },
  { titulo: "Agende ou exponha", detalhe: "Um horário, um webhook, um arquivo que chega — ou um portal." },
]

/** No workflow and no group: the screen teaches what a workflow is and where to start. */
export function VazioPrimeiroUso({ canEdit, onCriar }: { canEdit: boolean; onCriar: () => void }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbSitemap}
      titulo="Comece pelo primeiro workflow"
      descricao={
        <>
          Um workflow encadeia nós de leitura, processamento e saída. Ele roda quando você manda,
          num horário, ou quando um webhook ou um arquivo chega.
        </>
      }
      passos={STEPS}
      cta={{ rotulo: "Criar o primeiro workflow", icone: TbPlus, onClick: onCriar }}
      podeCriar={canEdit}
      pedirA="criar o primeiro workflow"
    />
  )
}

/** "Nenhum workflow com «q»" / "…com este filtro" / "…com «q» e este filtro". */
export function textoDeSemResultado(q: string, filtro: Filtro): string {
  return Estado.textoDeSemResultado({ nada: "Nenhum workflow", termo: q, comFiltro: filtro !== DEFAULT_STATE.filtro })
}

/**
 * Search or chip with no rows at all. `semFiltro` is how many would match the
 * search alone: when there are some, the obvious way out is removing the chip,
 * and the screen says so.
 */
export function SemResultado({ q, filtro, semFiltro, onLimpar }: {
  q: string
  filtro: Filtro
  semFiltro: number | null
  onLimpar: () => void
}) {
  const termo = q.trim()
  return (
    <Estado.SemResultado
      texto={textoDeSemResultado(q, filtro)}
      dica={semFiltro != null && semFiltro > 0 && termo
        ? `Há ${formatInteger(semFiltro)} com «${termo}» sem o filtro.`
        : undefined}
      onLimpar={onLimpar}
    />
  )
}

/** Listing or groups failed: without them there is no shelf. */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar os projetos" mensagem={mensagem} onTentar={onTentar} />
}

/** Only the metrics failed: the list stays whole, without the "como anda" column. */
export function MetricasIndisponiveis({ onTentar }: { onTentar: () => void }) {
  return (
    <Estado.AvisoAmbar onTentar={onTentar}>
      Sem dados de execução agora — a lista continua completa.
    </Estado.AvisoAmbar>
  )
}
