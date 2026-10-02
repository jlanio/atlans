/**
 * O proxy /terra precisa passar pelo middleware (bug do logout espúrio): antes
 * ele estava EXCLUÍDO do matcher, então renovava a sessão por conta própria num
 * caminho que descartava o cookie rotacionado. Este teste tranca o contrato do
 * matcher: /terra agora casa; as demais rotas públicas continuam de fora.
 */
import { describe, it, expect, vi } from "vitest"

vi.mock("next-auth", () => ({
  default: () => ({ handlers: {}, signIn: vi.fn(), signOut: vi.fn(), auth: (fn: unknown) => fn }),
}))
vi.mock("next-auth/providers/credentials", () => ({ default: () => ({}) }))

import { config } from "@/proxy"

const re = new RegExp(`^${config.matcher[0]}$`)

describe("matcher do middleware", () => {
  it("passa a cobrir o proxy /terra", () => {
    expect(re.test("/terra/workflows")).toBe(true)
    expect(re.test("/terra/artifacts/portal/abc")).toBe(true)
  })

  it("continua cobrindo as rotas de app", () => {
    expect(re.test("/projects")).toBe(true)
    expect(re.test("/workflow/create")).toBe(true)
    expect(re.test("/admin/users")).toBe(true)
    // /dashboard passa pelo middleware (o portão de papel do admin mora lá).
    expect(re.test("/dashboard")).toBe(true)
    // A Home `/` passa a ser COBERTA: sem o `|$` no matcher ela é protegida por
    // auth e recebe o SESSION_HEADER, em vez de escapar e cair no auth() do
    // layout (o double-refresh). Antes deste PR, `/` ficava de fora.
    expect(re.test("/")).toBe(true)
  })

  it("continua EXCLUINDO auth, portal público e estáticos", () => {
    for (const p of ["/share/abc", "/api/auth/session", "/api/csp-report", "/login", "/register",
                     "/reset-password", "/verify-email", "/internal/x",
                     "/_next/static/x", "/favicon.ico",
                     // O editor de código (public/monaco): arquivos públicos do
                     // pacote, que não precisam de auth() nem de Set-Cookie.
                     "/monaco/vs/loader.js", "/monaco/vs/editor/editor.main.css"]) {
      expect(re.test(p), p).toBe(false)
    }
  })
})
