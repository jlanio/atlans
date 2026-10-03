import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

/**
 * The sidebar's edge. It ALWAYS showed `cursor-w-resize` and could only
 * COLLAPSE — whoever dragged it to read an artifact's full name saw the bar
 * close. Now it resizes when expanded, and keeps expanding when collapsed,
 * which is the only way back from the 3rem rail through there.
 */
vi.mock("@/hooks/use-mobile", () => ({ useIsMobile: () => false }))

import {
  Sidebar, SidebarProvider, SidebarRail, SidebarTrigger, useSidebar,
  SIDEBAR_WIDTH_MIN, SIDEBAR_WIDTH_MAX, SIDEBAR_WIDTH_PADRAO, limitarLargura,
} from "@/app/components/ui/sidebar"

let renders = 0
function Largura() {
  const { width } = useSidebar()
  renders++
  return <output data-testid="largura">{width}</output>
}

function montar({ aberta = true, defaultWidth = SIDEBAR_WIDTH_PADRAO } = {}) {
  render(
    <SidebarProvider defaultOpen={aberta} defaultWidth={defaultWidth}>
      <Sidebar><SidebarRail /></Sidebar>
      <Largura />
    </SidebarProvider>,
  )
}
const largura = () => Number(screen.getByTestId("largura").textContent)
const separador = () => screen.getByRole("separator", { name: /redimensionar/i })
/** The LIVE width, which the drag writes straight into the CSS without going through React. */
const larguraNoCss = () =>
  document.querySelector<HTMLElement>('[data-slot="sidebar-wrapper"]')!.style.getPropertyValue("--sidebar-width")

function comSeparador() {
  const sep = separador()
  sep.setPointerCapture = vi.fn()
  sep.releasePointerCapture = vi.fn()
  return sep
}

beforeEach(() => {
  cleanup()
  renders = 0
  Object.defineProperty(document, "cookie", { writable: true, configurable: true, value: "" })
})
afterEach(cleanup)

describe("limitarLargura", () => {
  it("prende nos limites e arredonda", () => {
    expect(limitarLargura(10)).toBe(SIDEBAR_WIDTH_MIN)
    expect(limitarLargura(9999)).toBe(SIDEBAR_WIDTH_MAX)
    expect(limitarLargura(300.7)).toBe(301)
  })
})

