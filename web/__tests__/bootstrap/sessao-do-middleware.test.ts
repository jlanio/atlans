/**
 * Handoff of the session from the middleware to SSR (SESSION_HEADER in auth.ts).
 *
 * The dashboard layout called `auth()` in the Server Component. That `auth()` builds
 * the Request from `headers()`, where Next does NOT merge the cookies the
 * middleware just wrote — so, with an expired access_token, the RSC saw the
 * same expired `expires_at` and fired a SECOND POST /auth/refresh per
 * load (whose Set-Cookie next-auth still discards on the RSC path).
 * Doubling that traffic blows the 20/min rate limit, which in the backend is a single
 * bucket for the whole platform, and the 429 becomes a mass logout.
 *
 * These tests pin the handoff contract: what the middleware writes the layout
 * can read, and what does not look like one of our sessions is refused (so the layout
 * falls back to `auth()` instead of hydrating with garbage).
 */
import { describe, it, expect, vi } from "vitest"

// auth.ts calls NextAuth() at the top of the module; here only the pure
// serialization helpers matter, so the provider and NextAuth itself become stubs.
vi.mock("next-auth", () => ({
  default: () => ({ handlers: {}, signIn: vi.fn(), signOut: vi.fn(), auth: vi.fn() }),
}))
vi.mock("next-auth/providers/credentials", () => ({ default: () => ({}) }))

import { SESSION_HEADER, encodeSessionHeader, decodeSessionHeader } from "@/auth"

const sessao = {
  user: {
    id_hash: "u_abc123",
    username: "João Ção",
    email: "joao@exemplo.com.br",
    role: "user",
    agent_quota: 3,
    workspace_id: "ws_1",
    access_token: "eyJhbGciOiJIUzI1NiJ9.payload.assinatura",
  },
  expires: "2026-01-01T00:00:00.000Z",
}

describe("handoff de sessão middleware → SSR", () => {
  it("o nome do cabeçalho é o mesmo dos dois lados", () => {
    // If this value diverges between middleware and layout, the layout silently goes
    // back to the auth() fallback and the duplicate refresh comes back to life.
    expect(SESSION_HEADER).toBe("x-atlans-session")
  })

  it("round-trip preserva o access_token e caracteres não-ASCII", () => {
    const raw = encodeSessionHeader(sessao)
    expect(raw).not.toBeNull()
    // An HTTP header does not carry bytes outside latin-1: the value has to go out
    // percent-encoded, otherwise the "ã" breaks writing the header on the Edge.
    expect(raw).toMatch(/^[\x20-\x7E]+$/)
    expect(decodeSessionHeader(raw)).toEqual(sessao)
  })

  it("o valor cabe de fato num cabeçalho de request real", () => {
    const h = new Headers()
    h.set(SESSION_HEADER, encodeSessionHeader(sessao) as string)
    expect(decodeSessionHeader(h.get(SESSION_HEADER))).toEqual(sessao)
  })

  it("recusa ausência, lixo e sessão sem id_hash", () => {
    expect(decodeSessionHeader(null)).toBeNull()
    expect(decodeSessionHeader("")).toBeNull()
    expect(decodeSessionHeader("%%%")).toBeNull() // invalid percent-decode
    expect(decodeSessionHeader("nao-e-json")).toBeNull()
    expect(decodeSessionHeader(encodeURIComponent('"texto"'))).toBeNull()
    expect(decodeSessionHeader(encodeURIComponent("{}"))).toBeNull()
    expect(decodeSessionHeader(encodeURIComponent('{"user":{}}'))).toBeNull()
  })

  it("desiste de sessão grande demais em vez de estourar o limite de cabeçalho", () => {
    // A giant header kills the whole request in the proxy/Node; better for the
    // layout to fall back to auth() than for the page not to load.
    const gorda = { user: { ...sessao.user, access_token: "x".repeat(9000) } }
    expect(encodeSessionHeader(gorda)).toBeNull()
  })

  it("sessão nula não vira cabeçalho", () => {
    expect(encodeSessionHeader(null)).toBeNull()
    expect(encodeSessionHeader(undefined)).toBeNull()
  })
})
