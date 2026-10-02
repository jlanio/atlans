"use client"

import { Badge } from "@/app/components/ui/badge"
import { cn } from "@/lib/utils"
import { estiloDoTipo } from "@/consts/ExecutorTypeStyles"
import type { IExecutor } from "@/service/types"

/**
 * Badge que distingue o tipo do executor.
 *
 * O vocabulário (nome, ícone e cor) mora em `consts/ExecutorTypeStyles` — aqui
 * ficava a única cópia dele, e o filtro por tipo e os cabeçalhos de grupo
 * acabaram criando as suas, já com tonalidades diferentes.
 */
export function ExecutorTypeBadge({
  type,
  size = "md",
}: {
  type: IExecutor["executor_type"]
  size?: "sm" | "md"
}) {
  const estilo = estiloDoTipo(type)
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
