/**
 * History state in the URL (docs/specs/metrics-history.md §4.1).
 *
 * Everything that changes the screen lives in the query string: F5, going back
 * from the detail and a link pasted in chat reopen exactly the same view. The
 * defaults do not go into the URL, so it stays clean when nothing was touched.
 */
export type Period = 7 | 30 | 90
export const PERIODS: Period[] = [7, 30, 90]

export type ViewKind = "execucoes" | "workflows" | "executores" | "confirmacoes"
export const VIEWS: ViewKind[] = ["execucoes", "workflows", "executores", "confirmacoes"]

export type StatusFilter = "failed" | "running" | "success" | "cancelled"
const STATUS: StatusFilter[] = ["failed", "running", "success", "cancelled"]

export type SourceFilter = "manual" | "retry" | "webhook" | "schedule" | "mcp"
/** Origins the URL accepts. The UI list (`filtros.tsx`) has the same
 *  set in another order — a test guarantees they do not diverge. */
export const ORIGENS: SourceFilter[] = ["manual", "retry", "webhook", "schedule", "mcp"]

export interface HistoryState {
  periodo: Period
  visao: ViewKind
  status: StatusFilter | null
  workspace: string | null
  workflow: string | null
  executor: string | null
  origem: SourceFilter | null
  /**
   * "Assistente" chip: only runs of workflows CREATED by the assistant. It is
   * not called `origem` because that name already belongs to the trigger
   * (`trigger_source`) — they are two axes, and the screen lets you combine them.
   */
  assistente: boolean
  q: string
  /** run_id of the run open in the side panel. */
  execucao: string | null
}

export const DEFAULT_STATE: HistoryState = {
  periodo: 30,
  visao: "execucoes",
  status: null,
  workspace: null,
  workflow: null,
  executor: null,
  origem: null,
  assistente: false,
  q: "",
  execucao: null,
}

type Leitor = { get(nome: string): string | null }

function texto(sp: Leitor, nome: string): string | null {
  const v = sp.get(nome)
  if (v == null) return null
  const limpo = v.trim()
  return limpo === "" ? null : limpo.slice(0, 200)
}

/** Reads the query string; any invalid value falls back to the default. */
export function lerEstado(sp: Leitor): HistoryState {
  const rawPeriod = Number(sp.get("periodo"))
  const periodo = (PERIODS as number[]).includes(rawPeriod) ? (rawPeriod as Period) : DEFAULT_STATE.periodo
  const rawView = sp.get("visao")
  const visao = (VIEWS as string[]).includes(rawView ?? "") ? (rawView as ViewKind) : DEFAULT_STATE.visao
  const rawStatus = sp.get("status")
  const status = (STATUS as string[]).includes(rawStatus ?? "") ? (rawStatus as StatusFilter) : null
  const rawSource = sp.get("origem")
  const origem = (ORIGENS as string[]).includes(rawSource ?? "") ? (rawSource as SourceFilter) : null
  return {
    periodo,
    visao,
    status,
    workspace: texto(sp, "workspace"),
    workflow: texto(sp, "workflow"),
    executor: texto(sp, "executor"),
    origem,
    assistente: sp.get("assistente") === "1",
    q: texto(sp, "q") ?? "",
    execucao: texto(sp, "execucao"),
  }
}

/** Query string (without "?") with only what differs from the default. */
export function escreverEstado(estado: HistoryState): string {
  const sp = new URLSearchParams()
  if (estado.periodo !== DEFAULT_STATE.periodo) sp.set("periodo", String(estado.periodo))
  if (estado.visao !== DEFAULT_STATE.visao) sp.set("visao", estado.visao)
  if (estado.status) sp.set("status", estado.status)
  if (estado.workspace) sp.set("workspace", estado.workspace)
  if (estado.workflow) sp.set("workflow", estado.workflow)
  if (estado.executor) sp.set("executor", estado.executor)
  if (estado.origem) sp.set("origem", estado.origem)
  if (estado.assistente) sp.set("assistente", "1")
  if (estado.q.trim()) sp.set("q", estado.q.trim())
  if (estado.execucao) sp.set("execucao", estado.execucao)
  return sp.toString()
}

/** How many filters (apart from period, view and open run) are active. */
export function filtrosAtivos(estado: HistoryState): number {
  return [
    estado.status, estado.workspace, estado.workflow, estado.executor, estado.origem,
    estado.assistente || null, estado.q.trim() || null,
  ].filter(Boolean).length
}

/** ISO date (UTC) of the window start, for the `date_from` of `/runs`. */
export function windowStart(periodo: Period, agora: Date = new Date()): string {
  return new Date(agora.getTime() - periodo * 24 * 60 * 60 * 1000).toISOString()
}
