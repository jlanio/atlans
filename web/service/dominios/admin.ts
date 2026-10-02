// service/dominios/admin.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, put, patch, del } from "../http"
import axios, { AxiosError } from "axios"
import { resolveAxiosError } from "../resolveResponse"
import { API_URL } from "@/utils/env"
import type {
  IAdminBulkActionResponse, IAdminUser, IAdminUserListParams, IAdminUserListResponse, IArtifactSettings, IAssistenteEstado, ICamadaDoGlobo, IConversaDetalhe, IConversaLista, IConversaResumo, INodeAdminEntry, IPainelDoModelo, IStoragePurgeResult, IStorageUsage, IStorageUsageAdmin, ISystemHealth, IWorkflowContract, IWorkspaceRestoreResult, IWorkspaceTrash,
} from "../types"

// ── Modelo do assistente (admin) ───────────────────────────────────────────

/** O modelo em uso e o catálogo do provedor (mais o que uma extensão some ao
 *  painel). `simular` recalcula o que depende do modelo **sem salvar nada** —
 *  é a pré-visualização. Salvar ao simular seria trocar o modelo de produção
 *  ao passar o mouse numa lista. */
export function painelDoModelo(simular?: string | null) {
  return get<IPainelDoModelo>(`/admin/assistente/modelo${qs({ simular })}`)
}

/** Troca o modelo. `null` volta ao padrão do ambiente.
 *
 *  Vale da PRÓXIMA conversa em diante: as que já estão em curso terminam no
 *  modelo em que começaram. */
export function trocarModelo(modelo: string | null) {
  return put<IPainelDoModelo>("/admin/assistente/modelo", { modelo })
}

// ── Saúde do Sistema ──────��─────────────────────────────���──────────────────

export function getSystemHealth() { return get<ISystemHealth>("/admin/health") }

export function updateWebhookWhitelist(domains: string[]) {
  return patch<{ webhook_whitelist: string[] }>("/admin/health/webhook-whitelist", { domains })
}

// ── Admin: configuração global do Drive ────────────────────────────────────

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

/** URL pública de download — sem autenticação se não protegido. */
export function getArtifactDownloadUrl(idHash: string): string {
  return `${API_URL}/artifacts/${idHash}/download`
}

/** Resolve a URL pré-assinada do artefato.
 *
 *  O endpoint é público, mas aceita Bearer para artefatos protegidos — o
 *  interceptor anexa o JWT quando há sessão, que é o que a página montava à
 *  mão. O `fetch` da URL pré-assinada devolvida NÃO passa por aqui, e é
 *  proposital: ela aponta para o MinIO, e mandar o token da plataforma para
 *  outra origem seria vazá-lo. */
export function getArtifactDownload(idHash: string) {
  return get<{ download_url: string; filename: string }>(`/artifacts/${idHash}/download`)
}

export function getArtifactSettings() { return get<IArtifactSettings>("/artifacts/admin/settings") }

export function updateArtifactSettings(retentionDays: number | null) {
  return put<IArtifactSettings>("/artifacts/admin/settings", { artifact_retention_days: retentionDays })
}

// ── Admin: Gestão de Usuários ──────────────────────────────────────────────

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

// ── Admin: lixeira de workspaces ────────────────────────────────────────────

export function getWorkspaceTrash() {
  return get<import("../types").IWorkspaceTrash[]>("/admin/workspaces/trash")
}

export function restoreWorkspace(idHash: string) {
  return post<import("../types").IWorkspaceRestoreResult>(
    `/admin/workspaces/${encodeURIComponent(idHash)}/restore`,
  )
}

/**
 * Hard delete do registro. IRREVERSIVEL. Exige que o workspace esteja na
 * lixeira. `confirm` repete o id_hash — guarda do backend contra clique na
 * linha errada da tabela.
 */
export function purgeWorkspace(idHash: string) {
  return post<undefined>(
    `/admin/workspaces/${encodeURIComponent(idHash)}/purge`, { confirm: idHash },
  )
}

/**
 * Purga Drive e/ou Artefatos de um workspace. IRREVERSIVEL.
 * `confirm` precisa repetir o workspace_id — guarda do backend contra
 * clique acidental na linha errada da tabela.
 */
export function purgeWorkspaceStorage(workspaceId: string, scope: "all" | "artifacts" | "drive") {
  return post<import("../types").IStoragePurgeResult>(
    `/admin/storage/workspaces/${encodeURIComponent(workspaceId)}/purge`,
    { scope, confirm: workspaceId },
  )
}

// ── Assistente ───────────────────────────────────────────────────────────

/**
 * O painel consulta isto ANTES de aparecer na tela: sem chave configurada, o
 * assistente simplesmente não existe naquela instalação.
 *
 * A conversa em si NÃO passa por aqui — ela é `text/event-stream`, e o axios
 * não entrega stream no navegador. Quem a consome é `useAssistenteEditor`, com
 * `fetch` + leitor do corpo.
 */
export function estadoDoAssistente() {
  return get<import("../types").IAssistenteEstado>("/assistente/editor/estado")
}

/** Recomeça a conversa daquele fluxo. Não apaga fluxo nenhum — só o histórico. */
export function esquecerConversaDoAssistente(workflowId?: string) {
  return del(`/assistente/editor/conversa${qs({ workflow_id: workflowId })}`)
}

// ── Assistente da Home (conversas persistidas) ─────────────────────────
//
// Só listagem/replay/renomear/apagar moram aqui (JSON puro). A conversa em si
// é `text/event-stream`, consumida por `useAssistente` com fetch + leitor do corpo
// (o painel flutuante vem no PR seguinte) — o axios não entrega stream no
// navegador.

/** O assistente está disponível? A cota é a MESMA do editor (`assistente:tokens`). */
export function estadoDoAgente() {
  return get<import("../types").IAssistenteEstado>("/assistente/estado")
}

/** As minhas conversas não apagadas, mais recentemente ativas em cima. */
export function listarConversas(limit = 50, offset = 0) {
  return get<import("../types").IConversaLista>(`/assistente/conversas${qs({ limit, offset })}`)
}

/** O replay de uma conversa, em quadros (para o painel reaplicar). */
export function lerConversa(id: string) {
  return get<import("../types").IConversaDetalhe>(`/assistente/conversas/${encodeURIComponent(id)}`)
}

/** Renomeia uma conversa. */
export function renomearConversa(id: string, titulo: string) {
  return patch<import("../types").IConversaResumo>(`/assistente/conversas/${encodeURIComponent(id)}`, { titulo })
}

/** Apaga (soft) uma conversa: some da lista, o histórico fica. */
export function apagarConversa(id: string) {
  return del(`/assistente/conversas/${encodeURIComponent(id)}`)
}

/** Uma camada do globo (portão de membro): como carregar uma saída de execução. */
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
