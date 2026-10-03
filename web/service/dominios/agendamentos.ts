// service/dominios/agendamentos.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, put, del } from "../http"
import type {
  IMySchedule, IMySchedules, IWorkflowGroup,
} from "../types"

// ── Meu → Agendamentos ───────────────────────────────────────────────────

/** The person's schedules, across all their workspaces (Home panel).
 *  Paginated with a TOTAL (`{ itens, total }`), the same envelope as
 *  `listarConversas`: the route has a ceiling and without the total it
 *  truncated silently. The server clamps `limit` to 500. */
export function getMySchedules(limit = 200, offset = 0) {
  return get<import("../types").IMySchedules>(`/me/schedules${qs({ limit, offset })}`)
}

/** Pauses/activates a schedule. Goes via `put` (mutation) so the write epoch
 *  invalidates the next read of `getMySchedules`. Turning it back on resets
 *  `next_run_at` on the server — nothing fires the moment the switch flips. */
export function updateSchedule(workflowId: string, jobId: string, body: { active: boolean }) {
  // The response is the updated schedule (ScheduleRead), without `workflow_name`/
  // `flag_ative` — it is not an IAgendamentoMeu. The caller only needs
  // success/error and refetches `getMySchedules` (the write epoch invalidates
  // the read), so the body stays `unknown`.
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

/** New order of the groups, from the first position to the last.
 *  The backend stores the position by INDEX — there is no numbering on the client. */
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
