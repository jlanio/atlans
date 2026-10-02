"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import {
  TbAlertTriangle, TbCheck, TbChevronDown, TbChevronUp, TbCircleCheck,
  TbCircleX, TbCopy, TbDownload, TbExternalLink, TbLayoutList, TbList,
  TbPlayerStop, TbSearch, TbTerminal2, TbTrash, TbX,
} from "react-icons/tb"
import { cn } from "@/lib/utils"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import {
  RUN_BAR_HEIGHT, RunPanelTab, useRunPanelStore,
} from "@/app/stores/runPanelStore"
import { RunTimeline, timelineToText } from "./timeline"
import { useRunSnapshot } from "./use-run-snapshot"
import { Elapsed, formatMs, useCanvasHoverHighlight } from "./shared"
import NodesTab from "./nodes-tab"
import OutputTab from "./output-tab"
import ProblemsTab from "./problems-tab"
import RawTab from "./raw-tab"
import HistoryEmpty from "./history-empty"

const MAX_HEIGHT_RATIO = 0.9

function TabButton({ tab, active, count, icon, label, tone, onClick }: {
  tab: RunPanelTab
  active: boolean
  count?: number
  icon: React.ReactNode
  label: string
  tone?: "error"
  onClick: (tab: RunPanelTab) => void
}) {
  return (
    <button
      onClick={() => onClick(tab)}
      className={cn(
        "inline-flex items-center gap-1.5 border-b-2 px-3 py-1.5 text-xs transition-colors",
        active
          ? "border-primary text-foreground"
          : "border-transparent text-muted-foreground hover:text-foreground",
        count === 0 && !active && "opacity-50",
      )}
    >
      {icon}
      {label}
      {count != null && count > 0 && (
        <span className={cn(
          "rounded-full px-1.5 text-[10px] tabular-nums",
          tone === "error" ? "bg-destructive/15 text-destructive" : "bg-muted text-muted-foreground",
        )}>
          {count}
        </span>
      )}
    </button>
  )
}

/**
 * Painel de execução — dock inferior NÃO-modal.
 *
 * Substitui o antigo "console de execução", que era um Sheet com overlay
 * `bg-black/50` cobrindo a tela: abrir o console escurecia e desabilitava o
 * canvas, justamente onde vive o feedback visual que os logs complementam.
 * Aqui o painel é uma div ancorada dentro do próprio canvas — dá para ler o log
 * e ver a animação ao mesmo tempo, e clicar numa linha centraliza o nó.
 */
