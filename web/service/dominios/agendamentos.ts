// service/dominios/agendamentos.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, put, del } from "../http"
import type {
  IAgendamentoMeu, IAgendamentosMeus, IWorkflowGroup,
} from "../types"

// ── Meu → Agendamentos ───────────────────────────────────────────────────

/** Agendamentos da pessoa, entre todos os seus workspaces (painel da Home).
 *  Paginado com TOTAL (`{ itens, total }`), o mesmo envelope de
 *  `listarConversas`: a rota tem teto e sem o total ela truncava em silêncio.
 *  O servidor apara `limit` em 500. */
export function getMySchedules(limit = 200, offset = 0) {
  return get<import("../types").IAgendamentosMeus>(`/me/schedules${qs({ limit, offset })}`)
}

/** Pausa/ativa um agendamento. Vai por `put` (mutação) para a época de escrita
 *  invalidar a leitura seguinte de `getMySchedules`. Religar zera `next_run_at`
 *  no servidor — nada dispara na hora de virar o interruptor. */
export function updateSchedule(workflowId: string, jobId: string, body: { active: boolean }) {
  // A resposta é o schedule atualizado (ScheduleRead), sem `workflow_name`/
  // `flag_ative` — não é um IAgendamentoMeu. O chamador só precisa de
  // sucesso/erro e refaz `getMySchedules` (a época de escrita invalida a
  // leitura), então o corpo fica como `unknown`.
  return put<unknown>(`/workflows/${workflowId}/schedules/${jobId}`, body)
}

export function createWorkflowGroup(payload: { name: string; description?: string | null; workspace_id?: string; workflow_ids?: string[] }) {
  return post<import("../types").IWorkflowGroup>("/workflow-groups", payload)
}

export function updateWorkflowGroup(
  groupId: string,
  payload: { name?: string; description?: string | null },
) {
  return put<import("../types").IWorkflowGroup>(
    `/workflow-groups/${groupId}`, payload,
  )
}

/** Nova ordem dos grupos, da primeira posição para a última.
 *  O backend grava a posição pelo ÍNDICE — não há numeração no cliente. */
export function reorderWorkflowGroups(groupIds: string[]) {
  return put("/workflow-groups/reorder", { group_ids: groupIds })
}

export function deleteWorkflowGroup(groupId: string) { return del(`/workflow-groups/${groupId}`) }

export function addWorkflowToGroup(groupId: string, workflowId: string) {
  return post(`/workflow-groups/${groupId}/workflows/${workflowId}`)
}

export function removeWorkflowFromGroup(groupId: string, workflowId: string) {
  return del(`/workflow-groups/${groupId}/workflows/${workflowId}`)
}
