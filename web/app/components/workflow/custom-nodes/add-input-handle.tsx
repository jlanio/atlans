import { cn } from "@/lib/utils"
import { HTMLAttributes, ReactNode } from "react"

interface AddInputHandleProps extends HTMLAttributes<HTMLDivElement> {
  connectionVisible?: boolean
  children: ReactNode
  label?: string
}

/**
 * Mirrored wrapper of AddConnectionHandle for input handles.
 * A dashed line visually distinguishes inputs from outputs (solid line).
 * When connected: shows nothing (same as AddConnectionHandle).
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
            {/* Dashed line — distinguishes input from output */}
            {/* `text-muted-foreground` instead of inline `color`: the fallback
                was `#64748b`, a COOL gray that doesn't exist in either of the two
                palettes (the real `--muted-foreground` is warm). Being a class, the
                token resolves in both themes with no fallback at all. */}
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
