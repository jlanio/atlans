"use client"

import { TbSearch } from "react-icons/tb"
import { Input } from "@/app/components/ui/input"
import { cn } from "@/lib/utils"

interface Props {
  busca: string
  onBusca: (v: string) => void
  ext: string
  onExt: (v: string) => void
  /** Known extensions (accumulated), already sorted. */
  extensoes: string[]
}

/**
 * Search by name + extension chips. The chips became the contract's canonical
 * toggle group (§1): each one is `aria-pressed`, active in `bg-accent
 * text-foreground`, with the `ring-[3px]` focus pair and a 40px target on phones.
 * Before they were buttons with a literal orange border and no pressed state.
 */
export function DriveFilters({ busca, onBusca, ext, onExt, extensoes }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      <div className="relative min-w-[200px] flex-1">
        <TbSearch size={14} className="absolute top-1/2 left-3 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input
          placeholder="Buscar por nome…"
          aria-label="Buscar arquivos por nome"
          value={busca}
          onChange={e => onBusca(e.target.value)}
          className="h-9 pl-8 text-sm max-md:h-10"
        />
      </div>
      {extensoes.length > 1 && (
        <div role="group" aria-label="Filtrar por tipo de arquivo" className="flex flex-wrap items-center gap-1.5">
          <Chip ativo={ext === ""} onClick={() => onExt("")}>Todos</Chip>
          {extensoes.map(e => (
            <Chip key={e} ativo={ext === e} onClick={() => onExt(e === ext ? "" : e)} mono>
              {e}
            </Chip>
          ))}
        </div>
      )}
    </div>
  )
}

function Chip({
  ativo, onClick, mono, children,
}: { ativo: boolean; onClick: () => void; mono?: boolean; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 items-center rounded-md border bg-card px-3 text-xs font-medium transition-colors outline-none max-md:h-10",
        "focus-visible:ring-[3px] focus-visible:ring-ring/50",
        mono && "font-mono uppercase",
        ativo ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
      )}
    >
      {children}
    </button>
  )
}
