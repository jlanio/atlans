// service/dominios/workspaces.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, put, del } from "../http"
import type {
  IExecutorUserAssignment, IUserSearchResult, IWorkspace, IWorkspaceMember, IWorkspaceNotifications, IWorkspacePolicy, IWorkspacePolicyAdmin, IsolationFloor, PolicyTerminal,
} from "../types"

// ── Workspaces: execution policy ────────────────────────────────────────────
// (docs/specs/executor-isolation-routing.md). The GET brings tiers, terminal,
// floor and each tier's health; the mutations return the already recomputed
// policy, except the DELETE (204) — whoever removes re-reads.

export function getWorkspacePolicy(workspaceId: string) {
  return get<IWorkspacePolicy>(`/workspaces/${encodeURIComponent(workspaceId)}/executors`)
}

export function addWorkspacePolicyMember(workspaceId: string, executorId: string, tier: 1 | 2) {
  return post<IWorkspacePolicy>(
    `/workspaces/${encodeURIComponent(workspaceId)}/executors/${encodeURIComponent(executorId)}?tier=${tier}`,
  )
}

export function removeWorkspacePolicyMember(workspaceId: string, executorId: string) {
  return del(`/workspaces/${encodeURIComponent(workspaceId)}/executors/${encodeURIComponent(executorId)}`)
}

export function setWorkspaceFallback(workspaceId: string, terminal: PolicyTerminal) {
  return put<IWorkspacePolicy>(`/workspaces/${encodeURIComponent(workspaceId)}/fallback`, { terminal })
}

/** Platform admin only: the policy of every live workspace, for the floor screen. */
export function listWorkspacePolicies() {
  return get<IWorkspacePolicyAdmin[]>("/admin/workspaces/policies")
}

/** Platform admin only: `no_pool` forces the terminal to fail and locks the owner's choice. */
export function setWorkspaceIsolationFloor(workspaceId: string, floor: IsolationFloor) {
  return put<{
    workspace_id: string
    isolation_floor: IsolationFloor
    fallback_terminal: PolicyTerminal
    terminal_forced_to_fail: boolean
  }>(`/admin/workspaces/${encodeURIComponent(workspaceId)}/isolation-floor`, { floor })
}

export function getAgentUsers(agentId: string) {
  return get<IExecutorUserAssignment[]>(`/executores/${agentId}/users`)
}

export function assignAgentToUser(agentId: string, userId: string) {
  return post<{ executor_id: string; user_id: string; username: string }>(`/executores/${agentId}/users`, { user_id: userId })
}

export function removeAgentUser(agentId: string, userId: string) {
  return del(`/executores/${agentId}/users/${userId}`)
}

export function searchUsersByEmail(email: string) {
  return get<import("../types").IUserSearchResult[]>(
    `/workspaces/users/search${qs({ email })}`,
  )
}

// ── Workspaces ──────────────────────────────────────────────────────────────

export function listWorkspaces() { return get<import("../types").IWorkspace[]>("/workspaces") }

export function createWorkspace(name: string, description: string | null, ownerId: string | null) {
  return post<import("../types").IWorkspace>("/workspaces", {
    name, description, owner_id: ownerId,
  })
}

export function updateWorkspace(idHash: string, name: string, description: string | null) {
  return put<import("../types").IWorkspace>(
    `/workspaces/${encodeURIComponent(idHash)}`, { name, description },
  )
}

/**
 * Soft delete: the workspace goes to the trash. The workflows are disabled
 * along with it and the schedules stop. Restoring is an admin action — see
 * restoreWorkspace.
 */
export function deleteWorkspace(idHash: string) {
  return del(`/workspaces/${encodeURIComponent(idHash)}`)
}

// ── Workspaces: membros ─────────────────────────────────────────────────────

export function listWorkspaceMembers(idHash: string) {
  return get<import("../types").IWorkspaceMember[]>(
    `/workspaces/${encodeURIComponent(idHash)}/members`,
  )
}

export function inviteWorkspaceMember(idHash: string, email: string, role: string) {
  return post<import("../types").IWorkspaceMember>(
    `/workspaces/${encodeURIComponent(idHash)}/members`, { email, role },
  )
}

export function updateWorkspaceMemberRole(idHash: string, userId: string, role: string) {
  return put<import("../types").IWorkspaceMember>(
    `/workspaces/${encodeURIComponent(idHash)}/members/${encodeURIComponent(userId)}`,
    { role },
  )
}

/** Removes a member — it is also how a member leaves on their own. */
export function removeWorkspaceMember(idHash: string, userId: string) {
  return del(
    `/workspaces/${encodeURIComponent(idHash)}/members/${encodeURIComponent(userId)}`,
  )
}

// ── Workspaces: notification allowlist ──────────────────────────────────────

export function getWorkspaceNotifications(idHash: string) {
  return get<import("../types").IWorkspaceNotifications>(
    `/workspaces/${encodeURIComponent(idHash)}/notifications`,
  )
}

export function updateWorkspaceNotificationAllowlist(idHash: string, allowlist: string[]) {
  return put<import("../types").IWorkspaceNotifications>(
    `/workspaces/${encodeURIComponent(idHash)}/notifications`, { allowlist },
  )
}
