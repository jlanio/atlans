/**
 * The current step in the footer bar.
 *
 * The bar moves down to the footer as soon as the person submits (before the 1st text
 * token), and during reasoning and tools — which can take seconds —
 * this indicator tells what is happening NOW. What is protected here is the
 * reading of the last block of the turn in progress and the labels (the same as the panel's).
 */
import { describe, it, expect, afterEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

import { etapaDaConversa, IndicadorDeEtapa } from "@/app/components/home/assistente/etapa"
import type { AssistantBlock, AssistantTurn } from "@/app/components/home/assistente/quadros"

afterEach(() => cleanup())

const user = (texto: string): AssistantTurn => ({ id: `u-${texto}`, papel: "user", texto, blocos: [] } as AssistantTurn)
const assist = (blocos: AssistantBlock[]): AssistantTurn => ({ id: "a1", papel: "assistant", blocos } as AssistantTurn)
const ferramenta = (nome: string, estado: "correndo" | "ok" | "erro", argumentos: Record<string, unknown> = {}): AssistantBlock =>
  ({ tipo: "ferramenta", id: `f-${nome}`, nome, argumentos, estado })

describe("etapaDaConversa", () => {
  it("parado (não correndo) não tem passo", () => {
    expect(etapaDaConversa([user("oi"), assist([{ tipo: "pensando", texto: "…" }])], false)).toBeNull()
  })

  it("sem turno do assistente, também não", () => {
    expect(etapaDaConversa([user("oi")], true)).toBeNull()
  })

  it("turno ainda sem bloco → Pensando", () => {
    expect(etapaDaConversa([user("oi"), assist([])], true)).toEqual({ tipo: "pensando", rotulo: "Pensando" })
  })

  it("último bloco de raciocínio → Pensando", () => {
    expect(etapaDaConversa([assist([{ tipo: "pensando", texto: "preciso do catálogo" }])], true))
      .toEqual({ tipo: "pensando", rotulo: "Pensando" })
  })

  it("ferramenta EM CURSO → o rótulo dela, com o detalhe da chamada", () => {
    const etapa = etapaDaConversa([assist([ferramenta("get_authoring_guide", "correndo", { topic: "edges" })])], true)
    expect(etapa).toEqual({ tipo: "ferramenta", rotulo: "Consultando o guia", detalhe: "edges" })
  })

  it("ferramenta sem argumento curto conhecido → sem detalhe", () => {
    const etapa = etapaDaConversa([assist([ferramenta("run_workflow", "correndo", {})])], true)
    expect(etapa).toEqual({ tipo: "ferramenta", rotulo: "Executando o fluxo", detalhe: undefined })
  })

  it("ferramenta JÁ CONCLUÍDA (digerindo o resultado) → volta a Pensando", () => {
    expect(etapaDaConversa([assist([ferramenta("search_nodes", "ok", { query: "focos" })])], true))
      .toEqual({ tipo: "pensando", rotulo: "Pensando" })
  })

  it("já escrevendo (último bloco de texto) → sem passo: a resposta aparece na faixa", () => {
    expect(etapaDaConversa([assist([{ tipo: "pensando", texto: "…" }, { tipo: "texto", texto: "Achei 1 284." }])], true))
      .toBeNull()
  })

  it("lê o ÚLTIMO turno do assistente, não um anterior", () => {
    const turnos = [
      assist([{ tipo: "texto", texto: "resposta antiga" }]),
      user("e agora?"),
      assist([ferramenta("list_runs", "correndo")]),
    ]
    expect(etapaDaConversa(turnos, true)).toMatchObject({ tipo: "ferramenta", rotulo: "Listando execuções" })
  })
})

describe("IndicadorDeEtapa", () => {
  it("no pensar, mostra 'Pensando…' com o brilho que varre", () => {
    render(<IndicadorDeEtapa etapa={{ tipo: "pensando", rotulo: "Pensando" }} />)
    const el = screen.getByTestId("etapa-da-barra")
    expect(el.textContent).toContain("Pensando…")
    // aria-live so the screen reader announces the step change.
    expect(el.getAttribute("aria-live")).toBe("polite")
  })

  it("na ferramenta, mostra o rótulo e o detalhe", () => {
    render(<IndicadorDeEtapa etapa={{ tipo: "ferramenta", rotulo: "Consultando o guia", detalhe: "edges" }} />)
    const el = screen.getByTestId("etapa-da-barra")
    expect(el.textContent).toContain("Consultando o guia")
    expect(el.textContent).toContain("edges")
  })

  it("ferramenta sem detalhe não pinta o separador", () => {
    render(<IndicadorDeEtapa etapa={{ tipo: "ferramenta", rotulo: "Executando o fluxo" }} />)
    expect(screen.getByTestId("etapa-da-barra").textContent).not.toContain("·")
  })
})
