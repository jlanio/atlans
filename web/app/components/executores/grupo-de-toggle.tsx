"use client"

import type { IconType } from "react-icons"
import { cn } from "@/lib/utils"

/**
 * The contract's standard toggle group (§1): `role="group"` with
 * `aria-pressed` buttons, `inline-flex h-8 rounded-md border bg-card` frame,
 * `border-l first:border-l-0` divider, active `bg-accent`, focus
 * `ring-[3px] ring-ring/50` and a ≥40px target on phones (`max-md:h-10`).
 *
 * Replaces the two ad-hoc segmented controls the screen had (type and
 * status), which used `bg-muted` pills with `shadow-sm` — outside the pattern
 * of the sibling screens. The component is generic over the value type to serve both.
 */
export function GrupoDeToggle<T extends string>({ rotulo, valor, onChange, opcoes }: {
  rotulo: string
  valor: T
  onChange: (v: T) => void
  opcoes: { valor: T; rotulo: string; icone?: IconType; aria?: string }[]
}) {
  return (
    <div
      role="group"
      aria-label={rotulo}
      className="inline-flex h-8 overflow-hidden rounded-md border bg-card max-md:h-10"
    >
      {opcoes.map(opcao => {
        const ativo = opcao.valor === valor
        const Icone = opcao.icone
        return (
          <button
            key={opcao.valor}
            type="button"
            aria-pressed={ativo}
            aria-label={opcao.aria}
            onClick={() => onChange(opcao.valor)}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 text-xs font-medium outline-none transition-colors",
              "border-l first:border-l-0 focus-visible:z-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
              ativo ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
            )}
          >
            {Icone && <Icone size={13} className="shrink-0" aria-hidden="true" />}
            {opcao.rotulo}
          </button>
        )
      })}
    </div>
  )
}
