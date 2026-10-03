"use client"

import { Badge } from "@/app/components/ui/badge"
import { cn } from "@/lib/utils"
import { typeStyle } from "@/consts/ExecutorTypeStyles"
import type { IExecutor } from "@/service/types"

/**
 * Badge that distinguishes the executor type.
 *
 * The vocabulary (name, icon and color) lives in `consts/ExecutorTypeStyles` —
 * the only copy of it used to be here, and the type filter and the group
 * headers ended up creating their own, already with different shades.
 */
export function ExecutorTypeBadge({
  type,
  size = "md",
}: {
  type: IExecutor["executor_type"]
  size?: "sm" | "md"
}) {
  const estilo = typeStyle(type)
  const Icone = estilo.icone

  return (
    <Badge
      className={cn(
        "border gap-1",
        size === "sm" ? "text-[9px] px-1 py-0 leading-tight" : "text-[10px] select-none",
        estilo.fundo, estilo.texto, estilo.borda,
      )}
    >
      <Icone size={size === "sm" ? 10 : 12} /> {estilo.nome}
    </Badge>
  )
}
