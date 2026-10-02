import { describe, it, expect, beforeAll, beforeEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

/**
 * No telefone o <Sidebar> vira um <Sheet> portado para o <body>. Quem pinta o
 * painel lá é o SheetContent — e ele precisa receber o `className` do
 * <Sidebar>, senão uma barra temática (a da Home, `home dark`) declara a paleta
 * só nos filhos: texto quase branco sobre o `--sidebar` do tema do app, que no
 * tema claro é quase branco também.
 */

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (q: string) => ({
      matches: true, media: q, onchange: null,
      addEventListener: () => {}, removeEventListener: () => {},
      addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
    }),
  })
})

import {
  Sidebar, SidebarContent, SidebarProvider, useSidebar,
} from "@/app/components/ui/sidebar"

function Abrir() {
  const { setOpenMobile } = useSidebar()
  return <button onClick={() => setOpenMobile(true)}>abrir</button>
}

function montarNoTelefone() {
  Object.defineProperty(window, "innerWidth", { writable: true, configurable: true, value: 375 })
  return render(
    <SidebarProvider>
      <Abrir />
      <Sidebar className="home dark border-sidebar-border">
        <SidebarContent>conteúdo</SidebarContent>
      </Sidebar>
    </SidebarProvider>,
  )
}

function painelDoSheet() {
  return document.querySelector('[data-slot="sidebar"][data-mobile="true"]')
}

beforeEach(() => cleanup())

describe("Sidebar no telefone", () => {
  it("repassa o className do <Sidebar> para a superfície do Sheet", () => {
    montarNoTelefone()
    fireEvent.click(screen.getByText("abrir"))
    const painel = painelDoSheet()
    expect(painel).toBeTruthy()
    // A paleta da Home tem de chegar ao elemento que pinta o fundo.
    expect(painel!.className).toContain("home")
    expect(painel!.className).toContain("dark")
    // …sem perder o que o próprio Sheet já trazia.
    expect(painel!.className).toContain("bg-sidebar")
  })

  it("o diálogo do Sheet se apresenta em pt-BR", () => {
    montarNoTelefone()
    fireEvent.click(screen.getByText("abrir"))
    expect(screen.getByText("Barra lateral")).toBeTruthy()
  })
})
