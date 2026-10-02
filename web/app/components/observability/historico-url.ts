/**
 * Estado do Histórico na URL (docs/specs/historico-metricas.md §4.1).
 *
 * Tudo o que muda a tela vive na query string: F5, voltar do detalhe e um
 * link colado no chat reabrem exatamente a mesma visão. Os defaults não vão
 * para a URL, para ela ficar limpa quando nada foi tocado.
 */
export type Periodo = 7 | 30 | 90
export const PERIODOS: Periodo[] = [7, 30, 90]

export type Visao = "execucoes" | "workflows" | "executores" | "confirmacoes"
export const VISOES: Visao[] = ["execucoes", "workflows", "executores", "confirmacoes"]

export type StatusFiltro = "failed" | "running" | "success" | "cancelled"
const STATUS: StatusFiltro[] = ["failed", "running", "success", "cancelled"]

export type OrigemFiltro = "manual" | "retry" | "webhook" | "schedule" | "mcp"
/** Origens que a URL aceita. A lista de UI (`filtros.tsx`) tem a mesma
 *  composição em outra ordem — um teste garante que não divergem. */
export const ORIGENS: OrigemFiltro[] = ["manual", "retry", "webhook", "schedule", "mcp"]

export interface EstadoDoHistorico {
  periodo: Periodo
  visao: Visao
  status: StatusFiltro | null
  workspace: string | null
  workflow: string | null
  executor: string | null
  origem: OrigemFiltro | null
  /**
   * Chip "Assistente": só execuções de fluxos CRIADOS pelo assistente. Não se
   * chama `origem` porque esse nome já é do disparo (`trigger_source`) — são
   * dois eixos, e a tela deixa combiná-los.
   */
  assistente: boolean
  q: string
  /** run_id da execução aberta no painel lateral. */
  execucao: string | null
}

export const ESTADO_PADRAO: EstadoDoHistorico = {
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

/** Lê a query string; qualquer valor inválido cai no default. */
export function lerEstado(sp: Leitor): EstadoDoHistorico {
  const periodoBruto = Number(sp.get("periodo"))
  const periodo = (PERIODOS as number[]).includes(periodoBruto) ? (periodoBruto as Periodo) : ESTADO_PADRAO.periodo
  const visaoBruta = sp.get("visao")
  const visao = (VISOES as string[]).includes(visaoBruta ?? "") ? (visaoBruta as Visao) : ESTADO_PADRAO.visao
  const statusBruto = sp.get("status")
  const status = (STATUS as string[]).includes(statusBruto ?? "") ? (statusBruto as StatusFiltro) : null
  const origemBruta = sp.get("origem")
  const origem = (ORIGENS as string[]).includes(origemBruta ?? "") ? (origemBruta as OrigemFiltro) : null
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

/** Query string (sem "?") só com o que difere do default. */
export function escreverEstado(estado: EstadoDoHistorico): string {
  const sp = new URLSearchParams()
  if (estado.periodo !== ESTADO_PADRAO.periodo) sp.set("periodo", String(estado.periodo))
  if (estado.visao !== ESTADO_PADRAO.visao) sp.set("visao", estado.visao)
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

/** Quantos filtros (fora período, visão e execução aberta) estão ativos. */
export function filtrosAtivos(estado: EstadoDoHistorico): number {
  return [
    estado.status, estado.workspace, estado.workflow, estado.executor, estado.origem,
    estado.assistente || null, estado.q.trim() || null,
  ].filter(Boolean).length
}

/** Data ISO (UTC) do início da janela, para `date_from` de `/runs`. */
export function inicioDaJanela(periodo: Periodo, agora: Date = new Date()): string {
  return new Date(agora.getTime() - periodo * 24 * 60 * 60 * 1000).toISOString()
}
