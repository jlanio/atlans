// web/lib/respostas.ts
//
// What a screen does with the `IResponse` that `GisFlowService` returns.
//
// The transport (service/http.ts) NEVER rejects: a network drop, a 4xx and a
// 5xx come back resolved, with `error` filled in and `data` undefined. A
// `try/catch` around the call is dead code — and whoever reads only `data`
// turns the failure into a false statement. That is what happened in the
// editor: a run's log "expired" when the network dropped, and the recent runs
// and the artifact and Drive file pickers said "none" when they had not even
// asked.
//
// The pattern is that of the editor's neighboring screens (version history,
// pins, cancel run): a toast with the screen's title and the server's message.

import type { IResponse } from "@/service/types"
import { createToast } from "@/utils/createToast"

/**
 * The response's data — or `null`, after reporting the failure in a toast.
 *
 * `null` means "I don't know", not "empty": the list that receives it must not
 * fall into the "no items" state, which is what the person would read as the
 * answer. A response without a body also returns `null`; this is for reads,
 * which always have one.
 */
export function dadoOuAviso<T>(res: IResponse<T>, titulo: string): T | null {
  if (res.error) {
    createToast.error(titulo, res.error.message)
    return null
  }
  return res.data ?? null
}
