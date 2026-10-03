"use client"
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  TbBolt, TbChevronDown, TbChevronRight, TbCopy, TbDatabase,
  TbGitBranch, TbSubtask, TbTarget, TbTerminal2,
} from "react-icons/tb"
import { cn } from "@/lib/utils"
import { NodeRun, RunTimeline } from "./timeline"
import {
  DriftBadge, Elapsed, Highlight, NodeStatusIcon,
  formatMs, formatOffset, useOpenSubworkflow, useNodeFocus,
} from "./shared"
import { useRunPanelStore } from "@/app/stores/runPanelStore"

type SortKey = "order" | "duration"

const STATUS_TEXT: Record<NodeRun["status"], string> = {
  pending:   "aguardando",
  running:   "executando",
  completed: "concluído",
  failed:    "falhou",
  // Distinct from "aguardando" (waiting): this node STARTED. What is missing is
  // the news of its completion, which was lost before reaching the panel.
  unknown:   "sem resposta",
}

const NodeRow = memo(function NodeRow({
  node, maxMs, search, expanded, isRevealed, onToggle,
}: {
  node: NodeRun
  maxMs: number
  search: string
  expanded: boolean
  /** Comes as a prop (and not from a selector in here) so that only the
   *  revealed row re-renders — subscribed to the store, every row re-rendered
   *  on each click on the canvas. */
  isRevealed: boolean
  /** Takes the id instead of a closure already bound to the node: `onToggle={() =>
   *  toggle(node.nodeId)}` was born with a new identity on every parent render
   *  and broke the `memo` of ALL rows on every panel flush. */
  onToggle: (nodeId: string) => void
}) {
  const { focusNode, setHovered } = useNodeFocus()
  const { abrir, podeAbrir } = useOpenSubworkflow()
  const rowRef = useRef<HTMLDivElement>(null)
  const reveal = useRunPanelStore(s => s.reveal)

  // Canvas → panel: clicking a node on the canvas scrolls to its row here.
  useEffect(() => {
    if (!isRevealed) return
    rowRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })
    const timer = setTimeout(() => reveal(null), 1600)
    return () => clearTimeout(timer)
  }, [isRevealed, reveal])

  const widthPct = node.durationMs != null && maxMs > 0 ? (node.durationMs / maxMs) * 100 : 0

  return (
    <div
      ref={rowRef}
      onMouseEnter={() => setHovered(node)}
      onMouseLeave={() => setHovered(null)}
      className={cn(
        "border-b border-border/40 transition-colors",
        isRevealed && "bg-primary/10",
        node.status === "failed" && "bg-destructive/5",
      )}
    >
      <div
        className="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-accent/40 text-xs"
        onClick={() => onToggle(node.nodeId)}
        onDoubleClick={() => focusNode(node)}
      >
        <span className="text-muted-foreground/40 shrink-0">
          {expanded ? <TbChevronDown size={11} /> : <TbChevronRight size={11} />}
        </span>

        <span className="w-16 shrink-0 text-right font-mono text-[10px] text-muted-foreground/60 tabular-nums">
          {formatOffset(node.startOffsetMs)}
        </span>

        <NodeStatusIcon status={node.status} />

        {/* Node from inside a sub-workflow: without the badge the row passed for a
            node of the current workflow, and the name could match one here. */}
        {node.subFlow && (
          <span
            title={`Dentro do sub-fluxo executado por "${node.subFlow}"`}
            className="inline-flex shrink-0 items-center gap-0.5 rounded bg-indigo-500/10 px-1.5 py-px text-[10px] text-indigo-600 dark:text-indigo-400"
          >
            <TbSubtask size={10} /> {node.subFlow}
          </span>
        )}

        <span className="min-w-0 flex-1 truncate font-medium">
          <Highlight text={node.name} term={search} />
        </span>

        <span className="hidden shrink-0 font-mono text-[10px] text-muted-foreground/50 sm:inline">
          {node.type}
        </span>

        {node.cacheHit && (
          <span title="Resultado veio do cache" className="inline-flex items-center gap-0.5 rounded bg-purple-500/10 px-1.5 py-px text-[10px] text-purple-600 dark:text-purple-400">
            <TbBolt size={10} /> cache
          </span>
        )}
        {node.branchResult !== undefined && (
          <span title="Ramo tomado pela condição" className="inline-flex items-center gap-0.5 rounded bg-sky-500/10 px-1.5 py-px text-[10px] text-sky-600 dark:text-sky-400">
            <TbGitBranch size={10} /> {String(node.branchResult)}
          </span>
        )}
        {node.schemaDrift && <DriftBadge drift={node.schemaDrift} />}
        {node.prints.length > 0 && (
          <span title="Linhas de saída (print)" className="inline-flex items-center gap-0.5 rounded bg-cyan-500/10 px-1.5 py-px text-[10px] text-cyan-600 dark:text-cyan-400">
            <TbTerminal2 size={10} /> {node.prints.length}
          </span>
        )}

        <span className="w-14 shrink-0 text-right font-mono text-[10px] tabular-nums text-muted-foreground">
          {node.status === "running" && node.startedAt
            ? <Elapsed since={node.startedAt} />
            : formatMs(node.durationMs)}
        </span>

        {/* Proportional bar — read "who took long" without comparing numbers */}
        <span className="hidden h-1 w-20 shrink-0 overflow-hidden rounded-full bg-muted md:block">
          <span
            className={cn(
              "block h-full rounded-full",
              node.status === "failed" ? "bg-destructive/70" : "bg-primary/50",
            )}
            style={{ width: `${widthPct}%` }}
          />
        </span>
      </div>

      {expanded && (
        <div className="space-y-2 bg-muted/20 px-3 pb-3 pl-[6.25rem] pt-1 text-[11px]">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-muted-foreground">
            <span>estado: <span className="text-foreground/80">{STATUS_TEXT[node.status]}</span></span>
            <span>id: <span className="font-mono text-foreground/60">{node.nodeId}</span></span>
            {node.durationMs != null && (
              <span>duração: <span className="text-foreground/80">{node.durationMs.toFixed(1)}ms</span></span>
            )}
          </div>

          {node.outputKeys.length > 0 && (
            <div className="flex flex-wrap items-center gap-1 text-muted-foreground">
              <TbDatabase size={11} className="shrink-0" />
              <span>saídas:</span>
              {node.outputKeys.map(key => (
                <span key={key} className="rounded bg-muted px-1 py-px font-mono text-foreground/70">{key}</span>
              ))}
            </div>
          )}

          {node.prints.length > 0 && (
            <div className="rounded border border-cyan-500/20 bg-cyan-500/5 p-2 font-mono text-[10px] leading-relaxed">
              {node.prints.slice(-8).map((print, i) => (
                <div key={i} className="whitespace-pre-wrap break-all text-foreground/80">{print.text}</div>
              ))}
              {node.prints.length > 8 && (
                <div className="mt-1 text-muted-foreground/60">
                  … {node.prints.length - 8} linha(s) anterior(es) — veja a aba Saída
                </div>
              )}
            </div>
          )}

          {node.debug && (
            <div className="space-y-1">
              {Object.entries(node.debug).map(([key, summary]) => (
                <div key={key} className="rounded border border-amber-500/20 bg-amber-500/5 px-2 py-1 font-mono text-[10px]">
                  <span className="font-semibold text-amber-600 dark:text-amber-400">{key}</span>
                  <span className="mx-1 text-muted-foreground">→</span>
                  <span className="whitespace-pre-wrap break-all text-foreground/80">{summary}</span>
                </div>
              ))}
            </div>
          )}

          {node.problem && (
            <pre className="whitespace-pre-wrap break-all rounded bg-destructive/10 p-2 text-[10px] leading-relaxed text-destructive">
              {node.problem.message}
            </pre>
          )}

          <div className="flex items-center gap-2 pt-0.5">
            {podeAbrir(node) && (
              <button
                onClick={(e) => { e.stopPropagation(); abrir(node) }}
                className="inline-flex items-center gap-1 rounded border border-indigo-500/40 px-2 py-0.5 text-[10px] text-indigo-600 transition-colors hover:bg-indigo-500/10 dark:text-indigo-400"
              >
                <TbSubtask size={11} /> abrir sub-fluxo
              </button>
            )}
            <button
              onClick={(e) => { e.stopPropagation(); focusNode(node) }}
              className="inline-flex items-center gap-1 rounded border border-border px-2 py-0.5 text-[10px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <TbTarget size={11} /> {node.subFlow ? "ir para o nó que chamou" : "ir para o nó"}
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                navigator.clipboard.writeText(
                  `${node.name} (${node.type}) ${STATUS_TEXT[node.status]} ${formatMs(node.durationMs)}`,
                )
              }}
              className="inline-flex items-center gap-1 rounded border border-border px-2 py-0.5 text-[10px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <TbCopy size={11} /> copiar
            </button>
          </div>
        </div>
      )}
    </div>
  )
})

