/**
 * A animação de carga do canvas tem duas folgas: só aparece se a espera passa
 * de um atraso (uma carga rápida não merece indicador — piscaria) e, tendo
 * aparecido, fica um tempo mínimo (sumir logo depois é o mesmo piscar). Além
 * disso marca o contêiner do React Flow, que é como as colunas de botões
 * esmaecem e o grafo entra em fade.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup, act } from "@testing-library/react"

let domNode: HTMLDivElement | null = null
vi.mock("@xyflow/react", () => ({
  useStore: (seletor: (s: { domNode: HTMLDivElement | null }) => unknown) => seletor({ domNode }),
}))

import CanvasLoading, { ATRASO_PARA_MOSTRAR_MS, EXIBICAO_MINIMA_MS } from "@/app/components/workflow/canvas-loading"

const overlay = () => screen.queryByRole("status")
const avancar = (ms: number) => act(() => { vi.advanceTimersByTime(ms) })

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

    avancar(ATRASO_PARA_MOSTRAR_MS)
    expect(overlay()).toHaveTextContent("Carregando workflow…")
  })

  it("uma carga que termina antes do atraso nunca mostra nada", () => {
    const { rerender } = render(<CanvasLoading carregando />)
    avancar(ATRASO_PARA_MOSTRAR_MS - 50)
    rerender(<CanvasLoading carregando={false} />)
    avancar(2_000)
    expect(overlay()).toBeNull()
  })

  it("tendo aparecido, fica o tempo mínimo mesmo que a carga acabe antes", () => {
    const { rerender } = render(<CanvasLoading carregando />)
    avancar(ATRASO_PARA_MOSTRAR_MS)        // aparece
    avancar(50)
    rerender(<CanvasLoading carregando={false} />)

    avancar(EXIBICAO_MINIMA_MS - 50 - 1)    // um instante antes do mínimo
    expect(overlay()).not.toBeNull()
    avancar(1)
    expect(overlay()).toBeNull()
  })

  it("marca o canvas: rf-carregando durante a espera, rf-revelando na chegada", () => {
    const { rerender } = render(<CanvasLoading carregando />)
    expect(domNode!.classList.contains("rf-carregando")).toBe(true)
    expect(domNode!.classList.contains("rf-revelando")).toBe(false)

    rerender(<CanvasLoading carregando={false} />)
    expect(domNode!.classList.contains("rf-carregando")).toBe(false)
    expect(domNode!.classList.contains("rf-revelando")).toBe(true)

    avancar(700)
    expect(domNode!.classList.contains("rf-revelando")).toBe(false)
  })

  it("quem nunca esperou (tela de criação) não ganha revelação", () => {
    render(<CanvasLoading carregando={false} />)
    expect(domNode!.classList.contains("rf-revelando")).toBe(false)
    expect(overlay()).toBeNull()
  })
})
