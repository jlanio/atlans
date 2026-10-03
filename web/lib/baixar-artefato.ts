// web/lib/baixar-artefato.ts
//
// DOWNLOADING AN ARTIFACT, in a single place. Three screens need this (the
// app's Artifacts table, the Home's Artifacts list and the globe's layer
// panel), and the right path is not obvious: `GET /artifacts/{id}/download`
// does NOT return the file — it returns `{download_url, filename}` as JSON,
// with MinIO's presigned URL. Navigating to the platform endpoint in a new tab
// throws that JSON in the person's face; what downloads is the presigned URL,
// which already carries `Content-Disposition: attachment` in its signature.
//
// Two reasons to go through the service instead of opening the endpoint directly:
//
// 1. The interceptor attaches the JWT. Top-level navigation does not carry a
//    Bearer, so a `protected` artifact would regress to 401.
// 2. The presigned URL is opened in a new tab WITHOUT pulling the file into an
//    in-memory blob — the synchronous `revokeObjectURL` aborted large downloads
//    in Firefox and Safari.
//
// The fetch of the presigned URL does not go through the interceptor, on
// purpose: it points to MinIO, and sending the platform token to another origin
// would leak it.

import { GisFlowService } from "@/service/GisFlowService"

/** The error phrases. Default: the Portuguese of the Artifacts table; the translated Home passes its own. */
export interface DownloadTexts {
  noExecutor: string
  tenteDeNovo: string
}

export const DOWNLOAD_TEXTS_PT: DownloadTexts = {
  noExecutor: "Este arquivo permanece no executor e não pode ser baixado daqui.",
  tenteDeNovo: "Tente de novo.",
}

/**
 * Resolves the presigned URL and opens the download. Returns the error message
 * when it did not work — the caller decides how to show it (toast, inline
 * notice) —, and `null` when it worked. The SERVER's message, when there is
 * one, passes through as it came.
 */
export async function baixarArtefato(
  idHash: string,
  textos: DownloadTexts = DOWNLOAD_TEXTS_PT,
): Promise<string | null> {
  const res = await GisFlowService.getArtifactDownload(idHash)
  if (!res.success || !res.data?.download_url) {
    // 409 is policy, not a failure: the file stayed on the executor because of the
    // `keepLocal` flag and the server cannot fetch it. It deserves its own
    // phrase — "could not download" would send the person retrying forever.
    if (res.status === 409) return textos.noExecutor
    return res.error?.message ?? textos.tenteDeNovo
  }
  window.open(res.data.download_url, "_blank")
  return null
}
