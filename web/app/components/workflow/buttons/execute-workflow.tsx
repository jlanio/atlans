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

  // Pré-voo: a política do workspace ativo diz se há para onde despachar. Só
  // informa — o botão nunca depende da leitura, que pode falhar ou atrasar.
  // Relê ao montar e ao fim de cada execução: o executor que caiu durante o
  // run é justamente o caso em que o aviso mais importa.
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

  // Ref para executeWorkflow — o useCallback abaixo precisa ser estável para
  // o useEffect do Cmd+Enter não re-registrar o listener a cada render do
  // hook (executeWorkflow muda a cada render). Sem a ref, ou tínhamos
  // listener churn ou closure stale que capturava a versão da primeira
  // render (quando o canvas ainda não tinha hidratado → nodes=[]).
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

  // O tempo decorrido do run vive só na barra do painel de execução. Duplicá-lo
  // aqui dava dois relógios com bases diferentes — este partia do momento em que
  // ESTE mount via `isExecuting`, então ao reabrir um run em andamento reiniciava
  // do zero e contradizia o painel. O spinner do botão já sinaliza atividade.

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
    // Não mexe na store aqui: o estado final chega pelo WebSocket quando o
    // executor confirma a interrupção. Marcar como cancelado já poderia
    // mentir — o job pode concluir no intervalo entre o pedido e a parada.
    createToast.info("Cancelamento solicitado", "Aguardando o executor interromper o job…")
  }

  function handleClearExecute() {
    // Reseta o estado de execução na store: limpa statusWorkflow,
    // losingNodeIds/Edges, e volta isExecuting para false. Sem isso, os
    // nodes continuavam mostrando os ícones de check/erro/cache_hit e o
    // ring colorido mesmo após o clique em Clear.
    //
    // Antes havia aqui um `setEdges` que zerava `edge.style.stroke`. Era
    // no-op desde sempre: `CustomEdge` nunca leu `style` — a cor vem do
    // status da origem na store. Só custava: trocar a identidade do array de
    // arestas invalidava os WeakMap de lanes (edge-bundling) e de adjacência
    // (workflowExecutionStore) sem mudar um pixel.
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

        {/* Parar: só existe enquanto há um run vivo com task_id conhecido.
            Antes não havia como interromper um job caro ou travado — ele só
            terminava sozinho ou pelo timeout do executor. */}
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

        {/* Aviso de pré-voo: curto na tela, por extenso no tooltip e para o
            leitor de tela. Fica NA fileira — abaixo dela, empurrava a barra
            ancorada no rodapé a cada montagem e a cada run. O botão continua
            habilitado: o servidor é quem decide, e a leitura daqui pode estar
            defasada. */}
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
