import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"

/**
 * The Chat / Workspace switcher: who sees it, where each side leads, and the
 * attribute on <html> that exists only while the switch animates (it is what
 * gives globals.css the stage and the direction of the slide).
 */

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (q: string) => ({
      matches: false, media: q, onchange: null,
      addEventListener: () => {}, removeEventListener: () => {},
      addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
    }),
  })
})
function largura(px: number) {
  Object.defineProperty(window, "innerWidth", { writable: true, configurable: true, value: px })
}

const sessao = vi.hoisted(() => ({ papel: "admin" as string | undefined }))
vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: sessao.papel === undefined ? null : { user: { role: sessao.papel } },
    status: sessao.papel === undefined ? "loading" : "authenticated",
  }),
}))

// The router with View Transitions is the hook's own business (it has its
// tests); here it is a spy that hands back a transition the test settles.
const roteador = vi.hoisted(() => ({
  push: vi.fn(),
  terminar: () => {},
}))
vi.mock("@/app/hooks/useViewTransition", () => ({
  useViewTransitionRouter: () => ({ push: roteador.push, prefetch: vi.fn() }),
}))

import { SidebarProvider } from "@/app/components/ui/sidebar"
import SeletorDeModo, { ATRIBUTO_DA_TROCA, type Modo } from "@/app/components/sidebar/seletor-de-modo"

function montar(modo: Modo) {
  return render(
    <SidebarProvider>
      <SeletorDeModo modo={modo} />
    </SidebarProvider>,
  )
}
// Expanded and rail variants both render (CSS picks one); the expanded one is the <nav>.
function lado(nome: string) {
  return screen.getByRole("navigation", { name: "Modo" }).querySelector(`a[href="${nome}"]`) as HTMLAnchorElement
}

beforeEach(() => {
  sessao.papel = "admin"
  largura(1280)
  roteador.push.mockReset()
  roteador.push.mockImplementation(() => {
    let terminar = () => {}
    const finished = new Promise<void>((resolve) => { terminar = resolve })
    roteador.terminar = terminar
    return { skipTransition: vi.fn(), finished }
  })
})
afterEach(() => {
  cleanup()
  document.documentElement.removeAttribute(ATRIBUTO_DA_TROCA)
})

describe("SeletorDeModo", () => {
  it("só existe para o admin — quem não é admin não sai da Home", () => {
    sessao.papel = "user"
    montar("chat")
    expect(screen.queryByRole("navigation")).toBeNull()
    expect(screen.queryAllByRole("link")).toHaveLength(0)
  })

  it("enquanto a sessão carrega não aparece (falha fechada)", () => {
    sessao.papel = undefined
    montar("chat")
    expect(screen.queryByRole("navigation")).toBeNull()
    expect(screen.queryAllByRole("link")).toHaveLength(0)
  })

  it("Chat leva à Home e Workspace ao Dashboard, com o lado atual marcado", () => {
    montar("chat")
    expect(lado("/")).toHaveTextContent("Chat")
    expect(lado("/")).toHaveAttribute("aria-current", "page")
    expect(lado("/dashboard")).toHaveTextContent("Workspace")
    expect(lado("/dashboard")).not.toHaveAttribute("aria-current")
  })

  it("no Workspace, o lado marcado é o Workspace", () => {
    montar("workspace")
    expect(lado("/dashboard")).toHaveAttribute("aria-current", "page")
    expect(lado("/")).not.toHaveAttribute("aria-current")
  })

  it("trocar marca a direção no <html> só enquanto a transição dura", async () => {
    montar("chat")
    fireEvent.click(lado("/dashboard"))

    expect(roteador.push).toHaveBeenCalledWith("/dashboard", { maxWaitMs: 600 })
    expect(document.documentElement.getAttribute(ATRIBUTO_DA_TROCA)).toBe("workspace")

    await act(async () => { roteador.terminar() })
    expect(document.documentElement.hasAttribute(ATRIBUTO_DA_TROCA)).toBe(false)
  })

  it("a volta marca a direção 'chat'", () => {
    montar("workspace")
    fireEvent.click(lado("/"))
    expect(roteador.push).toHaveBeenCalledWith("/", { maxWaitMs: 600 })
    expect(document.documentElement.getAttribute(ATRIBUTO_DA_TROCA)).toBe("chat")
  })

  it("sem View Transitions o atributo não fica para trás", () => {
    roteador.push.mockReturnValue(null)
    montar("chat")
    fireEvent.click(lado("/dashboard"))
    expect(roteador.push).toHaveBeenCalled()
    expect(document.documentElement.hasAttribute(ATRIBUTO_DA_TROCA)).toBe(false)
  })

  it("clicar no lado atual não navega", () => {
    montar("chat")
    const evento = fireEvent.click(lado("/"))
    expect(evento).toBe(false) // default prevented: the link does not reload the Home
    expect(roteador.push).not.toHaveBeenCalled()
  })

  it("Ctrl+clique fica com o navegador (nova aba)", () => {
    montar("chat")
    const evento = fireEvent.click(lado("/dashboard"), { ctrlKey: true })
    expect(roteador.push).not.toHaveBeenCalled()
    expect(evento).toBe(true)
  })

  it("no telefone, navega pelo link sem a transição (a gaveta fecharia no meio)", () => {
    largura(500)
    montar("chat")
    const evento = fireEvent.click(lado("/dashboard"))
    expect(roteador.push).not.toHaveBeenCalled()
    expect(evento).toBe(true)
    expect(document.documentElement.hasAttribute(ATRIBUTO_DA_TROCA)).toBe(false)
  })
})
