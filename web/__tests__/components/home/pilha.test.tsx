import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

import Pilha, { ITENS_AO_CENTRO } from "@/app/components/home/assistente/pilha"
import { useHomeStore } from "@/app/stores/homeStore"
import type { TurnoDoAssistente } from "@/app/components/home/assistente/quadros"

/**
 * The conversation in the center: the SAME conversation as the panel, cut down to the last exchange and
 * drawn as the globe's caption (the strip). jsdom does no layout, so the
 * strip, the single line and the 4-line clamp are left to CSS; what is measured
 * here is the cut, the counter, the caption (`compacta`), the order — the items and
 * then the footer — and the exit to the side.
 */

function pergunta(id: string, texto: string): TurnoDoAssistente {
  return { id, papel: "user", texto, blocos: [] } as TurnoDoAssistente
}

function resposta(id: string, texto: string): TurnoDoAssistente {
  return { id, papel: "assistant", blocos: [{ tipo: "texto", texto }] } as TurnoDoAssistente
}

const confirmar = vi.fn()
const enviar = vi.fn()

beforeEach(() => { cleanup(); enviar.mockClear(); useHomeStore.setState({ painel: "barra" }) })

describe("Pilha — a última troca ao centro", () => {
  it("sem turnos não desenha nada", () => {
    const { container } = render(<Pilha turnos={[]} correndo={false} confirmar={confirmar} enviar={enviar} />)
    expect(container.innerHTML).toBe("")
  })

  it("mostra só os últimos itens e conta os que ficaram para trás", () => {
    const turnos = [
      pergunta("u1", "focos de calor em MT"),
      resposta("a1", "1 284 focos nas últimas 24 h."),
      pergunta("u2", "cruza com terras indígenas"),
      resposta("a2", "212 focos caem em 9 TIs."),
    ]
    render(<Pilha turnos={turnos} correndo={false} confirmar={confirmar} enviar={enviar} />)

    expect(ITENS_AO_CENTRO).toBe(2)
    expect(screen.getByText("cruza com terras indígenas")).toBeTruthy()
    expect(screen.getByText("212 focos caem em 9 TIs.")).toBeTruthy()
    expect(screen.queryByText("focos de calor em MT")).toBeNull()
    expect(screen.queryByText("1 284 focos nas últimas 24 h.")).toBeNull()
    expect(screen.getByText("2 mensagens anteriores")).toBeTruthy()
  })

  it("no singular quando só uma ficou para trás; sem contador quando nada ficou", () => {
    const { rerender } = render(
      <Pilha
        turnos={[pergunta("u1", "a"), resposta("a1", "b"), pergunta("u2", "c")]}
        correndo={false}
        confirmar={confirmar} enviar={enviar}
      />,
    )
    expect(screen.getByText("1 mensagem anterior")).toBeTruthy()

    rerender(<Pilha turnos={[pergunta("u1", "a"), resposta("a1", "b")]} correndo={false} confirmar={confirmar} enviar={enviar} />)
    expect(screen.queryByText(/mensage(m|ns) anterior/)).toBeNull()
  })

  it("Expandir abre o painel lateral — a mesma conversa, inteira", () => {
    render(<Pilha turnos={[pergunta("u1", "a"), resposta("a1", "b")]} correndo={false} confirmar={confirmar} enviar={enviar} />)

    fireEvent.click(screen.getByRole("button", { name: /expandir/i }))
    expect(useHomeStore.getState().painel).toBe("aberto")
  })

  it("é a legenda: a pergunta numa linha com o texto inteiro no title, a resposta cortada em 4 linhas", () => {
    render(
      <Pilha
        turnos={[pergunta("u1", "cruza com terras indígenas"), resposta("a1", "212 focos caem em 9 TIs.")]}
        correndo={false}
        confirmar={confirmar} enviar={enviar}
      />,
    )

    const linha = screen.getByText("cruza com terras indígenas").closest("p")!
    expect(linha.classList.contains("truncate")).toBe(true)
    expect(linha.getAttribute("title")).toBe("cruza com terras indígenas")
    expect(linha.textContent).toBe("Você · cruza com terras indígenas")
    expect(screen.getByText("212 focos caem em 9 TIs.").classList.contains("line-clamp-4")).toBe(true)
  })

  it("o rodapé (anteriores, Expandir) vem DEPOIS dos itens, colado à barra", () => {
    render(
      <Pilha
        turnos={[pergunta("u1", "a"), resposta("a1", "b"), pergunta("u2", "c")]}
        correndo={false}
        confirmar={confirmar} enviar={enviar}
      />,
    )

    const itens = document.querySelector("ol")!
    const expandir = screen.getByRole("button", { name: /expandir/i })
    const contador = screen.getByText("1 mensagem anterior")
    expect(itens.compareDocumentPosition(expandir) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(itens.compareDocumentPosition(contador) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it("os chips da última resposta aparecem na faixa e enviam a frase", () => {
    render(
      <Pilha
        turnos={[
          pergunta("u1", "focos"),
          { id: "a1", papel: "assistant", blocos: [{ tipo: "texto", texto: "128 focos." }, { tipo: "respostas_rapidas", opcoes: ["Só os últimos 7 dias"] }] },
        ]}
        correndo={false}
        confirmar={confirmar} enviar={enviar}
      />,
    )
    fireEvent.click(screen.getByRole("button", { name: "Só os últimos 7 dias" }))
    expect(enviar).toHaveBeenCalledWith("Só os últimos 7 dias")
  })

  it("o item pendente na faixa é a marca animada", () => {
    const { container } = render(
      <Pilha
        turnos={[pergunta("u1", "focos"), { id: "a1", papel: "assistant", blocos: [] }]}
        correndo
        confirmar={confirmar} enviar={enviar}
      />,
    )
    expect(screen.getByText("Trabalhando…")).toBeTruthy()
    expect(container.querySelector("svg.home-marca-anim")).toBeTruthy()
    expect(container.querySelector("svg.exec-activity")).toBeNull()
  })

  it("saindo: a seção marca data-saindo (o CSS desliza e apaga); o padrão é não estar saindo", () => {
    const turnos = [pergunta("u1", "a"), resposta("a1", "b")]
    const { rerender } = render(<Pilha turnos={turnos} correndo={false} confirmar={confirmar} enviar={enviar} />)
    expect(screen.getByTestId("pilha").dataset.saindo).toBe("false")
    rerender(<Pilha turnos={turnos} correndo={false} confirmar={confirmar} enviar={enviar} saindo />)
    expect(screen.getByTestId("pilha").dataset.saindo).toBe("true")
  })

  it("o texto que está sendo escrito termina no cursor", () => {
    const { container } = render(
      <Pilha turnos={[pergunta("u1", "a"), resposta("a1", "Achei 1 2")]} correndo confirmar={confirmar} enviar={enviar} />,
    )
    expect(container.querySelector("p > span.home-caret")).toBeTruthy()
  })

  it("com o pill de cota estourada na barra, a faixa sobe (o atributo que o CSS lê)", () => {
    const turnos = [pergunta("u1", "oi"), resposta("a1", "olá")]
    render(<Pilha turnos={turnos} correndo={false} confirmar={vi.fn()} enviar={vi.fn()} comAvisoDeCota />)
    expect(screen.getByTestId("pilha").dataset.avisoDeCota).toBe("true")
    cleanup()
    render(<Pilha turnos={turnos} correndo={false} confirmar={vi.fn()} enviar={vi.fn()} />)
    expect(screen.getByTestId("pilha").dataset.avisoDeCota).toBe("false")
  })

  it("a folga dos extras (chips de anexo) vira a var que o CSS soma ao bottom", () => {
    const turnos = [pergunta("u1", "oi"), resposta("a1", "olá")]
    // Without attachments, the offset is 0 — the strip stays in its usual position.
    const { rerender } = render(
      <Pilha turnos={turnos} correndo={false} confirmar={vi.fn()} enviar={vi.fn()} />,
    )
    expect(screen.getByTestId("pilha").style.getPropertyValue("--folga-extras")).toBe("0px")
    // With chips measured in the bar, the strip receives the height and moves up.
    rerender(<Pilha turnos={turnos} correndo={false} confirmar={vi.fn()} enviar={vi.fn()} folgaExtras={40} />)
    expect(screen.getByTestId("pilha").style.getPropertyValue("--folga-extras")).toBe("40px")
  })

})
