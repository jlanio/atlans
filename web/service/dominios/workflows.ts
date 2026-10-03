// service/dominios/workflows.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, put, patch, delComRetorno, del } from "../http"
import type {
  INodesAPI, IPinNodeMeta, IWorkflow, IWorkflowGroup, IWorkflowMoveResult, IWorkflowVersion,
} from "../types"

// ── Workflows ──────────────────────────────────────────────────────────────

export function executeWorkflow(id: string, inputs: Record<string, unknown> = {}, debugMode = false) {
  // Uses the authenticated endpoint (/workflows/{id}/execute) instead of
  // /webhook/execute — the canvas is a JWT-authenticated user session (manual
  // intent), not an external caller. The /webhook/execute endpoint requires a
  // WebhookTrigger in the workflow and blocks any other trigger type.
  return post<{ task_id: string; workflow: string }>(`/workflows/${id}/execute`, {
    inputs,
    debug_mode: debugMode,
  })
}

export function getNodes() { return get<INodesAPI[]>("/nodes") }

export function getWorkflowById(id: string) { return get<IWorkflow>(`/workflows/${id}`) }

export function getWorkflows(workspaceId?: string, opts?: { incluirDoAssistente?: boolean }) {
  // `assistente=1` includes the Home assistant's workflows (hidden by
  // default). Omitted when false so as not to clutter the URL (`qs` only drops
  // null/"" — a `false` would become `assistente=false`).
  return get<IWorkflow[]>(`/workflows${qs({
    workspace_id: workspaceId,
    assistente: opts?.incluirDoAssistente ? 1 : undefined,
  })}`)
}

export function createWorkflow(newWorkflow: Omit<IWorkflow, "id_hash" | "created_by_id" | "updated_by_id">) {
  // created_by_id and updated_by_id are filled in by the backend from the
  // authenticated user; the frontend must never make up these values.
  return post<IWorkflow>("/workflows", newWorkflow)
}

export function updateWorkflowById(id: string, updatedWorkflow: Partial<Omit<IWorkflow, "id_hash">>) {
  // Partial payload — send ONLY the fields that actually changed.
  // The backend (WorkflowUpdate in app/schemas/workflow.py) uses
  // `dict(exclude_unset=True)` and only persists what arrives, preserving
  // the rest. Sending a field with a hardcoded value OVERWRITES the real value.
  return put<IWorkflow>(`/workflows/${id}`, updatedWorkflow)
}

export function deleteWorkflowById(id: string) { return del(`/workflows/${id}`) }

/**
 * Duplicates the workflow in the SAME workspace as the original.
 *
 * Without `name`, the backend picks the first free "Cópia de X" (Copy of X) —
 * there is a uniqueness constraint on (name, workspace). The schedule comes
 * along TURNED OFF, and pins and portal publication do not come along.
 */
export function duplicateWorkflowById(id: string, name?: string) {
  return post<{ id: string; name: string }>(`/workflows/${id}/duplicate`, name ? { name } : {})
}

/**
 * Moves the workflow to another workspace, preserving the id_hash.
 *
 * Requires the admin/owner role in the SOURCE and in the DESTINATION — moving
 * crosses the tenant boundary, and `editor` (which is enough to duplicate
 * within one's own workspace) does not cover that.
 *
 * Does NOT fail on a broken dependency: what stops working in the destination
 * comes in `warnings`. The schedule arrives turned off, the portal goes back to
 * "disabled", group and pins are cleared. The history (runs, artifacts,
 * metrics) stays in the source workspace.
 */
export function moveWorkflowToWorkspace(id: string, targetWorkspaceId: string, name?: string) {
  return post<IWorkflowMoveResult>(`/workflows/${id}/move`, {
    target_workspace_id: targetWorkspaceId,
    ...(name ? { name } : {}),
  })
}

/**
 * Same report as the move, without writing anything — it feeds the dialog
 * before confirming. No `name`: the preview runs on every destination change,
 * and reacting to the name field would fire one call per keystroke. A name
 * collision comes back as a `name_conflict` warning in the real move's response.
 */
export function previewMoveWorkflow(id: string, targetWorkspaceId: string) {
  return post<IWorkflowMoveResult>(`/workflows/${id}/move/preview`, {
    target_workspace_id: targetWorkspaceId,
  })
}

export function updateStatusWorkflow(id: string, { flag_ative }: Pick<IWorkflow, "flag_ative">) {
  return put<undefined>(`/workflows/${id}`, { flag_ative })
}

/**
 * [Admin] Toggles a workflow's flag_ative bypassing workspace membership.
 * Used on the `/observability` screen to disable misconfigured workflows
 * without having to be a member of the owner's workspace.
 */
export function setAdminWorkflowStatus(id_hash: string, flag_ative: boolean) {
  return put<{ id_hash: string; flag_ative: boolean }>(
    `/admin/workflows/${id_hash}/status`,
    { flag_ative },
  )
}

// ── Pin Data ─────────���──────────────────────────��──────────────────────────

export function pinNodeOutput(workflowId: string, nodeId: string, outputs: Record<string, unknown>, ttlHours?: number | null) {
  return put<{ pinned: string; total_pinned: number; pinned_at: string; expires_at: string | null; ttl_hours: number | null }>(
    `/workflows/${workflowId}/pin/${nodeId}`,
    { node_id: nodeId, outputs, ttl_hours: ttlHours ?? null },
  )
}

export function unpinNodeOutput(workflowId: string, nodeId: string) {
  return delComRetorno<{ unpinned: string; total_pinned: number }>(
    `/workflows/${workflowId}/pin/${nodeId}`,
  )
}

export function listPinnedNodes(workflowId: string) {
  return get<{ pinned_nodes: import("../types").IPinNodeMeta[]; total: number }>(
    `/workflows/${workflowId}/pins`,
  )
}

// ── Versions ───────────────────────────────────────────────────────────────

export function getWorkflowVersions(id: string) {
  return get<IWorkflowVersion[]>(`/workflows/${id}/versions`)
}

export function restoreWorkflowVersion(id: string, version: number) {
  return post<IWorkflow>(`/workflows/${id}/versions/${version}/restore`)
}

// ── Sharing portal ─────────────────────────────────────────────────────────

export function updatePortalSettings(id: string, settings: { portal_access: string; portal_shared_with?: string[] | null }) {
  return patch<object>(`/workflows/${id}/portal`, settings)
}


// ── Workflow Groups ────────────────────────────────────────────────────────

export function getWorkflowGroups(workspaceId?: string) {
  return get<import("../types").IWorkflowGroup[]>(
    `/workflow-groups${qs({ workspace_id: workspaceId })}`,
  )
}
