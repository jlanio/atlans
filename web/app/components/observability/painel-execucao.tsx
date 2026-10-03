"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import {
  TbAlertTriangle, TbCopy, TbExternalLink, TbFileText, TbHierarchy3, TbPlayerPlay,
} from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/app/components/ui/sheet"
import { Skeleton } from "@/app/components/ui/skeleton"
import { StatusBadge } from "@/app/components/shared/StatusBadge"
import { rotuloDoStatus } from "@/app/components/shared/status-rotulos"
import { GisFlowService } from "@/service/GisFlowService"
import type { IRunDetail, IRunEvent } from "@/service/types"
import { createToast } from "@/utils/createToast"
import { formatDuration } from "@/utils/formatters"
import { formatLocal } from "@/lib/dayjs"
import { cn } from "@/lib/utils"
import { formatarDuracao, rotuloDaCategoria, rotuloDaOrigem, rotuloDoNivel } from "@/lib/formatos"

interface Props {
  /** Nulo fecha o painel. */
  runId: string | null
  onFechar: () => void
  /** "Ver todas deste workflow" (see all for this workflow): filters the table behind the panel. */
  onFiltrarWorkflow?: (workflowHash: string) => void
}

type NoDaExecucao = IRunDetail["node_stats"][string] & { id: string }

/** The badge row describes the panel; before the detail arrives there is no description. */
const ID_DA_DESCRICAO = "painel-execucao-descricao"

/** Nodes sorted as on the run page: the slowest first. */
export function nosDaExecucao(run: IRunDetail | null): NoDaExecucao[] {
  if (!run?.node_stats) return []
  return Object.entries(run.node_stats)
    .filter(([k]) => !k.startsWith("__"))
    .map(([id, n]) => ({ id, ...n }))
    .sort((a, b) => b.duration_ms - a.duration_ms)
}

/**
 * Below 1 s the ms precision matters ("123ms"); above it, the same scale as the
 * rest of the page ("1 min 57 s"), instead of "117.26s".
 */
function duracaoDoNo(ms: number | null | undefined): string {
  if (ms == null) return "—"
  if (ms < 1000) return formatDuration(ms) ?? "—"
  return formatarDuracao(ms / 1000)
}

/**
 * EVENT status (what happened to a node), which is not the run-status
 * vocabulary of `StatusBadge`: "started" is "iniciou", not "Na fila" (queued).
 */
const ACAO_DO_EVENTO: Record<string, string> = {
  started: "iniciou", running: "em andamento", completed: "concluiu", success: "concluiu",
  failed: "falhou", error: "falhou", cancelled: "cancelado", skipped: "pulado", cached: "cache",
}

/**
 * Log line spelled out: node name (not the id), what happened in Portuguese
 * and the error. `kind` is lifecycle/stdout/debug; what matters is in
 * `status`.
 */
export function descreverEvento(ev: IRunEvent, run: IRunDetail | null): string {
  const nome = (ev.node && run?.node_stats?.[ev.node]?.node_name) || ev.node || null
  const acao = ev.kind === "stdout" ? "saída"
    : ev.kind === "debug" ? "depuração"
    : ev.status ? (ACAO_DO_EVENTO[ev.status] ?? null)
    : null   // an unknown `kind` or `status` does not become raw text on screen
  return [nome, acao, ev.error].filter(Boolean).join(" · ")
}

/** The event `timestamp` comes in seconds (epoch); tolerates ms to be safe. */
function horaDoEvento(ts: number | undefined): string {
  if (ts == null) return "—"
  const ms = ts > 1e12 ? ts : ts * 1000
  return formatLocal(new Date(ms).toISOString(), "HH:mm:ss")
}

/**
 * Side panel of a run (spec §4.3): everything that does not fit in the table
 * row — the whole error, nodes, why it ran where it ran — without leaving the
 * list. The `/observability/run/{id}` page still exists, as "Abrir em página".
 */
