"use client"
import { useCallback, useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { TbHistory, TbLoader2, TbRefresh } from "react-icons/tb"
import { GisFlowService, IRunSummary } from "@/service/GisFlowService"
import { useWorkflowExecutionStore, toRunEvent } from "@/app/stores/workflowExecutionStore"
import { createToast } from "@/utils/createToast"
import { StatusBadge } from "@/app/components/shared/StatusBadge"
import { fromNowLocal } from "@/lib/dayjs"
import { dadoOuAviso } from "@/lib/respostas"
import { cn } from "@/lib/utils"

/**
 * A useful empty state: instead of "Nenhum log" (no logs), it lists the recent
 * runs and loads the events of one of them.
 *
 * Before, a finished run left the panel permanently empty — the store is
 * volatile and the observability page only keeps node_stats, without the events.
 * The /observability/runs/{id}/events endpoint exposes the same history that the
 * WebSocket replays on connect.
 */
const HistoryEmpty = () => {
  const { id } = useParams<{ id: string }>()
  const [runs, setRuns] = useState<IRunSummary[]>([])
  const [loading, setLoading] = useState(false)
  // The list did not arrive: the "no runs" slot says so, not the empty state.
  const [falhou, setFalhou] = useState(false)
  const [loadingRunId, setLoadingRunId] = useState<string | null>(null)
  const loadHistoricalEvents = useWorkflowExecutionStore(s => s.loadHistoricalEvents)

  const fetchRuns = useCallback(async () => {
    if (!id) return
    setLoading(true)
    const res = await GisFlowService.getObservabilityRuns({ workflow_id: id, limit: 5 })
    const dados = dadoOuAviso(res, "Erro ao carregar execuções recentes")
    setRuns(dados?.runs ?? [])
    setFalhou(dados === null)
    setLoading(false)
  }, [id])

  useEffect(() => { fetchRuns() }, [fetchRuns])

  async function openRun(runId: string) {
    setLoadingRunId(runId)
    try {
      const dados = dadoOuAviso(await GisFlowService.getRunEvents(runId), "Erro ao carregar o log da execução")
      // No response means no verdict about the history: "expirou" (expired) is only
      // for a log that ARRIVED empty.
      if (!dados) return
      const events = (dados.events ?? []).map(toRunEvent)
      if (events.length === 0) {
        createToast.info("Log indisponível", "O histórico desta execução expirou (mantido por 1 hora).")
        return
      }
      loadHistoricalEvents(runId, events)
    } finally {
      setLoadingRunId(null)
    }
  }

  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-6">
      <p className="text-xs text-muted-foreground/70">
        Nenhuma execução carregada. Execute o workflow ou abra um log recente.
      </p>

      <div className="w-full max-w-md rounded-md border border-border">
        <div className="flex items-center gap-2 border-b bg-muted/40 px-3 py-1.5 text-[11px] text-muted-foreground">
          <TbHistory size={12} />
          <span>Execuções recentes</span>
          <button onClick={fetchRuns} className="ml-auto transition-colors hover:text-foreground" title="Atualizar">
            <TbRefresh size={12} className={cn(loading && "animate-spin")} />
          </button>
        </div>

        {runs.length === 0 ? (
          <p className="p-3 text-center text-[11px] text-muted-foreground/60">
            {loading
              ? "Carregando…"
              : falhou ? "Não foi possível carregar as execuções." : "Nenhuma execução registrada."}
          </p>
        ) : (
          runs.map(run => (
            <button
              key={run.run_id}
              onClick={() => openRun(run.run_id)}
              disabled={loadingRunId != null}
              className="flex w-full items-center gap-2 border-b px-3 py-1.5 text-left text-[11px] transition-colors last:border-0 hover:bg-accent disabled:opacity-50"
            >
              <StatusBadge status={run.status} />
              <span className="text-muted-foreground">{fromNowLocal(run.started_at)}</span>
              <span className="flex-1" />
              {run.duration_seconds != null && (
                <span className="font-mono tabular-nums text-muted-foreground/70">
                  {run.duration_seconds.toFixed(2)}s
                </span>
              )}
              {loadingRunId === run.run_id && <TbLoader2 size={12} className="animate-spin" />}
            </button>
          ))
        )}
      </div>
    </div>
  )
}

export default HistoryEmpty
