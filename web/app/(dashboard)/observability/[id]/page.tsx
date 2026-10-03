"use client"
import { memo, useCallback, useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { GisFlowService, IRunSummary, INodeStatSummary } from "@/service/GisFlowService"
import { useWorkspace } from "@/context/WorkspaceContext"
import { DispatchTierBadge } from "@/app/components/shared/dispatch-tier-badge"
import { useFetchData } from "@/app/hooks/useFetchData"
import PageRoot from "@/app/components/page-root"
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card"
import { Button } from "@/app/components/ui/button"
import { TbArrowLeft, TbClock, TbRefresh, TbChevronDown, TbChevronUp, TbDatabase, TbBolt, TbBox, TbEdit, TbChevronRight } from "react-icons/tb"
import "dayjs/locale/pt-br"
import { dayjs, fromNowLocal } from "@/lib/dayjs"
import { formatDuration, successRateColor } from "@/utils/formatters"
import { StatusBadge } from "@/app/components/shared/StatusBadge"
import { CABECALHO_DE_COLUNAS, CELULA_COM_ROTULO, DESTAQUE_DA_FICHA, LINHA_EMPILHADA, LINHA_EXPANDIDA } from "@/app/components/shared/tabela-empilhada"

dayjs.locale("pt-br")

// Run row: the whole row leads to the run's page; the error expands through
// its own button, so the two gestures do not fight over the click.
// Memoized: the table lists up to 20 rows and the workspace/policy poll
// re-rendered the whole page; with a stable `onAbrir` (useCallback below)
// each row only reconciles when its own `run` changes.
const RunRow = memo(function RunRow({ run, dedicado, onAbrir }: { run: IRunSummary; dedicado: boolean; onAbrir: (runId: string) => void }) {
  const [expanded, setExpanded] = useState(false)
  const hasError = !!run.error_message

  return (
    <>
      <tr
        className={`border-b last:border-0 cursor-pointer hover:bg-muted/50 focus-within:bg-muted/50 ${LINHA_EMPILHADA}`}
        onClick={() => onAbrir(run.run_id)}
      >
        <td className={`py-2 pr-4 font-mono text-xs text-muted-foreground ${DESTAQUE_DA_FICHA}`}>
          {/* Keyboard/screen-reader target: a button on the id, not the whole row
              (a <tr role="button"> would erase the cells and cannot contain the
              button that expands the error). */}
          <button
            type="button"
            onClick={e => { e.stopPropagation(); onAbrir(run.run_id) }}
            aria-label={`Abrir execução ${run.run_id.slice(0, 8)}`}
            className="rounded-sm outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            {run.run_id.slice(0, 8)}…
          </button>
        </td>
        <td className="py-2 pr-4"><StatusBadge status={run.status} /></td>
        <td className="py-2 pr-4 text-sm">{fromNowLocal(run.started_at)}</td>
        <td className="py-2 pr-4 text-sm text-right">
          {run.duration_seconds != null ? `${run.duration_seconds.toFixed(2)}s` : "—"}
        </td>
        <td className="py-2 pr-4 font-mono text-xs text-muted-foreground max-w-[180px]" title={run.agent_host ?? undefined}>
          <span className="flex items-center gap-1.5">
            <span className="min-w-0 truncate">{run.agent_host ?? "—"}</span>
            <DispatchTierBadge tier={run.dispatch_tier} dedicado={dedicado} />
          </span>
        </td>
        {/* No `data-rotulo`: the cell is EMPTY when there was no retry, and a
            stray label would be worse than nothing. The glyph already carries the meaning. */}
        <td className="py-2 text-xs text-muted-foreground text-right">
          {run.retry_count > 0 && <span className="text-amber-600">↺{run.retry_count}</span>}
        </td>
        <td className="py-2 pl-2 text-right whitespace-nowrap">
          {hasError && (
            <button
              type="button"
              onClick={e => { e.stopPropagation(); setExpanded(v => !v) }}
              onKeyDown={e => e.stopPropagation()}
              aria-expanded={expanded}
              aria-label={expanded ? "Ocultar o erro" : "Mostrar o erro"}
              className="inline-flex size-6 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
            >
              {expanded ? <TbChevronUp className="h-3 w-3" /> : <TbChevronDown className="h-3 w-3" />}
            </button>
          )}
          <TbChevronRight className="ml-1 inline h-3 w-3 text-muted-foreground" aria-hidden="true" />
        </td>
      </tr>
      {expanded && run.error_message && (
        <tr className={`bg-red-50 dark:bg-red-950/20 ${LINHA_EXPANDIDA}`}>
          {/* `whitespace-pre-wrap` only breaks at spaces: a URL or a path with
              no space became the minimum width of the whole table, and it
              scrolled sideways. `wrap-anywhere` allows breaking at any point
              (`break-words` is not enough in a table: it does not reduce the
              column's minimum width). The height stops at 12 lines; a long
              traceback scrolls inside it. */}
          <td colSpan={7} className="px-3 py-2 text-xs text-red-700 dark:text-red-400 font-mono whitespace-pre-wrap wrap-anywhere">
            <div className="max-h-48 overflow-y-auto">{run.error_message}</div>
          </td>
        </tr>
      )}
    </>
  )
})

// ── Per-node execution Gantt ─────────────────────────────────────────────────
function GanttTimeline({ nodes }: { nodes: INodeStatSummary[] }) {
  // clone+sort memoized on `nodes` (above the early return because of the
  // rules of hooks) so as not to re-sort on every parent render.
  const sorted = useMemo(() => [...nodes].sort((a, b) => b.avg_duration_ms - a.avg_duration_ms), [nodes])
  if (nodes.length === 0) return null
  const maxMs = sorted[0].avg_duration_ms || 1

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Timeline de execução (média por nó)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-2">
          {sorted.map(node => {
            const pct = (node.avg_duration_ms / maxMs) * 100
            const hasError = node.failure_count > 0
            return (
              <div key={node.node_id} className="flex items-center gap-3 text-xs">
                {/* Label */}
                <div className="w-32 shrink-0 truncate text-right text-muted-foreground" title={node.node_name}>
                  {node.node_name}
                </div>
                {/* Barra */}
                <div className="flex-1 bg-muted rounded-full h-5 relative overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${hasError ? "bg-red-400/70" : "bg-primary/60"}`}
                    style={{ width: `${pct}%` }}
                  />
                  <span className="absolute inset-0 flex items-center pl-2 text-[10px] font-medium text-foreground/70">
                    {formatDuration(node.avg_duration_ms)}
                    {node.cache_hits > 0 && <span className="ml-1 text-purple-500">⚡{node.cache_hits}</span>}
                  </span>
                </div>
                {/* Falhas */}
                {hasError && (
                  <span className="shrink-0 text-red-500">{node.failure_count}✗</span>
                )}
              </div>
            )
          })}
        </div>
        <p className="text-[10px] text-muted-foreground mt-3">
          Barras representam a duração média por nó em relação ao nó mais lento. ⚡ = cache hits.
        </p>
      </CardContent>
    </Card>
  )
}

