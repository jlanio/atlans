"use client"
import { useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import { GisFlowService, IRunSummary } from "@/service/GisFlowService"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import { StatusBadge } from "@/app/components/shared/StatusBadge"
import { createToast } from "@/utils/createToast"
import { TbActivity, TbPlayerPlay, TbExternalLink, TbRefresh, TbInbox } from "react-icons/tb"
import "dayjs/locale/pt-br"
import { dayjs, fromNowLocal } from "@/lib/dayjs"
import { dadoOuAviso } from "@/lib/respostas"
import { useWorkspace } from "@/context/WorkspaceContext"

dayjs.locale("pt-br")

const _stagger = { hidden: {}, show: { transition: { staggerChildren: 0.04 } } }
const _fadeUp  = { hidden: { opacity: 0, y: 6 }, show: { opacity: 1, y: 0, transition: { duration: 0.2 } } }

const RecentRuns = () => {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { canExecute } = useWorkspace()
  const [open, setOpen]       = useState(false)
  const [runs, setRuns]       = useState<IRunSummary[]>([])
  const [loading, setLoading] = useState(false)
  // A lista não chegou: o lugar do "nenhuma execução" diz isso, e não o vazio.
  const [falhou, setFalhou] = useState(false)
  const [runningId, setRunningId] = useState<string | null>(null)

  const fetchRuns = useCallback(async () => {
    if (!id) return
    setLoading(true)
    const dados = dadoOuAviso(await GisFlowService.getWorkflowMetrics(id, 5), "Erro ao carregar execuções recentes")
    if (dados?.last_runs) setRuns(dados.last_runs)
    setFalhou(dados === null)
    setLoading(false)
  }, [id])

  function handleToggle() {
    const next = !open
    setOpen(next)
    if (next && runs.length === 0) fetchRuns()
  }

  async function handleRerun(run: IRunSummary) {
    setRunningId(run.run_id)
    const disparo = dadoOuAviso(await GisFlowService.executeWorkflow(id, {}, false), "Erro ao re-executar workflow")
    setRunningId(null)
    if (!disparo) return
    createToast.success("Workflow re-executado!")
    setOpen(false)
  }

  if (!id) return null

  return (
    <div className="relative z-20">
      <Button
        variant="outline"
        size="icon"
        onClick={handleToggle}
        title="Execuções recentes"
        className={open ? "border-primary text-primary" : ""}
      >
        <TbActivity size={18} />
      </Button>

      {open && (
        <>
          {/* Overlay para fechar ao clicar fora */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />

          <div className="absolute left-full ml-2 bottom-0 z-20 w-80 bg-background border border-border rounded-lg shadow-lg overflow-hidden">
            {/* Cabeçalho */}
            <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/40">
              <span className="text-xs font-medium text-muted-foreground">Execuções recentes</span>
              <button
                onClick={fetchRuns}
                disabled={loading}
                className="text-muted-foreground hover:text-foreground transition-colors"
                title="Atualizar"
              >
                <TbRefresh size={13} className={loading ? "animate-spin" : ""} />
              </button>
            </div>

            {/* Lista */}
            <div className="flex flex-col">
              {loading && runs.length === 0 && (
                <div className="flex flex-col divide-y divide-border">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="flex items-center gap-2 px-3 py-2.5">
                      <Skeleton className="h-4 w-12 rounded-full" />
                      <div className="flex-1 flex flex-col gap-1.5">
                        <Skeleton className="h-3 w-24" />
                        <Skeleton className="h-2.5 w-16" />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {!loading && runs.length === 0 && (
                <div className="flex flex-col items-center justify-center py-8 px-4 gap-3 text-center">
                  <div className="rounded-full bg-muted/60 p-3">
                    <TbInbox size={20} className="text-muted-foreground/50" />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {falhou ? "Não foi possível carregar as execuções." : "Nenhuma execução registrada ainda."}
                  </p>
                </div>
              )}

              {runs.length > 0 && (
                <motion.div
                  className="flex flex-col divide-y divide-border"
                  variants={_stagger}
                  initial="hidden"
                  animate="show"
                >
                  <AnimatePresence>
                    {runs.map(run => (
                      // Sem `layout`: a projeção medida por render (layout thrash)
                      // não é necessária — entrada/saída seguem por variants.
                      <motion.div
                        key={run.run_id}
                        variants={_fadeUp}
                        className="flex items-center gap-2 px-3 py-2 hover:bg-accent/30 transition-colors"
                      >
                        <StatusBadge status={run.status} />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-muted-foreground truncate font-mono">{run.run_id.slice(0, 8)}…</p>
                          <p className="text-[10px] text-muted-foreground/60">
                            {fromNowLocal(run.started_at)}
                            {run.duration_seconds != null && (
                              <span className="ml-1">· {run.duration_seconds.toFixed(1)}s</span>
                            )}
                          </p>
                        </div>
                        {canExecute && (
                          <button
                            onClick={() => handleRerun(run)}
                            disabled={runningId === run.run_id}
                            title="Re-executar"
                            className="shrink-0 flex items-center justify-center h-6 w-6 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                          >
                            <TbPlayerPlay size={12} className={runningId === run.run_id ? "animate-pulse" : ""} />
                          </button>
                        )}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </motion.div>
              )}
            </div>

            {/* Rodapé */}
            <div className="border-t px-3 py-2 bg-muted/20">
              <button
                onClick={() => { router.push(`/observability/${id}`); setOpen(false) }}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors w-full"
              >
                <TbExternalLink size={12} />
                Ver todas no Histórico
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default RecentRuns
