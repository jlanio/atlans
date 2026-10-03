/**
 * Projects state in the URL (docs/specs/projects.md §3.6).
 *
 * Search, chip and sort live in the query string: F5, going back from the
 * editor and a link pasted in chat reopen the same shelf. The defaults do not
 * go into the URL, so it stays clean when nothing was touched — same pattern
 * as `observability/historico-url.ts`.
 */
export type Filtro =
  | "todos" | "ativos" | "inativos"
  | "executando" | "falha" | "agendados" | "webhook" | "subfluxos" | "portal"
  | "assistente"
  | "pausado" | "nunca"

/** All filters the URL accepts. `pausado` and `nunca` have no chip: they arrive through the attention strip. */
export const FILTERS: Filtro[] = [
  "todos", "ativos", "inativos",
  "executando", "falha", "agendados", "webhook", "subfluxos", "portal",
  "assistente",
  "pausado", "nunca",
]

export type Ordem = "nome" | "execucao" | "alterado"
export const SORT_ORDERS: Ordem[] = ["nome", "execucao", "alterado"]

export interface ProjectsState {
  q: string
  filtro: Filtro
  ordem: Ordem
}

export const DEFAULT_STATE: ProjectsState = { q: "", filtro: "todos", ordem: "nome" }

type Leitor = { get(nome: string): string | null }

/** Reads the query string; any invalid value falls back to the default, without breaking the screen. */
export function lerEstado(sp: Leitor): ProjectsState {
  const rawFilter = sp.get("filtro")
  const filtro = (FILTERS as string[]).includes(rawFilter ?? "") ? (rawFilter as Filtro) : DEFAULT_STATE.filtro
  const rawOrder = sp.get("ordem")
  const ordem = (SORT_ORDERS as string[]).includes(rawOrder ?? "") ? (rawOrder as Ordem) : DEFAULT_STATE.ordem
  // Same ceiling as History: a search is not a document, and a giant `q`
  // pasted into the URL must not cost a `normalize` per row on every keystroke.
  const q = (sp.get("q") ?? "").trim().slice(0, 200)
  return { q, filtro, ordem }
}

/** Query string (without "?") with only what differs from the default. */
export function escreverEstado(estado: ProjectsState): string {
  const sp = new URLSearchParams()
  if (estado.q.trim()) sp.set("q", estado.q.trim())
  if (estado.filtro !== DEFAULT_STATE.filtro) sp.set("filtro", estado.filtro)
  if (estado.ordem !== DEFAULT_STATE.ordem) sp.set("ordem", estado.ordem)
  return sp.toString()
}

/**
 * How many slices are active: search and chip. Sorting does not slice the
 * list, so it does not count — "Limpar filtros" should not appear just because
 * the person sorted by date.
 */
export function filtrosAtivos(estado: ProjectsState): number {
  return [estado.q.trim() || null, estado.filtro !== DEFAULT_STATE.filtro ? estado.filtro : null]
    .filter(Boolean).length
}
