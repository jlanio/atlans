"use client"

import { TbRefresh, TbTrash } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import { formatInteger, plural } from "@/lib/formatos"

interface Props {
  /** Total for the whole filter; null on the 1st load (the subtitle becomes a skeleton). */
  total: number | null
  /** How many files the current page shows — always ≤ total. */
  mostrados: number
  /** Reload in progress: the button spins and locks. */
  atualizando: boolean
  /** How many items are selected (only the owner selects/deletes in batch). */
  selecionados: number
  canEdit: boolean
  onAtualizar: () => void
  onExcluirSelecionados: () => void
}

/**
 * "300 arquivos · 50 no total" shrinks to "50 arquivos" when everything fits on
 * one page, and becomes "Nenhum arquivo" at zero — never a dangling "0 arquivos".
 */
export function textoDoSubtitulo(total: number, mostrados: number): string {
  if (total === 0) return "Nenhum arquivo"
  if (mostrados > 0 && mostrados < total) {
    return `${plural(mostrados, "arquivo")} · ${formatInteger(total)} no total`
  }
  return plural(total, "arquivo")
}

/**
 * Drive header in the skeleton of contract §1: h1 + scope subtitle, "Excluir N"
 * (delete N) as the destructive action (only when there is a selection) and
 * "Atualizar" as ghost.
 */
export function DriveHeader({
  total, mostrados, atualizando, selecionados, canEdit, onAtualizar, onExcluirSelecionados,
}: Props) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold text-foreground">Drive</h1>
        {total != null ? (
          <p className="text-sm font-medium text-muted-foreground">{textoDoSubtitulo(total, mostrados)}</p>
        ) : (
          <Skeleton className="mt-1 h-4 w-64" />
        )}
      </div>

      <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
        {canEdit && selecionados > 0 && (
          <Button
            variant="destructive"
            size="sm"
            onClick={onExcluirSelecionados}
            className="gap-1.5 max-md:h-10"
          >
            <TbTrash size={14} aria-hidden="true" />
            Excluir {formatInteger(selecionados)}
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={onAtualizar}
          disabled={atualizando}
          aria-label="Atualizar a lista de arquivos"
          className="gap-1.5 max-md:h-10"
        >
          <TbRefresh size={14} className={atualizando ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
          Atualizar
        </Button>
      </div>
    </div>
  )
}
