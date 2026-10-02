"use client"

import { TbRefresh, TbTrash } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import { formatarInteiro, plural } from "@/lib/formatos"

interface Props {
  /** Total do filtro inteiro; nulo na 1ª carga (o subtítulo vira esqueleto). */
  total: number | null
  /** Quantos arquivos a página atual mostra — sempre ≤ total. */
  mostrados: number
  /** Recarga em curso: o botão gira e trava. */
  atualizando: boolean
  /** Quantos itens estão selecionados (só o owner seleciona/exclui em lote). */
  selecionados: number
  canEdit: boolean
  onAtualizar: () => void
  onExcluirSelecionados: () => void
}

/**
 * "300 arquivos · 50 no total" some para "50 arquivos" quando tudo cabe numa
 * página, e vira "Nenhum arquivo" no zero — nunca "0 arquivos" pendurado.
 */
export function textoDoSubtitulo(total: number, mostrados: number): string {
  if (total === 0) return "Nenhum arquivo"
  if (mostrados > 0 && mostrados < total) {
    return `${plural(mostrados, "arquivo")} · ${formatarInteiro(total)} no total`
  }
  return plural(total, "arquivo")
}

/**
 * Cabeçalho do Drive no esqueleto do contrato §1: h1 + subtítulo de escopo,
 * "Excluir N" como ação destrutiva (só quando há seleção) e "Atualizar" em
 * ghost.
 */
export function CabecalhoDoDrive({
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
            Excluir {formatarInteiro(selecionados)}
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
