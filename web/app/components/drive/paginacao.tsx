"use client"

import { TbChevronLeft, TbChevronRight } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { formatarInteiro } from "@/lib/formatos"

interface Props {
  page: number
  totalPages: number
  total: number
  mostrandoDe: number
  mostrandoAte: number
  /** Recarga em curso trava a navegação para não pular páginas no meio. */
  refreshing: boolean
  onPrev: () => void
  onNext: () => void
}

/**
 * Rodapé "Mostrando X–Y de N" + navegação, no mesmo formato de admin/users.
 * A estrutura (span "{page} / {totalPages}" ladeado pelos dois botões) é a que
 * o teste de troca de workspace usa para navegar — mantida de propósito.
 */
export function RodapeDePaginacao({
  page, totalPages, total, mostrandoDe, mostrandoAte, refreshing, onPrev, onNext,
}: Props) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-muted-foreground tabular-nums">
        Mostrando <span className="font-medium text-foreground">{formatarInteiro(mostrandoDe)}</span>–
        <span className="font-medium text-foreground">{formatarInteiro(mostrandoAte)}</span> de{" "}
        <span className="font-medium text-foreground">{formatarInteiro(total)}</span>
      </span>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          aria-label="Página anterior"
          disabled={page <= 1 || refreshing}
          onClick={onPrev}
          className="max-md:size-10"
        >
          <TbChevronLeft size={16} aria-hidden="true" />
        </Button>
        <span className="text-xs text-muted-foreground tabular-nums">{page} / {totalPages}</span>
        <Button
          size="sm"
          variant="outline"
          aria-label="Próxima página"
          disabled={page >= totalPages || refreshing}
          onClick={onNext}
          className="max-md:size-10"
        >
          <TbChevronRight size={16} aria-hidden="true" />
        </Button>
      </div>
    </div>
  )
}
