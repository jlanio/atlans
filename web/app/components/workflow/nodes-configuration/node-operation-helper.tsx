"use client"
import { INodePortAPI } from "@/service/types"
import { NODE_ICONS, NODE_TYPES, NodeTypes } from "@/consts/WorkflowIcons"
import { TbError404, TbArrowRight } from "react-icons/tb"
import { cn } from "@/lib/utils"

interface Props {
  name: string
  alias: string
  description: string
  type: string
  inputs: INodePortAPI[]
  outputs: INodePortAPI[]
}

function PortBadge({ label, dim }: { label: string; dim?: boolean }) {
  return (
    <span className={cn(
      "px-2 py-0.5 rounded text-[11px] font-mono border",
      dim
        ? "bg-muted text-muted-foreground border-border"
        : "bg-card text-foreground border-border"
    )}>
      {label}
    </span>
  )
}

function ArrowLine() {
  return (
    <div className="flex items-center gap-0.5 text-muted-foreground">
      <div className="w-8 h-px bg-border" />
      <TbArrowRight size={12} />
    </div>
  )
}

export default function NodeOperationHelper({ name, alias, description, type, inputs, outputs }: Props) {
  const Icon = NODE_ICONS[name] ?? TbError404
  const TypeIcon = NODE_TYPES[type as NodeTypes]

  const maxPorts = Math.max(inputs.length, outputs.length, 1)

  return (
    <div className="flex flex-col gap-5 px-4 py-4">

      {/* Cabeçalho de tipo */}
      <div className="flex items-center gap-1.5">
        {TypeIcon && <TypeIcon size={12} className="text-muted-foreground" />}
        <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium">
          {type ?? "node"}
        </p>
      </div>

      {/* Diagrama de operação */}
      <div className="flex items-center justify-center gap-2">

        {/* Inputs */}
        {inputs.length > 0 && (
          <div className="flex flex-col gap-2 items-end">
            {inputs.map(p => <PortBadge key={p.name} label={p.name} />)}
          </div>
        )}

        {/* Seta de entrada */}
        {inputs.length > 0 && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: maxPorts }).map((_, i) => (
              <ArrowLine key={i} />
            ))}
          </div>
        )}

        {/* Ícone central */}
        <div className="flex flex-col items-center gap-1 border rounded-md px-4 py-3 bg-muted/40 min-w-[4rem]">
          <Icon className="text-2xl text-foreground/80" />
          <p className="text-[10px] text-muted-foreground text-center leading-tight max-w-[5rem] truncate">
            {alias}
          </p>
        </div>

        {/* Seta de saída */}
        {outputs.length > 0 && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: maxPorts }).map((_, i) => (
              <ArrowLine key={i} />
            ))}
          </div>
        )}

        {/* Outputs */}
        {outputs.length > 0 && (
          <div className="flex flex-col gap-2 items-start">
            {outputs.map(p => <PortBadge key={p.name} label={p.name} dim />)}
          </div>
        )}

      </div>

      {/* Descrição */}
      {description && (
        <div className="flex flex-col gap-1.5">
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium">
            Descrição
          </p>
          <p className="text-sm text-foreground/80 leading-relaxed">
            {description}
          </p>
        </div>
      )}

      {/* Nota de ausência de configuração */}
      <div className="flex items-center gap-2 bg-muted/50 rounded-md px-3 py-2">
        <div className="w-1 h-4 rounded-full bg-border flex-shrink-0" />
        <p className="text-[11px] text-muted-foreground leading-snug">
          Este nó não requer configuração. Conecte as entradas e saídas para utilizá-lo.
        </p>
      </div>

    </div>
  )
}
