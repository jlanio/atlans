/**
 * O layout do dashboard não pode chamar `auth()` quando o middleware já entregou
 * a sessão.
 *
 * Cada `auth()` num Server Component com o access_token vencido custa um
 * POST /auth/refresh extra — inútil, porque o Set-Cookie do caminho RSC é
 * descartado pelo próprio next-auth — contra um rate limit de 20/min que é balde
 * único de toda a plataforma. Ao estourar, o 429 vira RefreshTokenExpired e
 * derruba todo mundo para /login.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"

const { authSpy, headersSpy, cookiesSpy } = vi.hoisted(() => ({
  authSpy: vi.fn(),
  headersSpy: vi.fn(),
  cookiesSpy: vi.fn(),
}))

vi.mock("next-auth", () => ({
  default: () => ({ handlers: {}, signIn: vi.fn(), signOut: vi.fn(), auth: authSpy }),
}))
vi.mock("next-auth/providers/credentials", () => ({ default: () => ({}) }))
vi.mock("next/headers", () => ({ headers: headersSpy, cookies: cookiesSpy }))
// O layout importa o CSS global; o PostCSS do Tailwind não roda sob o vitest.
vi.mock("@/app/globals.css", () => ({}))

// Filhos pesados: o teste olha só a decisão do layout, não a árvore renderizada.
const { passthrough } = vi.hoisted(() => ({
  passthrough: ({ children }: { children?: unknown }) => children ?? null,
}))
vi.mock("@/app/components/providers", () => ({ default: passthrough }))
vi.mock("@/app/components/sidebar", () => ({ default: passthrough }))
vi.mock("@/context/ThemeContext", () => ({ ThemeProvider: passthrough }))
vi.mock("@/context/WorkspaceContext", () => ({ WorkspaceProvider: passthrough }))
vi.mock("@/context/ActiveRunsContext", () => ({ ActiveRunsProvider: passthrough }))

import { SESSION_HEADER, encodeSessionHeader } from "@/auth"
import Layout from "@/app/(dashboard)/layout"

const sessaoDoMiddleware = {
  user: { id_hash: "u_1", username: "ana", role: "user", access_token: "TOKEN-RENOVADO" },
  expires: "2026-01-01T00:00:00.000Z",
}

/** Pega a prop `session` entregue ao <Providers>, seja qual for a profundidade. */
function sessionDoElemento(el: unknown): unknown {
  const props = (el as { props?: Record<string, unknown> })?.props
  if (!props) return undefined
  if ("session" in props) return props.session
  return sessionDoElemento(props.children)
}

beforeEach(() => {
  authSpy.mockReset()
  headersSpy.mockReset()
  cookiesSpy.mockReset()
  // O layout lê o cookie sidebar_state (defaultOpen); irrelevante para a sessão.
  cookiesSpy.mockResolvedValue({ get: () => undefined })
})

describe("layout do dashboard", () => {
  it("usa a sessão do middleware e NÃO chama auth() de novo", async () => {
    headersSpy.mockResolvedValue(
      new Headers({ [SESSION_HEADER]: encodeSessionHeader(sessaoDoMiddleware) as string }),
    )

    const el = await Layout({ children: null })

    expect(authSpy).not.toHaveBeenCalled()
    expect(sessionDoElemento(el)).toEqual(sessaoDoMiddleware)
  })

  it("cai no auth() quando o middleware não rodou", async () => {
    // Rede de segurança: rota fora do matcher / dev sem middleware. Aqui o
    // refresh duplicado não existe porque o middleware nem chegou a refrescar.
    const daRede = { user: { id_hash: "u_2", access_token: "TOKEN-DO-COOKIE" } }
    headersSpy.mockResolvedValue(new Headers())
    authSpy.mockResolvedValue(daRede)

    const el = await Layout({ children: null })

    expect(authSpy).toHaveBeenCalledTimes(1)
    expect(sessionDoElemento(el)).toEqual(daRede)
  })

  it("cabeçalho corrompido não hidrata o SessionProvider com lixo", async () => {
    headersSpy.mockResolvedValue(new Headers({ [SESSION_HEADER]: "%%%nao-e-json" }))
    authSpy.mockResolvedValue(null)

    const el = await Layout({ children: null })

    expect(authSpy).toHaveBeenCalledTimes(1)
    expect(sessionDoElemento(el)).toBeNull()
  })
})
