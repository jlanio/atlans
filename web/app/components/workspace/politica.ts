import type { IPolicyMember, IWorkspacePolicy, PolicyMode } from "@/service/types"

/**
 * Pure readings of a workspace's execution policy
 * (docs/specs/executor-isolation-routing.md).
 *
 * They live outside the components for two reasons: the active workspace's
 * panel, the row, the editor, the Run button's preflight and the move dialog
 * read the SAME policy and would say different things if each did its own
 * math; and everything here is testable without mounting any screen.
 *
 * Vocabulary (a single one, across the whole screen): modes "Compartilhado",
 * "Isolado" and "Dedicado + pool" (Shared, Isolated, Dedicated + pool); tiers
 * "principais" and "reserva" (primary, fallback); what happens when no one is
 * available is the "último recurso" (last resort). "Fallback" stays in the code.
 */

/** Short label for the mode — the vocabulary the user chose (spec §3.1). */
export function rotuloDoModo(mode: PolicyMode): string {
  switch (mode) {
    case "isolated":       return "Isolado"
    case "dedicated_pool": return "Dedicado + pool"
    default:               return "Compartilhado"
  }
}

/** The same label — fits in the row; kept for compatibility. */
export function rotuloCurtoDoModo(mode: PolicyMode): string {
  return rotuloDoModo(mode)
}

/** Mode badge colors: purple for those with a dedicated executor (the type's color), teal for the pool. */
export function classeDoModo(mode: PolicyMode): string {
  return mode === "pool"
    ? "border-teal-500/30 bg-teal-500/10 text-teal-700 dark:text-teal-400"
    : "border-purple-500/30 bg-purple-500/10 text-purple-700 dark:text-purple-400"
}

/** Executor status in pt-BR — the server speaks English. */
export function rotuloDoStatus(status: string): string {
  switch (status) {
    case "active":   return "ativo"
    case "pending":  return "pendente"
    case "inactive": return "inativo"
    case "revoked":  return "revogado"
    default:         return status
  }
}

/** The policy action that makes sense for the mode: a pool workspace has no policy to "edit" yet. */
export function rotuloDaAcaoDePolitica(mode: PolicyMode): string {
  return mode === "pool" ? "Restringir a executores dedicados" : "Editar política de execução"
}

/** "2 de 3 online", plus "· 1 sem sinal" (no signal) when there is unknown presence. */
export function contarOnline(online: number, total: number, semSinal = 0): string {
  const base = `${online} de ${total} online`
  return semSinal > 0 ? `${base} · ${semSinal} sem sinal` : base
}

/** Members whose presence the server could not read (Redis down / reconnecting). */
export function semSinal(membros: IPolicyMember[]): number {
  return membros.filter(m => m.online === null).length
}

/**
 * How many executors the effective chain has online right now: the tiers and,
 * when the policy allows it, the pool. `pool` comes back `null` from the server
 * precisely when it is not allowed (Isolated or floor), so summing what came
 * back is enough.
 */
export function disponiveisNaCadeia(p: IWorkspacePolicy): number {
  return p.available_primary + p.available_fallback + (p.pool?.available ?? 0)
}

/** Members that do not receive runs (pending/inactive/revoked) — the tier has dead weight. */
export function membrosInativos(p: IWorkspacePolicy): IPolicyMember[] {
  return [...p.primary, ...p.fallback].filter(m => m.status !== "active")
}

/**
 * The policy deserves the alert triangle: an inactive member, or no executor
 * in the chain online. The second condition only applies when the server
 * ROUTES by the policy — with the flag off the legacy path still falls back to
 * the pool, and warning "it will fail" would be lying.
 */
export function politicaEmAlerta(p: IWorkspacePolicy): boolean {
  if (p.mode === "pool") return false
  if (membrosInativos(p).length > 0) return true
  return p.policy_routing_enabled && disponiveisNaCadeia(p) === 0
}

