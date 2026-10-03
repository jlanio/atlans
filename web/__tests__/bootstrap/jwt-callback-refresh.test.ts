/**
 * Access token renewal in the jwt callback (web/auth.ts) — the heart of the
 * fix for the spurious logout bug.
 *
 * Before, ANY non-2xx response from /auth/refresh (rate limit 429, 5xx,
 * network timeout) became `token.error = "RefreshTokenExpired"`, which the
 * middleware and SessionSync read to send the user to /login — a transient
 * backend hiccup logged people out. And the error was never cleared on a successful
 * refresh, so it stuck. These tests lock the transient ×
 * terminal distinction and the clearing of the error.
 */
import { describe, it, expect, vi, beforeEach, type Mock } from "vitest"

// auth.ts calls NextAuth() at the top of the module; here only the pure function
// jwtCallback matters, so NextAuth and the provider become stubs.
vi.mock("next-auth", () => ({
  default: () => ({ handlers: {}, signIn: vi.fn(), signOut: vi.fn(), auth: vi.fn() }),
}))
vi.mock("next-auth/providers/credentials", () => ({ default: () => ({}) }))

import { jwtCallback, ACCESS_TTL_MS, REFRESH_BACKOFF_MS } from "@/auth"
import type { JWT } from "next-auth/jwt"

const AGORA = 1_000_000_000_000
const now = () => AGORA

/** Valid token, already authenticated, with the access EXPIRED (forces the refresh branch). */
function expiredToken(over: Partial<JWT> = {}): JWT {
  return {
    id_hash: "u1", username: "ana", role: "user", agent_quota: 0, workspace_id: null,
    access_token: "acc-velho", refresh_token: "ref-velho",
    access_token_expires_at: AGORA - 1000,
    ...over,
  } as JWT
}

function resposta(status: number, body: unknown = {}): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response
}

describe("jwtCallback — renovação e distinção transitório × terminal", () => {
  // Typed with `fetch`'s signature: `jwtCallback` takes `fetchFn?: typeof
  // fetch`, and a raw `vi.fn()` (Mock<Procedure>) is not assignable to it.
  let fetchFn: Mock<typeof fetch>
  beforeEach(() => { fetchFn = vi.fn<typeof fetch>() })

  it("login: popula o token, agenda expiração e limpa erro anterior", async () => {
    const user = {
      id_hash: "u1", username: "ana", role: "admin", agent_quota: 2, workspace_id: "ws1",
      access_token: "acc", refresh_token: "ref",
    }
    const out = await jwtCallback({ token: { error: "RefreshTokenExpired" } as unknown as JWT, user }, { fetchFn, now })
    expect(out.access_token).toBe("acc")
    expect(out.refresh_token).toBe("ref")
    expect(out.role).toBe("admin")
    expect(out.access_token_expires_at).toBe(AGORA + ACCESS_TTL_MS)
    expect(out.error).toBeUndefined()
    expect(fetchFn).not.toHaveBeenCalled()
  })

  it("dentro da validade: retorna sem renovar (sem fetch)", async () => {
    const out = await jwtCallback({ token: expiredToken({ access_token_expires_at: AGORA + 60_000 }) }, { fetchFn, now })
    expect(fetchFn).not.toHaveBeenCalled()
    expect(out.access_token).toBe("acc-velho")
  })

  it("refresh 200: troca os tokens e limpa erro grudado", async () => {
    fetchFn.mockResolvedValue(resposta(200, { access_token: "acc-novo", refresh_token: "ref-novo" }))
    const out = await jwtCallback({ token: expiredToken({ error: "RefreshTokenExpired" }) }, { fetchFn, now })
    expect(out.access_token).toBe("acc-novo")
    expect(out.refresh_token).toBe("ref-novo")
    expect(out.access_token_expires_at).toBe(AGORA + ACCESS_TTL_MS)
    expect(out.error).toBeUndefined()  // ← stuck error was cleared
  })

  it("refresh 200 sem refresh_token novo: preserva o refresh_token atual", async () => {
    fetchFn.mockResolvedValue(resposta(200, { access_token: "acc-novo" }))
    const out = await jwtCallback({ token: expiredToken() }, { fetchFn, now })
    expect(out.access_token).toBe("acc-novo")
    expect(out.refresh_token).toBe("ref-velho")
  })

  it("401 (refresh inválido/expirado/reusado): TERMINAL — seta RefreshTokenExpired", async () => {
    fetchFn.mockResolvedValue(resposta(401, { detail: "Refresh token inválido ou expirado." }))
    const out = await jwtCallback({ token: expiredToken() }, { fetchFn, now })
    expect(out.error).toBe("RefreshTokenExpired")
    // tokens are not swapped; the session will be ended by the middleware/SessionSync
    expect(out.access_token).toBe("acc-velho")
  })

  it("429 (rate limit): TRANSITÓRIO — não desloga, mantém tokens e reagenda", async () => {
    fetchFn.mockResolvedValue(resposta(429, { detail: "Muitas renovações." }))
    const out = await jwtCallback({ token: expiredToken() }, { fetchFn, now })
    expect(out.error).toBeUndefined()          // ← does NOT log out because of the rate limit
    expect(out.access_token).toBe("acc-velho")
    expect(out.refresh_token).toBe("ref-velho")
    expect(out.access_token_expires_at).toBe(AGORA + REFRESH_BACKOFF_MS)
  })

  it("500/503 (erro do servidor): TRANSITÓRIO — não desloga", async () => {
    for (const status of [500, 502, 503, 504]) {
      fetchFn.mockResolvedValue(resposta(status))
      const out = await jwtCallback({ token: expiredToken() }, { fetchFn, now })
      expect(out.error, `status ${status}`).toBeUndefined()
      expect(out.access_token_expires_at).toBe(AGORA + REFRESH_BACKOFF_MS)
    }
  })

  it("erro de rede/timeout: TRANSITÓRIO — não desloga", async () => {
    fetchFn.mockRejectedValue(new Error("ECONNRESET"))
    const out = await jwtCallback({ token: expiredToken() }, { fetchFn, now })
    expect(out.error).toBeUndefined()
    expect(out.access_token).toBe("acc-velho")
    expect(out.access_token_expires_at).toBe(AGORA + REFRESH_BACKOFF_MS)
  })
})
