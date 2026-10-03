"use client"

import { useEffect, useRef, useState } from "react"
import { TbSearch, TbSparkles, TbX } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { cn } from "@/lib/utils"
import { formatInteger } from "@/lib/formatos"
import { CHIP_FILTERS, SORT_LABEL, FILTER_LABEL } from "./filtros"
import { DEFAULT_STATE, SORT_ORDERS, filtrosAtivos, type ProjectsState, type Filtro, type Ordem } from "./projetos-url"

export interface FilterBarProps {
  estado: ProjectsState
  /** Receives only what changed; the page composer merges it with the rest and writes it to the URL. */
  onEstado: (mudanca: Partial<ProjectsState>) => void
  onLimpar: () => void
  /** Count of each chip over the whole list (`contarPorFiltro`). */
  contagens: Record<Filtro, number>
  /** "Recolher todos"/"Expandir todos" (collapse/expand all) only exists with groups. */
  temGrupos: boolean
  todosRecolhidos: boolean
  onRecolherTodos: () => void
  onExpandirTodos: () => void
}

// The search is local (the list is already in memory), but each keystroke
// written to the URL is a `router.replace`; a short pause gathers the keystrokes
// of a word without the person noticing the wait.
const SEARCH_DELAY_MS = 200

/**
 * Where the bar changes subject: after "Inativos" (from state to nature
 * and situation) and after "Com portal" (the slice by WHO created the workflow,
 * which is not a property of the workflow like the others).
 */
const SEPARATOR_AFTER: Filtro[] = ["inativos", "portal"]

/**
 * Search, sort, collapse and chips bar (docs/specs/projects.md §3.6).
 * The file is not called `filtros.tsx` on purpose: next to `filtros.ts`, the
 * same `import "./filtros"` would resolve to the `.ts` for tsc and Vite and to
 * the `.tsx` for Next's webpack — and the page would break only in the build.
 *
 * Nothing here holds filter state: everything goes up through `onEstado` and
 * comes back through the URL. The only exception is the search text, which
 * waits a moment idle.
 */
export function BarraDeFiltros({
  estado, onEstado, onLimpar, contagens, temGrupos, todosRecolhidos, onRecolherTodos, onExpandirTodos,
}: FilterBarProps) {
  const ativos = filtrosAtivos(estado)
  // `pausado` and `nunca` arrive through the attention strip and have no fixed
  // chip: a provisional chip, already checked, shows the slice in effect —
  // otherwise the strip disappears (when the number hits zero) and the list
  // stays filtered with nothing saying why.
  const filterWithoutChip = CHIP_FILTERS.includes(estado.filtro) ? null : estado.filtro

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Busca valor={estado.q} onValor={q => onEstado({ q })} />
        <Select value={estado.ordem} onValueChange={v => onEstado({ ordem: v as Ordem })}>
          <SelectTrigger size="sm" aria-label="Ordenar" className="max-md:h-10">
            <span className="text-muted-foreground">Ordenar:</span>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SORT_ORDERS.map(o => (
              <SelectItem key={o} value={o}>{SORT_LABEL[o]}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {temGrupos && (
          <Button
            variant="ghost"
            size="sm"
            onClick={todosRecolhidos ? onExpandirTodos : onRecolherTodos}
            className="max-md:h-10"
          >
            {todosRecolhidos ? "Expandir todos" : "Recolher todos"}
          </Button>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* On the phone the chips scroll horizontally instead of wrapping into three
            lines; on desktop they wrap, because there is width. */}
        <div
          role="group"
          aria-label="Filtros"
          className="flex min-w-0 items-center gap-1.5 max-md:overflow-x-auto max-md:pb-1 md:flex-wrap"
        >
          {CHIP_FILTERS.map(f => (
            <span key={f} className="contents">
              <Chip
                filtro={f}
                ativo={estado.filtro === f}
                n={contagens[f]}
                onClick={() => onEstado({ filtro: estado.filtro === f && f !== DEFAULT_STATE.filtro ? DEFAULT_STATE.filtro : f })}
              />
              {SEPARATOR_AFTER.includes(f) && <span aria-hidden="true" className="mx-0.5 h-4 w-px shrink-0 bg-border" />}
            </span>
          ))}
          {filterWithoutChip && (
            <Chip filtro={filterWithoutChip} ativo n={contagens[filterWithoutChip]} onClick={() => onEstado({ filtro: DEFAULT_STATE.filtro })} />
          )}
        </div>
        {ativos > 0 && (
          <button
            type="button"
            onClick={onLimpar}
            className="inline-flex h-8 shrink-0 items-center gap-1 rounded-md px-1.5 text-xs font-medium text-primary outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:h-10"
          >
            <TbX size={12} aria-hidden="true" /> Limpar filtros
          </button>
        )}
      </div>
    </div>
  )
}

function Chip({ filtro, ativo, n, onClick }: { filtro: Filtro; ativo: boolean; n: number | undefined; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full border px-3 text-xs font-medium whitespace-nowrap transition-colors outline-none max-md:h-10",
        "focus-visible:ring-[3px] focus-visible:ring-ring/50",
        ativo
          ? "border-primary bg-primary/10 text-foreground"
          : "border-border bg-card text-muted-foreground hover:border-foreground/30 hover:text-foreground",
      )}
    >
      {/* The chip's sparkle is the same as the row badge's: whoever sees one
          recognizes the other without reading the label. */}
      {filtro === "assistente" && <TbSparkles size={13} aria-hidden="true" className="text-primary" />}
      {FILTER_LABEL[filtro]}
      {n != null && <b className="font-semibold text-foreground tabular-nums">{formatInteger(n)}</b>}
    </button>
  )
}

function Busca({ valor, onValor }: { valor: string; onValor: (q: string) => void }) {
  const [texto, setText] = useState(valor)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  // What this field has already emitted: when the URL changes from outside
  // (Clear filters, new link), the field follows; when the URL only echoes what
  // it sent, there is nothing to do — and overwriting here would erase what the
  // person typed between the pause and the router's response.
  const emitido = useRef(valor)

  useEffect(() => {
    // The URL stores the text without leading/trailing spaces: "bacia " comes back
    // as "bacia". Comparing what was emitted also without them is what keeps the
    // URL echo from erasing the space the person just typed.
    if (valor !== emitido.current.trim()) {
      emitido.current = valor
      setText(valor)
    }
  }, [valor])

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  function onType(q: string) {
    setText(q)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      emitido.current = q
      onValor(q)
    }, SEARCH_DELAY_MS)
  }

  return (
    <div className="relative max-md:w-full md:w-72">
      <TbSearch size={14} aria-hidden="true" className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        role="searchbox"
        aria-label="Buscar workflow ou grupo"
        placeholder="Buscar workflow ou grupo…"
        value={texto}
        onChange={e => onType(e.target.value)}
        // 16px on the phone: below that iOS zooms in when the field gets focus.
        className="h-8 pl-8 text-base max-md:h-10 md:text-xs"
      />
    </div>
  )
}
