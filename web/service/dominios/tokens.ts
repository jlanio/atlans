// service/dominios/tokens.ts — recorte de GisFlowService (F5/A12).

import { get, post, delComRetorno } from "../http"
import { resolveResponse } from "../resolveResponse"
import type {
  ApiToken, ApiTokenCreate, ApiTokenCreated,
} from "../types"

// ── Access tokens (API) ───────────────────────────────────────────────────
//
// Personal, like credentials: they are only good for what the owner's account
// can already do. Errors come as `{ error, message }` — 422 for validation and
// 409 at the ceiling of 20 active tokens — and `resolveResponse` already
// extracts the message.

/** Most recent first. */
export function listApiTokens() { return get<ApiToken[]>("/auth/tokens") }

/** 201 with the secret in plaintext (`token`) — the only time it appears. */
export function createApiToken(payload: ApiTokenCreate) {
  return post<ApiTokenCreated>("/auth/tokens", payload)
}

/** Revocation, not deletion: the backend returns the token already marked as
 *  `revoked`, and the list keeps showing it. */
export function revokeApiToken(id: string) {
  return delComRetorno<ApiToken>(`/auth/tokens/${encodeURIComponent(id)}`)
}
