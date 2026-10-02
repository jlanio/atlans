"use client"
import { useCallback, useMemo, useRef } from "react"
import { useVirtualizer, type Virtualizer } from "@tanstack/react-virtual"
import { TbClock, TbSubtask, TbTarget } from "react-icons/tb"
import { cn } from "@/lib/utils"
import { RunTimeline } from "./timeline"
import { EmptyHint, Highlight, formatOffset, useNodeFocus } from "./shared"
import { useRunPanelStore } from "@/app/stores/runPanelStore"
import { useStickyScroll } from "./use-sticky-scroll"

/**
 * Saída de `print()` dos nós, agrupada por nó.
 *
 * O painel antigo renderizava cada print como uma linha de log completa — com
 * ícone, rótulo de status e duração — e, pior, escondia o nome do nó justamente
 * nessas linhas: com dois nós Python imprimindo, não dava para saber quem era
 * quem. Um print não tem status nem duração; aqui ele é tratado como stdout.
 *
 * Virtualizado: um run verboso pode ter dezenas de milhares de linhas de print
 * (até MAX_RUN_EVENTS eventos × ~200 linhas cada). Grupos e linhas são achatados
 * numa lista única e só as linhas visíveis vão ao DOM. O cabeçalho de cada nó
 * deixou de ser `sticky` — o trade-off por virtualizar a estrutura agrupada com
 * segurança; ele agora rola junto com a saída daquele nó.
 */
type ItemSaida =
  | { kind: "header"; node: RunTimeline["nodes"][number]; key: string }
  | { kind: "print"; node: RunTimeline["nodes"][number]; print: RunTimeline["nodes"][number]["prints"][number]; key: string }

const OutputTab = ({ timeline, showTimestamps, onToggleTimestamps }: {
  timeline: RunTimeline
  showTimestamps: boolean
  onToggleTimestamps: () => void
}) => {
  const search = useRunPanelStore(s => s.search)
  const { focusNode, setHovered } = useNodeFocus()
  const virtRef = useRef<Virtualizer<HTMLDivElement, Element> | null>(null)
  const { containerRef, bottomRef, showJump, jumpToBottom } = useStickyScroll(
    [timeline.totalPrints],
    useCallback(() => {
      const v = virtRef.current
      if (v && v.options.count > 0) v.scrollToIndex(v.options.count - 1, { align: "end" })
    }, []),
  )

  const groups = useMemo(() => {
    const term = search.trim().toLowerCase()
    return timeline.nodes
      .filter(n => n.prints.length > 0)
      .map(node => ({
        node,
        prints: term ? node.prints.filter(p => p.text.toLowerCase().includes(term)) : node.prints,
      }))
      .filter(g => g.prints.length > 0)
  }, [timeline.nodes, search])

  // Achata grupos → [header, print, print, header, print, ...] para a lista
  // virtual. Keys estáveis por nó+posição, para o `getItemKey` não remontar.
  const flat = useMemo(() => {
    const arr: ItemSaida[] = []
    for (const { node, prints } of groups) {
      arr.push({ kind: "header", node, key: `h:${node.nodeId}` })
      prints.forEach((print, j) => arr.push({ kind: "print", node, print, key: `p:${node.nodeId}:${j}` }))
    }
    return arr
  }, [groups])

  const virtualizer = useVirtualizer({
    count: flat.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 22,
    overscan: 16,
    getItemKey: (index) => flat[index].key,
  })
  virtRef.current = virtualizer

  if (groups.length === 0) {
    return (
      <EmptyHint>
        {timeline.totalPrints === 0
          ? "Nenhuma saída. Use print() dentro de um nó Script Python para escrever aqui."
          : "Nenhuma linha corresponde à busca."}
      </EmptyHint>
    )
  }

  const itens = virtualizer.getVirtualItems()

  return (
    <div className="relative flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-end border-b border-border/40 px-3 py-1 font-mono">
        <button
          onClick={onToggleTimestamps}
          className={cn(
            "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] transition-colors",
            showTimestamps ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground",
          )}
        >
          <TbClock size={11} /> tempos
        </button>
      </div>

      <div ref={containerRef} className="min-h-0 flex-1 overflow-y-auto font-mono text-[11px]">
        <div style={{ height: virtualizer.getTotalSize(), position: "relative", width: "100%" }}>
          {itens.map(vi => {
            const item = flat[vi.index]
            return (
              <div
                key={vi.key}
                data-index={vi.index}
                ref={virtualizer.measureElement}
                style={{ position: "absolute", top: 0, left: 0, width: "100%", transform: `translateY(${vi.start}px)` }}
              >
                {item.kind === "header" ? (
                  <header
                    onMouseEnter={() => setHovered(item.node)}
                    onMouseLeave={() => setHovered(null)}
                    onClick={() => focusNode(item.node)}
                    className="group flex cursor-pointer items-center gap-2 border-y border-border/50 bg-muted/80 px-3 py-1"
                    title="Clique para ir ao nó no canvas"
                  >
                    <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">saída de</span>
                    <span className="font-sans text-[11px] font-medium">{item.node.name}</span>
                    {/* Um print vindo de dentro do sub-fluxo tinha cabeçalho igual ao
                        de um nó daqui — e o nome pode ser o mesmo nos dois fluxos. */}
                    {item.node.subFlow && (
                      <span
                        title={`Dentro do sub-fluxo executado por "${item.node.subFlow}"`}
                        className="inline-flex items-center gap-0.5 rounded bg-indigo-500/10 px-1.5 py-px text-[10px] text-indigo-600 dark:text-indigo-400"
                      >
                        <TbSubtask size={10} /> {item.node.subFlow}
                      </span>
                    )}
                    <span className="text-[10px] text-muted-foreground/50">{item.node.nodeId}</span>
                    <TbTarget size={11} className="ml-auto text-muted-foreground/0 transition-colors group-hover:text-muted-foreground" />
                  </header>
                ) : (
                  <div className="flex gap-2 px-3 leading-relaxed">
                    {showTimestamps && (
                      <span className="w-16 shrink-0 text-right text-[10px] tabular-nums text-muted-foreground/40">
                        {formatOffset(item.print.offsetMs)}
                      </span>
                    )}
                    <span className="min-w-0 whitespace-pre-wrap break-all text-foreground/85">
                      <Highlight text={item.print.text} term={search} />
                    </span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
        <div ref={bottomRef} />
      </div>

      {showJump && (
        <button
          onClick={jumpToBottom}
          className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full border border-border bg-background px-3 py-1 text-[10px] shadow-md transition-colors hover:bg-accent"
        >
          ↓ novas linhas
        </button>
      )}
    </div>
  )
}

export default OutputTab
