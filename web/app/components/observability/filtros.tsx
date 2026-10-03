"use client"

import { useEffect, useRef, useState } from "react"
import { TbSearch, TbSparkles, TbX } from "react-icons/tb"
import { Input } from "@/app/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { cn } from "@/lib/utils"
import type { IExecutorMetrics, IObservabilityMetrics, IWorkflowMetricsRow } from "@/service/types"
import { SeloAssistente } from "../shared/selo-assistente"
import { formatarInteiro, rotuloDaOrigem } from "@/lib/formatos"
import { filtrosAtivos, type EstadoDoHistorico, type OrigemFiltro, type StatusFiltro } from "./historico-url"

export type ContagensPorStatus = Partial<IObservabilityMetrics["by_status"]>

interface Props {
  estado: EstadoDoHistorico
  /** Receives only what changed; the page composer merges it with the rest and writes it to the URL. */
  onEstado: (mudanca: Partial<EstadoDoHistorico>) => void
  /** The metrics' `by_status`; without it the chips come without a number. */
  contagens?: ContagensPorStatus | null
  workspaces?: { id: string; name: string }[]
  workflows?: IWorkflowMetricsRow[]
  /** The "Sem executor" row (`unassigned`) is excluded: it is not a filterable host. */
  executores?: IExecutorMetrics[]
  /** Only when the user has more than one workspace, or is an admin. */
  mostrarWorkspace?: boolean
}

/** Sentinel for the selects: Radix does not accept `""` as an item value. */
const TODOS = "__todos__"
const ATRASO_DA_BUSCA_MS = 300

const CHIPS: { status: StatusFiltro | null; rotulo: string; contar: (c: ContagensPorStatus) => number | null }[] = [
  { status: null, rotulo: "Todas", contar: c => somaTotal(c) },
  { status: "failed", rotulo: "Falhas", contar: c => c.failed ?? null },
  // The backend's `status=running` filter returns only `running`; `pending` stays
  // out of the chip so the number matches the list it opens.
  { status: "running", rotulo: "Em andamento", contar: c => c.running ?? null },
  { status: "success", rotulo: "Concluídas", contar: c => c.success ?? null },
  { status: "cancelled", rotulo: "Canceladas", contar: c => c.cancelled ?? null },
]

function somaTotal(c: ContagensPorStatus): number | null {
  const partes = [c.success, c.failed, c.running, c.pending, c.cancelled, c.other].filter((n): n is number => typeof n === "number")
  return partes.length === 0 ? null : partes.reduce((a, b) => a + b, 0)
}

/** Display order of the selector; the set must match `ORIGENS` in
 *  `historico-url.ts` (the URL discards an unknown origin — a test guarantees it). */
export const ORIGENS_DA_UI: OrigemFiltro[] = ["manual", "schedule", "webhook", "retry", "mcp"]

/**
 * Table filters (spec §4.3). Nothing here holds filter state: everything goes
 * up through `onEstado` and comes back through the URL — F5 and a pasted link
 * reopen the same view. The only exception is the search text, which waits
 * 300 ms idle before going up, otherwise every keystroke would be a query with
 * `ILIKE` on the server.
 */
export function Filtros({
  estado, onEstado, contagens, workspaces = [], workflows = [], executores = [], mostrarWorkspace = false,
}: Props) {
  const ativos = filtrosAtivos(estado)
  const c = contagens ?? {}

  const workflowsVisiveis = estado.workspace
    ? workflows.filter(w => w.workspace_id === estado.workspace)
    : workflows
  const executoresVisiveis = executores.filter(e => !e.unassigned && e.agent_host)

  function limpar() {
    onEstado({ status: null, workspace: null, workflow: null, executor: null, origem: null, assistente: false, q: "" })
  }

  return (
    <div className="flex flex-col gap-2" role="group" aria-label="Filtros das execuções">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Status">
          {CHIPS.map(chip => {
            const n = chip.contar(c)
            return (
              <Chip
                key={chip.rotulo}
                rotulo={chip.rotulo}
                ativo={estado.status === chip.status}
                n={n}
                onClick={() => onEstado({ status: chip.status })}
              />
            )
          })}
          <span aria-hidden="true" className="mx-0.5 h-4 w-px shrink-0 bg-border" />
          {/* Independent toggle: combines with the status ("Falhas" +
              "Assistente"). No number on purpose — the count we have is of
              WORKFLOWS, and next to chips that count RUNS it would lie. */}
          <Chip
            rotulo="Assistente"
            ativo={estado.assistente}
            n={null}
            icone
            onClick={() => onEstado({ assistente: !estado.assistente })}
          />
        </div>

        <div className="flex flex-1 flex-wrap items-center justify-end gap-2">
          {mostrarWorkspace && (
            <Seletor
              rotulo="Workspace"
              valor={estado.workspace}
              onValor={v => onEstado({ workspace: v, workflow: null })}
              opcoes={workspaces.map(w => ({ valor: w.id, rotulo: w.name }))}
            />
          )}
          <Seletor
            rotulo="Workflow"
            valor={estado.workflow}
            onValor={v => onEstado({ workflow: v })}
            opcoes={workflowsVisiveis.map(w => ({ valor: w.workflow_hash, rotulo: w.workflow_name, origem: w.origem }))}
          />
          <Seletor
            rotulo="Executor"
            valor={estado.executor}
            onValor={v => onEstado({ executor: v })}
            opcoes={executoresVisiveis.map(e => ({ valor: e.agent_host as string, rotulo: e.display_name }))}
          />
          <Seletor
            rotulo="Origem"
            todosRotulo="todas"
            valor={estado.origem}
            onValor={v => onEstado({ origem: (v as OrigemFiltro | null) })}
            opcoes={ORIGENS_DA_UI.map(o => ({ valor: o, rotulo: rotuloDaOrigem(o) ?? o }))}
          />
          <Busca valor={estado.q} onValor={q => onEstado({ q })} />
        </div>
      </div>

      {ativos > 0 && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{ativos === 1 ? "1 filtro ativo" : `${ativos} filtros ativos`}</span>
          <button
            type="button"
            onClick={limpar}
            className="inline-flex h-7 items-center gap-1 rounded-md px-1.5 font-medium text-primary hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 outline-none"
          >
            <TbX size={12} aria-hidden="true" /> Limpar filtros
          </button>
        </div>
      )}
    </div>
  )
}

