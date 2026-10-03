"use client"
import { memo, useCallback, useMemo, useRef, useState } from "react"
import { useVirtualizer, type Virtualizer } from "@tanstack/react-virtual"
import { TbBug, TbChevronDown, TbChevronRight, TbTerminal2 } from "react-icons/tb"
import { cn } from "@/lib/utils"
import { RunEvent } from "@/app/stores/workflowExecutionStore"
import { EmptyHint, Highlight, NodeStatusIcon, formatMs, formatOffset } from "./shared"
import { WF_COMPLETE } from "./timeline"
import { useRunPanelStore } from "@/app/stores/runPanelStore"
import { useStickyScroll } from "./use-sticky-scroll"

function levelClass(event: RunEvent) {
  if (event.level === "error") return "border-l-destructive bg-destructive/5"
  if (event.level === "warn")  return "border-l-amber-500 bg-amber-500/5"
  if (event.kind === "stdout") return "border-l-cyan-500/60"
  if (event.kind === "debug")  return "border-l-amber-500/50"
  return "border-l-transparent"
}

/** Text of the collapsed row and of the search.
 *
 *  An aggregated stdout event carries N lines in `lines` and NO longer has
 *  `message` — the executor stopped duplicating the text so the batch fits the
 *  frame's 64 KB ceiling. Without reading `lines` here, every `print()` line
 *  showed up empty in the panel and the search never found anything in the
 *  script's output. */
export function textoDoEvento(event: RunEvent): string {
  if (event.message) return event.message
  const linhas = event.lines
  if (!linhas || linhas.length === 0) return ""
  // One row per event in the raw stream: shows the first line and says how many
  // came with it (all are visible when expanded, and one by one in the "Nós" tab).
  if (linhas.length === 1) return linhas[0]
  return `${linhas[0]} … (+${linhas.length - 1} linha(s))`
}

function KindIcon({ event }: { event: RunEvent }) {
  if (event.kind === "stdout") return <TbTerminal2 size={11} className="shrink-0 text-cyan-500" />
  if (event.kind === "debug")  return <TbBug size={11} className="shrink-0 text-amber-500" />
  const status = event.status === "started" ? "running"
    : event.status === "failed" ? "failed"
    : event.status === "completed" ? "completed" : "pending"
  return <NodeStatusIcon status={status} size={11} />
}

const RawRow = memo(function RawRow({ event, startTs, search, expanded, onToggle }: {
  event: RunEvent
  startTs: number | null
  search: string
  expanded: boolean
  onToggle: (seq: number) => void
}) {
  const offset = startTs != null ? event.ts - startTs : null
  const label = event.node === WF_COMPLETE ? "workflow" : (event.node_name ?? event.node ?? "—")
  const texto = textoDoEvento(event)

  return (
    <div className={cn("border-b border-l-2 border-border/30", levelClass(event))}>
      <div
        className="flex cursor-pointer items-center gap-2 px-3 py-1 hover:bg-accent/30"
        onClick={() => onToggle(event.seq)}
      >
        <span className="shrink-0 text-muted-foreground/40">
          {expanded ? <TbChevronDown size={10} /> : <TbChevronRight size={10} />}
        </span>
        <span className="w-16 shrink-0 text-right text-[10px] tabular-nums text-muted-foreground/50">
          {formatOffset(offset)}
        </span>
        <KindIcon event={event} />
        <span className="w-16 shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground/60">
          {event.kind}
        </span>
        <span className="shrink-0 font-medium text-violet-500 dark:text-violet-400">{label}</span>
        {event.status && (
          <span className="shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground/70">
            {event.status}
          </span>
        )}
        {texto && (
          <span className="min-w-0 flex-1 truncate text-foreground/70">
            <Highlight text={texto} term={search} />
          </span>
        )}
        <span className="ml-auto shrink-0 text-[10px] tabular-nums text-muted-foreground/50">
          {event.duration_ms != null ? formatMs(event.duration_ms) : ""}
        </span>
      </div>
      {expanded && (
        <pre className="overflow-x-auto bg-muted/30 px-3 py-2 text-[10px] leading-relaxed text-muted-foreground">
          {JSON.stringify(event.raw, null, 2)}
        </pre>
      )}
    </div>
  )
})

