import { describe, it, expect, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { createRef } from "react"
import { LinhaDoMeu, GatilhoDeAcoes } from "@/app/components/home/linha"

/**
 * The single row of the three lists in the Meu group. The contract the lists'
 * tests inherit: a flex in which the main item is `min-w-0 flex-1` and the "⋯" is a SIBLING
 * with `shrink-0` — never `absolute` over the text (it was the `absolute` + `pr-7`
 * reserved by hand that gave zero slack and, on the phone, 16px of overlap).
 */
afterEach(cleanup)

describe("LinhaDoMeu", () => {
  it("é um flex de linha, com o recuo da sublista", () => {
    render(<LinhaDoMeu data-testid="linha">x</LinhaDoMeu>)
    const el = screen.getByTestId("linha")
    expect(el.getAttribute("data-slot")).toBe("linha-do-meu")
    for (const c of ["group/linha", "flex", "items-center", "pl-2", "pr-1"]) expect(el.className).toContain(c)
  })

  it("marca a linha ativa por data-active — o aria-current é do botão da lista", () => {
    render(
      <>
        <LinhaDoMeu data-testid="a" ativa>a</LinhaDoMeu>
        <LinhaDoMeu data-testid="b">b</LinhaDoMeu>
      </>,
    )
    expect(screen.getByTestId("a").getAttribute("data-active")).toBe("true")
    expect(screen.getByTestId("b").hasAttribute("data-active")).toBe(false)
  })
})

describe("GatilhoDeAcoes", () => {
  it("é um botão de verdade, nomeado pelo rótulo, que NÃO sai do fluxo", () => {
    render(<GatilhoDeAcoes rotulo="Focos" />)
    const b = screen.getByRole("button", { name: 'Ações de "Focos"' })
    expect(b.getAttribute("type")).toBe("button")
    expect(b.className).toContain("shrink-0")
    expect(b.className).not.toMatch(/\babsolute\b/)
  })

  it("tem 40px no telefone e aparece no hover da LINHA, no foco, no toque e com o menu aberto", () => {
    render(<GatilhoDeAcoes rotulo="Focos" />)
    const c = screen.getByRole("button").className
    for (const k of [
      "max-md:size-10", "group-hover/linha:opacity-100", "focus-visible:opacity-100",
      "coarse:opacity-100", "data-[state=open]:opacity-100",
    ]) expect(c).toContain(k)
  })

  it("repassa o que o gatilho do menu injeta (ref, data-state, onClick)", () => {
    // It is what `DropdownMenuTrigger asChild` does with the child.
    const ref = createRef<HTMLButtonElement>()
    let cliques = 0
    render(<GatilhoDeAcoes rotulo="x" ref={ref} data-state="open" onClick={() => { cliques++ }} />)
    const b = screen.getByRole("button")
    expect(ref.current).toBe(b)
    expect(b.getAttribute("data-state")).toBe("open")
    fireEvent.click(b)
    expect(cliques).toBe(1)
  })
})
