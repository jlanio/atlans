import type { IPolicyMember, IWorkspacePolicy } from "@/service/types"

/** Membro de nível com defaults sãos — sobrescreva só o que o teste quer provar. */
export function membro(extra: Partial<IPolicyMember> = {}): IPolicyMember {
  return {
    id_hash: "ex-1", name: "geo-01", executor_type: "dedicated", status: "active",
    tier: 1, online: true, capacity: null,
    ...extra,
  }
}

/**
 * Política com defaults de workspace Compartilhado saudável (pool com 2 online,
 * roteamento por política ligado). `available_*` NÃO é derivado dos membros de
 * propósito: é o servidor quem conta, e o teste diz explicitamente o que ele
 * respondeu.
 */
export function politica(extra: Partial<IWorkspacePolicy> = {}): IWorkspacePolicy {
  return {
    workspace_id: "ws-a",
    mode: "pool",
    primary: [],
    fallback: [],
    fallback_terminal: "fail",
    effective_terminal: "fail",
    isolation_floor: "none",
    available_primary: 0,
    available_fallback: 0,
    pool: { total: 2, available: 2 },
    policy_routing_enabled: true,
    target_executor_id: null,
    ...extra,
  }
}

/** Isolado com um principal online: o caso "simples" que ainda cabe no seletor rápido. */
export function isolada(extra: Partial<IWorkspacePolicy> = {}): IWorkspacePolicy {
  return politica({
    mode: "isolated",
    primary: [membro()],
    available_primary: 1,
    pool: null,
    target_executor_id: "ex-1",
    ...extra,
  })
}
