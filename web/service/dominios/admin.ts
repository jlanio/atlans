// service/dominios/admin.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, put, patch, del } from "../http"
import axios, { AxiosError } from "axios"
import { resolveAxiosError } from "../resolveResponse"
import { API_URL } from "@/utils/env"
import type {
  IAdminBulkActionResponse, IAdminUser, IAdminUserListParams, IAdminUserListResponse, IArtifactSettings, IAssistenteEstado, ICamadaDoGlobo, IConversaDetalhe, IConversaLista, IConversaResumo, INodeAdminEntry, IPainelDoModelo, IStoragePurgeResult, IStorageUsage, IStorageUsageAdmin, ISystemHealth, IWorkflowContract, IWorkspaceRestoreResult, IWorkspaceTrash,
} from "../types"

// ── Assistant model (admin) ────────────────────────────────────────────────

/** The model in use and the provider's catalog (plus whatever an extension adds
 *  to the panel). `simular` recomputes what depends on the model **without
 *  saving anything** — it is the preview. Saving on simulate would mean
 *  switching the production model by hovering over a list. */
export function painelDoModelo(simular?: string | null) {
  return get<IPainelDoModelo>(`/admin/assistente/modelo${qs({ simular })}`)
}

/** Switches the model. `null` goes back to the environment default.
 *
 *  Applies from the NEXT conversation on: those already in progress finish on
 *  the model they started with. */
export function trocarModelo(modelo: string | null) {
  return put<IPainelDoModelo>("/admin/assistente/modelo", { modelo })
}

// ── System Health ──────────────────────────────────────────────────────────

export function getSystemHealth() { return get<ISystemHealth>("/admin/health") }

export function updateWebhookWhitelist(domains: string[]) {
  return patch<{ webhook_whitelist: string[] }>("/admin/health/webhook-whitelist", { domains })
}

// ── Admin: global Drive configuration ──────────────────────────────────────

export function getAdminDriveSettings() {
  return get<{ max_size_mb: number }>("/admin/drive/settings")
}

export function updateAdminDriveSettings(maxSizeMb: number) {
  return put<{ max_size_mb: number }>("/admin/drive/settings", { max_size_mb: maxSizeMb })
}

export function getAdminDriveExtensions() {
  return get<{ extension: string; enabled: boolean }[]>("/admin/drive/extensions")
}

export function addAdminDriveExtension(extension: string) {
  return post<unknown>("/admin/drive/extensions", { extension })
}

export function removeAdminDriveExtension(extension: string) {
  return del(`/admin/drive/extensions/${extension}`)
}

export function batchDeleteArtifacts(idHashes: string[]) {
  return post<{ deleted: number }>("/artifacts/batch-delete", { id_hashes: idHashes })
}

/** Public download URL — no authentication if not protected. */
export function getArtifactDownloadUrl(idHash: string): string {
  return `${API_URL}/artifacts/${idHash}/download`
}

/** Resolves the artifact's presigned URL.
 *
 *  The endpoint is public, but accepts a Bearer for protected artifacts — the
 *  interceptor attaches the JWT when there is a session, which is what the
 *  page built by hand. The `fetch` of the returned presigned URL does NOT go
 *  through here, on purpose: it points to MinIO, and sending the platform
 *  token to another origin would leak it. */
export function getArtifactDownload(idHash: string) {
  return get<{ download_url: string; filename: string }>(`/artifacts/${idHash}/download`)
}

export function getArtifactSettings() { return get<IArtifactSettings>("/artifacts/admin/settings") }

export function updateArtifactSettings(retentionDays: number | null) {
  return put<IArtifactSettings>("/artifacts/admin/settings", { artifact_retention_days: retentionDays })
}

// ── Admin: User Management ─────────────────────────────────────────────────

export function getAdminUsers(params: import("../types").IAdminUserListParams = {}) {
  return get<import("../types").IAdminUserListResponse>(`/admin/users${qs(params as Record<string, string | number | undefined>)}`)
}

export function suspendUser(id_hash: string, reason?: string) {
  return post<import("../types").IAdminUser>(`/admin/users/${id_hash}/suspend`, { reason })
}

export function reactivateUser(id_hash: string) {
  return post<import("../types").IAdminUser>(`/admin/users/${id_hash}/reactivate`)
}

export function adminDeleteUser(id_hash: string) {
  return post<import("../types").IAdminUser>(`/admin/users/${id_hash}/delete`)
}

export function updateUserRole(id_hash: string, role: string) {
  return put<import("../types").IAdminUser>(`/admin/users/${id_hash}/role`, { role })
}

export function updateUserAgentQuota(id_hash: string, agent_quota: number) {
  return put<import("../types").IAdminUser>(`/admin/users/${id_hash}/executor-quota`, { agent_quota })
}

export function getUserAgentStats(id_hash: string) {
  return get<{
    user_id: string
    agent_quota: number
    created: number
    accessible: number
  }>(`/admin/users/${id_hash}/executor-stats`)
}

export function revokeAllUserAgents(id_hash: string) {
  return post<{
    user_id: string
    revoked_count: number
    agent_ids: string[]
    affected_workspaces: number
  }>(`/admin/users/${id_hash}/revoke-all-executores`)
}

