/**
 * Selo que distingue, na listagem, um workflow feito para ser CHAMADO por outro.
 *
 * A diferença não é decorativa: um sub-fluxo em geral não tem gatilho próprio,
 * e o botão de executar do card dispara um run que não faz o esperado. Sem o
 * selo, os dois tipos de projeto são o mesmo card.
 */
import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

import { SeloSubFluxo } from "@/app/components/projects/selo-subfluxo"

afterEach(cleanup)

describe("SeloSubFluxo", () => {
  it("aparece no workflow que declara saída de sub-fluxo", () => {
    render(<SeloSubFluxo workflow={{ is_subworkflow: true }} />)
    expect(screen.getByText("Sub-fluxo")).toBeInTheDocument()
  })

  it("o texto de ajuda avisa sobre o gatilho ausente", () => {
    // É a parte acionável: explica por que executar pela lista não resolve.
    render(<SeloSubFluxo workflow={{ is_subworkflow: true }} />)
    expect(screen.getByTitle(/não ter gatilho próprio/)).toBeInTheDocument()
  })

  it("não aparece em workflow comum", () => {
    render(<SeloSubFluxo workflow={{ is_subworkflow: false }} />)
    expect(screen.queryByText("Sub-fluxo")).not.toBeInTheDocument()
  })

  it("não aparece quando o campo não veio", () => {
    // Backend anterior a este campo, ou resposta de cache: ausência não pode
    // marcar todo projeto como sub-fluxo.
    render(<SeloSubFluxo workflow={{}} />)
    expect(screen.queryByText("Sub-fluxo")).not.toBeInTheDocument()
  })
})
