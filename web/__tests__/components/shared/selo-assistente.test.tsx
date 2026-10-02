import { afterEach, describe, expect, it } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import { SeloAssistente } from "@/app/components/shared/selo-assistente"

afterEach(cleanup)

/**
 * O selo é o que faz os fluxos do assistente pararem de "passar despercebidos"
 * nas listas do painel. Duas regras valem em toda tela: ele só aparece para
 * `origem === "assistente"`, e o rótulo existe também para quem não vê a
 * faísca (leitor de tela, `title` no hover).
 */
describe("SeloAssistente", () => {
  it("não pinta nada para fluxo de usuário, origem ausente ou nula", () => {
    const { container, rerender } = render(<SeloAssistente origem="usuario" />)
    expect(container).toBeEmptyDOMElement()
    rerender(<SeloAssistente origem={null} />)
    expect(container).toBeEmptyDOMElement()
    rerender(<SeloAssistente origem={undefined} />)
    expect(container).toBeEmptyDOMElement()
  })

  it("no fluxo do assistente traz texto e rótulo acessível", () => {
    render(<SeloAssistente origem="assistente" />)
    const selo = screen.getByLabelText("Fluxo criado pelo assistente")
    expect(selo).toHaveTextContent("assistente")
    expect(selo).toHaveAttribute("title", "Fluxo criado pelo assistente")
  })

  it("compacto deixa só a faísca, mas mantém o rótulo para quem não a vê", () => {
    const { container } = render(<SeloAssistente origem="assistente" compacto />)
    const selo = screen.getByLabelText("Fluxo criado pelo assistente")
    // Onde não cabe texto (linha densa, item de seletor) fica só o ícone — o
    // nome do fluxo ao lado não pode ser empurrado por um selo escrito. O
    // `<title>` do SVG é o rótulo do hover, não texto na tela.
    expect(selo.tagName.toLowerCase()).toBe("svg")
    expect(container.querySelector("span")).toBeNull()
  })
})
