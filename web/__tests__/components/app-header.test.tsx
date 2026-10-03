import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

/**
 * The AppHeader disappears in the canvas full-bleed (`/workflow/*`). On the Home (`/`) it
 * does NOT disappear entirely: the bar goes away, but the sidebar's floating trigger
 * remains — below 768px it is the only way to open the bar (the button inside the
 * Sheet only closes it).
 *
 * The Home's h1 is NOT from here: HomeView draws it. It is tested below
 * because for a while both drew one, and the page ended up with two <h1>s.
 */
const nav = vi.hoisted(() => ({ pathname: "/" }))
vi.mock("next/navigation", () => ({ usePathname: () => nav.pathname }))
vi.mock("@/context/WorkspaceContext", () => ({ useWorkspace: () => ({ loading: false }) }))
vi.mock("@/app/components/workspace/workspace-switcher", () => ({ default: () => <div data-testid="switcher" /> }))
vi.mock("@/app/components/ui/sidebar", () => ({
  // Passes the props on: the Home trigger test looks at className and aria-label.
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
    expect(classes).toContain("md:hidden")   // phone only
    expect(classes).toContain("fixed")       // floats over the globe
    expect(classes).toContain("home")        // wears the Home palette outside its tree
    expect(classes).toContain("size-10")     // 40px target (§5 of the screen standard)
    expect(classes).toContain("z-50")        // top of the Home stack (layers z-40, assistant z-30)
    expect(classes).not.toContain("z-40")    // tied with the layers panel, it covered the trigger
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
    // Outside the HomeView tree: declares the language on the button itself.
    expect(gatilho.getAttribute("lang")).toBe("en")
  })

  it("na Home (/) NÃO desenha h1 — o da página é da HomeView", () => {
    nav.pathname = "/"
    const { container } = render(<AppHeader />)
    // Two <h1>s on the same route break structure reading: here there must be
    // none, not even `sr-only`.
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
