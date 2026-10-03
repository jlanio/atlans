import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { CabecalhoDoHistorico, textoDeFrescor } from "@/app/components/observability/cabecalho"

afterEach(cleanup)

describe("CabecalhoDoHistorico", () => {
  it("título, subtítulo com a comparação, segmentado com aria-pressed e botão Atualizar", () => {
    const onPeriodo = vi.fn()
    const onAtualizar = vi.fn()
    render(<CabecalhoDoHistorico periodo={30} onPeriodo={onPeriodo} carregando={false} onAtualizar={onAtualizar} comparandoCom={30} />)

    expect(screen.getByRole("heading", { level: 1, name: "Histórico" })).toBeInTheDocument()
    expect(screen.getByText("Execuções dos seus workflows · comparado com os 30 dias anteriores")).toBeInTheDocument()

    const grupo = screen.getByRole("group", { name: "Período" })
    const buttons = Array.from(grupo.querySelectorAll("button"))
    expect(buttons.map(b => b.textContent)).toEqual(["7 dias", "30 dias", "90 dias"])
    expect(buttons.map(b => b.getAttribute("aria-pressed"))).toEqual(["false", "true", "false"])

    fireEvent.click(screen.getByRole("button", { name: "Últimos 7 dias" }))
    expect(onPeriodo).toHaveBeenCalledWith(7)

    fireEvent.click(screen.getByRole("button", { name: "Atualizar os dados do Histórico" }))
    expect(onAtualizar).toHaveBeenCalledTimes(1)
  })

  it("Atualizar fica desabilitado enquanto carrega", () => {
    render(<CabecalhoDoHistorico periodo={7} onPeriodo={() => {}} carregando onAtualizar={() => {}} comparandoCom={7} />)
    expect(screen.getByRole("button", { name: "Atualizar os dados do Histórico" })).toBeDisabled()
  })

  it("textoDeFrescor em grão grosso", () => {
    expect(textoDeFrescor(1000, 1000 + 3_000)).toBe("atualizado agora")
    expect(textoDeFrescor(1000, 1000 + 47_000)).toBe("atualizado há 40 s")
    expect(textoDeFrescor(1000, 1000 + 5 * 60_000)).toBe("atualizado há 5 min")
    expect(textoDeFrescor(1000, 1000 + 2 * 3_600_000)).toBe("atualizado há 2 h")
  })
})
