/**
 * Dashboard state in the URL (docs/specs/dashboard.md §1 and §3.9).
 *
 * Two slices live in the query string, so that F5, the back button and a
 * pasted link reopen the same view — same pattern as `observability/historico-url.ts`
 * and `projects/projetos-url.ts`:
 *   - the SCOPE: the dashboard is for the ACTIVE workspace by default; "Todos os
 *     workspaces" (all workspaces) switches it (`?escopo=todos`);
 *   - the PERIOD: the window of the indicators/chart and of the failures in
 *     "Precisa de atenção" — 7, 30 (default) or 90 days (`?periodo=`), the same
 *     set as History, whose type is reused.
 * Defaults don't go into the URL, so it stays clean when nothing was touched.
 */

import { PERIODOS, type Periodo } from "../observability/historico-url"

export { PERIODOS }
export type { Periodo }

export type EstadoDoEscopo = "ativo" | "todos"

export const ESCOPO_PADRAO: EstadoDoEscopo = "ativo"
/** The same default window as History (spec §3.1). */
export const PERIODO_PADRAO: Periodo = 30

export interface EstadoDoDashboard {
  escopo: EstadoDoEscopo
  periodo: Periodo
}

type Leitor = { get(nome: string): string | null }

/** Only `escopo=todos` becomes "todos"; any other value (or absence) → "ativo". */
export function lerEscopo(sp: Leitor): EstadoDoEscopo {
  return sp.get("escopo") === "todos" ? "todos" : ESCOPO_PADRAO
}

/** `periodo` is only valid as 7/30/90 (History's set); anything else (or absence) → 30. */
export function lerPeriodo(sp: Leitor): Periodo {
  const bruto = Number(sp.get("periodo"))
  return (PERIODOS as number[]).includes(bruto) ? (bruto as Periodo) : PERIODO_PADRAO
}

/** Reads both slices from the query string; an invalid value falls back to each one's default. */
export function lerEstado(sp: Leitor): EstadoDoDashboard {
  return { escopo: lerEscopo(sp), periodo: lerPeriodo(sp) }
}

/** Query string (without "?") of both slices; omits each default so the URL stays clean. */
export function escreverEstado(estado: EstadoDoDashboard): string {
  const sp = new URLSearchParams()
  if (estado.escopo !== ESCOPO_PADRAO) sp.set("escopo", estado.escopo)
  if (estado.periodo !== PERIODO_PADRAO) sp.set("periodo", String(estado.periodo))
  return sp.toString()
}
