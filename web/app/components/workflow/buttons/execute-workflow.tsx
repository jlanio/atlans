import { useCallback, useEffect, useRef, useState } from "react"
import { TbPlayerPlay, TbEraser, TbLoader, TbBug, TbPlayerStop, TbAlertTriangle } from "react-icons/tb"
import { GisFlowService } from "@/service/GisFlowService"
import { useWorkspace } from "@/context/WorkspaceContext"
import { avisoDePreFlight } from "@/app/components/workspace/politica"
import { createToast } from "@/utils/createToast"
import { dadoOuAviso } from "@/lib/respostas"
import { useExecuteWorkflow } from "../../../hooks/workflow/useExecuteWorkflow"
import { Button } from "@/app/components/ui/button"
import { Tooltip, TooltipTrigger, TooltipContent } from "@/app/components/ui/tooltip"
import ExecuteParamsDialog, { ParamSchema } from "../execute-params-dialog"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"

const ExecuteWorkflow = () => {

  const { executeWorkflow, isExecuting, debugMode, setDebugMode } = useExecuteWorkflow()
  const statusWorkflow = useWorkflowExecutionStore(s => s.statusWorkflow)
  const flagActive = useWorkflowSaveStore(s => s.flagActive)
  const [showParamsDialog, setShowParamsDialog] = useState(false)
  const [cancelling, setCancelling] = useState(false)

  const paramsSchema = statusWorkflow?.paramsSchema as Record<string, ParamSchema> | undefined

  // Preflight: the active workspace's policy says whether there's anywhere to
  // dispatch to. It only informs — the button never depends on the read, which
  // may fail or lag. Re-reads on mount and at the end of each execution: the
  // executor that went down during the run is precisely the case where the
  // warning matters most.
  const { current } = useWorkspace()
  const workspaceId = current?.id_hash ?? null
  const [preFlight, setPreFlight] = useState<string | null>(null)
  useEffect(() => {
    if (!workspaceId || isExecuting) return
    let cancelado = false
    GisFlowService.getWorkspacePolicy(workspaceId).then(res => {
      if (cancelado) return
      setPreFlight(res.error || !res.data ? null : avisoDePreFlight(res.data))
    })
    return () => { cancelado = true }
  }, [workspaceId, isExecuting])

  // Ref to executeWorkflow — the useCallback below needs to be stable so the
  // Cmd+Enter useEffect doesn't re-register the listener on every render of the
  // hook (executeWorkflow changes on every render). Without the ref, we had
  // either listener churn or a stale closure capturing the version from the
  // first render (when the canvas hadn't hydrated yet → nodes=[]).
  const executeWorkflowRef = useRef(executeWorkflow)
  useEffect(() => { executeWorkflowRef.current = executeWorkflow }, [executeWorkflow])

  const handleExecute = useCallback((inputs?: Record<string, unknown>) => {
    if (isExecuting || flagActive === false) return
    handleClearExecute()

    if (paramsSchema && Object.keys(paramsSchema).length > 0 && inputs === undefined) {
      setShowParamsDialog(true)
      return
    }
    executeWorkflowRef.current(inputs)
  }, [isExecuting, flagActive, paramsSchema])

  // The run's elapsed time lives only in the run panel's bar. Duplicating it
  // here gave two clocks with different bases — this one started from the moment
  // THIS mount saw `isExecuting`, so on reopening an in-progress run it restarted
  // from zero and contradicted the panel. The button's spinner already signals
  // activity.

  // Atalho de teclado: Cmd/Ctrl+Enter executa o workflow.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault()
        handleExecute()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [handleExecute])

  function handleParamsConfirm(inputs: Record<string, unknown>) {
    setShowParamsDialog(false)
    executeWorkflow(inputs)
  }

  async function handleCancel() {
    const runId = statusWorkflow?.task_id
    if (!runId || cancelling) return
    setCancelling(true)
    const pedido = dadoOuAviso(await GisFlowService.cancelRun(runId), "Não foi possível cancelar")
    setCancelling(false)
    if (!pedido) return
    if (pedido.outcome === "already_finished") {
      createToast.info("A execução já havia terminado")
      return
    }
    // Doesn't touch the store here: the final state arrives via WebSocket when the
    // executor confirms the interruption. Marking it as cancelled right away could
    // lie — the job may finish in the interval between the request and the stop.
    createToast.info("Cancelamento solicitado", "Aguardando o executor interromper o job…")
  }

  function handleClearExecute() {
    // Resets the execution state in the store: clears statusWorkflow,
    // losingNodeIds/Edges, and sets isExecuting back to false. Without this, the
    // nodes kept showing the check/error/cache_hit icons and the
    // colored ring even after clicking Clear.
    //
    // There used to be a `setEdges` here that reset `edge.style.stroke`. It was
    // a no-op all along: `CustomEdge` never read `style` — the color comes from
    // the source's status in the store. It only had a cost: changing the edges
    // array identity invalidated the lanes (edge-bundling) and adjacency
    // (workflowExecutionStore) WeakMaps without changing a pixel.
    useWorkflowExecutionStore.getState().resetExecution()
  }

  return (
    <>
      {paramsSchema && Object.keys(paramsSchema).length > 0 && (
        <ExecuteParamsDialog
          open={showParamsDialog}
          paramsSchema={paramsSchema}
          onConfirm={handleParamsConfirm}
          onCancel={() => setShowParamsDialog(false)}
        />
      )}

      <div className="flex items-center gap-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={() => setDebugMode(!debugMode)}
              variant="outline"
              size="icon"
              className={debugMode ? "border-yellow-500 text-yellow-500 hover:text-yellow-500" : undefined}
            >
              <TbBug size={18} />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">
            <p className="text-xs max-w-[200px]">
              {debugMode
                ? "Debug ativo — cada nó pausa e exibe dados intermediários antes de continuar"
                : "Ativar debug — pausa em cada nó para inspecionar dados"}
            </p>
          </TooltipContent>
        </Tooltip>

        <Button
          onClick={() => handleExecute()}
          size={"lg"}
          className="!px-4"
          disabled={isExecuting || flagActive === false}
          title={flagActive === false ? "Workflow desativado — ative-o na lista de projetos para executar" : undefined}
        >
          {isExecuting
            ? <TbLoader className="animate-spin" size={18} />
            : <TbPlayerPlay size={18} />
          }
          {flagActive === false ? "Desativado" : "Executar"}
        </Button>

        {/* Stop: only exists while there is a live run with a known task_id.
            Before there was no way to interrupt an expensive or stuck job — it
            only ended by itself or by the executor's timeout. */}
        {isExecuting && statusWorkflow?.task_id && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                onClick={handleCancel}
                disabled={cancelling}
                variant="outline"
                size="icon"
                className="border-destructive/50 text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                {cancelling ? <TbLoader className="animate-spin" size={18} /> : <TbPlayerStop size={18} />}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              <p className="max-w-[200px] text-xs">
                {cancelling ? "Cancelando…" : "Parar a execução em andamento"}
              </p>
            </TooltipContent>
          </Tooltip>
        )}

        {!isExecuting && statusWorkflow && statusWorkflow.status !== "idle" &&
          <Button onClick={handleClearExecute} variant="outline" size="icon">
            <TbEraser size={18} />
          </Button>
        }

        {/* Preflight warning: short on screen, spelled out in the tooltip and for the
            screen reader. It stays IN the row — below it, it pushed the bar
            docked at the bottom on every mount and every run. The button stays
            enabled: the server is who decides, and the read here may be
            stale. */}
        {preFlight && (
          <Tooltip>
            <TooltipTrigger asChild>
              <p
                role="status"
                className="flex h-10 cursor-default items-center gap-1 rounded-md border border-amber-500/40 bg-amber-500/10 px-2 text-xs font-medium text-amber-700 dark:text-amber-400"
              >
                <TbAlertTriangle size={14} className="shrink-0" aria-hidden="true" />
                <span aria-hidden="true">Sem executor</span>
                <span className="sr-only">{preFlight}</span>
              </p>
            </TooltipTrigger>
            <TooltipContent side="right">
              <p className="max-w-[260px] text-xs">{preFlight}</p>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    </>
  )
}

export default ExecuteWorkflow
