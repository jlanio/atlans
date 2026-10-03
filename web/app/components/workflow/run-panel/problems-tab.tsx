"use client"
import { useState } from "react"
import {
  TbAlertTriangle, TbCheck, TbChevronRight, TbCopy, TbRefreshAlert,
  TbSettings, TbSubtask, TbTarget, TbCircleX,
} from "react-icons/tb"
import { cn } from "@/lib/utils"
import { NodeRun, RunTimeline } from "./timeline"
import { ERROR_CATEGORY_LABEL, EmptyHint, formatOffset, useOpenSubworkflow, useNodeFocus } from "./shared"
import { useConfigNodeParams } from "@/app/hooks/workflow/useConfigNodeParams"

function ProblemCard({ node }: { node: NodeRun }) {
  const { focusNode, setHovered } = useNodeFocus()
  const { abrir, podeAbrir } = useOpenSubworkflow()
  const [showTrace, setShowTrace] = useState(false)
  const [copied, setCopied] = useState(false)
  const { setConfigNodeParam } = useConfigNodeParams()
  const problem = node.problem!

  function copyAll() {
    const parts = [
      `${node.name} (${node.type}) — ${node.nodeId}`,
      node.subFlow ? `dentro do sub-fluxo: ${node.subFlow}` : null,
      problem.message,
      problem.category ? `categoria: ${problem.category}` : null,
      problem.traceback,
    ].filter(Boolean)
    navigator.clipboard.writeText(parts.join("\n\n"))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div
      onMouseEnter={() => setHovered(node)}
      onMouseLeave={() => setHovered(null)}
      className="m-3 overflow-hidden rounded-md border border-destructive/30 bg-destructive/[0.03]"
    >
      <div className="flex items-center gap-2 border-b border-destructive/20 bg-destructive/5 px-3 py-1.5">
        <TbCircleX size={13} className="shrink-0 text-destructive" />
        <span className="text-xs font-medium">{node.name}</span>
        {node.subFlow && (
          <span
            title={`Falhou dentro do sub-fluxo executado por "${node.subFlow}"`}
            className="inline-flex items-center gap-0.5 rounded bg-indigo-500/10 px-1.5 py-px text-[10px] text-indigo-600 dark:text-indigo-400"
          >
            <TbSubtask size={10} /> {node.subFlow}
          </span>
        )}
        <span className="font-mono text-[10px] text-muted-foreground/60">{node.nodeId}</span>
        <span className="flex-1" />
        <span className="font-mono text-[10px] tabular-nums text-muted-foreground/60">
          {formatOffset(node.startOffsetMs)}
        </span>
      </div>

      <div className="space-y-2 px-3 py-2">
        <pre className="whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-destructive/90">
          {problem.message}
        </pre>

        {/* The taxonomy answers "is it worth retrying?" — more useful than 18
            stack lines for someone who just wants to know what to do now. */}
        {problem.category && (
          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            <span className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-muted-foreground">
              <TbAlertTriangle size={11} />
              {ERROR_CATEGORY_LABEL[problem.category] ?? problem.category}
            </span>
            {problem.retryable != null && (
              <span className={cn(
                "inline-flex items-center gap-1 rounded px-1.5 py-0.5",
                problem.retryable
                  ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                  : "bg-muted text-muted-foreground",
              )}>
                <TbRefreshAlert size={11} />
                {problem.retryable ? "pode ser transitório — repetir pode resolver" : "repetir não resolve"}
              </span>
            )}
          </div>
        )}

        {/* The backend ALWAYS sends the traceback on a failure. The old panel only
            showed it with debug mode on — which has to be decided before
            running, meaning it was never on when it was needed. */}
        {problem.traceback && (
          <div>
            <button
              onClick={() => setShowTrace(v => !v)}
              className="inline-flex items-center gap-1 text-[10px] text-muted-foreground transition-colors hover:text-foreground"
            >
              <TbChevronRight size={11} className={cn("transition-transform", showTrace && "rotate-90")} />
              traceback ({problem.traceback.split("\n").length} linhas)
            </button>
            {showTrace && (
              <pre className="mt-1 max-h-56 overflow-auto whitespace-pre-wrap break-all rounded border border-destructive/20 bg-destructive/5 p-2 font-mono text-[10px] leading-relaxed text-destructive/80">
                {problem.traceback}
              </pre>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 pt-0.5">
          {/* Opens the child's graph at the node that actually broke. `focusNode` below
              only reaches the parent's SubWorkflow node — the only id in this row
              that exists on the editor canvas. */}
          {podeAbrir(node) && (
            <button
              onClick={() => abrir(node)}
              className="inline-flex items-center gap-1 rounded border border-indigo-500/40 px-2 py-0.5 text-[10px] text-indigo-600 transition-colors hover:bg-indigo-500/10 dark:text-indigo-400"
            >
              <TbSubtask size={11} /> abrir sub-fluxo
            </button>
          )}
          <button
            onClick={() => focusNode(node)}
            className="inline-flex items-center gap-1 rounded border border-border px-2 py-0.5 text-[10px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <TbTarget size={11} /> {node.subFlow ? "ir para o nó que chamou" : "ir para o nó"}
          </button>
          <button
            onClick={() => { focusNode(node); setConfigNodeParam(node.canvasNodeId) }}
            className="inline-flex items-center gap-1 rounded border border-border px-2 py-0.5 text-[10px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <TbSettings size={11} /> abrir configuração
          </button>
          <button
            onClick={copyAll}
            className="inline-flex items-center gap-1 rounded border border-border px-2 py-0.5 text-[10px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            {copied ? <TbCheck size={11} className="text-emerald-500" /> : <TbCopy size={11} />} copiar erro
          </button>
        </div>
      </div>
    </div>
  )
}

const ProblemsTab = ({ timeline }: { timeline: RunTimeline }) => {
  const hasWorkflowError = timeline.workflow.status === "failed" && timeline.workflow.error

  if (timeline.problems.length === 0 && !hasWorkflowError) {
    return <EmptyHint>Nenhum problema nesta execução.</EmptyHint>
  }

  return (
    <div className="h-full overflow-y-auto">
      {timeline.problems.map(node => (
        <ProblemCard key={node.nodeId} node={node} />
      ))}

      {/* Run failure not attributable to a node (e.g. the executor died midway) */}
      {hasWorkflowError && timeline.problems.length === 0 && (
        <div className="m-3 rounded-md border border-destructive/30 bg-destructive/[0.03] p-3">
          <p className="mb-1 text-xs font-medium">Falha na execução</p>
          <pre className="whitespace-pre-wrap break-words font-mono text-[11px] text-destructive/90">
            {timeline.workflow.error}
          </pre>
          {timeline.workflow.category && (
            <span className="mt-2 inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground">
              <TbAlertTriangle size={11} />
              {ERROR_CATEGORY_LABEL[timeline.workflow.category] ?? timeline.workflow.category}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default ProblemsTab
