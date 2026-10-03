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
  /** Node type — sets the accent color. E.g.: "action", "trigger", "spatial" */
  nodeType?: string
  /** Title shown inside the card */
  title?: string
}

// No `memo` on purpose: `children` is a new JSX array on every parent render,
// so the shallow comparison never held anything back — the memo had a cost and
// delivered nothing. Mass re-rendering is solved at the source: parents read
// `selected` from the React Flow prop (instead of subscribing to the whole node
// array) and the execution state is read here through PER-ID selectors, which
// only fire for the node that actually changed.
const IconRoot = ({ id, children, className, nodeType, title, onDoubleClick, ...props }: IconRootProps) => {

  const pinnedNodes = useWorkflowCatalogStore(s => s.pinnedNodes)
  const newlyAddedNodeId = useWorkflowCatalogStore(s => s.newlyAddedNodeId)
  const setNewlyAddedNodeId = useWorkflowCatalogStore(s => s.setNewlyAddedNodeId)
  // Scalar/per-id selectors: `updateNodeStatuses` preserves the identity of
  // UNCHANGED nodes, so Zustand's Object.is cuts the render of every node
  // that didn't change. Subscribing to `statusWorkflow` (a new object on every
  // message) made all N cards re-render — and each one rebuilt its own Map over
  // the whole node list.
  const statusCanvas = useWorkflowExecutionStore(s => s.statusById.get(id))
  const workflowStatus = useWorkflowExecutionStore(s => s.statusWorkflow?.status)
  const emRamoPerdedor = useWorkflowExecutionStore(s => !!s.losingNodeIds?.has(id))
  // Filled only when the node is being drawn inside the sub-workflow
  // viewer — see subflow-viewer/scope.
  const noVisualizador = useSubflowReadOnly()
  const somenteLeitura = useCanvasReadOnly()
  const subflowStatus = useSubflowStatus()
  const isNew = id === newlyAddedNodeId

  // Clears the highlight after the animation ends
  useEffect(() => {
    if (!isNew) return
    const timer = setTimeout(() => {
      setNewlyAddedNodeId(undefined)
    }, 2500)
    return () => clearTimeout(timer)
  }, [isNew, setNewlyAddedNodeId])

  // Inside a sub-workflow the state comes from the scope, which derived it from
  // the run timeline: `statusById` only knows the editor canvas's nodes, because
  // it is seeded from them and then updated by id — and the child's node ids
  // arrive prefixed, matching none of them.
  const statusNode = subflowStatus ? subflowStatus.get(id) : statusCanvas
  const isPinned = pinnedNodes?.some(p => p.node_id === id && !p.expired)
  const { configNodeIdParam, removeConfigNodeParam, setConfigNodeParam } = useConfigNodeParams()

  // "Pending" is every node that hasn't started yet while the run is alive — and
  // not just the `queued` window, which lasts from the POST until the task_id
  // arrives: `setTaskId` promotes the workflow to "running" as soon as it replies.
  // Restricted to `queued`, the treatment was technically correct and practically
  // invisible; marking the rest of the run is what makes "what is still left"
  // readable in a large graph.
  const runDePe = workflowStatus === "queued" || workflowStatus === "running"
  const isPending = runDePe && (statusNode?.status ?? "idle") === "idle"

  const abrirConfiguracao = useCallback((e: React.MouseEvent<HTMLDivElement, MouseEvent>) => {
    // In the sub-workflow viewer, double-click belongs to navigation (going down
    // one level), and the node isn't even editable from there. Opening the
    // configuration here would point the modal at an id that doesn't exist on
    // the editor canvas.
    if (noVisualizador) return
    if (configNodeIdParam === id)
      return removeConfigNodeParam()
    if (onDoubleClick)
      onDoubleClick(e)
    setConfigNodeParam(id)
  }, [configNodeIdParam, id, removeConfigNodeParam, onDoubleClick, setConfigNodeParam, noVisualizador])

  // On a phone the gesture is a SINGLE TAP. Double tap exists in the browser, but
  // it competes with the canvas zoom and is slow by nature (the browser waits for
  // the second tap before deciding). And there it is the only path left: the
  // node toolbar, which on desktop also opens the configuration, depends on
  // hover and doesn't appear. React Flow tells a tap from a drag, so panning
  // with a finger over a node doesn't open the modal.
  const gestoDeAbrir = somenteLeitura
    ? { onClick: abrirConfiguracao }
    : { onDoubleClick: abrirConfiguracao }

  const style = TYPE_STYLES[nodeType ?? ""] ?? DEFAULT_STYLE

  // `losingNodeIds` is computed over the editor canvas's edges and doesn't know
  // the child's graph. Applying it inside the viewer would desaturate a
  // sub-workflow node just because its local id matches that of a losing branch
  // of the parent — losing branches in there stay unmarked.
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
        // Base card. `exec-card` is the scope of the execution layers, which live
        // in globals.css — see the "Estados de execução no canvas" block.
        "exec-card group relative isolate flex items-stretch bg-card border border-border rounded-lg shadow-sm",
        "w-[158px] h-[60px]",
        // Only SELECTION lives here. IMPORTANT: no `ring-offset-*` — Tailwind's
        // offset fills the gap between card and ring with `--tw-ring-offset-color`
        // (default = background), which shows up as a thin "detached" line.
        //
        // The STATE ring was moved out of here on purpose: `ring-*`, `shadow-sm`
        // and the glow keyframes competed for the same `box-shadow` property, and
        // a keyframe replaces the whole declaration — the pulse erased the
        // selection ring and the card shadow while it ran. Now a node that is
        // selected AND executing shows both rings.
        "data-[selected=true]:ring-2 data-[selected=true]:ring-muted-foreground/50",
        className,
      )}
    >

      {/* Colored stripe on the left */}
      <div className={cn("w-1 shrink-0 rounded-tl-lg rounded-bl-lg", style.stripe)} />

      {/* Icon section */}
      <div className={cn("flex items-center justify-center w-12 shrink-0", style.bg)}>
        <div className={cn("text-xl flex items-center justify-center", style.icon)}>
          {children}
        </div>
      </div>

      {/* Text section — `data-role` are hooks for the zoom LOD (globals.css):
          with the canvas zoomed out the subtitle disappears and the title grows. */}
      <div className="flex flex-col justify-center px-2.5 flex-1 min-w-0">
        <p data-role="node-title" className="text-sm font-medium text-foreground truncate leading-tight">
          {title ?? ""}
        </p>
        <p data-role="node-type-label" className={cn("text-[9px] uppercase tracking-widest leading-tight mt-0.5 font-medium", style.label)}>
          {nodeType ?? ""}
        </p>
      </div>

      {/* ── Indicador de pin (canto superior direito) ─────────────────────── */}
      {/* key={`pin-${id}`} makes the icon remount when the node changes, but the
          forwards animation only fires at the point where isPinned becomes
          true (first render of the TooltipTrigger). Gives tactile feedback
          when pinning without looping. */}
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
          {/* The color lives on the trigger because `ExecActivity` paints with
              `currentColor` — that is what lets the glyph follow the state token
              without receiving it as a prop. */}
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