export function bulkSuspendUsers(user_ids: string[], reason?: string) {
  return post<import("../types").IAdminBulkActionResponse>("/admin/users/bulk/suspend", { user_ids, reason })
}

export function bulkReactivateUsers(user_ids: string[]) {
  return post<import("../types").IAdminBulkActionResponse>("/admin/users/bulk/reactivate", { user_ids })
}

export function bulkDeleteUsers(user_ids: string[]) {
  return post<import("../types").IAdminBulkActionResponse>("/admin/users/bulk/delete", { user_ids })
}

// ── Armazenamento ───────────────────────���─────────────────────────────���────

export function getStorageUsage() { return get<import("../types").IStorageUsageAdmin>("/admin/storage") }

// ── Admin: workspace trash ──────────────────────────────────────────────────

export function getWorkspaceTrash() {
  return get<import("../types").IWorkspaceTrash[]>("/admin/workspaces/trash")
}

export function restoreWorkspace(idHash: string) {
  return post<import("../types").IWorkspaceRestoreResult>(
    `/admin/workspaces/${encodeURIComponent(idHash)}/restore`,
  )
}

/**
 * Hard delete of the record. IRREVERSIBLE. Requires the workspace to be in the
 * trash. `confirm` repeats the id_hash — a backend guard against clicking the
 * wrong row of the table.
 */
export function purgeWorkspace(idHash: string) {
  return post<undefined>(
    `/admin/workspaces/${encodeURIComponent(idHash)}/purge`, { confirm: idHash },
  )
}

/**
 * Purges a workspace's Drive and/or Artifacts. IRREVERSIBLE.
 * `confirm` must repeat the workspace_id — a backend guard against an
 * accidental click on the wrong row of the table.
 */
export function purgeWorkspaceStorage(workspaceId: string, scope: "all" | "artifacts" | "drive") {
  return post<import("../types").IStoragePurgeResult>(
    `/admin/storage/workspaces/${encodeURIComponent(workspaceId)}/purge`,
    { scope, confirm: workspaceId },
  )
}

// ── Assistente ───────────────────────────────────────────────────────────

/**
 * The panel queries this BEFORE appearing on screen: without a configured key,
 * the assistant simply does not exist on that installation.
 *
 * The conversation itself does NOT go through here — it is `text/event-stream`,
 * and axios does not deliver streams in the browser. What consumes it is
 * `useAssistenteEditor`, with `fetch` + a body reader.
 */
export function estadoDoAssistente() {
  return get<import("../types").IAssistenteEstado>("/assistente/editor/estado")
}

/** Restarts the conversation for that workflow. Deletes no workflow — only the history. */
export function esquecerConversaDoAssistente(workflowId?: string) {
  return del(`/assistente/editor/conversa${qs({ workflow_id: workflowId })}`)
}

// ── Home assistant (persisted conversations) ───────────────────────────
//
// Only listing/replay/rename/delete live here (plain JSON). The conversation
// itself is `text/event-stream`, consumed by `useAssistente` with fetch + a
// body reader (the floating panel comes in the next PR) — axios does not
// deliver streams in the browser.

/** Is the assistant available? The quota is the SAME as the editor's (`assistente:tokens`). */
export function estadoDoAgente() {
  return get<import("../types").IAssistenteEstado>("/assistente/estado")
}

/** My non-deleted conversations, most recently active on top. */
export function listarConversas(limit = 50, offset = 0) {
  return get<import("../types").IConversaLista>(`/assistente/conversas${qs({ limit, offset })}`)
}

/** The replay of a conversation, in frames (for the panel to reapply). */
export function lerConversa(id: string) {
  return get<import("../types").IConversaDetalhe>(`/assistente/conversas/${encodeURIComponent(id)}`)
}

/** Renames a conversation. */
export function renomearConversa(id: string, titulo: string) {
  return patch<import("../types").IConversaResumo>(`/assistente/conversas/${encodeURIComponent(id)}`, { titulo })
}

/** (Soft-)deletes a conversation: it disappears from the list, the history stays. */
export function apagarConversa(id: string) {
  return del(`/assistente/conversas/${encodeURIComponent(id)}`)
}

/** A globe layer (member gate): how to load a run output. */
export function camadaDoGlobo(artifactId: string) {
  return get<import("../types").ICamadaDoGlobo>(`/assistente/camadas/${encodeURIComponent(artifactId)}`)
}

// ── Workflow contract (SubWorkflow caller le contrato do alvo) ─────────

export function getWorkflowContract(idHash: string) {
  return get<import("../types").IWorkflowContract>(`/workflows/${encodeURIComponent(idHash)}/contract`)
}

// ── Admin: nodes habilitados / desabilitados ────────────────────────────

export function listAdminNodes() {
  return get<import("../types").INodeAdminEntry[]>("/admin/nodes")
}

export function patchAdminNode(name: string, body: { enabled: boolean; reason?: string | null }) {
  return patch<import("../types").INodeAdminEntry>(`/admin/nodes/${encodeURIComponent(name)}`, body)
}

export async function exportUsersCSV(params?: { search?: string; status?: string; role?: string }) {
  try {
    const url = `${API_URL}/admin/users/export/csv${qs(params || {})}`
    const response = await axios.get(url, { responseType: "blob" })
    return { data: response.data as Blob, error: null }
  } catch (err) {
    return resolveAxiosError(err as AxiosError)
  }
}
