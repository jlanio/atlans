"use client"

import type { IconType } from "react-icons"
import { cn } from "@/lib/utils"

/**
 * Grupo de toggle padrão do contrato (§1): `role="group"` com botões
 * `aria-pressed`, moldura `inline-flex h-8 rounded-md border bg-card`, divisória
 * `border-l first:border-l-0`, ativo `bg-accent`, foco `ring-[3px] ring-ring/50`
 * e alvo ≥40px no telefone (`max-md:h-10`).
 *
 * Substitui os dois controles segmentados ad-hoc que a tela tinha (tipo e
 * status), que usavam pílulas `bg-muted` com `shadow-sm` — fora do padrão das
 * telas irmãs. O componente é genérico no tipo do valor para servir aos dois.
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
