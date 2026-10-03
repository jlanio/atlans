"use client"
import { useEffect, useMemo } from "react"
import {
  Background, BackgroundVariant, Edge, ReactFlow, ReactFlowProvider, useReactFlow,
} from "@xyflow/react"
import {
  TbAlertTriangle, TbChevronRight, TbHome, TbLoader2, TbRefresh, TbSubtask, TbX,
} from "react-icons/tb"
import { cn } from "@/lib/utils"
import { INodeContext } from "@/context/useFlowContext"
import { useTheme } from "@/context/ThemeContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { useRunDockHeight } from "@/app/stores/runPanelStore"
import { SubflowLevel, useSubflowDrilldownStore } from "@/app/stores/subflowDrilldownStore"
import { nodeTypesFlow, customEdges } from "../canvas-types"
import { buildEdges, buildNodes } from "../utils/build-canvas"
import { useRunSnapshot } from "../run-panel/use-run-snapshot"
import { recortarNivel } from "./estado-do-nivel"
import { SubflowScope } from "./scope"
import { useSubflowDefinition } from "./use-subflow-definition"

interface Props {
  /** Name of the workflow open in the editor — first step of the breadcrumb. */
  rootLabel: string
}

/**
 * Viewer of what happened INSIDE a sub-workflow, in a run.
 *
 * Overlays the editor instead of navigating to the child workflow: the run lives
 * in this canvas session's store, so leaving the page would discard it — and
 * would also run into the parent's unsaved edits. By overlaying, the run panel
 * stays visible below and the breadcrumb provides the way back.
 */
export default function SubflowViewer({ rootLabel }: Props) {
  const path = useSubflowDrilldownStore(s => s.path)
  if (path.length === 0) return null
  return (
    <ReactFlowProvider>
      <Conteudo path={path} rootLabel={rootLabel} />
    </ReactFlowProvider>
  )
}

