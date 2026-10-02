import type { IPolicyMember, IWorkspacePolicy, PolicyMode } from "@/service/types"

/**
 * Leituras puras da política de execução de um workspace
 * (docs/specs/executor-isolation-routing.md).
 *
 * Vivem fora dos componentes por dois motivos: o painel do ativo, a fileira, o
 * editor, o pré-voo do botão Executar e o diálogo de mover leem a MESMA
 * política e diriam coisas diferentes se cada um fizesse a própria conta; e
 * tudo aqui é testável sem montar tela nenhuma.
 *
 * Vocabulário (um só, em toda a tela): modos "Compartilhado", "Isolado" e
 * "Dedicado + pool"; níveis "principais" e "reserva"; o que acontece quando
 * ninguém está disponível é o "último recurso". "Fallback" fica no código.
 */

/** Rótulo curto do modo — o vocabulário que o usuário escolheu (spec §3.1). */
export function rotuloDoModo(mode: PolicyMode): string {
  switch (mode) {
    case "isolated":       return "Isolado"
    case "dedicated_pool": return "Dedicado + pool"
    default:               return "Compartilhado"
  }
}

/** O mesmo rótulo — cabe na fileira; mantido por compatibilidade. */
export function rotuloCurtoDoModo(mode: PolicyMode): string {
  return rotuloDoModo(mode)
}

/** Cores do selo do modo: roxo para quem tem dedicado (a cor do tipo), teal para o pool. */
export function classeDoModo(mode: PolicyMode): string {
  return mode === "pool"
    ? "border-teal-500/30 bg-teal-500/10 text-teal-700 dark:text-teal-400"
    : "border-purple-500/30 bg-purple-500/10 text-purple-700 dark:text-purple-400"
}

/** Status do executor em pt-BR — o servidor fala inglês. */
export function rotuloDoStatus(status: string): string {
  switch (status) {
    case "active":   return "ativo"
    case "pending":  return "pendente"
    case "inactive": return "inativo"
    case "revoked":  return "revogado"
    default:         return status
  }
}

/** A ação de política que faz sentido para o modo: quem é pool ainda não tem política para "editar". */
export function rotuloDaAcaoDePolitica(mode: PolicyMode): string {
  return mode === "pool" ? "Restringir a executores dedicados" : "Editar política de execução"
}

/** "2 de 3 online", mais "· 1 sem sinal" quando há presença desconhecida. */
export function contarOnline(online: number, total: number, semSinal = 0): string {
  const base = `${online} de ${total} online`
  return semSinal > 0 ? `${base} · ${semSinal} sem sinal` : base
}

/** Membros cuja presença o servidor não conseguiu ler (Redis fora / reconectando). */
export function semSinal(membros: IPolicyMember[]): number {
  return membros.filter(m => m.online === null).length
}

/**
 * Quantos executores a cadeia efetiva tem online agora: os níveis e, quando a
 * política permite, o pool. `pool` vem `null` do servidor justamente quando
 * ele não é permitido (Isolado ou piso), então basta somar o que veio.
 */
export function disponiveisNaCadeia(p: IWorkspacePolicy): number {
  return p.available_primary + p.available_fallback + (p.pool?.available ?? 0)
}

/** Membros que não recebem execuções (pending/inactive/revoked) — o nível tem um peso morto. */
export function membrosInativos(p: IWorkspacePolicy): IPolicyMember[] {
  return [...p.primary, ...p.fallback].filter(m => m.status !== "active")
}

/**
 * A política merece o triângulo de alerta: um membro inativo, ou nenhum
 * executor da cadeia online. A segunda condição só vale quando o servidor
 * ROTEIA pela política — com a flag desligada o legado ainda cai no pool, e
 * alertar "vai falhar" seria mentir.
 */
export function politicaEmAlerta(p: IWorkspacePolicy): boolean {
  if (p.mode === "pool") return false
  if (membrosInativos(p).length > 0) return true
  return p.policy_routing_enabled && disponiveisNaCadeia(p) === 0
}

/** Frase do painel do ativo para uma política com grupo ou reserva. */
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

/** Saúde do pool por extenso, ou `null` quando a política não o usa. */
export function saudeDoPool(p: IWorkspacePolicy): string | null {
  if (!p.pool) return null
  if (p.pool.total === 0) return "Nenhum executor compartilhado cadastrado"
  if (p.pool.available === 0) return "Nenhum executor do pool online agora"
  return `Pool compartilhado ${contarOnline(p.pool.available, p.pool.total)}`
}

/**
 * O que acontece com as execuções deste workspace quando o dedicado cai.
 * Com a flag desligada, o legado SEMPRE transborda para o pool — é isso que
 * vale hoje, seja qual for a política configurada.
 */
export function descreverQueda(p: IWorkspacePolicy | null | undefined): string {
  if (!p || !p.policy_routing_enabled || p.mode !== "isolated") return "se cair, o pool assume"
  return "se cair, a execução falha"
}

/**
 * Aviso de pré-voo do botão Executar, ou `null` quando há para onde despachar.
 *
 * Informativo por desenho: o botão nunca depende dele. Só afirma algo sobre a
 * cadeia da política quando o servidor roteia por ela; com a flag desligada, a
 * única falta certa é a do próprio pool. "Aparece online" e não "está": a
 * presença lida pode estar defasada em relação ao que o dispatch verá.
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

/** Aviso ao mover um workflow entre workspaces de políticas diferentes; `null` se iguais ou não lidas. */
export function avisoDeMudancaDePolitica(
  origem: IWorkspacePolicy | null | undefined,
  destino: IWorkspacePolicy | null | undefined,
): string | null {
  if (!origem || !destino || origem.mode === destino.mode) return null
  return `A política de execução muda de ${rotuloDoModo(origem.mode)} para ${rotuloDoModo(destino.mode)}: `
    + "o workflow passa a seguir a política do destino."
}

/** Capacidade como o executor a publica; `IExecutorCapacity` e `IPolicyMember.capacity` têm a mesma forma. */
export type Capacidade = {
  queued?: number; running?: number; max_concurrent?: number; max_queue?: number
} | null | undefined

/** "1 de 4 em execução · 2 na fila", ou `null` quando o executor não publicou capacidade. */
export function descreverCapacidade(c: Capacidade): string | null {
  if (!c || c.max_concurrent == null || c.running == null) return null
  const base = `${c.running} de ${c.max_concurrent} em execução`
  return c.queued && c.queued > 0 ? `${base} · ${c.queued} na fila` : base
}

/** Cheio = não aceita mais nada agora: execuções no teto e fila no teto (ou sem fila). */
export function capacidadeCheia(c: Capacidade): boolean {
  if (!c || c.max_concurrent == null || c.running == null) return false
  if (c.running < c.max_concurrent) return false
  return c.max_queue == null || (c.queued ?? 0) >= c.max_queue
}
