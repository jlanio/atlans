"use client"

import { TbRefresh, TbTrash } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"

interface Props {
  /** Frase de escopo já pronta; `null` na 1ª carga (vira esqueleto). */
  subtitulo: string | null
  /** Recarga em curso: o botão gira e trava. */
  atualizando: boolean
  /** Quantos artefatos o botão vermelho promete apagar (interseção seleção×carregado). */
  aExcluir: number
  /** Só editores do workspace veem o botão de excluir. */
  podeExcluir: boolean
  onAtualizar: () => void
  onExcluir: () => void
}

/**
 * Cabeçalho de Artefatos (contrato §1): título, subtítulo de escopo com
 * esqueleto na 1ª carga, "Atualizar" em ghost e — só quando há seleção — a ação
 * destrutiva "Excluir N" à direita de tudo. Antes o Atualizar era outline.
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
