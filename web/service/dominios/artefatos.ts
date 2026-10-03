// service/dominios/artefatos.ts — recorte de GisFlowService (F5/A12).

import { qs, get, del } from "../http"
import type {
  IArtifactListParams, IArtifactListResponse,
} from "../types"

// ── Artefatos ──────────────────────────────────────��───────────────────────

/**
 * Lists artifacts. ALWAYS paginate: the screen downloaded the user's whole
 * table and filtered in memory, which froze the tab for seconds in a workspace
 * with history. `search`, `workspace_id` and `kind` go to the server for the
 * same reason — the client does not need to see what it will not show.
 */
export function getArtifacts(params: import("../types").IArtifactListParams = {}) {
  return get<import("../types").IArtifactListResponse>(
    `/artifacts${qs(params as Record<string, string | number | boolean | undefined>)}`,
  )
}

export function deleteArtifact(idHash: string) { return del(`/artifacts/${idHash}`) }
