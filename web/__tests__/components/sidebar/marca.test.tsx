import { describe, it, expect, beforeAll, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

/**
 * The brand on the 3rem rail and the wordmark in the phone drawer. In the
 * default app the whole brand disappears when collapsed; Home (`glifoNoTrilho`)
 * keeps the glyph — for the admin it is the link to Projects, the only explicit
 * way out of Home — and hides only the wordmark, in `sr-only` (it's the link's
 * name).
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
afterEach(() => { cleanup(); largura(1280) })

import { SidebarProvider } from "@/app/components/ui/sidebar"
import Marca from "@/app/components/sidebar/marca"
import { DisplayNameProvider } from "@/app/components/share/nome-na-tela"

function montar(ui: React.ReactNode, props: Omit<React.ComponentProps<typeof SidebarProvider>, "children"> = {}) {
  return render(<SidebarProvider {...props}>{ui}</SidebarProvider>)
}

describe("Marca", () => {
  it("no app padrão some inteira no modo ícone — só o gatilho fica no trilho", () => {
    montar(<Marca />)
    const wordmark = screen.getByText("Atlans")
    expect(wordmark.parentElement!.className).toContain("group-data-[collapsible=icon]:hidden")
    expect(wordmark.className).not.toContain("sr-only")
  })

  it("com glifoNoTrilho a marca fica e só o wordmark vira sr-only", () => {
    montar(<Marca glifoNoTrilho />)
    const wordmark = screen.getByText("Atlans")
    expect(wordmark.parentElement!.className).not.toContain("group-data-[collapsible=icon]:hidden")
    expect(wordmark.className).toContain("group-data-[collapsible=icon]:sr-only")
  })

  it("com href é link e, no trilho, a tooltip diz o destino", async () => {
    montar(<Marca href="/projects" glifoNoTrilho tooltip={{ children: "Projetos" }} />, { open: false })
    const link = screen.getByRole("link")
    expect(link.getAttribute("href")).toBe("/projects")
    fireEvent.focus(link)
    const dica = await screen.findAllByText("Projetos")
    expect(dica.some((el) => !el.closest("[hidden]"))).toBe(true)
  })

  it("expandida, a tooltip fica escondida — o wordmark já diz tudo", async () => {
    montar(<Marca href="/projects" glifoNoTrilho tooltip={{ children: "Projetos" }} />)
    fireEvent.focus(screen.getByRole("link"))
    const dica = await screen.findAllByText("Projetos")
    expect(dica.every((el) => el.closest("[hidden]"))).toBe(true)
  })
})

describe("O wordmark é o nome da instalação", () => {
  it("sem NOME_NA_TELA o código mostra «Atlans»; com ela, o nome da instalação", () => {
    // The form with the domain is the holder's installation (their brand, see
    // TRADEMARKS.md): it doesn't go in the code, it comes from each
    // installation's environment.
    montar(<Marca />)
    expect(screen.getByText("Atlans").getAttribute("title") ?? screen.getByText("Atlans").textContent).toContain("Atlans")
    cleanup()
    montar(<DisplayNameProvider nome="Geo Exemplo"><Marca /></DisplayNameProvider>)
    expect(screen.getByText("Geo Exemplo")).toBeTruthy()
    expect(screen.queryByText("Atlans")).toBeNull()
  })
})

describe("TitleSidebar", () => {
  it("no desktop recolhido o wordmark apaga; na gaveta do telefone aparece sempre", () => {
    // `open` is the DESKTOP state; with the `sidebar_state=false` cookie the
    // wordmark sat at opacity-0 inside the drawer, which only exists when open.
    montar(<Marca />, { open: false })
    expect(screen.getByText("Atlans").className).toContain("opacity-0")
    cleanup()
    largura(375)
    montar(<Marca />, { open: false })
    expect(screen.getByText("Atlans").className).toContain("opacity-100")
  })
})
