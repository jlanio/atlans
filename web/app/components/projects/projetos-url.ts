/**
 * Estado de Projetos na URL (docs/specs/projetos.md §3.6).
 *
 * Busca, chip e ordenação vivem na query string: F5, voltar do editor e um
 * link colado no chat reabrem a mesma estante. Os defaults não vão para a
 * URL, para ela ficar limpa quando nada foi tocado — mesmo padrão de
 * `observability/historico-url.ts`.
 */
export type Filtro =
  | "todos" | "ativos" | "inativos"
  | "executando" | "falha" | "agendados" | "webhook" | "subfluxos" | "portal"
  | "assistente"
  | "pausado" | "nunca"

/** Todos os filtros que a URL aceita. `pausado` e `nunca` não têm chip: chegam pela faixa de atenção. */
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

/** Lê a query string; qualquer valor inválido cai no default, sem quebrar a tela. */
export function lerEstado(sp: Leitor): EstadoDeProjetos {
  const filtroBruto = sp.get("filtro")
  const filtro = (FILTROS as string[]).includes(filtroBruto ?? "") ? (filtroBruto as Filtro) : ESTADO_PADRAO.filtro
  const ordemBruta = sp.get("ordem")
  const ordem = (ORDENS as string[]).includes(ordemBruta ?? "") ? (ordemBruta as Ordem) : ESTADO_PADRAO.ordem
  // Mesmo teto do Histórico: uma busca não é um documento, e um `q` gigante
  // colado na URL não pode custar um `normalize` por linha a cada tecla.
  const q = (sp.get("q") ?? "").trim().slice(0, 200)
  return { q, filtro, ordem }
}

/** Query string (sem "?") só com o que difere do default. */
export function escreverEstado(estado: EstadoDeProjetos): string {
  const sp = new URLSearchParams()
  if (estado.q.trim()) sp.set("q", estado.q.trim())
  if (estado.filtro !== ESTADO_PADRAO.filtro) sp.set("filtro", estado.filtro)
  if (estado.ordem !== ESTADO_PADRAO.ordem) sp.set("ordem", estado.ordem)
  return sp.toString()
}

/**
 * Quantos recortes estão ativos: busca e chip. A ordenação não recorta a
 * lista, então não conta — "Limpar filtros" não deve aparecer só porque a
 * pessoa ordenou por data.
 */
export function filtrosAtivos(estado: EstadoDeProjetos): number {
  return [estado.q.trim() || null, estado.filtro !== ESTADO_PADRAO.filtro ? estado.filtro : null]
    .filter(Boolean).length
}
