"use client"

import { TbRefresh } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { formatarInteiro } from "@/lib/formatos"
import { PERIODOS, type EstadoDoEscopo, type Periodo } from "./dashboard-url"

interface ContagensDoSubtitulo {
  /** Nome do workspace ativo; usado só no escopo "ativo". */
  workspaceNome: string | null
  /** Quantos workspaces o usuário tem; usado só no escopo "todos". */
  workspaces: number
  /** `metrics.active_workflows`; `null` na 1ª carga (subtítulo vira esqueleto). */
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

/** "N workflow(s) ativo(s)" — o plural do número, não a forma fixa da spec. */
function ativosTexto(n: number): string {
  return `${formatarInteiro(n)} ${n === 1 ? "workflow ativo" : "workflows ativos"}`
}

/**
 * Subtítulo por escopo (docs/specs/dashboard.md §3.9). Exportado para teste.
 * No escopo do workspace ativo, o nome e a contagem de ativos; no "todos", o
 * número de workspaces mais os ativos somados. `ativos` nulo é a 1ª carga —
 * quem chama (o cabeçalho) troca por um esqueleto em vez de escrever "— ativos".
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
 * Cabeçalho do Dashboard (docs/specs/dashboard.md §3.9): o título, o subtítulo
 * que diz de que escopo o painel fala, o toggle de escopo (só com mais de um
 * workspace) e o Atualizar. O toggle troca `?escopo=` — a mesma escolha que
 * desce para todas as chamadas de dados.
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
        {/* Atualizar à esquerda, como em /projetos: a ação de recarregar vem
            primeiro; o toggle de escopo é filtro, fica depois. */}
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
        {/* Toggle só faz sentido com mais de um workspace: com um só, não há
            "todos" diferente do "ativo". */}
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
        {/* Seletor de período (docs/specs/dashboard.md §3.1): o mesmo grupo do
            Histórico. Governa a janela dos indicadores/gráfico e das falhas em
            "Precisa de atenção"; a "Saúde · agora" e as "Próximas" não mudam. */}
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