/** Raw chronological stream — the old view, kept for advanced debugging. */
const RawTab = ({ events, startTs, droppedEvents }: {
  events: RunEvent[]
  startTs: number | null
  droppedEvents: number
}) => {
  const search = useRunPanelStore(s => s.search)

  // Expansion state OUTSIDE the row: virtualization unmounts the row when it
  // leaves the window, and a local useState would lose the expansion on
  // scrolling back.
  const [expandidos, setExpanded] = useState<Set<number>>(() => new Set())
  const toggleExpansion = useCallback((seq: number) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(seq)) next.delete(seq)
      else next.add(seq)
      return next
    })
  }, [])

  // Ref to the virtualizer, so the "stick to the end" callback reaches
  // scrollToIndex without a circular dependency on the hook's containerRef.
  const virtRef = useRef<Virtualizer<HTMLDivElement, Element> | null>(null)
  const { containerRef, bottomRef, showJump, jumpToBottom } = useStickyScroll(
    [events.length],
    useCallback(() => {
      const v = virtRef.current
      if (v && v.options.count > 0) v.scrollToIndex(v.options.count - 1, { align: "end" })
    }, []),
  )

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return events
    return events.filter(e =>
      (e.message ?? "").toLowerCase().includes(term) ||
      // Searches inside the whole aggregated batch, not just the summary line — that
      // is where the `print()` output lives since `message` stopped duplicating it.
      (e.lines?.some(linha => linha.toLowerCase().includes(term)) ?? false) ||
      (e.node_name ?? "").toLowerCase().includes(term) ||
      (e.node ?? "").toLowerCase().includes(term) ||
      (e.status ?? "").toLowerCase().includes(term))
  }, [events, search])

  // Virtualization: renders only the ~40 visible rows instead of keeping up to
  // MAX_RUN_EVENTS (2000) in the DOM. Dynamic measurement (measureElement +
  // built-in ResizeObserver) because the row expands on click. `getItemKey` uses
  // `seq` for the same reason as the old map: rotation removes stdout from the
  // MIDDLE, and the index would shift the keys of every survivor.
  const rowVirtualizer = useVirtualizer({
    count: visible.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 26,
    overscan: 12,
    getItemKey: (index) => visible[index].seq,
  })
  virtRef.current = rowVirtualizer

  if (visible.length === 0) {
    return <EmptyHint>{events.length === 0 ? "Nenhum evento." : "Nenhum evento corresponde à busca."}</EmptyHint>
  }

  const itens = rowVirtualizer.getVirtualItems()

  return (
    <div className="relative flex h-full flex-col">
      {/* Silently truncating would make the panel look complete when it is not. It
          stays OUTSIDE the scroll container (header) so it does not shift the
          virtualizer's offset calculation. */}
      {droppedEvents > 0 && (
        <div className="shrink-0 border-b bg-amber-500/5 px-3 py-1 font-mono text-[10px] text-amber-600 dark:text-amber-400">
          {droppedEvents} linha(s) de saída mais antiga(s) descartada(s) para limitar o uso de memória
        </div>
      )}
      <div ref={containerRef} className="min-h-0 flex-1 overflow-y-auto font-mono text-[11px]">
        <div style={{ height: rowVirtualizer.getTotalSize(), position: "relative", width: "100%" }}>
          {itens.map(vi => (
            <div
              key={vi.key}
              data-index={vi.index}
              ref={rowVirtualizer.measureElement}
              style={{ position: "absolute", top: 0, left: 0, width: "100%", transform: `translateY(${vi.start}px)` }}
            >
              <RawRow
                event={visible[vi.index]}
                startTs={startTs}
                search={search}
                expanded={expandidos.has(visible[vi.index].seq)}
                onToggle={toggleExpansion}
              />
            </div>
          ))}
        </div>
        <div ref={bottomRef} />
      </div>
      {showJump && (
        <button
          onClick={jumpToBottom}
          className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full border border-border bg-background px-3 py-1 text-[10px] shadow-md transition-colors hover:bg-accent"
        >
          ↓ novos eventos
        </button>
      )}
    </div>
  )
}

export default RawTab
