import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

/**
 * A borda da barra lateral. Ela SEMPRE mostrou `cursor-w-resize` e só sabia
 * RECOLHER — quem arrastava para ler o nome inteiro de um artefato via a barra
 * fechar. Agora ela redimensiona quando expandida, e segue expandindo quando
 * recolhida, que é o único caminho de volta do trilho de 3rem por ali.
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
/** A largura VIVA, que o arrasto escreve direto no CSS sem passar pelo React. */
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
    // Alcançável por Tab: sem isto, redimensionar seria só para quem tem mouse.
    expect(sep.getAttribute("tabindex")).toBe("0")
  })

  it("arrastar muda a largura, e soltar para de segui-la", () => {
    montar()
    const sep = comSeparador()

    fireEvent.pointerDown(sep, { button: 0, pointerId: 1 })
    fireEvent.pointerMove(sep, { clientX: 340, pointerId: 1 })
    expect(larguraNoCss()).toBe("340px")

    fireEvent.pointerUp(sep, { pointerId: 1 })
    expect(largura()).toBe(340)          // só agora o estado recebe

    fireEvent.pointerMove(sep, { clientX: 200, pointerId: 1 })
    expect(larguraNoCss()).toBe("340px") // solto, o movimento não conta mais
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
    // Antes eram 60 e 60 por segundo de arrasto, com nove consumidores de
    // `useSidebar` (a lista virtualizada de Artefatos entre eles) re-renderizando
    // junto e uma escrita SÍNCRONA em `document.cookie` a cada quadro.
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
    expect(renders - antes).toBe(0)      // o gesto não passa pelo React
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
    // O `sidebar-gap` reserva o espaço e empurra o <main>; o separador NÃO vive
    // dentro dele (é irmão), então uma regra `has-…` ancorada no próprio gap
    // nunca casaria e o conteúdo ficaria 200ms atrás da borda no arrasto.
    montar()
    const gap = document.querySelector<HTMLElement>('[data-slot="sidebar-gap"]')!
    const container = document.querySelector<HTMLElement>('[data-slot="sidebar-container"]')!
    const grupo = document.querySelector<HTMLElement>('[data-slot="sidebar"]')!
    const sep = separador()

    expect(gap.contains(sep)).toBe(false)          // a razão de ancorar no grupo
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
    // Pelo teclado a escrita é imediata: o gesto é discreto, não contínuo.
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
  // A Home traduzida passa os textos do idioma dela; o resto do app (editor,
  // projetos, admin) segue em português — e é o padrão que isto tranca.
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
