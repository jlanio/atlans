import { describe, it, expect, beforeEach, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

import Conversa, { type ContextoDoBloco } from "@/app/components/home/assistente/conversa"
import type { BlocoDoAssistente, TurnoDoAssistente } from "@/app/components/home/assistente/quadros"

/**
 * A mesma Conversa em dois modos: a de sempre (editor e painel: a linha do
 * tempo inteira) e a LEGENDA da faixa da Home (`compacta`): a pergunta numa
 * linha, e da resposta só o que ficou e o que está vivo. jsdom não faz layout —
 * a linha única e o corte em 4 linhas são classes —; o que se mede aqui é quem
 * entra na legenda e quem fica de fora, e que o padrão continua sendo tudo.
 */

const PERGUNTA = "cruze os focos de hoje com as terras indígenas e me dê um resumo por município"
const T1 = "Vou contar os focos por terra indígena."
const T2 = "Encontrei 128 focos em 9 terras indígenas."

function pergunta(id: string, texto = PERGUNTA): TurnoDoAssistente {
  return { id, papel: "user", texto, blocos: [] }
}

function resposta(id: string, blocos: BlocoDoAssistente[]): TurnoDoAssistente {
  return { id, papel: "assistant", blocos }
}

function texto(t: string): BlocoDoAssistente {
  return { tipo: "texto", texto: t }
}

function pensando(): BlocoDoAssistente {
  return { tipo: "pensando", texto: "Counting the hotspots first." }
}

function ferramenta(id: string, estado: "correndo" | "ok" | "erro" = "ok", nome = "search_nodes"): BlocoDoAssistente {
  return { tipo: "ferramenta", id, nome, argumentos: {}, estado }
}

const CAMADA: BlocoDoAssistente = {
  tipo: "camada",
  camada: { artifact_id: "art1", nome: "Focos de calor", available: true },
}
const ERRO: BlocoDoAssistente = {
  tipo: "erro",
  erro: { code: "sem_conexao", message: "Resposta interrompida." },
}

/** Um turno concluído com a linha do tempo inteira: raciocínio, passos, dois textos, cartão. */
const CONCLUIDO: BlocoDoAssistente[] = [
  pensando(), ferramenta("f1"), ferramenta("f2"), texto(T1), ferramenta("f3"), texto(T2), CAMADA,
]

const extras = (bloco: BlocoDoAssistente) =>
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
        turnos={[pergunta("u1"), resposta("a1", CONCLUIDO), resposta("a2", [ERRO])]}
        correndo={false}
        extras={extras}
      />,
    )

    const bolha = screen.getByText(PERGUNTA)
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
  /** O rótulo do raciocínio vivo: o texto inteiro segue "Trabalhando…", mas o "…"
   * mora num sr-only ao lado das reticências digitadas — o matcher exato de
   * string não o vê como um nó só. */
  const pensandoVivo = (raiz: ParentNode = document) =>
    [...raiz.querySelectorAll("summary .texto-pensando")]
      .filter((el) => el.textContent?.replace(/\s+/g, "") === "Trabalhando…")

  it("a pergunta vira uma linha: Você · pergunta, truncada, com o texto inteiro no title", () => {
    render(<Conversa turnos={[pergunta("u1")]} correndo={false} compacta />)

    // A frase fica num span próprio: é ela que se lê e que se encontra.
    const frase = screen.getByText(PERGUNTA)
    expect(frase.tagName).toBe("SPAN")
    const linha = frase.closest("p")!
    expect(linha.classList.contains("truncate")).toBe(true)
    expect(linha.classList.contains("bg-primary/10")).toBe(false)
    expect(linha.getAttribute("title")).toBe(PERGUNTA)
    expect(linha.textContent).toBe(`Você · ${PERGUNTA}`)
  })

  it("da resposta concluída fica só o último texto (cortado em 4 linhas), o cartão e o erro — sem passos nem raciocínio", () => {
    const { container } = render(
      <Conversa
        turnos={[pergunta("u1"), resposta("a1", CONCLUIDO), resposta("a2", [ERRO])]}
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
    const emCurso = [pensando(), texto(T1), ferramenta("f1"), ferramenta("f2", "correndo", "run_workflow")]
    const { container, rerender } = render(
      <Conversa turnos={[pergunta("u1"), resposta("a1", emCurso)]} correndo compacta />,
    )

    const vivos = passos(container)
    expect(vivos.length).toBe(1)
    expect(vivos[0].getAttribute("data-ferramenta")).toBe("run_workflow")
    expect(vivos[0].getAttribute("data-estado")).toBe("correndo")
    expect(screen.queryByText("Raciocínio")).toBeNull()
    // O último texto até aqui continua à vista: é o que ficou.
    expect(screen.getByText(T1)).toBeTruthy()

    const depois = [...emCurso.slice(0, 3), ferramenta("f2", "ok", "run_workflow"), texto(T2)]
    rerender(<Conversa turnos={[pergunta("u1"), resposta("a1", depois)]} correndo compacta />)
    expect(passos(container).length).toBe(0)
    expect(screen.queryByText(T1)).toBeNull()
    expect(screen.getByText(T2)).toBeTruthy()
  })

  it("o raciocínio em curso aparece como Trabalhando… e some quando o texto chega", () => {
    const { rerender } = render(
      <Conversa turnos={[pergunta("u1"), resposta("a1", [pensando()])]} correndo compacta />,
    )
    const [rotulo] = pensandoVivo()
    expect(rotulo).toBeTruthy()
    // A escolha do dono (previewer do indicador de pensamento): o rótulo tem o
    // brilho que varre e as reticências digitadas vivem num ::after à parte —
    // o "…" que o leitor de tela encontra é o do sr-only.
    expect(rotulo.querySelector(".tic-pensando")).toBeTruthy()

    rerender(<Conversa turnos={[pergunta("u1"), resposta("a1", [pensando(), texto(T2)])]} correndo compacta />)
    expect(pensandoVivo().length).toBe(0)
    expect(screen.queryByText("Raciocínio")).toBeNull()
    expect(screen.getByText(T2)).toBeTruthy()
  })

  it("o raciocínio em curso depois de um passo concluído continua sendo Trabalhando… (o índice é o original)", () => {
    // [pensando, passo ok, pensando vivo]: o filtro tira os dois primeiros, mas o
    // grupo vivo continua sendo o último ORIGINAL — senão viraria "Raciocínio".
    render(
      <Conversa turnos={[pergunta("u1"), resposta("a1", [pensando(), ferramenta("f1"), pensando()])]} correndo compacta />,
    )
    expect(pensandoVivo().length).toBe(1)
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
    const espiao = vi.fn<(bloco: BlocoDoAssistente, contexto: ContextoDoBloco) => React.ReactNode>(() => null)
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
    const semBloco = [pergunta("u1"), resposta("a1", [])]
    const { container, rerender } = render(<Conversa turnos={semBloco} correndo />)
    expect(container.querySelector("svg.exec-activity")).toBeTruthy()
    expect(screen.queryByTestId("marca")).toBeNull()

    rerender(<Conversa turnos={semBloco} correndo indicador={Marca} />)
    expect(container.querySelector("svg.exec-activity")).toBeNull()
    expect(screen.getByTestId("marca").getAttribute("width")).toBe("13")

    // O raciocínio vivo (o <summary> "Trabalhando…") também troca o indicador — na legenda idem.
    rerender(<Conversa turnos={[pergunta("u1"), resposta("a1", [pensando()])]} correndo indicador={Marca} compacta />)
    // O "…" mora no sr-only ao lado das reticências digitadas: acha pelo rótulo.
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

    // Uma ferramenta depois do texto leva o cursor com ela; o fim do turno também.
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