describe("SidebarRail — expandida, é um separador", () => {
  it("anuncia o papel e os limites (padrão WAI-ARIA de janela)", () => {
    montar()
    const sep = separador()
    expect(sep.getAttribute("aria-orientation")).toBe("vertical")
    expect(sep.getAttribute("aria-valuenow")).toBe(String(SIDEBAR_WIDTH_PADRAO))
    expect(sep.getAttribute("aria-valuemin")).toBe(String(SIDEBAR_WIDTH_MIN))
    expect(sep.getAttribute("aria-valuemax")).toBe(String(SIDEBAR_WIDTH_MAX))
    // Reachable by Tab: without this, resizing would be mouse-only.
    expect(sep.getAttribute("tabindex")).toBe("0")
  })

  it("arrastar muda a largura, e soltar para de segui-la", () => {
    montar()
    const sep = comSeparador()

    fireEvent.pointerDown(sep, { button: 0, pointerId: 1 })
    fireEvent.pointerMove(sep, { clientX: 340, pointerId: 1 })
    expect(larguraNoCss()).toBe("340px")

    fireEvent.pointerUp(sep, { pointerId: 1 })
    expect(largura()).toBe(340)          // only now does the state receive it

    fireEvent.pointerMove(sep, { clientX: 200, pointerId: 1 })
    expect(larguraNoCss()).toBe("340px") // released, the movement no longer counts
  })

  it("o arrasto respeita os limites", () => {
    montar()
    const sep = comSeparador()
    fireEvent.pointerDown(sep, { button: 0, pointerId: 1 })
    fireEvent.pointerMove(sep, { clientX: 20, pointerId: 1 })
    expect(larguraNoCss()).toBe(`${SIDEBAR_WIDTH_MIN}px`)
    fireEvent.pointerMove(sep, { clientX: 5000, pointerId: 1 })
    expect(larguraNoCss()).toBe(`${SIDEBAR_WIDTH_MAX}px`)
    fireEvent.pointerUp(sep, { pointerId: 1 })
    expect(largura()).toBe(SIDEBAR_WIDTH_MAX)
  })

  it("um gesto inteiro custa UM render e UM cookie, não um por quadro", () => {
    // It used to be 60 and 60 per second of dragging, with nine `useSidebar`
    // consumers (the virtualized Artifacts list among them) re-rendering along
    // and a SYNCHRONOUS write to `document.cookie` on every frame.
    let escritas = 0
    Object.defineProperty(document, "cookie", {
      configurable: true, get: () => "", set: () => { escritas++ },
    })
    montar()
    const sep = comSeparador()
    fireEvent.pointerDown(sep, { button: 0, pointerId: 1 })
    const antes = renders
    escritas = 0
    for (let i = 0; i < 60; i++) fireEvent.pointerMove(sep, { clientX: 200 + i * 3, pointerId: 1 })
    expect(renders - antes).toBe(0)      // the gesture doesn't go through React
    expect(escritas).toBe(0)

    fireEvent.pointerUp(sep, { pointerId: 1 })
    expect(renders - antes).toBe(1)
    expect(escritas).toBe(1)
  })

  it("o teclado ajusta: setas, Shift para passo grande, Home/End nos limites", () => {
    montar()
    const sep = separador()
    fireEvent.keyDown(sep, { key: "ArrowRight" })
    expect(largura()).toBe(SIDEBAR_WIDTH_PADRAO + 16)
    fireEvent.keyDown(sep, { key: "ArrowLeft", shiftKey: true })
    expect(largura()).toBe(SIDEBAR_WIDTH_PADRAO + 16 - 48)
    fireEvent.keyDown(sep, { key: "End" })
    expect(largura()).toBe(SIDEBAR_WIDTH_MAX)
    fireEvent.keyDown(sep, { key: "Home" })
    expect(largura()).toBe(SIDEBAR_WIDTH_MIN)
  })

  it("NaN não vira largura: o cookie é entrada do cliente", () => {
    expect(limitarLargura(Number.NaN)).toBe(SIDEBAR_WIDTH_PADRAO)
    montar({ defaultWidth: Number.NaN })
    expect(largura()).toBe(SIDEBAR_WIDTH_PADRAO)
  })

  it("a transição para de animar nos DOIS divs — o que anda e o que empurra", () => {
    // `sidebar-gap` reserves the space and pushes <main>; the separator does NOT
    // live inside it (it's a sibling), so a `has-…` rule anchored on the gap
    // itself would never match and the content would lag 200ms behind the edge
    // during the drag.
    montar()
    const gap = document.querySelector<HTMLElement>('[data-slot="sidebar-gap"]')!
    const container = document.querySelector<HTMLElement>('[data-slot="sidebar-container"]')!
    const grupo = document.querySelector<HTMLElement>('[data-slot="sidebar"]')!
    const sep = separador()

    expect(gap.contains(sep)).toBe(false)          // the reason for anchoring on the group
    expect(container.contains(sep)).toBe(true)
    expect(grupo.contains(gap) && grupo.contains(sep)).toBe(true)
    for (const el of [gap, container]) {
      expect(el.className).toContain("group-has-data-[arrastando]:transition-none")
    }
  })

  it("duplo clique volta ao padrão", () => {
    montar({ defaultWidth: 400 })
    expect(largura()).toBe(400)
    fireEvent.doubleClick(separador())
    expect(largura()).toBe(SIDEBAR_WIDTH_PADRAO)
  })

  it("a largura vai para o cookie — é o servidor que a lê no F5", () => {
    // From the keyboard the write is immediate: the gesture is discrete, not continuous.
    montar()
    fireEvent.keyDown(separador(), { key: "End" })
    expect(document.cookie).toContain(`sidebar_width=${SIDEBAR_WIDTH_MAX}`)
  })

  it("a largura escolhida vira a variável de CSS que a barra usa", () => {
    montar({ defaultWidth: 320 })
    const envoltorio = document.querySelector<HTMLElement>('[data-slot="sidebar-wrapper"]')!
    expect(envoltorio.style.getPropertyValue("--sidebar-width")).toBe("320px")
  })
})

describe("SidebarRail — recolhida, continua o botão que expande", () => {
  it("vira botão, e não separador: é o único caminho de volta do trilho", () => {
    montar({ aberta: false })
    expect(screen.queryByRole("separator")).toBeNull()
    const bt = screen.getByRole("button", { name: /expandir barra lateral/i })
    fireEvent.click(bt)
    expect(screen.getByRole("separator", { name: /redimensionar/i })).toBeTruthy()
  })
})


describe("os rótulos: o português da administração por padrão, os da Home quando passados", () => {
  // The translated Home passes the texts in its language; the rest of the app
  // (editor, projects, admin) stays in Portuguese — and that is the default this locks.
  it("sem textos, o trilho e o gatilho falam o português de sempre", () => {
    montar({ aberta: true })
    expect(separador().getAttribute("aria-label")).toBe("Redimensionar a barra lateral")
    expect(separador().getAttribute("title")).toBe("Arraste para redimensionar · duplo clique volta ao padrão")
    cleanup()
    render(<SidebarProvider><SidebarTrigger /></SidebarProvider>)
    expect(screen.getByRole("button", { name: "Alternar barra lateral" })).toBeTruthy()
  })

  it("com textos, aberta e recolhida", () => {
    const textos = { expandir: "Expand sidebar", redimensionar: "Resize the sidebar", dica: "Drag to resize" }
    render(<SidebarProvider defaultOpen><Sidebar><SidebarRail textos={textos} /></Sidebar></SidebarProvider>)
    expect(screen.getByRole("separator", { name: "Resize the sidebar" }).getAttribute("title")).toBe("Drag to resize")
    cleanup()
    render(<SidebarProvider defaultOpen={false}><Sidebar><SidebarRail textos={textos} /></Sidebar></SidebarProvider>)
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeTruthy()
  })
})
