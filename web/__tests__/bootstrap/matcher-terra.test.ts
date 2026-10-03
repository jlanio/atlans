/**
 * The /terra proxy needs to go through the middleware (spurious logout bug): before,
 * it was EXCLUDED from the matcher, so it renewed the session on its own on a
 * path that discarded the rotated cookie. This test locks the matcher's
 * contract: /terra now matches; the other public routes stay out.
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
    // /dashboard goes through the middleware (the admin role gate lives there).
    expect(re.test("/dashboard")).toBe(true)
    // The Home `/` is now COVERED: without the `|$` in the matcher it is protected by
    // auth and receives the SESSION_HEADER, instead of escaping and landing in the
    // layout's auth() (the double refresh). Before this PR, `/` was left out.
    expect(re.test("/")).toBe(true)
  })

  it("continua EXCLUINDO auth, portal público e estáticos", () => {
    for (const p of ["/share/abc", "/api/auth/session", "/api/csp-report", "/login", "/register",
                     "/reset-password", "/verify-email", "/internal/x",
                     "/_next/static/x", "/favicon.ico",
                     // The code editor (public/monaco): public files from the
                     // package, which need neither auth() nor Set-Cookie.
                     "/monaco/vs/loader.js", "/monaco/vs/editor/editor.main.css"]) {
      expect(re.test(p), p).toBe(false)
    }
  })
})