// Slowest nodes table
function NodeStatsTable({ nodes }: { nodes: INodeStatSummary[] }) {
  // Math.max(...map) memoized on `nodes` (above the early return because of the
  // rules of hooks); with an empty list it gives 1, without affecting the empty state below.
  const maxMs = useMemo(() => Math.max(...nodes.map(n => n.avg_duration_ms), 1), [nodes])
  if (nodes.length === 0) return (
    <div className="flex flex-col items-center justify-center py-8 gap-3 text-center">
      <div className="rounded-full bg-muted/60 p-3">
        <TbBox size={22} className="text-muted-foreground/40" />
      </div>
      <p className="text-sm text-muted-foreground max-w-[280px]">
        Nenhum dado de nós disponível ainda. Execute o workflow para coletar estatísticas por nó.
      </p>
    </div>
  )

  return (
    <table className="w-full text-sm">
      <thead className={CABECALHO_DE_COLUNAS}>
        <tr className="text-xs text-muted-foreground border-b">
          <th className="pb-2 text-left font-medium">Nó</th>
          <th className="pb-2 text-right font-medium">Duração média</th>
          <th className="pb-2 text-right font-medium">Falhas</th>
          <th className="pb-2 text-right font-medium">Cache hits</th>
          <th className="pb-2 text-right font-medium">Features (saída)</th>
        </tr>
      </thead>
      <tbody>
        {nodes.map(node => (
          <tr key={node.node_id} className={`border-b last:border-0 ${LINHA_EMPILHADA}`}>
            <td className={`py-2 pr-4 ${DESTAQUE_DA_FICHA}`}>
              <div className="flex flex-col gap-1">
                <span className="font-medium">{node.node_name}</span>
                {/* Relative duration bar */}
                <div className="h-1 w-full max-w-[120px] bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${(node.avg_duration_ms / maxMs) * 100}%` }}
                  />
                </div>
              </div>
            </td>
            <td data-rotulo="média" className={`py-2 pr-4 text-right font-mono text-xs ${CELULA_COM_ROTULO}`}>
              {formatDuration(node.avg_duration_ms)}
            </td>
            <td data-rotulo="falhas" className={`py-2 pr-4 text-right ${CELULA_COM_ROTULO}`}>
              {node.failure_count > 0
                ? <span className="text-red-600 font-medium">{node.failure_count}</span>
                : <span className="text-muted-foreground">0</span>}
            </td>
            <td data-rotulo="cache" className={`py-2 pr-4 text-right ${CELULA_COM_ROTULO}`}>
              {node.cache_hits > 0
                ? <span className="text-purple-600 font-medium flex items-center justify-end gap-1"><TbBolt className="h-3 w-3" />{node.cache_hits}</span>
                : <span className="text-muted-foreground">—</span>}
            </td>
            <td data-rotulo="saída" className={`py-2 text-right ${CELULA_COM_ROTULO}`}>
              {node.avg_output_features != null
                ? <span className="flex items-center justify-end gap-1 text-muted-foreground"><TbDatabase className="h-3 w-3" />{node.avg_output_features.toLocaleString()}</span>
                : <span className="text-muted-foreground">—</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function WorkflowObservabilityPage() {

  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  // The "rodou no pool" (ran on the pool) badge only makes sense in a workspace
  // WITH a dedicated one. The workflow's workspace comes in the payload only
  // for admins; for everyone else it is the active one — the only one the
  // workflow can be in.
  const { current } = useWorkspace()
  const [dedicado, setDedicado] = useState(false)

  const { data: metrics, loading, error, refetch: fetchMetrics } = useFetchData(
    () => GisFlowService.getWorkflowMetrics(id, 20),
    "Não foi possível carregar as métricas deste workflow.",
    [id]
  )

  // Waits for the metrics: for admins the workspace comes in them, and reading the
  // active one before that cost a second request (and a badge for the wrong workspace).
  const workspaceId = metrics ? (metrics.workspace_id ?? current?.id_hash ?? null) : null
  useEffect(() => {
    if (!workspaceId) { setDedicado(false); return }
    let cancelado = false
    GisFlowService.getWorkspacePolicy(workspaceId).then(res => {
      if (cancelado) return
      // A failing read = no badge: nothing is asserted about the policy.
      setDedicado(!res.error && (res.data?.primary.length ?? 0) > 0)
    })
    return () => { cancelado = true }
  }, [workspaceId])

  const successRate = metrics ? `${(metrics.success_rate * 100).toFixed(1)}%` : "—"
  // Stable so RunRow's React.memo holds: without this, every render gave a new
  // function to all rows and the poll re-rendered the whole table.
  const abrirRun = useCallback((runId: string) => router.push(`/observability/run/${runId}`), [router])

  return (
    <PageRoot>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push("/observability")} aria-label="Voltar ao Histórico">
            <TbArrowLeft />
          </Button>
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              {metrics?.workflow_name ?? "Workflow"}
            </h1>
            <p className="font-medium text-muted-foreground">Métricas de execução.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* The detail is read-only; whoever arrives here through a failure almost
              always wants to fix the workflow, and the editor is another route. */}
          <Button variant="outline" size="sm" onClick={() => router.push(`/workflow/${id}`)}>
            <TbEdit />
            Abrir no editor
          </Button>
          <Button variant="ghost" size="sm" onClick={() => fetchMetrics()} disabled={loading}>
            <TbRefresh className={loading ? "animate-spin" : ""} />
            Atualizar
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Summary metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total de Execuções</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.total_runs ?? "—"}</div>
            {metrics && metrics.failed_runs > 0 && (
              <p className="text-xs text-red-500 mt-1">{metrics.failed_runs} falhas</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Taxa de Sucesso</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${successRateColor(metrics?.success_rate)}`}>
              {successRate}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <TbClock className="h-3 w-3" /> Duração Média
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics ? `${metrics.avg_duration_seconds.toFixed(2)}s` : "—"}
            </div>
            {metrics?.min_duration_seconds != null && metrics?.max_duration_seconds != null && (
              <p className="text-xs text-muted-foreground mt-1">
                {metrics.min_duration_seconds.toFixed(1)}s — {metrics.max_duration_seconds.toFixed(1)}s
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">ID do Workflow</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm font-mono text-muted-foreground truncate">{id}</div>
          </CardContent>
        </Card>
      </div>

      {/* Latest runs table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Últimas execuções</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Carregando…</p>
          ) : metrics?.last_runs?.length ? (
            // Seven columns do not fit on a phone: from `md` up the table
            // scrolls on its own (the body contains the page's horizontal
            // scroll); below that the row becomes a stacked card, with no
            // scrolling at all (see tabela-empilhada.ts).
            <div className="overflow-x-auto">
            <table className="w-full md:min-w-[720px]">
              <thead className={CABECALHO_DE_COLUNAS}>
                <tr className="text-xs text-muted-foreground border-b">
                  <th className="pb-2 text-left font-medium">Run ID</th>
                  <th className="pb-2 text-left font-medium">Status</th>
                  <th className="pb-2 text-left font-medium">Início</th>
                  <th className="pb-2 text-right font-medium">Duração</th>
                  <th className="pb-2 text-left font-medium">Executor</th>
                  <th className="pb-2 text-right font-medium">Retry</th>
                  <th className="pb-2" />
                </tr>
              </thead>
              <tbody>
                {metrics.last_runs.map(run => (
                  <RunRow key={run.run_id} run={run} dedicado={dedicado} onAbrir={abrirRun} />
                ))}
              </tbody>
            </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Nenhuma execução registrada.</p>
          )}
        </CardContent>
      </Card>

      {/* Timeline Gantt */}
      {!loading && (metrics?.node_stats_summary?.length ?? 0) > 0 && (
        <GanttTimeline nodes={metrics!.node_stats_summary} />
      )}

      {/* Slowest nodes table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Nós mais lentos</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Carregando…</p>
          ) : (
            <NodeStatsTable nodes={metrics?.node_stats_summary ?? []} />
          )}
        </CardContent>
      </Card>
    </PageRoot>
  )
}
