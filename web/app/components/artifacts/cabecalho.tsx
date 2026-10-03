"use client"

import { TbRefresh, TbTrash } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"

interface Props {
  /** Ready-made scope sentence; `null` on the 1st load (becomes a skeleton). */
  subtitulo: string | null
  /** Reload in progress: the button spins and locks. */
  atualizando: boolean
  /** How many artifacts the red button promises to delete (selection×loaded intersection). */
  aExcluir: number
  /** Only workspace editors see the delete button. */
  podeExcluir: boolean
  onAtualizar: () => void
  onExcluir: () => void
}

/**
 * Artifacts header (contract §1): title, scope subtitle with a skeleton on the
 * 1st load, "Atualizar" as ghost and — only when there is a selection — the
 * destructive "Excluir N" action to the right of everything. Before, Refresh
 * was outline.
 */
export function CabecalhoDeArtefatos({
  subtitulo, atualizando, aExcluir, podeExcluir, onAtualizar, onExcluir,
}: Props) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold text-foreground">Artefatos</h1>
        {subtitulo ? (
          <p className="text-sm font-medium text-muted-foreground">{subtitulo}</p>
        ) : (
          <Skeleton className="mt-1 h-4 w-64" />
        )}
      </div>

      <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
        <Button
          variant="ghost"
          size="sm"
          onClick={onAtualizar}
          disabled={atualizando}
          aria-label="Atualizar a lista de artefatos"
          className="gap-1.5 max-md:h-10"
        >
          <TbRefresh size={14} className={atualizando ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
          Atualizar
        </Button>
        {podeExcluir && aExcluir > 0 && (
          <Button
            variant="destructive"
            size="sm"
            onClick={onExcluir}
            className="gap-1.5 max-md:h-10 max-md:flex-1"
          >
            <TbTrash size={14} aria-hidden="true" />
            Excluir {aExcluir}
          </Button>
        )}
      </div>
    </div>
  )
}
