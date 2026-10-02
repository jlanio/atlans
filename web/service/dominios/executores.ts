// service/dominios/executores.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, put, patch, del } from "../http"
import type {
  IDesktopInstaller, IExecutor, IExecutorCreateRequest, IExecutorCreatedResponse, IExecutorEnrollmentOtpResponse,
} from "../types"

// ── Executores ─────────────────────────────────────────────────────────────

export function getAgents(workspace_id?: string) {
  return get<IExecutor[]>(`/executores${qs({ workspace_id })}`)
}

export function createAgent(payload: IExecutorCreateRequest) {
  return post<IExecutorCreatedResponse>("/executores", payload)
}

/**
 * Gera um OTP de uso unico para enrollment do executor.
 * O plaintext retornado aparece APENAS UMA VEZ — entregue ao operador
 * via canal seguro (1Password, Signal, etc).
 */
/** Metadados do instalador Windows publicado (versao, tamanho, URL). */
export function getDesktopInstaller() {
  return get<IDesktopInstaller>("/executores/install/windows/latest.json")
}

export function generateEnrollmentOtp(agentId: string) {
  return post<IExecutorEnrollmentOtpResponse>(`/executores/${agentId}/enroll-otp`)
}

export function updateAgent(id_hash: string, payload: { name?: string; description?: string }) {
  return patch<IExecutor>(`/executores/${id_hash}`, payload)
}

/** `force`: retira o executor dos níveis da política mesmo que isso esvazie o principal de algum workspace. */
export function revokeAgent(id_hash: string, force = false) {
  return del(`/executores/${id_hash}${force ? "?force=true" : ""}`)
}

export function deleteAgent(id_hash: string, force = false) {
  return del(`/executores/${id_hash}/permanent${force ? "?force=true" : ""}`)
}

// ── Executores: observabilidade de ACKs ───────────────────────────────────

export function getPendingAcks() {
  return get<{
    count: number
    threshold_overdue_seconds: number
    items: { job_id: string; executor_id: string; elapsed_seconds: number }[]
  }>("/executores/pending-acks")
}

// ── Executores: acesso ─────────────────────────────────────────────────────

export function getMyAgents() { return get<IExecutor[]>("/executores/my") }

export function getMyAgentsCount() { return get<{ count: number }>("/executores/my/count") }

export function setDefaultAgent(agentId: string) {
  return post<IExecutor>("/executores/set-default", { executor_id: agentId })
}

export function unsetDefaultAgent(agentId: string) {
  return post<IExecutor>("/executores/unset-default", { executor_id: agentId })
}

export function setWorkspaceAgent(workspaceId: string, agentId: string | null) {
  return put<{ workspace_id: string; target_executor_id: string | null }>(
    `/workspaces/${workspaceId}/executor`, { target_executor_id: agentId },
  )
}
