"use client"

import { TbFile, TbSearch, TbWorld } from "react-icons/tb"
import { Input } from "@/app/components/ui/input"
import { cn } from "@/lib/utils"
import { formatInteger } from "@/lib/formatos"
import type { ArtifactTab } from "@/app/(dashboard)/artifacts/use-artifacts-query"

/**
 * Artifacts controls: the tabs and the format filter become canonical toggle
 * groups (contract §1) — `role="group"`, `aria-pressed`, active in `bg-accent`
 * — instead of the bottom-bordered tabs and the loose default/outline buttons
 * the screen had. The search stays the same (it goes to the server with
 * debounce in the page); here it is only the field.
 */

const ABAS: { valor: ArtifactTab; rotulo: string; icone: typeof TbFile }[] = [
  { valor: "execution",   rotulo: "Execução",   icone: TbFile },
  { valor: "publication", rotulo: "Publicação", icone: TbWorld },
]

/** Execution × Publication. The counter is the SERVER total of the open tab. */
export function AbasDeArtefatos({ tab, total, onTab }: {
  tab: ArtifactTab; total: number; onTab: (t: ArtifactTab) => void
}) {
  return (
    <div
      role="group"
      aria-label="Tipo de artefato"
      className="inline-flex h-8 overflow-hidden rounded-md border bg-card max-md:h-10"
    >
      {ABAS.map(({ valor, rotulo, icone: Icone }) => {
        const ativo = valor === tab
        return (
          <button
            key={valor}
            type="button"
            aria-pressed={ativo}
            onClick={() => onTab(valor)}
            className={cn(
              "flex items-center gap-1.5 px-3 text-xs font-medium outline-none transition-colors",
              "border-l first:border-l-0 focus-visible:z-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
              ativo ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
            )}
          >
            <Icone size={14} aria-hidden="true" />
            {rotulo}
            {/* Only shows the count of the ACTIVE tab: the total is from the server for
                the open filter, and there is no way to know the other tab's without
                a second request. */}
            {ativo && total > 0 && (
              <span className="rounded-full bg-background/70 px-1.5 py-0.5 text-[10px] tabular-nums">
                {formatInteger(total)}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

/** Search field (the debounce and the trip to the server live in the page). */
export function ArtifactsSearch({ valor, onChange }: {
  valor: string; onChange: (v: string) => void
}) {
  return (
    <div className="relative w-full max-w-xs">
      <TbSearch size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
      <Input
        placeholder="Buscar por workflow, chave ou arquivo…"
        value={valor}
        onChange={e => onChange(e.target.value)}
        aria-label="Buscar artefatos"
        className="h-8 pl-8 text-sm max-md:h-10"
      />
    </div>
  )
}

/**
 * Format filter as a toggle group. "Todos" ("all") is always first; it only
 * appears when there is more than one accumulated format (otherwise the filter
 * separates nothing).
 */
export function FormatFilter({ formatos, atual, onFormato }: {
  formatos: string[]; atual: string; onFormato: (f: string) => void
}) {
  if (formatos.length <= 1) return null
  const opcoes = ["all", ...formatos]
  return (
    <div
      role="group"
      aria-label="Formato"
      className="inline-flex h-8 overflow-hidden rounded-md border bg-card max-md:h-10"
    >
      {opcoes.map(f => {
        const ativo = atual === f
        return (
          <button
            key={f}
            type="button"
            aria-pressed={ativo}
            onClick={() => onFormato(f)}
            className={cn(
              "px-3 text-xs font-medium outline-none transition-colors",
              "border-l first:border-l-0 focus-visible:z-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
              ativo ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
            )}
          >
            {f === "all" ? "Todos" : f.toUpperCase()}
          </button>
        )
      })}
    </div>
  )
}
