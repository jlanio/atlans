import { describe, it, expect, beforeEach, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

import Conversa, { type BlockContext } from "@/app/components/home/assistente/conversa"
import type { AssistantBlock, AssistantTurn } from "@/app/components/home/assistente/quadros"

/**
 * The same Conversa in two modes: the usual one (editor and panel: the whole
 * timeline) and the CAPTION of the Home strip (`compacta`): the question on one
 * line, and from the answer only what remained and what is live. jsdom does no layout —
 * the single line and the 4-line clamp are classes —; what is measured here is who
 * goes into the caption and who stays out, and that the default is still everything.
 */

const QUESTION = "cruze os focos de hoje com as terras indígenas e me dê um resumo por município"
const T1 = "Vou contar os focos por terra indígena."
const T2 = "Encontrei 128 focos em 9 terras indígenas."

function pergunta(id: string, texto = QUESTION): AssistantTurn {
  return { id, papel: "user", texto, blocos: [] }
}

function resposta(id: string, blocos: AssistantBlock[]): AssistantTurn {
  return { id, papel: "assistant", blocos }
}

function texto(t: string): AssistantBlock {
  return { tipo: "texto", texto: t }
}

function pensando(): AssistantBlock {
  return { tipo: "pensando", texto: "Counting the hotspots first." }
}

function ferramenta(id: string, estado: "correndo" | "ok" | "erro" = "ok", nome = "search_nodes"): AssistantBlock {
  return { tipo: "ferramenta", id, nome, argumentos: {}, estado }
}

const CAMADA: AssistantBlock = {
  tipo: "camada",
  camada: { artifact_id: "art1", nome: "Focos de calor", available: true },
}
const ERRO: AssistantBlock = {
  tipo: "erro",
  erro: { code: "sem_conexao", message: "Resposta interrompida." },
}

/** A finished turn with the whole timeline: reasoning, steps, two texts, card. */
const COMPLETED: AssistantBlock[] = [
  pensando(), ferramenta("f1"), ferramenta("f2"), texto(T1), ferramenta("f3"), texto(T2), CAMADA,
]

const extras = (bloco: AssistantBlock) =>
  bloco.tipo === "camada" ? <span data-testid="cartao-camada">{bloco.camada.nome}</span> : null

function passos(container: HTMLElement) {
  return container.querySelectorAll("li[data-ferramenta]")
}

function scroller(container: HTMLElement) {
  return container.querySelector(".overflow-y-auto")!
}

beforeEach(cleanup)

describe("Conversa — o padrão (editor e painel) é a linha do tempo inteira", () => {
  it("a pergunta é a bolha, e todo passo, raciocínio, texto e cartão aparecem", () => {
    const { container } = render(
      <Conversa
        turnos={[pergunta("u1"), resposta("a1", COMPLETED), resposta("a2", [ERRO])]}
        correndo={false}
        extras={extras}
      />,
    )

    const bolha = screen.getByText(QUESTION)
    expect(bolha.tagName).toBe("P")
    expect(bolha.classList.contains("bg-primary/10")).toBe(true)
    expect(bolha.getAttribute("title")).toBeNull()
    expect(screen.queryByText("Você")).toBeNull()

    expect(passos(container).length).toBe(3)
    expect(screen.getByText("Raciocínio")).toBeTruthy()
    expect(screen.getByText(T1)).toBeTruthy()
    expect(screen.getByText(T2).classList.contains("line-clamp-4")).toBe(false)
    expect(screen.getByTestId("cartao-camada")).toBeTruthy()
    expect(screen.getByRole("alert").textContent).toContain("Resposta interrompida.")
  })
})

describe("Conversa — a legenda da faixa (`compacta`)", () => {
  /** The label of the live reasoning: the full text is still "Trabalhando…", but the "…"
   * lives in an sr-only next to the typed ellipsis — the exact string
   * matcher does not see it as a single node. */
  const liveThinking = (raiz: ParentNode = document) =>
    [...raiz.querySelectorAll("summary .texto-pensando")]
      .filter((el) => el.textContent?.replace(/\s+/g, "") === "Trabalhando…")

  it("a pergunta vira uma linha: Você · pergunta, truncada, com o texto inteiro no title", () => {
    render(<Conversa turnos={[pergunta("u1")]} correndo={false} compacta />)

    // The sentence sits in its own span: it is what gets read and what gets found.
    const frase = screen.getByText(QUESTION)
    expect(frase.tagName).toBe("SPAN")
    const linha = frase.closest("p")!
    expect(linha.classList.contains("truncate")).toBe(true)
    expect(linha.classList.contains("bg-primary/10")).toBe(false)
    expect(linha.getAttribute("title")).toBe(QUESTION)
    expect(linha.textContent).toBe(`Você · ${QUESTION}`)
  })

  it("da resposta concluída fica só o último texto (cortado em 4 linhas), o cartão e o erro — sem passos nem raciocínio", () => {
    const { container } = render(
      <Conversa
        turnos={[pergunta("u1"), resposta("a1", COMPLETED), resposta("a2", [ERRO])]}
        correndo={false}
        extras={extras}
        compacta
      />,
    )

    expect(screen.getByText(T2).classList.contains("line-clamp-4")).toBe(true)
    expect(screen.queryByText(T1)).toBeNull()
    expect(passos(container).length).toBe(0)
    expect(screen.queryByText("Raciocínio")).toBeNull()
    expect(screen.getByTestId("cartao-camada")).toBeTruthy()
    expect(screen.getByRole("alert").textContent).toContain("Resposta interrompida.")
  })

  it("sem padding próprio e com a lista mais junta: a faixa é quem espaça", () => {
    const turnos = [pergunta("u1"), resposta("a1", [texto(T2)])]
    const { container, rerender } = render(<Conversa turnos={turnos} correndo={false} />)
    expect(scroller(container).classList.contains("px-3")).toBe(true)
    expect(container.querySelector("ol")!.classList.contains("gap-4")).toBe(true)

    rerender(<Conversa turnos={turnos} correndo={false} compacta />)
    expect(scroller(container).classList.contains("px-3")).toBe(false)
    expect(container.querySelector("ol")!.classList.contains("gap-1.5")).toBe(true)
  })

  it("enquanto o turno corre mostra só o passo em curso; quando o texto chega, o passo sai", () => {
    const inProgress = [pensando(), texto(T1), ferramenta("f1"), ferramenta("f2", "correndo", "run_workflow")]
    const { container, rerender } = render(
      <Conversa turnos={[pergunta("u1"), resposta("a1", inProgress)]} correndo compacta />,
    )

    const vivos = passos(container)
    expect(vivos.length).toBe(1)
    expect(vivos[0].getAttribute("data-ferramenta")).toBe("run_workflow")
    expect(vivos[0].getAttribute("data-estado")).toBe("correndo")
    expect(screen.queryByText("Raciocínio")).toBeNull()
    // The last text so far stays in view: it is what remained.
    expect(screen.getByText(T1)).toBeTruthy()

    const depois = [...inProgress.slice(0, 3), ferramenta("f2", "ok", "run_workflow"), texto(T2)]
    rerender(<Conversa turnos={[pergunta("u1"), resposta("a1", depois)]} correndo compacta />)
    expect(passos(container).length).toBe(0)
    expect(screen.queryByText(T1)).toBeNull()
    expect(screen.getByText(T2)).toBeTruthy()
  })

  it("o raciocínio em curso aparece como Trabalhando… e some quando o texto chega", () => {
    const { rerender } = render(
      <Conversa turnos={[pergunta("u1"), resposta("a1", [pensando()])]} correndo compacta />,
    )
    const [rotulo] = liveThinking()
    expect(rotulo).toBeTruthy()
    // The owner's choice (thinking-indicator previewer): the label has the
    // sweeping shimmer and the typed ellipsis lives in a separate ::after —
    // the "…" the screen reader finds is the sr-only one.
    expect(rotulo.querySelector(".tic-pensando")).toBeTruthy()

    rerender(<Conversa turnos={[pergunta("u1"), resposta("a1", [pensando(), texto(T2)])]} correndo compacta />)
    expect(liveThinking().length).toBe(0)
    expect(screen.queryByText("Raciocínio")).toBeNull()
    expect(screen.getByText(T2)).toBeTruthy()
  })

  it("o raciocínio em curso depois de um passo concluído continua sendo Trabalhando… (o índice é o original)", () => {
    // [thinking, step ok, live thinking]: the filter removes the first two, but the
    // live group is still the last ORIGINAL one — otherwise it would become "Raciocínio".
    render(
      <Conversa turnos={[pergunta("u1"), resposta("a1", [pensando(), ferramenta("f1"), pensando()])]} correndo compacta />,
    )
    expect(liveThinking().length).toBe(1)
    expect(screen.queryByText("Raciocínio")).toBeNull()
    expect(document.querySelectorAll("li[data-ferramenta]").length).toBe(0)
  })

  it("o turno que ainda não produziu bloco diz Trabalhando… nos dois modos", () => {
    const turnos = [pergunta("u1"), resposta("a1", [])]
    const { rerender } = render(<Conversa turnos={turnos} correndo />)
    expect(screen.getByText("Trabalhando…")).toBeTruthy()

    rerender(<Conversa turnos={turnos} correndo compacta />)
    expect(screen.getByText("Trabalhando…")).toBeTruthy()
  })
})

describe("Conversa — o contexto dos extras e o indicador do item pendente", () => {
  it("os extras sabem se o bloco está no ÚLTIMO turno", () => {
    const espiao = vi.fn<(bloco: AssistantBlock, contexto: BlockContext) => React.ReactNode>(() => null)
    render(
      <Conversa
        turnos={[pergunta("u1"), resposta("a1", [CAMADA]), pergunta("u2"), resposta("a2", [CAMADA])]}
        correndo={false}
        extras={espiao}
      />,
    )
    expect(espiao).toHaveBeenCalledTimes(2)
    expect(espiao.mock.calls[0][1]).toEqual({ ultimoTurno: false })
    expect(espiao.mock.calls[1][1]).toEqual({ ultimoTurno: true })
  })

  it("o item pendente usa o ExecActivity por padrão e o indicador passado quando há um — no turno sem bloco e no raciocínio vivo", () => {
    const Marca = ({ size }: { size?: number }) => <svg data-testid="marca" width={size} />
    const withoutBlocks = [pergunta("u1"), resposta("a1", [])]
    const { container, rerender } = render(<Conversa turnos={withoutBlocks} correndo />)
    expect(container.querySelector("svg.exec-activity")).toBeTruthy()
    expect(screen.queryByTestId("marca")).toBeNull()

    rerender(<Conversa turnos={withoutBlocks} correndo indicador={Marca} />)
    expect(container.querySelector("svg.exec-activity")).toBeNull()
    expect(screen.getByTestId("marca").getAttribute("width")).toBe("13")

    // The live reasoning (the <summary> "Trabalhando…") also swaps the indicator — likewise in the caption.
    rerender(<Conversa turnos={[pergunta("u1"), resposta("a1", [pensando()])]} correndo indicador={Marca} compacta />)
    // The "…" lives in the sr-only next to the typed ellipsis: find it by the label.
    const rotulo = container.querySelector("summary .texto-pensando")
    expect(rotulo?.textContent?.replace(/\s+/g, "")).toBe("Trabalhando…")
    expect(screen.getByTestId("marca").getAttribute("width")).toBe("12")
    expect(container.querySelector("svg.exec-activity")).toBeNull()
  })
})

describe("Conversa — o cursor no parágrafo vivo (`cursorAoEscrever`)", () => {
  it("só com a prop, só no último texto do turno em curso, nos dois modos", () => {
    const turnos = [pergunta("u1"), resposta("a1", [texto(T1)]), pergunta("u2"), resposta("a2", [texto(T2)])]
    const { container, rerender } = render(<Conversa turnos={turnos} correndo />)
    expect(container.querySelector(".home-caret")).toBeNull()

    rerender(<Conversa turnos={turnos} correndo cursorAoEscrever />)
    const carets = container.querySelectorAll(".home-caret")
    expect(carets.length).toBe(1)
    expect(carets[0].parentElement?.textContent).toBe(T2)

    rerender(<Conversa turnos={turnos} correndo cursorAoEscrever compacta />)
    expect(container.querySelectorAll(".home-caret").length).toBe(1)

    // A tool after the text takes the cursor with it; so does the end of the turn.
    rerender(
      <Conversa
        turnos={[...turnos.slice(0, 3), resposta("a2", [texto(T2), ferramenta("f1", "correndo")])]}
        correndo
        cursorAoEscrever
      />,
    )
    expect(container.querySelector(".home-caret")).toBeNull()
    rerender(<Conversa turnos={turnos} correndo={false} cursorAoEscrever />)
    expect(container.querySelector(".home-caret")).toBeNull()
  })
})
