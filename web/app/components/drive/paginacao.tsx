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
  /** A reload in progress locks navigation so pages aren't skipped midway. */
  refreshing: boolean
  onPrev: () => void
  onNext: () => void
}

/**
 * "Mostrando X–Y de N" footer + navigation, in the same format as admin/users.
 * The structure (span "{page} / {totalPages}" flanked by the two buttons) is what
 * the workspace-switch test uses to navigate — kept on purpose.
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
