/**
 * /login e /register viraram redirecionamentos: a entrada é o modal da Home.
 * O `redirect` do Next LANÇA (é assim que ele interrompe o render) — o mock
 * imita isso e captura o destino.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"

const nav = vi.hoisted(() => ({
  redirect: vi.fn((destino: string) => { throw new Error(`NEXT_REDIRECT ${destino}`) }),
}))
vi.mock("next/navigation", () => ({ redirect: nav.redirect }))

import LoginPage from "@/app/(auth)/login/page"
import RegisterPage from "@/app/(auth)/register/page"

beforeEach(() => { nav.redirect.mockClear() })

describe("/login e /register redirecionam para a Home com o modal", () => {
  it("/login leva o callbackUrl interno", async () => {
    await expect(LoginPage({ searchParams: Promise.resolve({ callbackUrl: "/projects" }) })).rejects.toThrow("NEXT_REDIRECT")
    expect(nav.redirect).toHaveBeenCalledWith("/?entrar=1&callbackUrl=%2Fprojects")
  })

  it("/login descarta um callbackUrl que levaria a outro host", async () => {
    await expect(LoginPage({ searchParams: Promise.resolve({ callbackUrl: "//evil.example" }) })).rejects.toThrow("NEXT_REDIRECT")
    expect(nav.redirect).toHaveBeenCalledWith("/?entrar=1")
  })

  it("/login sem callbackUrl abre só o modal", async () => {
    await expect(LoginPage({ searchParams: Promise.resolve({}) })).rejects.toThrow("NEXT_REDIRECT")
    expect(nav.redirect).toHaveBeenCalledWith("/?entrar=1")
  })

  it("/register abre o cadastro", () => {
    expect(() => RegisterPage()).toThrow("NEXT_REDIRECT")
    expect(nav.redirect).toHaveBeenCalledWith("/?cadastro=1")
  })
})
