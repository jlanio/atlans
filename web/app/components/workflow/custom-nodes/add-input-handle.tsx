import { cn } from "@/lib/utils"
import { HTMLAttributes, ReactNode } from "react"

interface AddInputHandleProps extends HTMLAttributes<HTMLDivElement> {
  connectionVisible?: boolean
  children: ReactNode
  label?: string
}

/**
 * Wrapper espelhado do AddConnectionHandle para handles de entrada.
 * Linha tracejada distingue visualmente entradas de saídas (linha sólida).
 * Quando conectado: não exibe nada (igual ao AddConnectionHandle).
 */
const AddInputHandle = ({ connectionVisible: open, children, label, className, style }: AddInputHandleProps) => {
  return (
    <div className="flex items-center">
      {children}

      {open && (
        <div
          className={cn("port-top absolute flex items-center -left-1.5", className)}
          style={{ ...style, transform: 'translateY(-50%)' }}
        >
          <div className="absolute flex items-center w-14 -translate-x-full">
            {/* Linha tracejada — distingue entrada de saída */}
            {/* `text-muted-foreground` em vez de `color` inline: o fallback
                era `#64748b`, um cinza FRIO que não existe em nenhuma das duas
                paletas (o `--muted-foreground` real é quente). Sendo classe, o
                token resolve nos dois temas sem fallback nenhum. */}
            <div
              className="absolute z-0 w-14 h-0.5 text-muted-foreground"
              style={{
                backgroundImage: 'repeating-linear-gradient(90deg, currentColor 0, currentColor 4px, transparent 4px, transparent 8px)',
              }}
            />
            {label && (
              <div className="absolute left-1/2 z-20 -translate-x-1/2 bg-card px-1 rounded">
                <p className="text-xs max-w-20 truncate">{label}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default AddInputHandle
