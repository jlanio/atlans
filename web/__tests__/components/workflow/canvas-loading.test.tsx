/**
 * The canvas loading animation has two allowances: it only appears if the wait
 * goes past a delay (a fast load doesn't deserve an indicator — it would
 * flicker) and, once it has appeared, it stays for a minimum time (vanishing
 * right after is the same flicker). It also marks the React Flow container,
 * which is how the button columns dim and the graph fades in.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup, act } from "@testing-library/react"

let domNode: HTMLDivElement | null = null
vi.mock("@xyflow/react", () => ({
  useStore: (seletor: (s: { domNode: HTMLDivElement | null }) => unknown) => seletor({ domNode }),
}))

import CanvasLoading, { SHOW_DELAY_MS, MIN_DISPLAY_MS } from "@/app/components/workflow/canvas-loading"

const overlay = () => screen.queryByRole("status")
const advance = (ms: number) => act(() => { vi.advanceTimersByTime(ms) })

beforeEach(() => {
  cleanup()
  vi.useFakeTimers()
  domNode = document.createElement("div")
  domNode.className = "react-flow"
})

afterEach(() => {
  vi.useRealTimers()
})

describe("animação de carga do canvas", () => {
  it("não aparece de imediato; aparece depois do atraso", () => {
    render(<CanvasLoading carregando />)
    expect(overlay()).toBeNull()

    advance(SHOW_DELAY_MS)
    expect(overlay()).toHaveTextContent("Carregando workflow…")
  })

  it("uma carga que termina antes do atraso nunca mostra nada", () => {
    const { rerender } = render(<CanvasLoading carregando />)
    advance(SHOW_DELAY_MS - 50)
    rerender(<CanvasLoading carregando={false} />)
    advance(2_000)
    expect(overlay()).toBeNull()
  })

  it("tendo aparecido, fica o tempo mínimo mesmo que a carga acabe antes", () => {
    const { rerender } = render(<CanvasLoading carregando />)
    advance(SHOW_DELAY_MS)        // aparece
    advance(50)
    rerender(<CanvasLoading carregando={false} />)

    advance(MIN_DISPLAY_MS - 50 - 1)    // an instant before the minimum
    expect(overlay()).not.toBeNull()
    advance(1)
    expect(overlay()).toBeNull()
  })

  it("marca o canvas: rf-carregando durante a espera, rf-revelando na chegada", () => {
    const { rerender } = render(<CanvasLoading carregando />)
    expect(domNode!.classList.contains("rf-carregando")).toBe(true)
    expect(domNode!.classList.contains("rf-revelando")).toBe(false)

    rerender(<CanvasLoading carregando={false} />)
    expect(domNode!.classList.contains("rf-carregando")).toBe(false)
    expect(domNode!.classList.contains("rf-revelando")).toBe(true)

    advance(700)
    expect(domNode!.classList.contains("rf-revelando")).toBe(false)
  })

  it("quem nunca esperou (tela de criação) não ganha revelação", () => {
    render(<CanvasLoading carregando={false} />)
    expect(domNode!.classList.contains("rf-revelando")).toBe(false)
    expect(overlay()).toBeNull()
  })
})
