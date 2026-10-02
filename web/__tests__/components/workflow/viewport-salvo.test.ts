/**
 * O viewport salvo é restaurado ao abrir e gravado no save explícito. Estas
 * regras dizem o que conta como "salvo válido" e o que conta como "mudou".
 */
import { describe, it, expect } from "vitest"
import { viewportSalvoValido, viewportsIguais } from "@/app/components/workflow/utils/viewport-salvo"

describe("viewportSalvoValido", () => {
  it("aceita x, y e zoom numéricos", () => {
    expect(viewportSalvoValido({ x: -120, y: 40, zoom: 1.25 })).toBe(true)
  })

  it("rejeita ausência, campo faltando e número inválido", () => {
    expect(viewportSalvoValido(undefined)).toBe(false)
    expect(viewportSalvoValido(null)).toBe(false)
    expect(viewportSalvoValido({ x: 0, y: 0 })).toBe(false)
    expect(viewportSalvoValido({ x: 0, y: 0, zoom: Number.NaN })).toBe(false)
  })
})

describe("viewportsIguais", () => {
  it("ruído de ponto flutuante do d3-zoom não conta como mudança", () => {
    expect(viewportsIguais({ x: 0, y: 0, zoom: 1 }, { x: 0.2, y: -0.3, zoom: 1.0004 })).toBe(true)
  })

  it("pan ou zoom de verdade conta", () => {
    expect(viewportsIguais({ x: 0, y: 0, zoom: 1 }, { x: 40, y: 0, zoom: 1 })).toBe(false)
    expect(viewportsIguais({ x: 0, y: 0, zoom: 1 }, { x: 0, y: 0, zoom: 1.1 })).toBe(false)
  })

  it("sem referência salva, só 'nenhum' é igual a 'nenhum'", () => {
    expect(viewportsIguais(null, null)).toBe(true)
    expect(viewportsIguais({ x: 0, y: 0, zoom: 1 }, null)).toBe(false)
  })
})
