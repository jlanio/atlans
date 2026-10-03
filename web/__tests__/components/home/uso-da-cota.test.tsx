/**
 * The quota donut (the house "context indicator"): clamped percentage,
 * color bands, reopening countdown when exceeded and the full text
 * in the aria-label/tooltip: spent, ceiling, percentage and time — and nothing else (the
 * warning about the quota shared with the editor left the text).
 */
import { describe, it, expect, beforeEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

import UsoDaCota, {
  detalheDaCota,
  faixaDaCota,
  percentualDaCota,
} from "@/app/components/home/assistente/uso-da-cota"
import type { IAssistenteCota } from "@/service/types"

const cota = (gasto: number, teto = 1_500_000, reabre: number | null = 10_800): IAssistenteCota =>
  ({ gasto, teto, reabre_em_segundos: reabre })

beforeEach(cleanup)

describe("percentual e faixa", () => {
  it("arredonda, clampa em 0–100 e nunca divide por zero", () => {
    expect(percentualDaCota(cota(450_000))).toBe(30)
    expect(percentualDaCota(cota(1_230_000))).toBe(82)
    // The server lets the LAST turn go over the ceiling: the donut does not go past 100.
    expect(percentualDaCota(cota(2_000_000))).toBe(100)
    expect(percentualDaCota(cota(-5))).toBe(0)
    expect(percentualDaCota(cota(10, 0))).toBe(0)
  })

  it("as faixas viram nas fronteiras certas: 80% e o teto", () => {
    expect(faixaDaCota(cota(1_190_000))).toBe("normal")   // 79%
    expect(faixaDaCota(cota(1_200_000))).toBe("alerta")   // 80%
    expect(faixaDaCota(cota(1_500_000))).toBe("cheia")    // = ceiling counts as exceeded
    expect(faixaDaCota(cota(2_000_000))).toBe("cheia")
  })
})

describe("o donut na tela", () => {
  it("uso normal: percentual no rótulo e o detalhe completo no aria-label", () => {
    render(<UsoDaCota cota={cota(1_230_000)} />)
    const donut = screen.getByTestId("uso-da-cota")
    expect(donut.textContent).toBe("82%")
    expect(donut.dataset.faixa).toBe("alerta")
    const rotulo = donut.getAttribute("aria-label") ?? ""
    expect(rotulo).toContain("1.230.000 de 1.500.000 tokens (82%)")
    expect(rotulo).toContain("a janela renova em 3 h")
    // The text ends at the time: without the shared-quota warning and without a space
    // left over after the period.
    expect(rotulo).not.toContain("compartilhada")
    expect(rotulo).toMatch(/\.$/)
  })

  it("estourada: o rótulo vira a contagem de reabertura", () => {
    render(<UsoDaCota cota={cota(2_000_000, 1_500_000, 3_600)} />)
    const donut = screen.getByTestId("uso-da-cota")
    expect(donut.textContent).toBe("reabre em 1 h")
    expect(donut.dataset.faixa).toBe("cheia")
    expect(donut.getAttribute("aria-label")).toContain("a janela reabre em 1 h")
  })

  it("estourada sem prazo (o TTL não veio) diz só que a cota acabou", () => {
    render(<UsoDaCota cota={cota(1_500_000, 1_500_000, null)} />)
    expect(screen.getByTestId("uso-da-cota").textContent).toBe("cota do dia usada")
  })

  it("sem cota (Redis fora, assistente desligado) o componente não existe", () => {
    const { container } = render(<UsoDaCota cota={null} />)
    expect(container.firstChild).toBeNull()
    const { container: c2 } = render(<UsoDaCota cota={cota(10, 0)} />)
    expect(c2.firstChild).toBeNull()
  })
})

describe("detalheDaCota", () => {
  it("sem prazo nenhum, não inventa janela", () => {
    const texto = detalheDaCota(cota(0, 1_500_000, null))
    expect(texto).toContain("0 de 1.500.000 tokens (0%)")
    expect(texto).not.toContain("janela")
  })
})
