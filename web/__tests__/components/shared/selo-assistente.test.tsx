import { afterEach, describe, expect, it } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import { SeloAssistente } from "@/app/components/shared/selo-assistente"

afterEach(cleanup)

/**
 * The badge is what keeps the assistant's workflows from "going unnoticed" in
 * the dashboard lists. Two rules hold on every screen: it only appears for
 * `origem === "assistente"`, and the label also exists for those who can't see
 * the sparkle (screen reader, `title` on hover).
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
    // Where there's no room for text (dense row, picker item) only the icon
    // stays — the workflow name next to it can't be pushed aside by a written
    // badge. The SVG's `<title>` is the hover label, not text on the screen.
    expect(selo.tagName.toLowerCase()).toBe("svg")
    expect(container.querySelector("span")).toBeNull()
  })
})
