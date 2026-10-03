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
export const FILTROS: Filtro[] = [
  "todos", "ativos", "inativos",
  "executando", "falha", "agendados", "webhook", "subfluxos", "portal",
  "assistente",
  "pausado", "nunca",
]

export type Ordem = "nome" | "execucao" | "alterado"
export const ORDENS: Ordem[] = ["nome", "execucao", "alterado"]

export interface EstadoDeProjetos {
  q: string
  filtro: Filtro
  ordem: Ordem
}

export const ESTADO_PADRAO: EstadoDeProjetos = { q: "", filtro: "todos", ordem: "nome" }

type Leitor = { get(nome: string): string | null }

/** Reads the query string; any invalid value falls back to the default, without breaking the screen. */
export function lerEstado(sp: Leitor): EstadoDeProjetos {
  const filtroBruto = sp.get("filtro")
  const filtro = (FILTROS as string[]).includes(filtroBruto ?? "") ? (filtroBruto as Filtro) : ESTADO_PADRAO.filtro
  const ordemBruta = sp.get("ordem")
  const ordem = (ORDENS as string[]).includes(ordemBruta ?? "") ? (ordemBruta as Ordem) : ESTADO_PADRAO.ordem
  // Same ceiling as History: a search is not a document, and a giant `q`
  // pasted into the URL must not cost a `normalize` per row on every keystroke.
  const q = (sp.get("q") ?? "").trim().slice(0, 200)
  return { q, filtro, ordem }
}

/** Query string (without "?") with only what differs from the default. */
export function escreverEstado(estado: EstadoDeProjetos): string {
  const sp = new URLSearchParams()
  if (estado.q.trim()) sp.set("q", estado.q.trim())
  if (estado.filtro !== ESTADO_PADRAO.filtro) sp.set("filtro", estado.filtro)
  if (estado.ordem !== ESTADO_PADRAO.ordem) sp.set("ordem", estado.ordem)
  return sp.toString()
}

/**
 * How many slices are active: search and chip. Sorting does not slice the
 * list, so it does not count — "Limpar filtros" should not appear just because
 * the person sorted by date.
 */
export function filtrosAtivos(estado: EstadoDeProjetos): number {
  return [estado.q.trim() || null, estado.filtro !== ESTADO_PADRAO.filtro ? estado.filtro : null]
    .filter(Boolean).length
}
