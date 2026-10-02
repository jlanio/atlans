// service/dominios/artefatos.ts — recorte de GisFlowService (F5/A12).

import { qs, get, del } from "../http"
import type {
  IArtifactListParams, IArtifactListResponse,
} from "../types"

// ── Artefatos ──────────────────────────────────────��───────────────────────

/**
 * Lista artefatos. SEMPRE pagine: a tela baixava a tabela inteira do usuario
 * e filtrava em memoria, o que travava a aba por segundos em workspace com
 * historico. `search`, `workspace_id` e `kind` vao ao servidor pelo mesmo
 * motivo — o cliente nao precisa ver o que nao vai mostrar.
 */
export function getArtifacts(params: import("../types").IArtifactListParams = {}) {
  return get<import("../types").IArtifactListResponse>(
    `/artifacts${qs(params as Record<string, string | number | boolean | undefined>)}`,
  )
}

export function deleteArtifact(idHash: string) { return del(`/artifacts/${idHash}`) }
