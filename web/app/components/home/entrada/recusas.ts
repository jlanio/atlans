// web/app/components/home/entrada/recusas.ts
//
// O que a entrada mostra quando o servidor recusa. O servidor só fala
// português: em português a tela mostra a mensagem dele, a de sempre; em inglês
// e espanhol, o texto do idioma, escolhido pelo status.
//
// Só a recusa que É do servidor passa por essa tradução por status — o corpo
// que o `http_exception_handler` escreve (`error: "http_exception"`). O 429 do
// limitador por IP (`{detail: "Too Many Requests"}`), o 502 do proxy /terra
// (`{detail: "Serviço indisponível"}`), o 500 inesperado e a página de erro de
// uma CDN têm outro corpo, e o mesmo status ali quer dizer outra coisa: um 429
// sem o corpo do servidor não é conta bloqueada, e um 403 de uma CDN não é a
// conta suspensa.

import type { AxiosError } from "axios"

type Corpo = { error?: string; message?: string; detail?: string }

/** A recusa veio do próprio servidor (e não do limitador, do proxy ou de uma CDN). */
export function ehRecusaDoServidor(data: unknown): boolean {
  return !!data && typeof data === "object" && (data as Corpo).error === "http_exception"
}

export interface TextosDaRecusaDoLink {
  tokenInvalido: string
  muitasTentativas: string
  servidorIndisponivel: string
}

/**
 * A recusa de um link do e-mail (verificar, redefinir). Em português, a
 * mensagem do servidor como veio, ou "token inválido" quando não veio nenhuma
 * — o de sempre. Nos outros idiomas, pelo status: as recusas do token (400 e
 * 404) viram o "token inválido" do idioma.
 */
export function textoDaRecusaDoLink(erro: unknown, traduzir: boolean, t: TextosDaRecusaDoLink): string {
  const resposta = (erro as AxiosError<Corpo> | null)?.response
  if (!traduzir) return resposta?.data?.message ?? t.tokenInvalido
  if (!resposta || resposta.status >= 500) return t.servidorIndisponivel
  if (resposta.status === 429) return t.muitasTentativas
  return t.tokenInvalido
}