/** Sentence for the active workspace's panel for a policy with a group or a fallback. */
export function descreverPolitica(p: IWorkspacePolicy): string {
  const partes = [`Principais ${contarOnline(p.available_primary, p.primary.length, semSinal(p.primary))}`]
  if (p.fallback.length > 0) {
    partes.push(`Reserva ${contarOnline(p.available_fallback, p.fallback.length, semSinal(p.fallback))}`)
  }
  partes.push(p.effective_terminal === "pool"
    ? "último recurso: pool"
    : "sem último recurso: a execução falha")
  return partes.join(" · ")
}

/** The pool's health spelled out, or `null` when the policy does not use it. */
export function saudeDoPool(p: IWorkspacePolicy): string | null {
  if (!p.pool) return null
  if (p.pool.total === 0) return "Nenhum executor compartilhado cadastrado"
  if (p.pool.available === 0) return "Nenhum executor do pool online agora"
  return `Pool compartilhado ${contarOnline(p.pool.available, p.pool.total)}`
}

/**
 * What happens to this workspace's runs when the dedicated executor goes down.
 * With the flag off, the legacy path ALWAYS overflows to the pool — that is
 * what holds today, whatever the configured policy.
 */
export function descreverQueda(p: IWorkspacePolicy | null | undefined): string {
  if (!p || !p.policy_routing_enabled || p.mode !== "isolated") return "se cair, o pool assume"
  return "se cair, a execução falha"
}

/**
 * Preflight warning for the Run button, or `null` when there is somewhere to dispatch to.
 *
 * Informational by design: the button never depends on it. It only claims
 * something about the policy's chain when the server routes by it; with the
 * flag off, the only certain shortfall is the pool's own. "Appears online" and
 * not "is": the presence read may lag behind what the dispatch will see.
 */
export function avisoDePreFlight(p: IWorkspacePolicy | null | undefined): string | null {
  if (!p) return null
  if (p.mode === "pool") {
    if (!p.pool) return null
    if (p.pool.total === 0) return "Nenhum executor compartilhado cadastrado: a execução não terá para onde ir."
    if (p.pool.available === 0) return "Nenhum executor do pool aparece online agora: a execução vai falhar sem despacho."
    return null
  }
  if (!p.policy_routing_enabled) return null
  if (disponiveisNaCadeia(p) > 0) return null
  return p.effective_terminal === "fail"
    ? "Nenhum executor da política aparece online e o workspace é isolado: a execução vai falhar sem despacho."
    : "Nenhum executor da política nem do pool aparece online agora: a execução vai falhar sem despacho."
}

/** Warning when moving a workflow between workspaces with different policies; `null` if equal or not read. */
export function avisoDeMudancaDePolitica(
  origem: IWorkspacePolicy | null | undefined,
  destino: IWorkspacePolicy | null | undefined,
): string | null {
  if (!origem || !destino || origem.mode === destino.mode) return null
  return `A política de execução muda de ${rotuloDoModo(origem.mode)} para ${rotuloDoModo(destino.mode)}: `
    + "o workflow passa a seguir a política do destino."
}

/** Capacity as the executor publishes it; `IExecutorCapacity` and `IPolicyMember.capacity` have the same shape. */
export type Capacidade = {
  queued?: number; running?: number; max_concurrent?: number; max_queue?: number
} | null | undefined

/** "1 de 4 em execução · 2 na fila" (1 of 4 running · 2 queued), or `null` when the executor has not published capacity. */
export function descreverCapacidade(c: Capacidade): string | null {
  if (!c || c.max_concurrent == null || c.running == null) return null
  const base = `${c.running} de ${c.max_concurrent} em execução`
  return c.queued && c.queued > 0 ? `${base} · ${c.queued} na fila` : base
}

/** Full = accepts nothing more right now: runs at the ceiling and queue at the ceiling (or no queue). */
export function capacidadeCheia(c: Capacidade): boolean {
  if (!c || c.max_concurrent == null || c.running == null) return false
  if (c.running < c.max_concurrent) return false
  return c.max_queue == null || (c.queued ?? 0) >= c.max_queue
}
