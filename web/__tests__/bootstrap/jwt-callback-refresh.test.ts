/**
 * Renovação do access token no callback jwt (web/auth.ts) — o coração da
 * correção do bug de logout espúrio.
 *
 * Antes, QUALQUER resposta não-2xx de /auth/refresh (429 do rate limit, 5xx,
 * timeout de rede) virava `token.error = "RefreshTokenExpired"`, que o
 * middleware e o SessionSync leem para mandar o usuário ao /login — um soluço
 * transitório do backend deslogava. E o erro nunca era limpo num refresh
 * bem-sucedido, então grudava. Estes testes trancam a distinção transitório ×
 * terminal e a limpeza do erro.
 */
import { describe, it, expect, vi, beforeEach, type Mock } from "vitest"

// auth.ts chama NextAuth() no topo do módulo; aqui só interessa a função pura
// jwtCallback, então NextAuth e o provider viram stubs.
vi.mock("next-auth", () => ({
  default: () => ({ handlers: {}, signIn: vi.fn(), signOut: vi.fn(), auth: vi.fn() }),
}))
vi.mock("next-auth/providers/credentials", () => ({ default: () => ({}) }))

import { jwtCallback, ACCESS_TTL_MS, REFRESH_BACKOFF_MS } from "@/auth"
import type { JWT } from "next-auth/jwt"

const AGORA = 1_000_000_000_000
const now = () => AGORA

/** Token válido, já autenticado, com o access EXPIRADO (força o ramo de refresh). */
function tokenExpirado(over: Partial<JWT> = {}): JWT {
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
  // Tipado com a assinatura de `fetch`: `jwtCallback` recebe `fetchFn?: typeof
  // fetch`, e um `vi.fn()` cru (Mock<Procedure>) não é atribuível a ela.
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
    const out = await jwtCallback({ token: tokenExpirado({ access_token_expires_at: AGORA + 60_000 }) }, { fetchFn, now })
    expect(fetchFn).not.toHaveBeenCalled()
    expect(out.access_token).toBe("acc-velho")
  })

  it("refresh 200: troca os tokens e limpa erro grudado", async () => {
    fetchFn.mockResolvedValue(resposta(200, { access_token: "acc-novo", refresh_token: "ref-novo" }))
    const out = await jwtCallback({ token: tokenExpirado({ error: "RefreshTokenExpired" }) }, { fetchFn, now })
    expect(out.access_token).toBe("acc-novo")
    expect(out.refresh_token).toBe("ref-novo")
    expect(out.access_token_expires_at).toBe(AGORA + ACCESS_TTL_MS)
    expect(out.error).toBeUndefined()  // ← erro grudado foi limpo
  })

  it("refresh 200 sem refresh_token novo: preserva o refresh_token atual", async () => {
    fetchFn.mockResolvedValue(resposta(200, { access_token: "acc-novo" }))
    const out = await jwtCallback({ token: tokenExpirado() }, { fetchFn, now })
    expect(out.access_token).toBe("acc-novo")
    expect(out.refresh_token).toBe("ref-velho")
  })

  it("401 (refresh inválido/expirado/reusado): TERMINAL — seta RefreshTokenExpired", async () => {
    fetchFn.mockResolvedValue(resposta(401, { detail: "Refresh token inválido ou expirado." }))
    const out = await jwtCallback({ token: tokenExpirado() }, { fetchFn, now })
    expect(out.error).toBe("RefreshTokenExpired")
    // tokens não são trocados; a sessão será encerrada pelo middleware/SessionSync
    expect(out.access_token).toBe("acc-velho")
  })

  it("429 (rate limit): TRANSITÓRIO — não desloga, mantém tokens e reagenda", async () => {
    fetchFn.mockResolvedValue(resposta(429, { detail: "Muitas renovações." }))
    const out = await jwtCallback({ token: tokenExpirado() }, { fetchFn, now })
    expect(out.error).toBeUndefined()          // ← NÃO desloga por rate limit
    expect(out.access_token).toBe("acc-velho")
    expect(out.refresh_token).toBe("ref-velho")
    expect(out.access_token_expires_at).toBe(AGORA + REFRESH_BACKOFF_MS)
  })

  it("500/503 (erro do servidor): TRANSITÓRIO — não desloga", async () => {
    for (const status of [500, 502, 503, 504]) {
      fetchFn.mockResolvedValue(resposta(status))
      const out = await jwtCallback({ token: tokenExpirado() }, { fetchFn, now })
      expect(out.error, `status ${status}`).toBeUndefined()
      expect(out.access_token_expires_at).toBe(AGORA + REFRESH_BACKOFF_MS)
    }
  })

  it("erro de rede/timeout: TRANSITÓRIO — não desloga", async () => {
    fetchFn.mockRejectedValue(new Error("ECONNRESET"))
    const out = await jwtCallback({ token: tokenExpirado() }, { fetchFn, now })
    expect(out.error).toBeUndefined()
    expect(out.access_token).toBe("acc-velho")
    expect(out.access_token_expires_at).toBe(AGORA + REFRESH_BACKOFF_MS)
  })
})
