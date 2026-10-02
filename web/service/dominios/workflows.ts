// service/dominios/workflows.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, put, patch, delComRetorno, del } from "../http"
import type {
  INodesAPI, IPinNodeMeta, IWorkflow, IWorkflowGroup, IWorkflowMoveResult, IWorkflowVersion,
} from "../types"

// ── Workflows ──────────────────────────────────────────────────────────────

export function executeWorkflow(id: string, inputs: Record<string, unknown> = {}, debugMode = false) {
  // Usa o endpoint autenticado (/workflows/{id}/execute) em vez de
  // /webhook/execute — o canvas é uma sessão JWT-auth de usuário (intent
  // manual), não um caller externo. O endpoint /webhook/execute exige
  // WebhookTrigger no fluxo e bloqueia qualquer outro tipo de trigger.
  return post<{ task_id: string; workflow: string }>(`/workflows/${id}/execute`, {
    inputs,
    debug_mode: debugMode,
  })
}

export function getNodes() { return get<INodesAPI[]>("/nodes") }

export function getWorkflowById(id: string) { return get<IWorkflow>(`/workflows/${id}`) }

export function getWorkflows(workspaceId?: string, opts?: { incluirDoAssistente?: boolean }) {
  // `assistente=1` inclui os fluxos do assistente da Home (escondidos por
  // padrão). Omitido quando falso para não sujar a URL (o `qs` só descarta
  // null/"" — um `false` viraria `assistente=false`).
  return get<IWorkflow[]>(`/workflows${qs({
    workspace_id: workspaceId,
    assistente: opts?.incluirDoAssistente ? 1 : undefined,
  })}`)
}

export function createWorkflow(newWorkflow: Omit<IWorkflow, "id_hash" | "created_by_id" | "updated_by_id">) {
  // created_by_id e updated_by_id são preenchidos pelo backend a partir
  // do usuário autenticado; o frontend nunca deve inventar esses valores.
  return post<IWorkflow>("/workflows", newWorkflow)
}

export function updateWorkflowById(id: string, updatedWorkflow: Partial<Omit<IWorkflow, "id_hash">>) {
  // Payload parcial — envie APENAS os campos que realmente mudaram.
  // O backend (WorkflowUpdate em app/schemas/workflow.py) usa
  // `dict(exclude_unset=True)` e só persiste o que chegar, preservando
  // os demais. Enviar campo com valor hardcoded SOBRESCREVE o valor real.
  return put<IWorkflow>(`/workflows/${id}`, updatedWorkflow)
}

export function deleteWorkflowById(id: string) { return del(`/workflows/${id}`) }

/**
 * Duplica o workflow no MESMO workspace do original.
 *
 * Sem `name`, o backend escolhe o primeiro "Cópia de X" livre — há restrição
 * de unicidade por (nome, workspace). O agendamento acompanha DESLIGADO, e
 * pins e publicação no portal não acompanham.
 */
export function duplicateWorkflowById(id: string, name?: string) {
  return post<{ id: string; name: string }>(`/workflows/${id}/duplicate`, name ? { name } : {})
}

/**
 * Move o workflow para outro workspace, preservando o id_hash.
 *
 * Exige role admin/owner na ORIGEM e no DESTINO — mover atravessa a fronteira
 * de tenant, e `editor` (que basta para duplicar dentro do proprio workspace)
 * nao cobre isso.
 *
 * NAO falha por dependencia quebrada: o que deixa de funcionar no destino vem
 * em `warnings`. Agendamento chega desligado, portal volta a "disabled", grupo
 * e pins sao limpos. O historico (execucoes, artefatos, metricas) permanece no
 * workspace de origem.
 */
export function moveWorkflowToWorkspace(id: string, targetWorkspaceId: string, name?: string) {
  return post<IWorkflowMoveResult>(`/workflows/${id}/move`, {
    target_workspace_id: targetWorkspaceId,
    ...(name ? { name } : {}),
  })
}

/**
 * Mesmo relatorio do move, sem gravar nada — alimenta o dialogo antes de
 * confirmar. Sem `name`: o preview roda a cada troca de destino, e reagir ao
 * campo de nome dispararia uma chamada por tecla digitada. A colisao de nome
 * volta como aviso `name_conflict` na resposta do move real.
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
 * [Admin] Alterna flag_ative de um workflow bypassando membership de
 * workspace. Usado na tela `/observability` para desativar workflows
 * mal configurados sem precisar ser membro do workspace do dono.
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

// ── Versões ────────────────────────────────────────────────────────────────

export function getWorkflowVersions(id: string) {
  return get<IWorkflowVersion[]>(`/workflows/${id}/versions`)
}

export function restoreWorkflowVersion(id: string, version: number) {
  return post<IWorkflow>(`/workflows/${id}/versions/${version}/restore`)
}

// ── Portal de compartilhamento ─────────────────────────────────────────────

export function updatePortalSettings(id: string, settings: { portal_access: string; portal_shared_with?: string[] | null }) {
  return patch<object>(`/workflows/${id}/portal`, settings)
}


// ── Grupos de Workflow ─────���───────────────────────────────────────────────

export function getWorkflowGroups(workspaceId?: string) {
  return get<import("../types").IWorkflowGroup[]>(
    `/workflow-groups${qs({ workspace_id: workspaceId })}`,
  )
}
