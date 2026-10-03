"use client"
import { useMemo } from "react"
import { useParams, useRouter } from "next/navigation"
import { useSession } from "next-auth/react"
import { GisFlowService } from "@/service/GisFlowService"
import { useFetchData } from "@/app/hooks/useFetchData"
import PageRoot from "@/app/components/page-root"
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card"
import { Button } from "@/app/components/ui/button"
import { StatusBadge } from "@/app/components/shared/StatusBadge"
import { COLUMN_HEADER, LABELED_CELL, CARD_HIGHLIGHT, STACKED_ROW } from "@/app/components/shared/tabela-empilhada"
import { formatDuration } from "@/utils/formatters"
import {
  TbArrowLeft, TbClock, TbRefresh, TbCalendar, TbServer,
  TbArrowRight, TbDatabase, TbBolt, TbAlertTriangle,
  TbShieldLock, TbUser, TbBuildingFactory2,
} from "react-icons/tb"
import { formatLocal } from "@/lib/dayjs"
import { categoryLabel, originLabel } from "@/lib/formatos"

function formatDateTime(iso: string | null) {
  return formatLocal(iso, "DD/MM/YYYY HH:mm:ss")
}

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>()
  const router = useRouter()
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === "admin"

  const { data: run, loading, error, refetch } = useFetchData(
    () => GisFlowService.getRunDetail(runId),
    "Nao foi possivel carregar os detalhes desta execucao.",
    [runId]
  )

  // entries/filter/sort + Math.max(...) ran on every render; memoized on
  // `run` (they recompute only when the detail changes), with maxMs derived from the memo.
  const { nodeEntries, maxMs } = useMemo(() => {
    const entries = run?.node_stats
      ? Object.entries(run.node_stats)
          .filter(([k]) => !k.startsWith("__"))
          .sort(([, a], [, b]) => b.duration_ms - a.duration_ms)
      : []
    const max = entries.length > 0
      ? Math.max(...entries.map(([, n]) => n.duration_ms), 1)
      : 1
    return { nodeEntries: entries, maxMs: max }
  }, [run])

  return (
    <PageRoot>
      {/* Cabecalho */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push("/observability")}>
            <TbArrowLeft />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-foreground">
                Execucao
              </h1>
              {run && <StatusBadge status={run.status} />}
            </div>
            <p className="font-mono text-xs text-muted-foreground mt-0.5">
              {runId}
            </p>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={refetch}>
          <TbRefresh className={loading ? "animate-spin" : ""} />
          Atualizar
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3 text-sm">{error}</div>
      )}

      {/* Run context: workflow and workspace come for any user in
       *  scope; the owner only for admins. Error origin and category, when
       *  the run already has them (runs older than the column lack them). */}
      {run && (run.workflow_name || run.workspace_name || run.trigger_source || run.error_category || (isAdmin && run.owner_username)) && (
        <div className="flex flex-wrap items-center gap-4 rounded-md border bg-muted/30 px-4 py-2 text-xs">
          {isAdmin && (
            <span className="inline-flex items-center gap-1.5 font-medium text-amber-700 dark:text-amber-400">
              <TbShieldLock size={14} /> Admin
            </span>
          )}
          {run.workflow_name && (
            <span className="inline-flex items-center gap-1.5 text-muted-foreground">
              <TbArrowRight size={12} /> Workflow: <span className="text-foreground">{run.workflow_name}</span>
            </span>
          )}
          {isAdmin && run.owner_username && (
            <span className="inline-flex items-center gap-1.5 text-muted-foreground">
              <TbUser size={12} /> Dono: <span className="text-foreground">{run.owner_username}</span>
            </span>
          )}
          {originLabel(run.trigger_source) && (
            <span className="inline-flex items-center gap-1.5 text-muted-foreground">
              Origem: <span className="text-foreground">{originLabel(run.trigger_source)}{run.triggered_by_username ? ` · ${run.triggered_by_username}` : ""}</span>
            </span>
          )}
          {categoryLabel(run.error_category) && (
            <span className="inline-flex items-center gap-1.5 text-muted-foreground">
              Categoria do erro: <span className="text-foreground">{categoryLabel(run.error_category)}</span>
            </span>
          )}
          {run.workspace_name && (
            <span className="inline-flex items-center gap-1.5 text-muted-foreground">
              <TbBuildingFactory2 size={12} /> Workspace: <span className="text-foreground">{run.workspace_name}</span>
            </span>
          )}
        </div>
      )}

      {run && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                  <TbClock size={14} /> Duracao
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {run.duration_seconds != null ? `${run.duration_seconds.toFixed(2)}s` : "—"}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                  <TbCalendar size={14} /> Inicio
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm font-medium">{formatDateTime(run.started_at)}</div>
                {run.finished_at && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Fim: {formatDateTime(run.finished_at)}
                  </p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                  <TbServer size={14} /> Executor
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm font-medium truncate" title={run.agent_host ?? undefined}>
                  {run.agent_host ?? "Servidor local"}
                </div>
                {run.retry_count > 0 && (
                  <p className="text-xs text-amber-600 mt-1">{run.retry_count} retentativa(s)</p>
                )}
              </CardContent>
            </Card>
            <Card
              className={run.workflow_hash ? "cursor-pointer hover:border-primary/50 transition-colors" : ""}
              onClick={() => run.workflow_hash && router.push(`/observability/${run.workflow_hash}`)}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                  <TbArrowRight size={14} /> Workflow
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm font-medium text-primary truncate">
                  Ver historico do workflow
                </div>
                <p className="text-[10px] text-muted-foreground font-mono mt-1 truncate">
                  {run.workflow_hash}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Error message */}
          {run.error_message && (
            <Card className="border-destructive/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-destructive flex items-center gap-1.5">
                  <TbAlertTriangle size={14} /> Erro
                </CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs text-destructive/90 font-mono whitespace-pre-wrap break-words max-h-[200px] overflow-y-auto">
                  {run.error_message}
                </pre>
              </CardContent>
            </Card>
          )}

          {/* node_stats table */}
          {nodeEntries.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Desempenho por no</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  {/* min-w forces SCROLLING instead of compression: the container already
                      has overflow-x, but without this `w-full` squeezes the six
                      columns until they all become ellipses. Only from `md`
                      up — below that the row becomes a stacked card (see
                      tabela-empilhada.ts). */}
                  <table className="w-full text-sm md:min-w-[680px]">
                    <thead className={COLUMN_HEADER}>
                      <tr className="text-xs text-muted-foreground border-b">
                        <th className="pb-2 pl-6 text-left font-medium">No</th>
                        <th className="pb-2 text-left font-medium">Status</th>
                        <th className="pb-2 text-right font-medium">Duracao</th>
                        <th className="pb-2 text-right font-medium">Cache</th>
                        <th className="pb-2 text-right font-medium">Features (entrada)</th>
                        <th className="pb-2 pr-6 text-right font-medium">Features (saida)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {nodeEntries.map(([nodeId, node]) => (
                        <tr key={nodeId} className={`border-b last:border-0 hover:bg-accent/30 ${STACKED_ROW}`}>
                          <td className={`py-2.5 pl-6 ${CARD_HIGHLIGHT}`}>
                            <div className="flex flex-col gap-1">
                              <span className="font-medium">{node.node_name}</span>
                              <div className="h-1 w-full max-w-[120px] bg-muted rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${node.status === "failed" ? "bg-red-400" : "bg-primary/60"}`}
                                  style={{ width: `${(node.duration_ms / maxMs) * 100}%` }}
                                />
                              </div>
                            </div>
                          </td>
                          <td className="py-2.5">
                            <StatusBadge status={node.status} />
                          </td>
                          <td data-rotulo="duração" className={`py-2.5 text-right font-mono text-xs ${LABELED_CELL}`}>
                            {formatDuration(node.duration_ms)}
                          </td>
                          <td data-rotulo="cache" className={`py-2.5 text-right ${LABELED_CELL}`}>
                            {node.cache_hit
                              ? <span className="text-purple-600 flex items-center justify-end gap-1"><TbBolt className="h-3 w-3" />Hit</span>
                              : <span className="text-muted-foreground">—</span>}
                          </td>
                          <td data-rotulo="entrada" className={`py-2.5 text-right text-muted-foreground ${LABELED_CELL}`}>
                            {node.input_features != null
                              ? <span className="flex items-center justify-end gap-1"><TbDatabase className="h-3 w-3" />{node.input_features.toLocaleString()}</span>
                              : "—"}
                          </td>
                          <td data-rotulo="saída" className={`py-2.5 pr-6 text-right text-muted-foreground ${LABELED_CELL}`}>
                            {node.output_features != null
                              ? <span className="flex items-center justify-end gap-1"><TbDatabase className="h-3 w-3" />{node.output_features.toLocaleString()}</span>
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </PageRoot>
  )
}
