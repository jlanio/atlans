// service/dominios/drive.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, del } from "../http"
import type {
  IDriveFile, IDriveFileList, IDriveListParams,
} from "../types"

// ── Drive ───────────────────────────────────────────────────────────────────

/**
 * Lists the files in a workspace's Drive.
 *
 * `page`/`page_size` are always sent: the backend cuts at 50 by default and
 * the two consumers never sent anything, so everything past the 50th file was
 * unreachable from the UI while the header announced the real total.
 */
export function getDriveFiles(params: import("../types").IDriveListParams) {
  return get<import("../types").IDriveFileList>(
    `/drive${qs(params as unknown as Record<string, string | number | undefined>)}`,
  )
}

/** Uploads a file to the workspace's Drive (multipart).
 *
 *  axios builds the boundary on its own from the FormData — hard-coding
 *  `Content-Type: multipart/form-data`, as the pages did, produces a header
 *  WITHOUT a boundary. It worked because axios overwrote it. */
export function uploadDriveFile(workspaceId: string, file: File) {
  const form = new FormData()
  form.append("file", file)
  // The return value is the created file's `WorkspaceFileOut`. It was `unknown`,
  // and the /drive page indeed only looks at the error — but the Home's
  // attachments store the `id_hash` of what was uploaded, and without the type
  // that would be a manual cast.
  return post<import("../types").IDriveFile>(`/drive/upload${qs({ workspace_id: workspaceId })}`, form)
}

export function getDriveDownloadUrl(idHash: string) {
  return get<{ download_url: string }>(`/drive/${idHash}/download`)
}

export function deleteDriveFile(idHash: string) {
  return del(`/drive/${idHash}`)
}

export function batchDeleteDriveFiles(idHashes: string[]) {
  return post<{ deleted: number; no_executor?: number }>(
    "/drive/batch-delete", { id_hashes: idHashes },
  )
}
