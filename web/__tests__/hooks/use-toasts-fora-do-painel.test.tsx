/**
 * The toasts keep clear of an assistant panel on screen.
 *
 * The Toaster stacks them in the bottom right corner, where the editor's drawer
 * and the Home's conversation keep their message field: a toast landed on what
 * the person was typing. The hook publishes where the panel is (root CSS
 * variables); `globals.css` picks by width which one moves the toasts, and
 * `ui/sonner.tsx` adds it to its own distances. jsdom does no layout: the
 * geometry here is set by hand.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, act, cleanup } from "@testing-library/react"
import { useRef } from "react"
import { toast } from "sonner"

import { useToastsForaDoPainel } from "@/app/hooks/useToastsForaDoPainel"
import { Toaster } from "@/app/components/ui/sonner"

const raiz = document.documentElement
const lido = (nome: string) => raiz.style.getPropertyValue(nome)

/** The ResizeObservers created, so the test can say "it resized". */
let observadores: Array<() => void> = []

function geometria(elemento: HTMLElement, rect: Partial<DOMRect>) {
  elemento.getBoundingClientRect = () => ({ top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0, x: 0, y: 0, toJSON() {}, ...rect }) as DOMRect
}

function Painel({ ativo = true, folga = 0 }: { ativo?: boolean; folga?: number }) {
  const painel = useRef<HTMLElement>(null)
  const campo = useRef<HTMLFormElement>(null)
  useToastsForaDoPainel(painel, campo, ativo, folga)
  return (
    <aside ref={painel} data-testid="painel">
      <form ref={campo} data-testid="campo" />
    </aside>
  )
}

/** Rendered with the geometry in place before the first measure. */
function montar(props: { ativo?: boolean; folga?: number } = {}) {
  const proto = HTMLElement.prototype.getBoundingClientRect
  HTMLElement.prototype.getBoundingClientRect = function (this: HTMLElement) {
    if (this.tagName === "ASIDE") return { left: 1060 } as DOMRect
    if (this.tagName === "FORM") return { top: 790 } as DOMRect
    return proto.call(this)
  }
  try {
    return render(<Painel {...props} />)
  } finally {
    HTMLElement.prototype.getBoundingClientRect = proto
  }
}

beforeEach(() => {
  observadores = []
  vi.stubGlobal("ResizeObserver", class {
    constructor(private aoMudar: () => void) { observadores.push(() => this.aoMudar()) }
    observe() {}
    unobserve() {}
    disconnect() {}
  })
  // The root's box ends before the scrollbar gutter, as `scrollbar-gutter:
  // stable` leaves it — and `clientWidth` would still say 1440.
  geometria(raiz, { right: 1430, bottom: 900 })
  Object.defineProperty(raiz, "clientWidth", { configurable: true, value: 1440 })
  Object.defineProperty(raiz, "clientHeight", { configurable: true, value: 900 })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("toasts fora do painel do assistente", () => {
  it("diz quanto da borda direita o painel ocupa e quanto do pé o campo ocupa", () => {
    montar()

    expect(lido("--painel-ocupa-direita")).toBe("370px")
    expect(lido("--painel-ocupa-baixo")).toBe("110px")
  })

  it("a folga cobre o que fica colado ao painel (a coluna do canvas, no editor)", () => {
    montar({ folga: 48 })

    expect(lido("--painel-ocupa-direita")).toBe("418px")
  })

  it("acompanha o painel arrastado e o campo que cresce com o texto", () => {
    const { getByTestId } = montar()

    geometria(getByTestId("painel"), { left: 900 })
    geometria(getByTestId("campo"), { top: 700 })
    act(() => observadores.forEach(avisar => avisar()))

    expect(lido("--painel-ocupa-direita")).toBe("530px")
    expect(lido("--painel-ocupa-baixo")).toBe("200px")
  })

  it("mede de novo quando o painel termina de entrar (a Home desliza da direita)", () => {
    const { getByTestId } = montar()

    geometria(getByTestId("painel"), { left: 996 })
    act(() => { getByTestId("painel").dispatchEvent(new Event("animationend")) })

    expect(lido("--painel-ocupa-direita")).toBe("434px")
  })

  it("fechado ou desmontado, os toasts voltam ao canto", () => {
    const { rerender, unmount } = montar()
    expect(lido("--painel-ocupa-direita")).not.toBe("")

    rerender(<Painel ativo={false} />)
    expect(lido("--painel-ocupa-direita")).toBe("")
    expect(lido("--painel-ocupa-baixo")).toBe("")

    rerender(<Painel ativo />)
    unmount()
    expect(lido("--painel-ocupa-direita")).toBe("")
  })

  it("o Toaster soma esses recuos às suas próprias distâncias", async () => {
    // jsdom has no matchMedia, and sonner asks it about the theme.
    vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }))
    render(<Toaster />)
    act(() => { toast("Salvo") })

    const toaster = await vi.waitFor(() => {
      const el = document.querySelector<HTMLElement>("[data-sonner-toaster]")
      if (!el) throw new Error("sem toaster")
      return el
    })
    expect(toaster.style.getPropertyValue("--offset-right")).toBe(
      "min(calc(24px + var(--toasts-recuo-direita, 0px)), calc(100% - var(--width) - 16px))",
    )
    expect(toaster.style.getPropertyValue("--offset-bottom")).toBe("calc(24px + var(--toasts-recuo-baixo, 0px))")
    expect(toaster.style.getPropertyValue("--mobile-offset-bottom")).toBe("calc(16px + var(--toasts-recuo-baixo, 0px))")
    // The other sides keep sonner's own distances.
    expect(toaster.style.getPropertyValue("--offset-left")).toBe("24px")
  })
})
