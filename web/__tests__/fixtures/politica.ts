import type { IPolicyMember, IWorkspacePolicy } from "@/service/types"

/** Tier member with sane defaults — override only what the test wants to prove. */
export function membro(extra: Partial<IPolicyMember> = {}): IPolicyMember {
  return {
    id_hash: "ex-1", name: "geo-01", executor_type: "dedicated", status: "active",
    tier: 1, online: true, capacity: null,
    ...extra,
  }
}

/**
 * Policy with the defaults of a healthy Shared workspace (pool with 2 online,
 * policy routing on). `available_*` is NOT derived from the members on
 * purpose: the server is the one that counts, and the test states explicitly
 * what it answered.
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

/** Isolated with one primary online: the "simple" case that still fits in the quick picker. */
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