const NodesTab = ({ timeline }: { timeline: RunTimeline }) => {
  const search = useRunPanelStore(s => s.search)
  const revealNodeId = useRunPanelStore(s => s.revealNodeId)
  const [sort, setSort] = useState<SortKey>("order")
  // Keyed by nodeId — the old panel used the index in the filtered array,
  // so switching filters opened the wrong row.
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase()
    const filtered = term
      ? timeline.nodes.filter(n =>
          n.name.toLowerCase().includes(term) ||
          n.type.toLowerCase().includes(term) ||
          n.nodeId.toLowerCase().includes(term))
      : timeline.nodes
    if (sort === "duration") {
      return [...filtered].sort((a, b) => (b.durationMs ?? -1) - (a.durationMs ?? -1))
    }
    return filtered
  }, [timeline.nodes, search, sort])

  const maxMs = useMemo(
    () => Math.max(1, ...timeline.nodes.map(n => n.durationMs ?? 0)),
    [timeline.nodes],
  )

  // Stable (functional form of setState): this is what lets NodeRow's `memo`
  // actually hold.
  const toggle = useCallback((nodeId: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(nodeId)) next.delete(nodeId)
      else next.add(nodeId)
      return next
    })
  }, [])

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-3 border-b bg-muted/30 px-3 py-1 text-[10px] uppercase tracking-wider text-muted-foreground/70">
        <button
          onClick={() => setSort("order")}
          className={cn("transition-colors hover:text-foreground", sort === "order" && "font-semibold text-foreground")}
        >
          ordem de execução
        </button>
        <span className="text-muted-foreground/30">·</span>
        <button
          onClick={() => setSort("duration")}
          className={cn("transition-colors hover:text-foreground", sort === "duration" && "font-semibold text-foreground")}
          title="Ordena do mais lento para o mais rápido — acha o gargalo em um clique"
        >
          duração
        </button>
        <span className="flex-1" />
        {timeline.slowest && (
          <span className="normal-case tracking-normal">
            mais lento: <span className="text-foreground/70">{timeline.slowest.name}</span> {formatMs(timeline.slowest.durationMs)}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {visible.map(node => (
          <NodeRow
            key={node.nodeId}
            node={node}
            maxMs={maxMs}
            search={search}
            expanded={expanded.has(node.nodeId)}
            isRevealed={revealNodeId === node.nodeId}
            onToggle={toggle}
          />
        ))}
      </div>
    </div>
  )
}

export default NodesTab
