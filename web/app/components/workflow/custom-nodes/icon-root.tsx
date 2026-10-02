import { Tooltip, TooltipContent, TooltipTrigger } from "@/app/components/ui/tooltip"
import { useConfigNodeParams } from "@/app/hooks/workflow/useConfigNodeParams"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { useSubflowReadOnly, useSubflowStatus } from "../subflow-viewer/scope"
import { useCanvasReadOnly } from "../canvas-interaction"
import { dayjs } from "@/lib/dayjs"
import { cn } from "@/lib/utils"
import { ReactNode, useCallback, useEffect } from "react"
import { TbCheck, TbAlertCircle, TbHelpCircle, TbPinFilled, TbBolt } from "react-icons/tb"
import ExecActivity from "@/app/components/shared/exec-activity"

import { TYPE_STYLES, DEFAULT_STYLE } from "@/consts/NodeTypeStyles"

// ── Tipos ────────────────────────────────────────────────────────────────────
interface IconRootProps extends React.HTMLProps<HTMLDivElement> {
  id: string
  children: ReactNode
  className?: string
  /** Tipo do nó — define a cor de acento. Ex: "action", "trigger", "spatial" */
  nodeType?: string
  /** Título exibido dentro do card */
  title?: string
}

// Sem `memo` de propósito: `children` é um array JSX novo a cada render do pai,
// então a comparação rasa nunca segurava nada — o memo cobrava um custo e não
// entregava. O re-render em massa é resolvido na origem: os pais leem `selected`
// da prop do React Flow (em vez de assinar o array de nós inteiro) e o estado de
// execução é lido daqui por seletores POR ID, que só disparam para o nó que
// realmente mudou.
const IconRoot = ({ id, children, className, nodeType, title, onDoubleClick, ...props }: IconRootProps) => {

  const pinnedNodes = useWorkflowCatalogStore(s => s.pinnedNodes)
  const newlyAddedNodeId = useWorkflowCatalogStore(s => s.newlyAddedNodeId)
  const setNewlyAddedNodeId = useWorkflowCatalogStore(s => s.setNewlyAddedNodeId)
  // Seletores escalares/por-id: `updateNodeStatuses` preserva a identidade dos
  // nós NÃO alterados, então o Object.is do Zustand corta o render de todo nó
  // que não mudou. Assinar `statusWorkflow` (objeto novo a cada mensagem) fazia
  // os N cards re-renderizarem — e cada um reconstruía o próprio Map sobre a
  // lista inteira de nós.
  const statusCanvas = useWorkflowExecutionStore(s => s.statusById.get(id))
  const workflowStatus = useWorkflowExecutionStore(s => s.statusWorkflow?.status)
  const emRamoPerdedor = useWorkflowExecutionStore(s => !!s.losingNodeIds?.has(id))
  // Preenchidos só quando o nó está sendo desenhado dentro do visualizador de
  // sub-fluxo — ver subflow-viewer/scope.
  const noVisualizador = useSubflowReadOnly()
  const somenteLeitura = useCanvasReadOnly()
  const subflowStatus = useSubflowStatus()
  const isNew = id === newlyAddedNodeId

  // Limpa destaque após a animação terminar
  useEffect(() => {
    if (!isNew) return
    const timer = setTimeout(() => {
      setNewlyAddedNodeId(undefined)
    }, 2500)
    return () => clearTimeout(timer)
  }, [isNew, setNewlyAddedNodeId])

  // Dentro de um sub-fluxo o estado vem do escopo, que o derivou da linha do
  // tempo do run: `statusById` só conhece os nós do canvas do editor, porque é
  // semeado a partir deles e depois atualizado por id — e os ids dos nós do
  // filho chegam prefixados, sem casar com nenhum.
  const statusNode = subflowStatus ? subflowStatus.get(id) : statusCanvas
  const isPinned = pinnedNodes?.some(p => p.node_id === id && !p.expired)
  const { configNodeIdParam, removeConfigNodeParam, setConfigNodeParam } = useConfigNodeParams()

  // "Pendente" é todo nó que ainda não começou enquanto o run está de pé — e
  // não só a janela de `queued`, que dura o intervalo entre o POST e o task_id
  // chegar: `setTaskId` promove o workflow a "running" assim que ele responde.
  // Restrito a `queued`, o tratamento era tecnicamente correto e praticamente
  // invisível; marcar o resto do run é o que torna legível "o que ainda falta"
  // num grafo grande.
  const runDePe = workflowStatus === "queued" || workflowStatus === "running"
  const isPending = runDePe && (statusNode?.status ?? "idle") === "idle"

  const abrirConfiguracao = useCallback((e: React.MouseEvent<HTMLDivElement, MouseEvent>) => {
    // No visualizador de sub-fluxo o duplo clique pertence à navegação (descer
    // um nível), e o nó nem é editável dali. Abrir a configuração aqui apontaria
    // o modal para um id que não existe no canvas do editor.
    if (noVisualizador) return
    if (configNodeIdParam === id)
      return removeConfigNodeParam()
    if (onDoubleClick)
      onDoubleClick(e)
    setConfigNodeParam(id)
  }, [configNodeIdParam, id, removeConfigNodeParam, onDoubleClick, setConfigNodeParam, noVisualizador])

  // No telefone o gesto é TOQUE SIMPLES. O duplo toque existe no navegador, mas
  // disputa com o zoom do canvas e é lento por natureza (o navegador espera o
  // segundo toque antes de decidir). E ali é o único caminho que sobra: a barra
  // de ferramentas do nó, que no desktop também abre a configuração, depende de
  // hover e não aparece. O React Flow separa toque de arraste, então dar pan
  // com o dedo sobre um nó não abre o modal.
  const gestoDeAbrir = somenteLeitura
    ? { onClick: abrirConfiguracao }
    : { onDoubleClick: abrirConfiguracao }

  const style = TYPE_STYLES[nodeType ?? ""] ?? DEFAULT_STYLE

  // `losingNodeIds` é calculado sobre as arestas do canvas do editor e não
  // conhece o grafo do filho. Aplicá-lo dentro do visualizador dessaturaria um
  // nó do sub-fluxo só porque o id local dele coincide com o de um ramo
  // perdedor do pai — ramos perdedores lá dentro ficam sem marcação.
  const isLosing = !noVisualizador && emRamoPerdedor

  return (
    <div
      {...props}
      {...gestoDeAbrir}
      data-status={statusNode?.status}
      data-losing={isLosing ? "true" : "false"}
      data-pending={isPending ? "true" : "false"}
      data-new={isNew ? "true" : "false"}
      className={cn(
        // Card base. `exec-card` é o escopo das camadas de execução, que vivem
        // em globals.css — ver o bloco "Estados de execução no canvas".
        "exec-card group relative isolate flex items-stretch bg-card border border-border rounded-lg shadow-sm",
        "w-[158px] h-[60px]",
        // Só SELEÇÃO mora aqui. IMPORTANTE: sem `ring-offset-*` — o offset do
        // Tailwind preenche o gap entre card e ring com `--tw-ring-offset-color`
        // (default = background), o que aparece como uma linha fina "descolada".
        //
        // O anel de ESTADO saiu daqui de propósito: `ring-*`, `shadow-sm` e os
        // keyframes de brilho disputavam a mesma propriedade `box-shadow`, e um
        // keyframe substitui a declaração inteira — o pulso apagava o anel de
        // seleção e a sombra do card enquanto rodava. Agora um nó selecionado E
        // em execução mostra os dois anéis.
        "data-[selected=true]:ring-2 data-[selected=true]:ring-muted-foreground/50",
        className,
      )}
    >

      {/* Stripe colorida à esquerda */}
      <div className={cn("w-1 shrink-0 rounded-tl-lg rounded-bl-lg", style.stripe)} />

      {/* Seção do ícone */}
      <div className={cn("flex items-center justify-center w-12 shrink-0", style.bg)}>
        <div className={cn("text-xl flex items-center justify-center", style.icon)}>
          {children}
        </div>
      </div>

      {/* Seção de texto — `data-role` são ganchos do LOD por zoom (globals.css):
          com o canvas afastado o subtítulo some e o título cresce. */}
      <div className="flex flex-col justify-center px-2.5 flex-1 min-w-0">
        <p data-role="node-title" className="text-sm font-medium text-foreground truncate leading-tight">
          {title ?? ""}
        </p>
        <p data-role="node-type-label" className={cn("text-[9px] uppercase tracking-widest leading-tight mt-0.5 font-medium", style.label)}>
          {nodeType ?? ""}
        </p>
      </div>

      {/* ── Indicador de pin (canto superior direito) ─────────────────────── */}
      {/* key={`pin-${id}`} faz o ícone remontar quando o node muda, mas a
          animação forwards só é disparada no ponto em que isPinned vira
          true (primeira render do TooltipTrigger). Dá feedback tátil
          ao pinar sem rodar em loop. */}
      {isPinned && (
        <Tooltip>
          <TooltipTrigger data-role="node-badge" className="absolute top-1 right-1.5">
            <TbPinFilled size={12} className="text-amber-500 pin-hit-pulse" />
          </TooltipTrigger>
          <TooltipContent side="top" className="opacity-80">
            <p>Output fixado (pin)</p>
          </TooltipContent>
        </Tooltip>
      )}

      {/* ── Indicadores de status (canto inferior direito) ───────────────── */}
      {statusNode?.status === "started" && (
        <Tooltip>
          {/* A cor fica no gatilho porque `ExecActivity` pinta com
              `currentColor` — é o que deixa o glifo seguir o token do estado
              sem precisar recebê-lo por prop. */}
          <TooltipTrigger data-role="node-badge" className="absolute bottom-1 right-1.5 text-exec-running">
            <ExecActivity size={14} />
          </TooltipTrigger>
          <TooltipContent side="bottom" className="opacity-80">
            <p>Em execução</p>
          </TooltipContent>
        </Tooltip>
      )}

      {statusNode?.status === "completed" && (
        <Tooltip>
          <TooltipTrigger data-role="node-badge" className="absolute bottom-1 right-1.5">
            {statusNode.cache_hit
              ? <TbBolt size={13} className="text-exec-cache cache-hit-pulse" />
              : <TbCheck size={13} className="text-exec-success" />}
          </TooltipTrigger>
          <TooltipContent side="bottom" className="opacity-80">
            <p>
              {statusNode.cache_hit
                ? "Resultado do cache (pin data)"
                : `Executado em ${dayjs.duration(Math.round(statusNode.duration ?? 0)).format("mm[min ]ss[s ] SSS[ms ]")}`}
            </p>
          </TooltipContent>
        </Tooltip>
      )}

      {statusNode?.status === "failed" && (
        <Tooltip>
          <TooltipTrigger data-role="node-badge" className="absolute bottom-1 right-1.5">
            <TbAlertCircle size={15} className="text-exec-error" />
          </TooltipTrigger>
          <TooltipContent side="bottom" className="opacity-80">
            <p>{statusNode.error}</p>
          </TooltipContent>
        </Tooltip>
      )}

      {statusNode?.status === "unknown" && (
        <Tooltip>
          <TooltipTrigger data-role="node-badge" className="absolute bottom-1 right-1.5">
            <TbHelpCircle size={15} className="text-exec-unknown" />
          </TooltipTrigger>
          <TooltipContent side="bottom" className="opacity-80">
            <p>
              Resultado não recebido. O nó começou e a execução terminou, mas o
              aviso de término dele não chegou — veja a observabilidade para o
              desfecho real.
            </p>
          </TooltipContent>
        </Tooltip>
      )}

    </div>
  )
}

export default IconRoot
