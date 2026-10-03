/**
 * The dashboard layout must not call `auth()` when the middleware has already delivered
 * the session.
 *
 * Each `auth()` in a Server Component with an expired access_token costs an
 * extra POST /auth/refresh — useless, because the Set-Cookie of the RSC path is
 * discarded by next-auth itself — against a 20/min rate limit that is a single bucket
 * for the whole platform. When it overflows, the 429 becomes RefreshTokenExpired and
 * kicks everyone out to /login.
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
// The layout imports the global CSS; Tailwind's PostCSS does not run under vitest.
vi.mock("@/app/globals.css", () => ({}))

// Heavy children: the test only looks at the layout's decision, not the rendered tree.
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

const middlewareSession = {
  user: { id_hash: "u_1", username: "ana", role: "user", access_token: "TOKEN-RENOVADO" },
  expires: "2026-01-01T00:00:00.000Z",
}

/** Grabs the `session` prop handed to <Providers>, at whatever depth. */
function sessionOfElement(el: unknown): unknown {
  const props = (el as { props?: Record<string, unknown> })?.props
  if (!props) return undefined
  if ("session" in props) return props.session
  return sessionOfElement(props.children)
}

beforeEach(() => {
  authSpy.mockReset()
  headersSpy.mockReset()
  cookiesSpy.mockReset()
  // The layout reads the sidebar_state cookie (defaultOpen); irrelevant to the session.
  cookiesSpy.mockResolvedValue({ get: () => undefined })
})

describe("layout do dashboard", () => {
  it("usa a sessão do middleware e NÃO chama auth() de novo", async () => {
    headersSpy.mockResolvedValue(
      new Headers({ [SESSION_HEADER]: encodeSessionHeader(middlewareSession) as string }),
    )

    const el = await Layout({ children: null })

    expect(authSpy).not.toHaveBeenCalled()
    expect(sessionOfElement(el)).toEqual(middlewareSession)
  })

  it("cai no auth() quando o middleware não rodou", async () => {
    // Safety net: a route outside the matcher / dev without middleware. Here the
    // duplicate refresh does not exist because the middleware never got to refresh.
    const fromNetwork = { user: { id_hash: "u_2", access_token: "TOKEN-DO-COOKIE" } }
    headersSpy.mockResolvedValue(new Headers())
    authSpy.mockResolvedValue(fromNetwork)

    const el = await Layout({ children: null })

    expect(authSpy).toHaveBeenCalledTimes(1)
    expect(sessionOfElement(el)).toEqual(fromNetwork)
  })

  it("cabeçalho corrompido não hidrata o SessionProvider com lixo", async () => {
    headersSpy.mockResolvedValue(new Headers({ [SESSION_HEADER]: "%%%nao-e-json" }))
    authSpy.mockResolvedValue(null)

    const el = await Layout({ children: null })

    expect(authSpy).toHaveBeenCalledTimes(1)
    expect(sessionOfElement(el)).toBeNull()
  })
})