const RunPanel = () => {
  const router = useRouter()
  const open = useRunPanelStore(s => s.open)
  // Snapshot agregado: `events` e `statusWorkflow` mudam a cada mensagem do WS e
  // assiná-los por selector re-renderizava o painel inteiro nessa frequência.
  // `open` decide se vale reconstruir a linha do tempo por nó: recolhido, o
  // painel desenha só a barra de resumo, e reconstruí-la oito vezes por segundo
  // era CPU que nunca chegava à tela.
  const { timeline, events, droppedEvents } = useRunSnapshot(open)
  const isExecuting = useWorkflowExecutionStore(s => s.isExecuting)
  const wsState = useWorkflowExecutionStore(s => s.wsState)
  const viewingRunId = useWorkflowExecutionStore(s => s.viewingRunId)
  const isHistorical = useWorkflowExecutionStore(s => s.isHistorical)
  const clearEvents = useWorkflowExecutionStore(s => s.clearEvents)

  const height = useRunPanelStore(s => s.height)
  const tab = useRunPanelStore(s => s.tab)
  const search = useRunPanelStore(s => s.search)
  const setOpen = useRunPanelStore(s => s.setOpen)
  const setHeight = useRunPanelStore(s => s.setHeight)
  const setTab = useRunPanelStore(s => s.setTab)
  const setSearch = useRunPanelStore(s => s.setSearch)
  const openAt = useRunPanelStore(s => s.openAt)

  const [showTimestamps, setShowTimestamps] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showSearch, setShowSearch] = useState(false)
  const searchRef = useRef<HTMLInputElement>(null)
  const dragRef = useRef<{ startY: number; startH: number } | null>(null)

  useCanvasHoverHighlight()

  const runStatus = timeline.workflow.status
  const hasProblems = timeline.problems.length > 0 || runStatus === "failed"

  // Falhou → abre direto em "Problemas". O usuário não deveria ter que procurar
  // a linha vermelha no meio de dezenas de eventos de ciclo de vida.
  const announcedFailureRef = useRef<string | null>(null)
  useEffect(() => {
    if (runStatus !== "failed") return
    const key = viewingRunId ?? "run"
    if (announcedFailureRef.current === key) return
    announcedFailureRef.current = key
    openAt("problems")
  }, [runStatus, viewingRunId, openAt])

  // Ctrl+` alterna o painel; Ctrl+F busca quando ele está aberto.
  useEffect(() => {
    function isEditing(target: EventTarget | null) {
      const el = target as HTMLElement | null
      if (!el) return false
      return el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName)
    }

    function onKeyDown(e: KeyboardEvent) {
      // Não sequestra atalhos enquanto o usuário digita — sem esta guarda o
      // Ctrl+F dentro da configuração de um nó abria a busca do painel.
      if (isEditing(e.target)) return
      if ((e.ctrlKey || e.metaKey) && e.key === "`") {
        e.preventDefault()
        setOpen(!useRunPanelStore.getState().open)
        return
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f" && useRunPanelStore.getState().open) {
        e.preventDefault()
        setShowSearch(true)
        requestAnimationFrame(() => searchRef.current?.focus())
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [setOpen])

  // Eventos de PONTEIRO, não de mouse: com `mousedown`/`mousemove` a alça era
  // inerte ao toque, e no telefone o painel ficava preso na altura de abertura
  // — o duplo toque na barra maximizava, mas não havia como escolher um meio
  // termo. `setPointerCapture` ainda resolve o arraste que sai do elemento,
  // que com listeners no document dependia de o ponteiro não ser capturado por
  // outro alvo no meio do caminho.
  const handleResizePointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault()
    const alca = e.currentTarget
    alca.setPointerCapture(e.pointerId)
    dragRef.current = { startY: e.clientY, startH: height }

    function onMove(me: PointerEvent) {
      if (!dragRef.current) return
      const delta = dragRef.current.startY - me.clientY
      const max = Math.round(window.innerHeight * MAX_HEIGHT_RATIO)
      setHeight(Math.min(dragRef.current.startH + delta, max))
    }
    function onUp() {
      dragRef.current = null
      alca.removeEventListener("pointermove", onMove)
      alca.removeEventListener("pointerup", onUp)
      alca.removeEventListener("pointercancel", onUp)
    }
    alca.addEventListener("pointermove", onMove)
    alca.addEventListener("pointerup", onUp)
    // O navegador cancela o ponteiro quando decide que o gesto virou rolagem;
    // sem tratar isso, `dragRef` ficava preso e a alça seguia "arrastando".
    alca.addEventListener("pointercancel", onUp)
  }, [height, setHeight])

  function copyAll() {
    navigator.clipboard.writeText(timelineToText(timeline, viewingRunId))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  function download() {
    const blob = new Blob([timelineToText(timeline, viewingRunId)], { type: "text/plain;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `execucao-${viewingRunId ?? "log"}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  const hasRun = events.length > 0 || isExecuting

  return (
    // nowheel/nopan impedem o canvas de capturar scroll e arraste feitos dentro
    // do painel — sem isso rolar a lista dava zoom no grafo.
    <div
      className="nowheel nopan nodrag absolute inset-x-0 bottom-0 z-20 flex flex-col border-t border-border bg-background/95 shadow-[0_-4px_16px_-8px_rgba(0,0,0,0.35)] backdrop-blur"
      style={{ height: open ? height : RUN_BAR_HEIGHT }}
      onContextMenu={e => e.stopPropagation()}
    >
      {open && (
        <div
          onPointerDown={handleResizePointerDown}
          // `touch-none` impede o navegador de tratar o arraste como rolagem
          // da página e cancelar o ponteiro no primeiro pixel. A faixa é mais
          // alta no telefone: 8px é um alvo impossível de acertar com o dedo.
          className="group/resize absolute inset-x-0 -top-3 sm:-top-1 z-10 flex h-6 sm:h-2 touch-none cursor-ns-resize items-center justify-center"
        >
          <div className="h-1 w-10 sm:h-px rounded-full bg-border/50 transition-colors group-hover/resize:bg-primary" />
        </div>
      )}

      {/* ── Barra HUD — sempre visível ─────────────────────────────────────── */}
      <div
        className="flex h-[34px] shrink-0 cursor-pointer select-none items-center gap-2 px-3 text-xs"
        onClick={() => setOpen(!open)}
        // Duplo clique expande. Precisa reabrir explicitamente: os dois cliques
        // que precedem o dblclick já passaram pelo toggle e deixaram fechado.
        onDoubleClick={() => {
          setOpen(true)
          setHeight(Math.round(window.innerHeight * MAX_HEIGHT_RATIO))
        }}
      >
        <HudSummary
          timeline={timeline}
          isExecuting={isExecuting}
          wsLive={wsState === "open"}
          isHistorical={isHistorical}
          hasRun={hasRun}
        />

        <span className="flex-1" />

        {hasProblems && !open && (
          <button
            onClick={e => { e.stopPropagation(); openAt("problems") }}
            className="rounded border border-destructive/40 px-2 py-0.5 text-[11px] text-destructive transition-colors hover:bg-destructive/10"
          >
            ver erro
          </button>
        )}

        <span className="hidden text-[10px] text-muted-foreground/40 sm:inline">Ctrl+`</span>
        {open ? <TbChevronDown size={14} className="text-muted-foreground" />
              : <TbChevronUp size={14} className="text-muted-foreground" />}
      </div>

      {open && (
        <>
          {/* ── Abas ──────────────────────────────────────────────────────── */}
          <div className="flex shrink-0 items-center gap-0.5 border-y bg-muted/20 px-1">
            <TabButton
              tab="nodes" active={tab === "nodes"} onClick={setTab}
              icon={<TbLayoutList size={13} />} label="Nós" count={timeline.counts.total}
            />
            <TabButton
              tab="output" active={tab === "output"} onClick={setTab}
              icon={<TbTerminal2 size={13} />} label="Saída" count={timeline.totalPrints}
            />
            <TabButton
              tab="problems" active={tab === "problems"} onClick={setTab}
              icon={<TbAlertTriangle size={13} />} label="Problemas"
              count={timeline.problems.length} tone="error"
            />
            <TabButton
              tab="raw" active={tab === "raw"} onClick={setTab}
              icon={<TbList size={13} />} label="Bruto" count={events.length}
            />

            <span className="flex-1" />

            {showSearch ? (
              <div className="flex items-center gap-1 rounded border border-border bg-background px-1.5">
                <TbSearch size={12} className="text-muted-foreground" />
                <input
                  ref={searchRef}
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  onKeyDown={e => { if (e.key === "Escape") { setSearch(""); setShowSearch(false) } }}
                  placeholder="buscar…"
                  className="w-36 bg-transparent py-0.5 text-[11px] outline-none placeholder:text-muted-foreground/50"
                />
                <button
                  onClick={() => { setSearch(""); setShowSearch(false) }}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  <TbX size={12} />
                </button>
              </div>
            ) : (
              <IconAction title="Buscar (Ctrl+F)" onClick={() => { setShowSearch(true); requestAnimationFrame(() => searchRef.current?.focus()) }}>
                <TbSearch size={13} />
              </IconAction>
            )}

            <IconAction title="Copiar tudo" onClick={copyAll}>
              {copied ? <TbCheck size={13} className="text-emerald-500" /> : <TbCopy size={13} />}
            </IconAction>
            <IconAction title="Baixar log" onClick={download}>
              <TbDownload size={13} />
            </IconAction>
            {viewingRunId && (
              <IconAction title="Abrir no Histórico" onClick={() => router.push(`/observability/run/${viewingRunId}`)}>
                <TbExternalLink size={13} />
              </IconAction>
            )}
            <IconAction title="Limpar painel" onClick={clearEvents}>
              <TbTrash size={13} />
            </IconAction>
            <IconAction title="Fechar" onClick={() => setOpen(false)}>
              <TbX size={13} />
            </IconAction>
          </div>

          {/* ── Conteúdo ──────────────────────────────────────────────────── */}
          <div className="min-h-0 flex-1">
            {!hasRun ? (
              <HistoryEmpty />
            ) : tab === "nodes" ? (
              <NodesTab timeline={timeline} />
            ) : tab === "output" ? (
              <OutputTab
                timeline={timeline}
                showTimestamps={showTimestamps}
                onToggleTimestamps={() => setShowTimestamps(v => !v)}
              />
            ) : tab === "problems" ? (
              <ProblemsTab timeline={timeline} />
            ) : (
              <RawTab events={events} startTs={timeline.startTs} droppedEvents={droppedEvents} />
            )}
          </div>
        </>
      )}
    </div>
  )
}

function IconAction({ title, onClick, children }: {
  title: string
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
    >
      {children}
    </button>
  )
}

/** Resumo da barra — responde "o que está acontecendo" sem abrir o painel. */
function HudSummary({ timeline, isExecuting, wsLive, isHistorical, hasRun }: {
  timeline: RunTimeline
  isExecuting: boolean
  wsLive: boolean
  isHistorical: boolean
  hasRun: boolean
}) {
  const { counts, workflow, slowest, startTs } = timeline

  if (!hasRun) {
    return <span className="text-muted-foreground">Painel de execução — nenhuma execução carregada</span>
  }

  if (workflow.status === "failed") {
    const failed = timeline.problems[0]
    return (
      <span className="flex min-w-0 items-center gap-2">
        <TbCircleX size={14} className="shrink-0 text-destructive" />
        <span className="shrink-0 font-medium text-destructive">Falhou</span>
        {workflow.durationMs != null && (
          <span className="shrink-0 text-muted-foreground">em {formatMs(workflow.durationMs)}</span>
        )}
        {failed && <span className="shrink-0 text-muted-foreground">no nó <span className="text-foreground">{failed.name}</span></span>}
        <span className="min-w-0 truncate text-muted-foreground/80">
          {failed?.problem?.message ?? workflow.error}
        </span>
      </span>
    )
  }

  if (workflow.status === "cancelled") {
    return (
      <span className="flex min-w-0 items-center gap-2">
        <TbPlayerStop size={14} className="shrink-0 text-amber-500" />
        <span className="shrink-0 font-medium">Cancelado</span>
        {workflow.durationMs != null && (
          <span className="shrink-0 text-muted-foreground">após {formatMs(workflow.durationMs)}</span>
        )}
        <span className="shrink-0 text-muted-foreground">· {counts.done} de {counts.total} nós concluídos</span>
      </span>
    )
  }

  if (workflow.status === "completed") {
    return (
      <span className="flex min-w-0 items-center gap-2">
        <TbCircleCheck size={14} className="shrink-0 text-emerald-500" />
        <span className="shrink-0 font-medium">Concluído</span>
        {workflow.durationMs != null && (
          <span className="shrink-0 text-muted-foreground">em {formatMs(workflow.durationMs)}</span>
        )}
        <span className="shrink-0 text-muted-foreground">· {counts.done} nós</span>
        {counts.unknown > 0 && (
          <span
            className="shrink-0 text-amber-600 dark:text-amber-400"
            title="Estes nós começaram e o aviso de término não chegou. O desfecho real está no Histórico."
          >
            · {counts.unknown} sem resposta
          </span>
        )}
        {slowest && (
          <span className="min-w-0 truncate text-muted-foreground">
            · mais lento: <span className="text-foreground/80">{slowest.name}</span> {formatMs(slowest.durationMs)}
          </span>
        )}
        {isHistorical && <span className="shrink-0 rounded bg-muted px-1.5 text-[10px] text-muted-foreground">histórico</span>}
      </span>
    )
  }

  // Em andamento
  // `unknown` conta como resolvido: o nó não está mais em execução, só não se
  // sabe como terminou. Fora daqui, a barra de um run já encerrado ficaria
  // eternamente abaixo de 100%.
  const finished = counts.done + counts.failed + counts.unknown
  const progress = counts.total > 0 ? (finished / counts.total) * 100 : 0
  const running = timeline.nodes.find(n => n.status === "running")

  return (
    <span className="flex min-w-0 items-center gap-2">
      <span className={cn(
        "h-1.5 w-1.5 shrink-0 rounded-full",
        wsLive ? "animate-pulse bg-emerald-500" : isExecuting ? "bg-amber-500" : "bg-muted-foreground/40",
      )} />
      <span className="shrink-0 font-medium">
        {wsLive ? "Executando" : isExecuting ? "Conectando" : "Desconectado"}
      </span>
      <span className="hidden h-1.5 w-28 shrink-0 overflow-hidden rounded-full bg-muted sm:block">
        <span className="block h-full rounded-full bg-primary transition-all" style={{ width: `${progress}%` }} />
      </span>
      <span className="shrink-0 tabular-nums text-muted-foreground">{finished}/{counts.total}</span>
      {startTs && <span className="shrink-0 text-muted-foreground"><Elapsed since={startTs} /></span>}
      {running && (
        <span className="min-w-0 truncate text-muted-foreground">
          · <span className="text-foreground/80">{running.name}</span>
        </span>
      )}
      {counts.failed > 0 && (
        <span className="shrink-0 text-destructive">✕ {counts.failed}</span>
      )}
    </span>
  )
}

export default RunPanel
