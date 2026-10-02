import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

/**
 * A casca da Home em inglês e espanhol: a vitrine do catálogo (os PAÍSES
 * mudam de nome; os órgãos, que são nomes próprios, não), e os botões de quem
 * ainda não entrou. Os mocks são os mínimos do home-sidebar.test.
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
  Object.defineProperty(window, "innerWidth", { writable: true, configurable: true, value: 1280 })
})

vi.mock("next-auth/react", () => ({ useSession: () => ({ data: null, status: "unauthenticated" }) }))
vi.mock("@/app/components/sidebar/user-sidebar", () => ({ default: () => <div data-testid="user-sidebar" /> }))
vi.mock("@/app/components/home/chats/lista", () => ({ ChatsLista: () => <div /> }))
vi.mock("@/app/components/home/agendamentos/lista", () => ({ AgendamentosLista: () => <div /> }))
vi.mock("@/app/components/home/artefatos/lista", () => ({ ArtefatosLista: () => <div /> }))

import { SidebarProvider } from "@/app/components/ui/sidebar"
import HomeSidebar from "@/app/components/sidebar/home-sidebar"
import { IdiomaProvider } from "@/context/IdiomaContext"
import { CATALOGO } from "@/lib/catalogo"
import type { Idioma } from "@/lib/idioma"

beforeEach(cleanup)

const montar = (idioma: Idioma) =>
  render(
    <IdiomaProvider inicial={{ idioma, detectado: idioma, escolhido: idioma }}>
      <SidebarProvider>
        <HomeSidebar />
      </SidebarProvider>
    </IdiomaProvider>,
  )

describe("HomeSidebar — em inglês", () => {
  it("a vitrine e a entrada falam inglês; os países mudam de nome, os órgãos não", () => {
    montar("en")
    expect(screen.getByText("In the catalog")).toBeTruthy()
    expect(screen.getByText(CATALOGO.camadas.toLocaleString("en"))).toBeTruthy()
    expect(screen.getByText(new RegExp(`from ${CATALOGO.instituicoes} institutions in ${CATALOGO.paises} countries`))).toBeTruthy()
    for (const rotulo of ["Brazil", "Outside Brazil", "Stop searching for data. Ask Atlans."]) {
      expect(screen.getByText(rotulo), rotulo).toBeTruthy()
    }
    // A fita dos países: "Equador" vira "Ecuador" (duas cópias — a da emenda do laço).
    expect(screen.getAllByText("Ecuador").length).toBeGreaterThan(0)
    expect(screen.queryByText("Equador")).toBeNull()
    // Os órgãos são nomes próprios.
    expect(screen.getAllByText("IBGE").length).toBeGreaterThan(0)
    expect(screen.getByRole("navigation", { name: "Home sidebar" })).toBeTruthy()
    expect(screen.getByRole("button", { name: "Sign in" })).toBeTruthy()
    expect(screen.getByRole("button", { name: "Create account" })).toBeTruthy()
  })
})

describe("HomeSidebar — em espanhol", () => {
  it("a vitrine e a entrada falam espanhol", () => {
    montar("es")
    expect(screen.getByText("En el catálogo")).toBeTruthy()
    expect(screen.getByText("Fuera de Brasil")).toBeTruthy()
    expect(screen.getAllByText("Uruguay").length).toBeGreaterThan(0)
    expect(screen.getByRole("button", { name: "Iniciar sesión" })).toBeTruthy()
    expect(screen.getByRole("button", { name: "Crear cuenta" })).toBeTruthy()
  })
})


describe("o trilho da borda, no idioma da Home", () => {
  it("em inglês, o separador de largura e a dica", () => {
    montar("en")
    const trilho = document.querySelector<HTMLElement>('[data-sidebar="rail"]')!
    expect(trilho.getAttribute("aria-label")).toBe("Resize the sidebar")
    expect(trilho.getAttribute("title")).toBe("Drag to resize · double-click to restore the default")
  })
})

describe("o lang da barra, já no HTML do servidor", () => {
  // A barra é irmã da HomeView: sem o próprio `lang`, o inglês dela ficava sob
  // o `lang="pt-BR"` da raiz até a hidratação trocar o do <html>.
  it.each(["en", "es"] as const)("em %s, a navegação e o trilho declaram o idioma", (idioma) => {
    montar(idioma)
    expect(screen.getByRole("navigation").getAttribute("lang")).toBe(idioma)
    const trilho = document.querySelector<HTMLElement>('[data-sidebar="rail"]')!
    expect(trilho.closest("[lang]")?.getAttribute("lang")).toBe(idioma)
  })
})