function Chip({ rotulo, ativo, n, icone = false, onClick }: {
  rotulo: string
  ativo: boolean
  n: number | null
  /** The assistant sparkle, the same as the rows' badge. */
  icone?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-xs font-medium whitespace-nowrap transition-colors outline-none max-md:h-10",
        "focus-visible:ring-[3px] focus-visible:ring-ring/50",
        ativo
          ? "border-primary bg-primary/10 text-foreground"
          : "border-border bg-card text-muted-foreground hover:border-foreground/30 hover:text-foreground",
      )}
    >
      {icone && <TbSparkles size={13} aria-hidden="true" className="text-primary" />}
      {rotulo}
      {n != null && <b className="font-semibold text-foreground tabular-nums">{formatarInteiro(n)}</b>}
    </button>
  )
}

function Seletor({ rotulo, todosRotulo = "todos", valor, onValor, opcoes }: {
  rotulo: string
  todosRotulo?: string
  valor: string | null
  onValor: (v: string | null) => void
  /** `origem` exists only in the workflow selector, for the assistant sparkle. */
  opcoes: { valor: string; rotulo: string; origem?: string | null }[]
}) {
  // A URL value that is not in the list (workflow from another workspace, host
  // that left the fleet) still needs to show in the trigger — otherwise the
  // select shows "all" while the table is filtered.
  const lista = valor && !opcoes.some(o => o.valor === valor)
    ? [...opcoes, { valor, rotulo: valor }]
    : opcoes
  return (
    <Select value={valor ?? TODOS} onValueChange={v => onValor(v === TODOS ? null : v)}>
      <SelectTrigger size="sm" aria-label={rotulo} className="max-md:h-10 max-md:flex-1">
        <span className="text-muted-foreground">{rotulo}:</span>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={TODOS}>{todosRotulo}</SelectItem>
        {lista.map(o => (
          <SelectItem key={o.valor} value={o.valor}>
            <span className="flex min-w-0 items-center gap-1.5">
              <SeloAssistente origem={o.origem} compacto />
              <span className="truncate">{o.rotulo}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

function Busca({ valor, onValor }: { valor: string; onValor: (q: string) => void }) {
  const [texto, setTexto] = useState(valor)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  // What this field has already emitted: when the URL changes from outside
  // (Clear filters, new link), the field follows; when the URL only echoes what
  // it sent, there is nothing to do — and overwriting here would erase what the
  // person typed between the debounce and the router's response.
  const emitido = useRef(valor)

  useEffect(() => {
    // The URL stores the text without leading/trailing spaces: "timeout " comes
    // back as "timeout". Comparing what was emitted also without them is what
    // keeps the URL echo from erasing the space the person just typed.
    if (valor !== emitido.current.trim()) {
      emitido.current = valor
      setTexto(valor)
    }
  }, [valor])

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  function aoDigitar(q: string) {
    setTexto(q)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      emitido.current = q
      onValor(q)
    }, ATRASO_DA_BUSCA_MS)
  }

  return (
    <div className="relative max-md:w-full md:w-64">
      <TbSearch size={14} aria-hidden="true" className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        role="searchbox"
        aria-label="Buscar execuções"
        placeholder="Buscar por erro, workflow ou ID"
        value={texto}
        onChange={e => aoDigitar(e.target.value)}
        className="h-8 pl-8 text-xs max-md:h-10 md:text-xs"
      />
    </div>
  )
}
