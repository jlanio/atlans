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

import { PERIODS, type Period } from "../observability/historico-url"

export { PERIODS }
export type { Period }

export type ScopeState = "ativo" | "todos"

export const DEFAULT_SCOPE: ScopeState = "ativo"
/** The same default window as History (spec §3.1). */
export const DEFAULT_PERIOD: Period = 30

export interface DashboardState {
  escopo: ScopeState
  periodo: Period
}

type Leitor = { get(nome: string): string | null }

/** Only `escopo=todos` becomes "todos"; any other value (or absence) → "ativo". */
export function lerEscopo(sp: Leitor): ScopeState {
  return sp.get("escopo") === "todos" ? "todos" : DEFAULT_SCOPE
}

/** `periodo` is only valid as 7/30/90 (History's set); anything else (or absence) → 30. */
export function readPeriod(sp: Leitor): Period {
  const bruto = Number(sp.get("periodo"))
  return (PERIODS as number[]).includes(bruto) ? (bruto as Period) : DEFAULT_PERIOD
}

/** Reads both slices from the query string; an invalid value falls back to each one's default. */
export function lerEstado(sp: Leitor): DashboardState {
  return { escopo: lerEscopo(sp), periodo: readPeriod(sp) }
}

/** Query string (without "?") of both slices; omits each default so the URL stays clean. */
export function escreverEstado(estado: DashboardState): string {
  const sp = new URLSearchParams()
  if (estado.escopo !== DEFAULT_SCOPE) sp.set("escopo", estado.escopo)
  if (estado.periodo !== DEFAULT_PERIOD) sp.set("periodo", String(estado.periodo))
  return sp.toString()
}
