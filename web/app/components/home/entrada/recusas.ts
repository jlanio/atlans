// web/app/components/home/entrada/recusas.ts
//
// What the sign-in shows when the server rejects. The server only speaks
// Portuguese: in Portuguese the screen shows its message, as always; in English
// and Spanish, the language's text, chosen by status.
//
// Only a rejection that IS from the server goes through this per-status
// translation — the body `http_exception_handler` writes
// (`error: "http_exception"`). The per-IP limiter's 429
// (`{detail: "Too Many Requests"}`), the /terra proxy's 502
// (`{detail: "Serviço indisponível"}`), an unexpected 500 and a CDN's error
// page have another body, and the same status there means something else: a
// 429 without the server body is not a locked account, and a 403 from a CDN is
// not a suspended account.

import type { AxiosError } from "axios"

type Corpo = { error?: string; message?: string; detail?: string }

/** The rejection came from the server itself (and not from the limiter, the proxy or a CDN). */
export function isServerRejection(data: unknown): boolean {
  return !!data && typeof data === "object" && (data as Corpo).error === "http_exception"
}

export interface LinkRejectionTexts {
  tokenInvalido: string
  muitasTentativas: string
  servidorIndisponivel: string
}

/**
 * The rejection of an e-mail link (verify, reset). In Portuguese, the server
 * message as it came, or "token inválido" when none came — as always. In the
 * other languages, by status: the token rejections (400 and 404) become the
 * language's "token inválido".
 */
export function linkRejectionText(erro: unknown, traduzir: boolean, t: LinkRejectionTexts): string {
  const resposta = (erro as AxiosError<Corpo> | null)?.response
  if (!traduzir) return resposta?.data?.message ?? t.tokenInvalido
  if (!resposta || resposta.status >= 500) return t.servidorIndisponivel
  if (resposta.status === 429) return t.muitasTentativas
  return t.tokenInvalido
}
