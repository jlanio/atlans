// service/dominios/credenciais.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, put, del } from "../http"
import type {
  ICredentialTypeSchema, ICredentials, ICredentialsRequest,
} from "../types"

// ── Credenciais ─────────────────────────────────────���──────────────────────

export function getCredentialTypes() { return get<ICredentialTypeSchema[]>("/credentials/types") }

export function testCredential(payload: { type: string; data: Record<string, string> }) {
  return post<{ ok: boolean; message: string }>("/credentials/test", payload)
}

export function getCredentialsUsage(workspaceId?: string) {
  return get<Record<string, { node_count: number; workflow_count: number }>>(
    `/credentials/usage${qs({ workspace_id: workspaceId })}`,
  )
}

export function createCredential(newCredential: Partial<ICredentialsRequest>) {
  return post<ICredentials>("/credentials", newCredential)
}

export function getCredentials(type?: string) {
  return get<ICredentials[]>(`/credentials${qs({ type })}`)
}

export function getCredentialData(id: string) {
  return get<ICredentialsRequest>(`/credentials/${id}/data`)
}

export function updateCredential(id: string, updateCredential: Partial<ICredentialsRequest>) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { created_at, updated_at, ...credential } = updateCredential
  return put<ICredentials>(`/credentials/${id}`, credential)
}

export function deleteCredentialById(id: string) { return del(`/credentials/${id}`) }