function Conteudo({ path, rootLabel }: Props & { path: SubflowLevel[] }) {
  const { theme } = useTheme()
  const dockHeight = useRunDockHeight()
  const nodesAPI = useWorkflowCatalogStore(s => s.nodesAPI)
  const isHistorical = useWorkflowExecutionStore(s => s.isHistorical)
  const popTo = useSubflowDrilldownStore(s => s.popTo)
  const push = useSubflowDrilldownStore(s => s.push)
  const close = useSubflowDrilldownStore(s => s.close)
  const focusNodeId = useSubflowDrilldownStore(s => s.focusNodeId)
  const { timeline } = useRunSnapshot()
  const { fitView } = useReactFlow()

  const nivel = path[path.length - 1]
  const { workflow, carregando, erro, recarregar } = useSubflowDefinition(nivel.workflowHash)

  const nodes = useMemo<INodeContext[]>(
    () => buildNodes(workflow?.definition, nodesAPI),
    [workflow?.definition, nodesAPI],
  )
  const edges = useMemo<Edge[]>(
    () => buildEdges(workflow?.definition, nodes),
    [workflow?.definition, nodes],
  )

  // This level's address in the events: the ids of the SubWorkflow nodes traversed.
  const caminho = useMemo(() => path.map(n => n.canvasNodeId), [path])

  // Until the graph arrives there is nothing to compare against, and comparing
  // anyway would flag ALL executed nodes as "no longer in the graph" — a false
  // alarm on every opening, from the very warning that exists to keep the
  // screen from passing for complete.
  const grafoPronto = !!workflow
  const { estadoPorId, semCorrespondencia } = useMemo(() => {
    if (!grafoPronto) return { estadoPorId: new Map(), semCorrespondencia: [] }
    const idsDoGrafo = new Set(nodes.map(n => n.id))
    return recortarNivel(timeline.nodes, caminho, idsDoGrafo)
  }, [timeline.nodes, caminho, nodes, grafoPronto])

  // Esc closes the whole descent — the expected gesture for leaving an overlay.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") close()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [close])

  // Centers the node that started the descent (e.g. the one that failed). Frames
  // the whole graph when there is no target — landing on an out-of-view canvas
  // would be worse than framing nothing.
  //
  // The dependencies are the control: `nodes` only changes when the drawn graph
  // changes, i.e. on each level change — going down AND back via the breadcrumb,
  // which reuses the same React Flow instance and would inherit the previous
  // level's zoom. Panel updates, which in a live run arrive eight times per
  // second, do not go through here: `nodes` is memoized on the definition.
  useEffect(() => {
    if (nodes.length === 0) return
    const alvo = focusNodeId && nodes.some(n => n.id === focusNodeId) ? focusNodeId : null
    const frame = requestAnimationFrame(() => {
      if (alvo) fitView({ nodes: [{ id: alvo }], duration: 400, maxZoom: 1.3, padding: 0.6 })
      else fitView({ padding: 0.15 })
    })
    return () => cancelAnimationFrame(frame)
  }, [nodes, focusNodeId, fitView])

  function descer(node: INodeContext) {
    if (node.data?.name !== "SubWorkflow") return
    const hash = String(node.data?.properties?.workflowHash ?? "").trim()
    if (!hash) return
    push({
      canvasNodeId: node.id,
      workflowHash: hash,
      label: (node.data?.properties?.alias as string) || (node.data?.alias as string) || "Sub-fluxo",
    })
  }

  return (
    <div
      className="absolute inset-x-0 top-0 z-30 flex flex-col border-b border-border bg-background/95 backdrop-blur"
      style={{ bottom: dockHeight }}
    >
      {/* ── Trilha ────────────────────────────────────────────────────────── */}
      <div className="flex shrink-0 items-center gap-1 border-b border-border bg-muted/30 px-3 py-1.5 text-xs">
        <TbSubtask size={14} className="shrink-0 text-indigo-500" />
        <button
          onClick={() => popTo(-1)}
          className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          title="Voltar ao fluxo aberto no editor"
        >
          <TbHome size={12} /> {rootLabel || "Fluxo atual"}
        </button>
        {path.map((degrau, i) => (
          <span key={`${degrau.canvasNodeId}-${i}`} className="flex min-w-0 items-center">
            <TbChevronRight size={12} className="shrink-0 text-muted-foreground/40" />
            <button
              onClick={() => popTo(i)}
              className={cn(
                "truncate rounded px-1.5 py-0.5 transition-colors hover:bg-accent",
                i === path.length - 1 ? "font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {degrau.label}
            </button>
          </span>
        ))}

        {workflow && (
          <span className="ml-1 shrink-0 truncate text-[10px] text-muted-foreground/60">
            {workflow.name}
          </span>
        )}

        <span className="flex-1" />

        {carregando && <TbLoader2 size={13} className="animate-spin text-muted-foreground" />}
        <button
          onClick={recarregar}
          title="Recarregar o sub-fluxo"
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <TbRefresh size={13} />
        </button>
        <button
          onClick={close}
          title="Fechar (Esc)"
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <TbX size={13} />
        </button>
      </div>

      {/* ── Ressalvas ─────────────────────────────────────────────────────── */}
      {(isHistorical || semCorrespondencia.length > 0) && (
        <div className="flex shrink-0 flex-col gap-0.5 border-b border-amber-500/20 bg-amber-500/5 px-3 py-1 text-[11px] text-amber-700 dark:text-amber-300">
          {isHistorical && (
            <span className="flex items-start gap-1.5">
              <TbAlertTriangle size={12} className="mt-0.5 shrink-0" />
              O grafo é a versão atual do sub-fluxo; a execução pode ter usado outra.
            </span>
          )}
          {semCorrespondencia.length > 0 && (
            <span className="flex items-start gap-1.5">
              <TbAlertTriangle size={12} className="mt-0.5 shrink-0" />
              {semCorrespondencia.length} nó(s) executaram aqui e não existem mais no
              grafo: {semCorrespondencia.slice(0, 5).join(", ")}
              {semCorrespondencia.length > 5 && ` e mais ${semCorrespondencia.length - 5}`}.
            </span>
          )}
        </div>
      )}

      {/* ── Sub-workflow canvas ───────────────────────────────────────────── */}
      <div className="relative min-h-0 flex-1">
        {erro ? (
          <p className="p-6 text-center text-xs text-destructive">{erro}</p>
        ) : !grafoPronto ? (
          <p className="p-6 text-center text-xs text-muted-foreground/60">
            Carregando o sub-fluxo…
          </p>
        ) : nodes.length === 0 ? (
          <p className="p-6 text-center text-xs text-muted-foreground/60">
            Sub-fluxo sem nós para desenhar.
          </p>
        ) : (
          <SubflowScope estadoPorId={estadoPorId}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              colorMode={theme}
              nodeTypes={nodeTypesFlow}
              edgeTypes={customEdges}
              onNodeDoubleClick={(_, node) => descer(node as INodeContext)}
              nodesDraggable={false}
              nodesConnectable={false}
              edgesFocusable={false}
              deleteKeyCode={null}
              onlyRenderVisibleElements
            >
              <Background
                variant={theme === "dark" ? BackgroundVariant.Cross : BackgroundVariant.Dots}
                gap={12}
                size={1}
              />
            </ReactFlow>
          </SubflowScope>
        )}

        <p className="pointer-events-none absolute bottom-2 left-1/2 -translate-x-1/2 rounded bg-background/80 px-2 py-0.5 text-[10px] text-muted-foreground/60">
          somente leitura · duplo clique num nó Sub-Workflow para descer mais um nível
        </p>
      </div>
    </div>
  )
}
