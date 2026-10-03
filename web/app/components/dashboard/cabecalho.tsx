"use client"

import { TbRefresh } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { formatarInteiro } from "@/lib/formatos"
import { PERIODOS, type EstadoDoEscopo, type Periodo } from "./dashboard-url"

interface ContagensDoSubtitulo {
  /** Name of the active workspace; used only in the "ativo" (active) scope. */
  workspaceNome: string | null
  /** How many workspaces the user has; used only in the "todos" (all) scope. */
  workspaces: number
  /** `metrics.active_workflows`; `null` on the 1st load (subtitle becomes a skeleton). */
  ativos: number | null
}

interface Props extends ContagensDoSubtitulo {
  escopo: EstadoDoEscopo
  onEscopo: (escopo: EstadoDoEscopo) => void
  periodo: Periodo
  onPeriodo: (periodo: Periodo) => void
  atualizando: boolean
  onAtualizar: () => void
}

/** "N workflow(s) ativo(s)" — the plural from the number, not the spec's fixed form. */
function ativosTexto(n: number): string {
  return `${formatarInteiro(n)} ${n === 1 ? "workflow ativo" : "workflows ativos"}`
}

/**
 * Subtitle per scope (docs/specs/dashboard.md §3.9). Exported for testing.
 * In the active-workspace scope, the name and the count of active workflows;
 * in "todos", the number of workspaces plus the summed active ones. A null
 * `ativos` is the 1st load — the caller (the header) swaps in a skeleton
 * instead of writing "— ativos".
 */
export function textoDoSubtitulo(escopo: EstadoDoEscopo, { workspaceNome, workspaces, ativos }: ContagensDoSubtitulo): string {
  const n = ativos ?? 0
  if (escopo === "todos") {
    const ws = `${formatarInteiro(workspaces)} ${workspaces === 1 ? "workspace" : "workspaces"}`
    return `Todos os workspaces · ${ws} · ${ativosTexto(n)}`
  }
  return `«${workspaceNome ?? "workspace"}» · ${ativosTexto(n)}`
}

/**
 * Dashboard header (docs/specs/dashboard.md §3.9): the title, the subtitle
 * that says which scope the dashboard is about, the scope toggle (only with
 * more than one workspace) and Atualizar (refresh). The toggle switches
 * `?escopo=` — the same choice that flows down to every data call.
 */
export function CabecalhoDoDashboard({
  escopo, onEscopo, periodo, onPeriodo, workspaceNome, workspaces, ativos, atualizando, onAtualizar,
}: Props) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
        {ativos != null ? (
          <p className="text-sm font-medium text-muted-foreground">
            {textoDoSubtitulo(escopo, { workspaceNome, workspaces, ativos })}
          </p>
        ) : (
          <Skeleton className="mt-1 h-4 w-64" />
        )}
      </div>

      <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
        {/* Atualizar on the left, as in /projetos: the reload action comes
            first; the scope toggle is a filter, it goes after. */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onAtualizar}
          disabled={atualizando}
          aria-label="Atualizar o painel"
          className="gap-1.5 max-md:h-10"
        >
          <TbRefresh size={14} className={atualizando ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
          Atualizar
        </Button>
        {/* The toggle only makes sense with more than one workspace: with just
            one, there is no "todos" different from the "ativo". */}
        {workspaces > 1 && (
          <div
            role="group"
            aria-label="Escopo do painel"
            className="inline-flex h-8 w-full overflow-hidden rounded-md border bg-card max-md:h-10 sm:w-auto"
          >
            <BotaoDeEscopo
              ativo={escopo === "ativo"}
              rotulo={`«${workspaceNome ?? "workspace"}»`}
              onClick={() => onEscopo("ativo")}
            />
            <BotaoDeEscopo
              ativo={escopo === "todos"}
              rotulo="Todos os workspaces"
              onClick={() => onEscopo("todos")}
            />
          </div>
        )}
        {/* Period selector (docs/specs/dashboard.md §3.1): the same group as
            History. It governs the window of the indicators/chart and of the
            failures in "Precisa de atenção"; "Saúde · agora" and "Próximas" don't change. */}
        <div
          role="group"
          aria-label="Período"
          className="inline-flex h-8 w-full overflow-hidden rounded-md border bg-card max-md:h-10 sm:w-auto"
        >
          {PERIODOS.map(p => {
            const ativo = p === periodo
            return (
              <button
                key={p}
                type="button"
                aria-pressed={ativo}
                aria-label={`Últimos ${p} dias`}
                onClick={() => onPeriodo(p)}
                className={cn(
                  "flex-1 px-3 text-xs font-medium transition-colors outline-none sm:flex-none",
                  "border-l first:border-l-0 focus-visible:z-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
                  ativo ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )}
              >
                {p} dias
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function BotaoDeEscopo({ ativo, rotulo, onClick }: { ativo: boolean; rotulo: string; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={cn(
        "flex-1 truncate px-3 text-xs font-medium transition-colors outline-none sm:flex-none sm:max-w-[12rem]",
        "border-l first:border-l-0 focus-visible:z-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
        ativo ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
      )}
    >
      {rotulo}
    </button>
  )
}
