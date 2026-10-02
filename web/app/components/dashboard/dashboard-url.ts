/**
 * Estado do Dashboard na URL (docs/specs/dashboard.md §1 e §3.9).
 *
 * Dois recortes vivem na query string, para que F5, o botão voltar e um link
 * colado reabram a mesma visão — mesmo padrão de `observability/historico-url.ts`
 * e `projects/projetos-url.ts`:
 *   - o ESCOPO: o painel é do workspace ATIVO por padrão; "Todos os workspaces"
 *     troca (`?escopo=todos`);
 *   - o PERÍODO: a janela dos indicadores/gráfico e das falhas em "Precisa de
 *     atenção" — 7, 30 (padrão) ou 90 dias (`?periodo=`), o mesmo conjunto do
 *     Histórico, de onde o tipo é reusado.
 * Os defaults não vão para a URL, para ela ficar limpa quando nada foi tocado.
 */

import { PERIODOS, type Periodo } from "../observability/historico-url"

export { PERIODOS }
export type { Periodo }

export type EstadoDoEscopo = "ativo" | "todos"

export const ESCOPO_PADRAO: EstadoDoEscopo = "ativo"
/** A mesma janela padrão do Histórico (spec §3.1). */
export const PERIODO_PADRAO: Periodo = 30

export interface EstadoDoDashboard {
  escopo: EstadoDoEscopo
  periodo: Periodo
}

type Leitor = { get(nome: string): string | null }

/** Só `escopo=todos` vira "todos"; qualquer outro valor (ou ausência) → "ativo". */
export function lerEscopo(sp: Leitor): EstadoDoEscopo {
  return sp.get("escopo") === "todos" ? "todos" : ESCOPO_PADRAO
}

/** `periodo` só vale 7/30/90 (o conjunto do Histórico); qualquer outro (ou ausência) → 30. */
export function lerPeriodo(sp: Leitor): Periodo {
  const bruto = Number(sp.get("periodo"))
  return (PERIODOS as number[]).includes(bruto) ? (bruto as Periodo) : PERIODO_PADRAO
}

/** Lê os dois recortes da query string; valor inválido cai no default de cada um. */
export function lerEstado(sp: Leitor): EstadoDoDashboard {
  return { escopo: lerEscopo(sp), periodo: lerPeriodo(sp) }
}

/** Query string (sem "?") dos dois recortes; omite cada default para a URL ficar limpa. */
export function escreverEstado(estado: EstadoDoDashboard): string {
  const sp = new URLSearchParams()
  if (estado.escopo !== ESCOPO_PADRAO) sp.set("escopo", estado.escopo)
  if (estado.periodo !== PERIODO_PADRAO) sp.set("periodo", String(estado.periodo))
  return sp.toString()
}
