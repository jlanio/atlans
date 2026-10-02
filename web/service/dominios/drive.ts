// service/dominios/drive.ts — recorte de GisFlowService (F5/A12).

import { qs, get, post, del } from "../http"
import type {
  IDriveFile, IDriveFileList, IDriveListParams,
} from "../types"

// ── Drive ───────────────────────────────────────────────────────────────────

/**
 * Lista arquivos do Drive de um workspace.
 *
 * `page`/`page_size` são obrigatoriamente enviados: o backend corta em 50 por
 * padrão e os dois consumidores nunca mandavam nada, então tudo além do 50º
 * arquivo era inalcançável pela UI enquanto o cabeçalho anunciava o total
 * real.
 */
export function getDriveFiles(params: import("../types").IDriveListParams) {
  return get<import("../types").IDriveFileList>(
    `/drive${qs(params as unknown as Record<string, string | number | undefined>)}`,
  )
}

/** Upload de um arquivo para o Drive do workspace (multipart).
 *
 *  O axios monta o boundary sozinho a partir do FormData — fixar
 *  `Content-Type: multipart/form-data` na mão, como as páginas faziam, gera
 *  um header SEM boundary. Funcionava porque o axios o sobrescrevia. */
export function uploadDriveFile(workspaceId: string, file: File) {
  const form = new FormData()
  form.append("file", file)
  // O retorno é o `WorkspaceFileOut` do arquivo criado. Era `unknown`, e a
  // página /drive de fato só olha o erro — mas os anexos da Home guardam o
  // `id_hash` do que subiu, e sem o tipo isso seria um cast na mão.
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
