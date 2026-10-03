import { describe, it, expect, beforeAll, beforeEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

/**
 * On the phone the <Sidebar> becomes a <Sheet> portaled to <body>. What paints
 * the panel there is the SheetContent — and it needs to receive the <Sidebar>'s
 * `className`, otherwise a themed bar (Home's, `home dark`) declares the palette
 * only on the children: near-white text over the app theme's `--sidebar`, which
 * in the light theme is near-white too.
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
    // Home's palette has to reach the element that paints the background.
    expect(painel!.className).toContain("home")
    expect(painel!.className).toContain("dark")
    // …without losing what the Sheet itself already brought.
    expect(painel!.className).toContain("bg-sidebar")
  })

  it("o diálogo do Sheet se apresenta em pt-BR", () => {
    montarNoTelefone()
    fireEvent.click(screen.getByText("abrir"))
    expect(screen.getByText("Barra lateral")).toBeTruthy()
  })
})
