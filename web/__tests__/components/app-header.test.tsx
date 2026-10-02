import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

/**
 * O AppHeader some no full-bleed do canvas (`/workflow/*`). Na Home (`/`) ele
 * NÃO some por inteiro: a barra some, mas sobra o gatilho flutuante da sidebar
 * — abaixo de 768px ele é o único jeito de abrir a barra (o botão de dentro do
 * Sheet só fecha).
 *
 * O h1 da Home NÃO é daqui: quem o desenha é a HomeView. Está testado abaixo
 * porque por um tempo os dois desenharam um, e a página ficou com dois <h1>.
 */
const nav = vi.hoisted(() => ({ pathname: "/" }))
vi.mock("next/navigation", () => ({ usePathname: () => nav.pathname }))
vi.mock("@/context/WorkspaceContext", () => ({ useWorkspace: () => ({ loading: false }) }))
vi.mock("@/app/components/workspace/workspace-switcher", () => ({ default: () => <div data-testid="switcher" /> }))
vi.mock("@/app/components/ui/sidebar", () => ({
  // Repassa as props: o teste do gatilho da Home olha className e aria-label.
  SidebarTrigger: (props: React.ComponentProps<"button">) => <button data-testid="trigger" {...props} />,
}))

import { AppHeader } from "@/app/components/app-header"
import { IdiomaProvider } from "@/context/IdiomaContext"

beforeEach(() => cleanup())

describe("AppHeader", () => {
  it("na Home (/) não desenha a barra", () => {
    nav.pathname = "/"
    render(<AppHeader />)
    expect(screen.queryByTestId("switcher")).toBeNull()
    expect(document.querySelector("header")).toBeNull()
  })

  it("na Home (/) dá o gatilho flutuante mobile-only — sem ele o telefone fica sem menu", () => {
    nav.pathname = "/"
    render(<AppHeader />)
    const gatilho = screen.getByTestId("trigger")
    expect(gatilho.getAttribute("aria-label")).toBe("Abrir menu")
    const classes = gatilho.className
    expect(classes).toContain("md:hidden")   // só no telefone
    expect(classes).toContain("fixed")       // flutua sobre o globo
    expect(classes).toContain("home")        // veste a paleta da Home fora da árvore dela
    expect(classes).toContain("size-10")     // alvo de 40px (§5 do padrão de telas)
    expect(classes).toContain("z-50")        // topo da pilha da Home (camadas z-40, assistente z-30)
    expect(classes).not.toContain("z-40")    // empatado com o painel de camadas, ele cobria o gatilho
  })

  it("na Home (/) em inglês, o gatilho fala inglês — é o único menu do telefone", () => {
    nav.pathname = "/"
    render(
      <IdiomaProvider inicial={{ idioma: "en", detectado: "en", escolhido: "en" }}>
        <AppHeader />
      </IdiomaProvider>,
    )
    const gatilho = screen.getByTestId("trigger")
    expect(gatilho.getAttribute("aria-label")).toBe("Open menu")
    expect(gatilho.getAttribute("label")).toBe("Toggle sidebar")
    // Fora da árvore da HomeView: declara o idioma no próprio botão.
    expect(gatilho.getAttribute("lang")).toBe("en")
  })

  it("na Home (/) NÃO desenha h1 — o da página é da HomeView", () => {
    nav.pathname = "/"
    const { container } = render(<AppHeader />)
    // Dois <h1> na mesma rota quebram a leitura de estrutura: aqui não pode
    // existir nenhum, nem `sr-only`.
    expect(container.querySelector("h1")).toBeNull()
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull()
  })

  it("some no canvas (/workflow/*)", () => {
    nav.pathname = "/workflow/create"
    const { container } = render(<AppHeader />)
    expect(container.firstChild).toBeNull()
  })

  it("aparece nas demais rotas — / é exato, não prefixo", () => {
    nav.pathname = "/projects"
    render(<AppHeader />)
    expect(screen.getByTestId("switcher")).toBeTruthy()
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull()
  })
})