export function PainelExecucao({ runId, onFechar, onFiltrarWorkflow }: Props) {
  const [run, setRun] = useState<IRunDetail | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  // The 403 from "Executar de novo" (run again) applies to the whole workflow:
  // after it the button disappears instead of promising again what the API
  // already denied.
  const [podeReexecutar, setPodeReexecutar] = useState(true)
  const [confirmandoRetry, setConfirmandoRetry] = useState(false)
  const [reexecutando, setReexecutando] = useState(false)
  const [log, setLog] = useState<{ eventos: IRunEvent[]; expirado: boolean } | null>(null)
  const [carregandoLog, setCarregandoLog] = useState(false)
  // Opening another run before the previous one responds: the slow response
  // must not paint the new one's panel.
  const seq = useRef(0)

  useEffect(() => {
    setRun(null)
    setErro(null)
    setLog(null)
    setPodeReexecutar(true)
    setConfirmandoRetry(false)
    if (!runId) return
    const meu = ++seq.current
    setCarregando(true)
    GisFlowService.getRunDetail(runId).then(res => {
      if (meu !== seq.current) return
      setCarregando(false)
      if (res?.data) setRun(res.data)
      else setErro(res?.error?.message ?? "Não foi possível carregar esta execução.")
    })
  }, [runId])

  async function reexecutar() {
    if (!run) return
    setReexecutando(true)
    const res = await GisFlowService.retryRun(run.workflow_hash, run.run_id)
    setReexecutando(false)
    setConfirmandoRetry(false)
    if (res?.data) {
      createToast.success("Execução enviada", "Uma nova execução do workflow entrou na fila.")
      return
    }
    if (res?.status === 403) setPodeReexecutar(false)
    createToast.error("Não foi possível executar de novo", res?.error?.message)
  }

  async function verLog() {
    if (!run) return
    setCarregandoLog(true)
    const res = await GisFlowService.getRunEvents(run.run_id)
    setCarregandoLog(false)
    if (!res?.data) {
      createToast.error("Não foi possível carregar o log", res?.error?.message)
      return
    }
    setLog({ eventos: res.data.events ?? [], expirado: !!res.data.expired })
  }

  async function copiarId() {
    if (!run) return
    try {
      await navigator.clipboard.writeText(run.run_id)
      createToast.success("ID copiado", run.run_id)
    } catch {
      createToast.error("Não foi possível copiar", "Copie o ID do cabeçalho do painel.")
    }
  }

  // Recomputing the node list on every render (entries/filter/map/sort) is
  // wasteful when `run` has not changed.
  const nos = useMemo(() => nosDaExecucao(run), [run])
  const nivel = rotuloDoNivel(run?.dispatch_tier)
  const origem = rotuloDaOrigem(run?.trigger_source)
  const categoria = rotuloDaCategoria(run?.error_category)
  const nome = run?.workflow_name ?? "Execução"

  return (
    <Sheet open={!!runId} onOpenChange={aberto => { if (!aberto) onFechar() }}>
      <SheetContent
        side="right"
        resizable={{ storageKey: "atlas_run_sheet_width", defaultWidth: 520, minWidth: 420, maxWidth: 1200 }}
        className="flex w-full flex-col gap-0 p-0"
        // No description while loading: Radix warns in the console when
        // `aria-describedby` points to nothing.
        aria-describedby={run ? ID_DA_DESCRICAO : undefined}
      >
        <SheetHeader className="shrink-0 border-b pr-12">
          <p className="font-mono text-[10.5px] font-semibold tracking-[0.1em] text-muted-foreground uppercase">
            Execução · <span className="normal-case tracking-normal select-all">{runId}</span>
          </p>
          <SheetTitle className="text-lg leading-tight">{carregando && !run ? "Carregando…" : nome}</SheetTitle>
          {run && (
            <SheetDescription asChild id={ID_DA_DESCRICAO}>
              <div className="flex flex-wrap items-center gap-1.5 text-xs">
                <StatusBadge status={run.status} />
                {run.retry_count > 0 && <Selo>{run.retry_count + 1}ª tentativa</Selo>}
                {nivel && <Selo tom={nivel === "reserva" ? "roxo" : "teal"} title={nivel === "reserva" ? "Rodou num executor de reserva da política" : "Rodou no pool compartilhado"}>rodou na {nivel === "reserva" ? "reserva" : "pool"}</Selo>}
                {origem && <Selo>{origem}</Selo>}
                {run.triggered_by_username && <Selo>disparada por {run.triggered_by_username}</Selo>}
                {onFiltrarWorkflow && (
                  <button
                    type="button"
                    onClick={() => onFiltrarWorkflow(run.workflow_hash)}
                    className="ml-auto text-xs font-medium text-primary hover:underline"
                  >
                    Ver todas deste workflow
                  </button>
                )}
              </div>
            </SheetDescription>
          )}
        </SheetHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto p-4">
          {erro && (
            <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{erro}</p>
          )}

          {carregando && !run && (
            <div className="flex flex-col gap-4" aria-busy="true" aria-label="Carregando execução">
              <div className="grid grid-cols-2 gap-3">
                {[0, 1, 2, 3].map(i => <div key={i} className="flex flex-col gap-1.5"><Skeleton className="h-3 w-16" /><Skeleton className="h-4 w-32" /></div>)}
              </div>
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          )}

          {run && (
            <>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-[12.5px]">
                <Fato rotulo="Início">{formatLocal(run.started_at, "DD/MM/YYYY HH:mm:ss")}</Fato>
                <Fato rotulo="Duração">
                  {formatarDuracao(run.duration_seconds)}
                  {run.typical_seconds != null && (
                    <span className="text-muted-foreground"> · típica {formatarDuracao(run.typical_seconds)}</span>
                  )}
                </Fato>
                <Fato rotulo="Executor">
                  {run.executor_name ?? run.agent_host ?? <span className="text-muted-foreground">—</span>}
                  {nivel && <span className="text-muted-foreground"> · {nivel}</span>}
                </Fato>
                <Fato rotulo="Workspace">{run.workspace_name ?? <span className="text-muted-foreground">—</span>}</Fato>
                {categoria && <Fato rotulo="Categoria do erro">{categoria}</Fato>}
                {run.owner_username && <Fato rotulo="Dono do workflow">{run.owner_username}</Fato>}
              </dl>

              {run.error_message && (
                <section aria-labelledby="painel-erro">
                  <h3 id="painel-erro" className="mb-1.5 flex items-center gap-1.5 text-[10.5px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
                    <TbAlertTriangle size={12} aria-hidden="true" /> Erro{categoria && <span className="normal-case tracking-normal">· {categoria}</span>}
                  </h3>
                  <pre className="max-h-64 overflow-auto rounded-md border border-red-500/30 bg-red-50 px-3 py-2 font-mono text-[11.5px] leading-relaxed break-words whitespace-pre-wrap text-red-700 dark:bg-red-500/10 dark:text-red-300">
                    {run.error_message}
                  </pre>
                </section>
              )}

              <section aria-labelledby="painel-nos">
                <h3 id="painel-nos" className="mb-1.5 flex items-center gap-1.5 text-[10.5px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
                  <TbHierarchy3 size={12} aria-hidden="true" /> Nós{nos.length > 0 && <span className="normal-case tracking-normal">· {nos.length} executados</span>}
                </h3>
                {nos.length === 0 ? (
                  <p className="text-xs text-muted-foreground">Nenhum nó registrado para esta execução.</p>
                ) : (
                  <ul className="flex flex-col overflow-hidden rounded-md border">
                    {nos.map(no => {
                      const falhou = no.status === "failed" || no.status === "error"
                      const ok = no.status === "success" || no.status === "cached"
                      return (
                        <li key={no.id} className="grid grid-cols-[14px_minmax(0,1fr)_auto] items-center gap-2 border-t px-2.5 py-1.5 text-[12.5px] first:border-t-0">
                          <span
                            aria-hidden="true"
                            className={cn("size-[7px] rounded-full", falhou ? "bg-red-500" : ok ? "bg-green-500" : no.status === "running" ? "bg-blue-500" : "bg-muted-foreground/40")}
                          />
                          <div className="flex min-w-0 flex-col">
                            <span className="truncate" title={no.node_name || no.id}>{no.node_name || no.id}</span>
                            {falhou && no.error && (
                              <span className="truncate text-[11.5px] text-red-600 dark:text-red-400" title={no.error}>{no.error}</span>
                            )}
                          </div>
                          <span className={cn("text-xs tabular-nums", falhou ? "text-red-600 dark:text-red-400" : "text-muted-foreground")}>
                            {duracaoDoNo(no.duration_ms)}
                            {falhou ? " · falhou" : !ok && no.status ? ` · ${rotuloDoStatus(no.status).toLowerCase()}` : ""}
                            {no.cache_hit && <span className="text-purple-600 dark:text-purple-400"> · cache</span>}
                          </span>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </section>

              {log && (
                <section aria-labelledby="painel-log">
                  <h3 id="painel-log" className="mb-1.5 flex items-center gap-1.5 text-[10.5px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
                    <TbFileText size={12} aria-hidden="true" /> Log
                  </h3>
                  {log.expirado || log.eventos.length === 0 ? (
                    <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
                      O log expirou — os eventos ficam guardados por 1 hora depois da execução.
                    </p>
                  ) : (
                    <ol className="max-h-72 overflow-auto rounded-md border font-mono text-[11px] leading-relaxed">
                      {log.eventos.map((ev, i) => (
                        <li key={i} className={cn("flex gap-2 border-t px-2.5 py-1 first:border-t-0", (ev.level === "error" || ev.status === "failed") && "text-red-600 dark:text-red-400")}>
                          <span className="shrink-0 text-muted-foreground">{horaDoEvento(ev.timestamp)}</span>
                          <span className="min-w-0 flex-1 break-words">
                            {descreverEvento(ev, run)}
                            {ev.duration_ms != null && <span className="text-muted-foreground"> ({formatDuration(ev.duration_ms)})</span>}
                          </span>
                        </li>
                      ))}
                    </ol>
                  )}
                </section>
              )}
            </>
          )}
        </div>

        {run && (
          <div className="flex shrink-0 flex-wrap gap-2 border-t p-4">
            {podeReexecutar && (
              <Button size="sm" onClick={() => setConfirmandoRetry(true)} className="max-md:h-10">
                <TbPlayerPlay size={14} aria-hidden="true" /> Executar de novo
              </Button>
            )}
            <Button size="sm" variant="outline" asChild className="max-md:h-10">
              <Link href={`/workflow/${run.workflow_hash}`}>Abrir workflow</Link>
            </Button>
            {!log && (
              <Button size="sm" variant="outline" onClick={verLog} disabled={carregandoLog} className="max-md:h-10">
                <TbFileText size={14} aria-hidden="true" /> {carregandoLog ? "Carregando…" : "Ver log"}
              </Button>
            )}
            <Button size="sm" variant="ghost" asChild className="max-md:h-10">
              <Link href={`/observability/run/${run.run_id}`}><TbExternalLink size={14} aria-hidden="true" /> Abrir em página</Link>
            </Button>
            <Button size="sm" variant="ghost" onClick={copiarId} className="max-md:h-10">
              <TbCopy size={14} aria-hidden="true" /> Copiar ID
            </Button>
          </div>
        )}

        <Dialog open={confirmandoRetry} onOpenChange={aberto => { if (!aberto && !reexecutando) setConfirmandoRetry(false) }}>
          <DialogContent closeDisabled={reexecutando}>
            <DialogHeader>
              <DialogTitle>Executar «{nome}» de novo?</DialogTitle>
              <DialogDescription>
                Dispara uma execução nova com a definição atual do workflow — não repete as entradas desta.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmandoRetry(false)} disabled={reexecutando}>Cancelar</Button>
              <Button onClick={reexecutar} disabled={reexecutando}>{reexecutando ? "Enviando…" : "Executar"}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </SheetContent>
    </Sheet>
  )
}

function Fato({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <dt className="text-[10.5px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">{rotulo}</dt>
      <dd className="truncate">{children}</dd>
    </div>
  )
}

function Selo({ children, tom, title }: { children: React.ReactNode; tom?: "roxo" | "teal"; title?: string }) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex h-[22px] items-center rounded-full border px-2 text-[11.5px] font-medium whitespace-nowrap",
        tom === "roxo" && "border-transparent bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400",
        tom === "teal" && "border-transparent bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-400",
        !tom && "border-border bg-card text-muted-foreground",
      )}
    >
      {children}
    </span>
  )
}
