import { describe, it, expect, beforeAll, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

/**
 * A marca no trilho de 3rem e o wordmark na gaveta do telefone. No app padrão
 * a marca some inteira recolhida; a Home (`glifoNoTrilho`) mantém o glifo —
 * para o admin ele é o link para Projetos, a única saída explícita da Home —
 * e esconde só o wordmark, em `sr-only` (é o nome do link).
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
import { NomeNaTelaProvider } from "@/app/components/share/nome-na-tela"

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
    // A forma com o domínio é a instalação do titular (marca dele, ver
    // TRADEMARKS.md): não vai no código, vem do ambiente de cada instalação.
    montar(<Marca />)
    expect(screen.getByText("Atlans").getAttribute("title") ?? screen.getByText("Atlans").textContent).toContain("Atlans")
    cleanup()
    montar(<NomeNaTelaProvider nome="Geo Exemplo"><Marca /></NomeNaTelaProvider>)
    expect(screen.getByText("Geo Exemplo")).toBeTruthy()
    expect(screen.queryByText("Atlans")).toBeNull()
  })
})

describe("TitleSidebar", () => {
  it("no desktop recolhido o wordmark apaga; na gaveta do telefone aparece sempre", () => {
    // `open` é o estado do DESKTOP; com o cookie `sidebar_state=false` o
    // wordmark ficava em opacity-0 dentro da gaveta, que só existe aberta.
    montar(<Marca />, { open: false })
    expect(screen.getByText("Atlans").className).toContain("opacity-0")
    cleanup()
    largura(375)
    montar(<Marca />, { open: false })
    expect(screen.getByText("Atlans").className).toContain("opacity-100")
  })
})
