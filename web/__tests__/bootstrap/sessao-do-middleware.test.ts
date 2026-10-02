/**
 * Repasse da sessão do middleware para o SSR (SESSION_HEADER em auth.ts).
 *
 * O layout do dashboard chamava `auth()` no Server Component. Esse `auth()` monta
 * a Request a partir de `headers()`, onde o Next NÃO mescla os cookies que o
 * middleware acabou de gravar — então, com o access_token vencido, o RSC via o
 * mesmo `expires_at` vencido e disparava um SEGUNDO POST /auth/refresh por
 * carregamento (cujo Set-Cookie o next-auth ainda descarta no caminho RSC).
 * Dobrar esse tráfego estoura o rate limit de 20/min, que no backend é um balde
 * único para toda a plataforma, e o 429 vira logout em massa.
 *
 * Estes testes fixam o contrato do handoff: o que o middleware escreve o layout
 * consegue ler, e o que não tem cara de sessão nossa é recusado (para o layout
 * cair no fallback de `auth()` em vez de hidratar com lixo).
 */
import { describe, it, expect, vi } from "vitest"

// auth.ts chama NextAuth() no topo do módulo; aqui só interessam os helpers
// puros de serialização, então o provider e o próprio NextAuth viram stubs.
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
    // Se este valor divergir entre middleware e layout, o layout volta
    // silenciosamente ao fallback de auth() e o refresh duplicado ressuscita.
    expect(SESSION_HEADER).toBe("x-atlans-session")
  })

  it("round-trip preserva o access_token e caracteres não-ASCII", () => {
    const raw = encodeSessionHeader(sessao)
    expect(raw).not.toBeNull()
    // Cabeçalho HTTP não carrega bytes fora do latin-1: o valor tem que sair
    // percent-encoded, senão o "ã" derruba a escrita do header no Edge.
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
    expect(decodeSessionHeader("%%%")).toBeNull() // percent-decode inválido
    expect(decodeSessionHeader("nao-e-json")).toBeNull()
    expect(decodeSessionHeader(encodeURIComponent('"texto"'))).toBeNull()
    expect(decodeSessionHeader(encodeURIComponent("{}"))).toBeNull()
    expect(decodeSessionHeader(encodeURIComponent('{"user":{}}'))).toBeNull()
  })

  it("desiste de sessão grande demais em vez de estourar o limite de cabeçalho", () => {
    // Cabeçalho gigante derruba a requisição inteira no proxy/Node; melhor o
    // layout cair no fallback de auth() do que a página não carregar.
    const gorda = { user: { ...sessao.user, access_token: "x".repeat(9000) } }
    expect(encodeSessionHeader(gorda)).toBeNull()
  })

  it("sessão nula não vira cabeçalho", () => {
    expect(encodeSessionHeader(null)).toBeNull()
    expect(encodeSessionHeader(undefined)).toBeNull()
  })
})
