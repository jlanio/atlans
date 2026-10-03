"use client"
import { useEffect, useState } from "react"
import { useReactFlow } from "@xyflow/react"
import {
  TbCircleCheck, TbCircleX, TbCircleDashed, TbAlertTriangle, TbHelpCircle,
} from "react-icons/tb"
import ExecActivity from "@/app/components/shared/exec-activity"
import { cn } from "@/lib/utils"
import { NodeRun, NodeRunStatus } from "./timeline"
import { useRunPanelStore } from "@/app/stores/runPanelStore"
import { SubflowLevel, useSubflowDrilldownStore } from "@/app/stores/subflowDrilldownStore"
import { caminhoDeChamada, idLocal } from "../utils/subflow-path"

/** PT-BR labels for the categories of the backend's error taxonomy.
 *
 * The backend publishes the stable category (string); the translation lives here
 * so the panel can say "retrying won't help, fix the input" instead of just
 * dumping the stack trace.
 */
export const ERROR_CATEGORY_LABEL: Record<string, string> = {
  user:       "Entrada ou configuração inválida",
  validation: "Reprovado na validação de segurança",
  timeout:    "Tempo limite excedido",
  resource:   "Recursos insuficientes (memória)",
  transient:  "Falha temporária de infraestrutura",
  internal:   "Erro interno inesperado",
}

const MINUTE_MS = 60_000

/** Above one minute, `m:ss` — "2m07s" reads at a glance; "127.40s" does not. */
function longForm(ms: number): string {
  const minutes = Math.floor(ms / MINUTE_MS)
  const seconds = Math.floor((ms % MINUTE_MS) / 1000)
  return `${minutes}m${String(seconds).padStart(2, "0")}s`
}

export function formatOffset(ms: number | null): string {
  if (ms == null) return "—"
  if (ms < 1000) return `+${Math.round(ms)}ms`
  if (ms >= MINUTE_MS) return `+${longForm(ms)}`
  return `+${(ms / 1000).toFixed(2)}s`
}

export function formatMs(ms?: number | null): string {
  if (ms == null) return "—"
  if (ms < 1000) return `${Math.round(ms)}ms`
  if (ms >= MINUTE_MS) return longForm(ms)
  return `${(ms / 1000).toFixed(2)}s`
}

// The panel and the node card talk about the SAME state, a few centimeters
// apart, so they use the same glyph and the same color. `running` showed a
// spinning spinner while the card showed the activity bars, and the colors
// came from fixed Tailwind classes instead of the `--exec-*` tokens — which,
// unlike those, follow the theme.
export function NodeStatusIcon({ status, size = 13 }: { status: NodeRunStatus; size?: number }) {
  if (status === "completed") return <TbCircleCheck size={size} className="text-exec-success shrink-0" />
  if (status === "failed")    return <TbCircleX size={size} className="text-exec-error shrink-0" />
  if (status === "running")   return <ExecActivity size={size} className="text-exec-running shrink-0" />
  // `unknown` must NOT fall into the "waiting" icon: the node started, the run
  // ended, and what is missing is the news of completion — not the work.
  if (status === "unknown")   return <TbHelpCircle size={size} className="text-exec-unknown shrink-0" />
  return <TbCircleDashed size={size} className="text-muted-foreground/40 shrink-0" />
}

export function DriftBadge({ drift }: { drift: { missing: string[]; extra: string[] } }) {
  const parts = [
    drift.missing.length > 0 ? `faltando ${drift.missing.join(", ")}` : null,
    drift.extra.length > 0 ? `extra ${drift.extra.join(", ")}` : null,
  ].filter(Boolean).join(" · ")
  return (
    <span
      title={`Schema declarado difere da saída real: ${parts}`}
      className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-1.5 py-px text-[10px] text-amber-600 dark:text-amber-400"
    >
      <TbAlertTriangle size={10} /> schema
    </span>
  )
}

/** Self-contained stopwatch — only mounts while something is actually running.
 *
 * The old panel derived `startedAt` from `Date.now()` inside a `useMemo`
 * that depended on the nodes array, and that array changes on every WebSocket
 * message: the counter reset to zero on every event from any node.
 */
export function Elapsed({ since }: { since: number }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(id)
  }, [])
  const ms = Math.max(0, now - since)
  const text = ms >= MINUTE_MS
    ? longForm(ms)
    : ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
  return <span className="tabular-nums">{text}</span>
}

/** A panel row that knows which CANVAS node it corresponds to.
 *
 * Only `canvasNodeId` — never `nodeId`. For a node inside a sub-workflow the two
 * differ: the child's id does not exist on the parent's canvas, and using it here
 * was a silent no-op (no focus, no highlight, no configuration). Asking for the
 * whole row instead of a string takes the choice away from the caller — passing
 * the wrong id no longer compiles.
 */
export interface AlvoNoCanvas {
  canvasNodeId: string
}

