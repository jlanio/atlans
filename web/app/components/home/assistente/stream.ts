// web/app/components/home/assistente/stream.ts
//
// Reading the assistant stream, in one place.
//
// The two consumers — `useAssistente` (Home) and `useAssistenteEditor` (editor
// drawer) — were born as forks of each other, and the copies had already
// diverged: the editor's did not release the reader in `finally`, and a "Parar"
// (or switching workflows) that aborted the read midway left the connection
// hanging until the server gave up on its own.
//
// What belongs to each hook stays in it: the route and the POST body, the
// `conversa` frame, the replay and the confirmation (Home only) — and the
// `erroDaResposta` status table, which differs ON PURPOSE between the two routes
// and so comes in here as a parameter.
//
// Decoding the frames and applying them to the turn belongs to `quadros.ts`, pure.
import type { Dispatch, SetStateAction } from "react"

import type { IAssistantState } from "@/service/types"
import {
  aplicarQuadro,
  cotaDoQuadro,
  criarDecodificador,
  type SSEFrame,
  type AssistantTurn,
} from "./quadros"

/** The error of a turn the network cut: the `fetch` rejected or the stream broke. */
export const NO_CONNECTION = {
  code: "sem_conexao",
  message: "A conversa foi interrompida.",
  hint: "confira a conexão e tente de novo",
}

let sequencia = 0
/** Turn id — render key and target of `applyToTurn`. Unique within the tab. */
export const nextTurnId = () => `t${++sequencia}`

/** Applies a frame to turn `id`, without touching the others. */
export function applyToTurn(
  setTurns: Dispatch<SetStateAction<AssistantTurn[]>>,
  id: string,
  quadro: SSEFrame,
): void {
  setTurns((anteriores) => anteriores.map((t) => (t.id === id ? aplicarQuadro(t, quadro) : t)))
}

/**
 * The `cota` frame is not a turn block: it is the window's running total,
 * charged on each model response, and it raises the spend in the state — the
 * donut moves DURING the turn. The deadline stays as it was: rereading `/estado`
 * at the end of the turn is what updates it. Returns whether the frame was a
 * quota frame (and has already been handled).
 */
export function applyQuota(
  setAppState: Dispatch<SetStateAction<IAssistantState | null>>,
  quadro: SSEFrame,
): boolean {
  const cota = cotaDoQuadro(quadro)
  if (!cota) return false
  setAppState((atual) => atual
    ? { ...atual, cota: { gasto: cota.gasto, teto: cota.teto, reabre_em_segundos: atual.cota?.reabre_em_segundos ?? null } }
    : atual)
  return true
}

/**
 * Reads the `text/event-stream` to the end, handing each COMPLETE frame to
 * `tratar` — a frame split between two `read()` calls waits for the rest.
 *
 * Rejects with the read error: the "Parar" `AbortError` and a network drop
 * reach the caller, which decides what each one becomes in the turn.
 */
export async function lerQuadrosSSE(
  corpo: ReadableStream<Uint8Array>,
  tratar: (quadro: SSEFrame) => void,
): Promise<void> {
  const leitor = corpo.getReader()
  const decodificar = criarDecodificador()
  // `stream: true` on the text decoder for the same reason as the frame one:
  // a multi-byte character (and Portuguese is full of them) can start in one
  // `read()` and end in the next.
  const utf8 = new TextDecoder()
  try {
    for (;;) {
      const { done, value } = await leitor.read()
      if (done) {
        // The final `decode()` flushes what was left of a character split in the
        // last chunk. In practice the stream ends at the `\n\n` of `fim`, but
        // relying on that would be relying on the frame format.
        for (const quadro of decodificar(utf8.decode())) tratar(quadro)
        return
      }
      for (const quadro of decodificar(utf8.decode(value, { stream: true }))) tratar(quadro)
    }
  } finally {
    // Release the reader even when the abort (or a frame `tratar` could not
    // digest) cuts the read midway — otherwise the connection hangs until the
    // server gives up on its own.
    await leitor.cancel().catch(() => {})
  }
}

/** The code and the sentence for each status the route rejects BEFORE becoming a stream. */
export type RouteErrors = Record<number, { code: string; message: string }>

/**
 * The API error body when the response did not even become a stream.
 *
 * The shape is `{error, message, status_code}` (`app/core/utils/error_handlers.py`),
 * and the 503 for the disabled assistant comes with `detail`: the server's
 * sentence, when present, wins over the table's. What cannot be read becomes the
 * table's sentence (or an honest "A API respondeu N.") instead of "undefined".
 *
 * `padroes` is the ROUTE's table, and the two differ on purpose: the Home's 429
 * is `muitas_requisicoes` because, in its stream, `rate_limited` is the DAILY
 * quota; the editor's 409 is the conversation in progress on the workflow, the
 * Home's is the confirmation that expired.
 */
export async function erroDaResposta(resposta: Response, padroes: RouteErrors): Promise<Record<string, unknown>> {
  const padrao = padroes[resposta.status] ?? { code: "erro_http", message: `A API respondeu ${resposta.status}.` }
  try {
    const corpo = await resposta.json()
    const mensagem = corpo?.message ?? corpo?.detail
    return typeof mensagem === "string" && mensagem ? { ...padrao, message: mensagem } : padrao
  } catch {
    return padrao
  }
}
