// service/dominios/tokens.ts — recorte de GisFlowService (F5/A12).

import { get, post, delComRetorno } from "../http"
import { resolveResponse } from "../resolveResponse"
import type {
  ApiToken, ApiTokenCreate, ApiTokenCreated,
} from "../types"

// ── Tokens de acesso (API) ─────────────────────────────────────────────────
//
// Pessoais, como as credenciais: valem só para o que a conta do dono já pode
// fazer. Erros vêm como `{ error, message }` — 422 de validação e 409 no teto
// de 20 tokens ativos — e o `resolveResponse` já extrai a mensagem.

/** Mais recente primeiro. */
export function listApiTokens() { return get<ApiToken[]>("/auth/tokens") }

/** 201 com o segredo em claro (`token`) — a única vez que ele aparece. */
export function createApiToken(payload: ApiTokenCreate) {
  return post<ApiTokenCreated>("/auth/tokens", payload)
}

/** Revogação, não exclusão: o backend devolve o token já marcado como
 *  `revoked`, e a lista continua a mostrá-lo. */
export function revokeApiToken(id: string) {
  return delComRetorno<ApiToken>(`/auth/tokens/${encodeURIComponent(id)}`)
}