/** Panel → canvas correlation actions. */
export function useNodeFocus() {
  const reactFlow = useReactFlow()
  const guardarHover = useRunPanelStore(s => s.setHovered)

  function setHovered(alvo: AlvoNoCanvas | null) {
    guardarHover(alvo?.canvasNodeId ?? null)
  }

  /** Selects and centers the node on the canvas — possible because the panel is
   *  no longer modal: before, the Sheet's overlay covered and disabled the canvas. */
  function focusNode(alvo: AlvoNoCanvas) {
    const nodeId = alvo.canvasNodeId
    const exists = reactFlow.getNodes().some(n => n.id === nodeId)
    if (!exists) return
    // Only reallocates the nodes whose selection CHANGED. Recreating the whole
    // array made the entire graph re-render on every click on a panel row.
    reactFlow.setNodes(nodes => nodes.map(n => {
      const selected = n.id === nodeId
      return n.selected === selected ? n : { ...n, selected }
    }))
    reactFlow.fitView({ nodes: [{ id: nodeId }], duration: 400, maxZoom: 1.3, padding: 0.6 })
  }

  return { focusNode, setHovered }
}

/**
 * Panel → sub-workflow canvas: opens the child's graph at the node this row
 * represents.
 *
 * Complements `focusNode`, which for a row from inside a sub-workflow can only
 * center the parent's SubWorkflow node — the only id of that row that exists on
 * the editor canvas. Here the destination is the actual node.
 *
 * The path comes from the row's `nodeId`, which is the full address (`sA::sB::X`);
 * each step's `workflowHash` comes from the SubWorkflow nodes traversed. Only the
 * first step is on the editor canvas: the following ones live inside workflows
 * not yet loaded, and the viewer resolves them on the way down.
 */
export function useAbrirSubfluxo() {
  const reactFlow = useReactFlow()
  const open = useSubflowDrilldownStore(s => s.open)

  /** Did the row come from inside a sub-workflow AND can the path be built? */
  function podeAbrir(node: NodeRun): boolean {
    return caminhoDeChamada(node.nodeId).length > 0 && !!hashDoNoNoCanvas(node)
  }

  function hashDoNoNoCanvas(node: NodeRun): string {
    const raiz = caminhoDeChamada(node.nodeId)[0]
    const alvo = reactFlow.getNodes().find(n => n.id === raiz)
    const props = (alvo?.data?.properties ?? {}) as Record<string, unknown>
    return String(props.workflowHash ?? "").trim()
  }

  function abrir(node: NodeRun) {
    const caminho = caminhoDeChamada(node.nodeId)
    if (caminho.length === 0) return

    const nosDoCanvas = reactFlow.getNodes()
    // Only the root step can be resolved from here. Deeper ones go in with an
    // empty hash and the viewer fills them in on the way down — but descending
    // straight to a deep level would stop at the first step without a hash, so
    // we open up to there.
    const degraus: SubflowLevel[] = []
    for (const canvasNodeId of caminho) {
      const noCanvas = nosDoCanvas.find(n => n.id === canvasNodeId)
      const props = (noCanvas?.data?.properties ?? {}) as Record<string, unknown>
      const hash = String(props.workflowHash ?? "").trim()
      if (!hash) break
      const data = (noCanvas?.data ?? {}) as { alias?: string }
      degraus.push({
        canvasNodeId,
        workflowHash: hash,
        label: (props.alias as string) || data.alias || "Sub-fluxo",
      })
    }
    if (degraus.length === 0) return

    // Centers the row's node only when we reach its level; stopping earlier,
    // the target does not exist in the open graph and the viewer frames the whole.
    const chegou = degraus.length === caminho.length
    open(degraus, chegou ? idLocal(node.nodeId) : null)
  }

  return { abrir, podeAbrir }
}

/** Highlights in the DOM the node under the cursor in the panel.
 *
 * Toggles a class directly on the React Flow element instead of going through
 * `setNodes` — changing the nodes array on every hover would re-render the whole graph.
 */
export function useCanvasHoverHighlight() {
  const hoveredNodeId = useRunPanelStore(s => s.hoveredNodeId)
  useEffect(() => {
    if (!hoveredNodeId) return
    const el = document.querySelector(`.react-flow__node[data-id="${CSS.escape(hoveredNodeId)}"]`)
    el?.classList.add("run-panel-hover")
    return () => el?.classList.remove("run-panel-hover")
  }, [hoveredNodeId])
}

/** Highlights search terms inside a text. */
export function Highlight({ text, term }: { text: string; term: string }) {
  if (!term) return <>{text}</>
  const index = text.toLowerCase().indexOf(term.toLowerCase())
  if (index < 0) return <>{text}</>
  return (
    <>
      {text.slice(0, index)}
      <mark className="bg-amber-300/40 text-inherit rounded-sm px-px">
        {text.slice(index, index + term.length)}
      </mark>
      {text.slice(index + term.length)}
    </>
  )
}

export function EmptyHint({ children }: { children: React.ReactNode }) {
  return (
    <p className={cn("p-6 text-center text-xs text-muted-foreground/60 select-none")}>
      {children}
    </p>
  )
}
