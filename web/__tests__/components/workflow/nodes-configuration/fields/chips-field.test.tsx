/**
 * Chips field — the column list of the Attribute Join.
 *
 * It used to be comma-separated text: it didn't show what was already there,
 * and removing a name from the middle meant editing the string. The old format
 * remains in saved definitions, so the field has to READ both.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen, cleanup, fireEvent } from "@testing-library/react"

import ChipsField, {
  fichasNovas,
  lerFichas,
} from "@/app/components/workflow/nodes-configuration/fields/chips-field"
import { INodesPropertyAPI } from "@/service/types"

afterEach(cleanup)

const campo = {
  name: "columns",
  label: "Colunas de B a trazer",
  type: "chips",
  default: [],
  description: null,
} as unknown as INodesPropertyAPI

function montar(valor: unknown) {
  const setNodeField = vi.fn()
  render(
    <ChipsField
      field={campo}
      values={{ columns: valor } as Record<string, string>}
      setNodeField={setNodeField}
    />,
  )
  return setNodeField
}

const entrada = () => screen.getByPlaceholderText(/Adicionar outra|Nome da coluna/)

describe("lerFichas", () => {
  it("lê a lista JSON que o campo grava", () => {
    expect(lerFichas('["pop","renda"]')).toEqual(["pop", "renda"])
  })

  it("lê o formato antigo, separado por vírgula", () => {
    // It's what is saved in workflows created before the field changed. Without
    // this, opening one would show the field empty — and saving would erase the configuration.
    expect(lerFichas("pop, renda_media")).toEqual(["pop", "renda_media"])
  })

  it("lê uma lista de verdade", () => {
    expect(lerFichas(["a", " b "])).toEqual(["a", "b"])
  })

  it.each([undefined, null, "", "   ", "[]"])("%s vira lista vazia", (v) => {
    expect(lerFichas(v)).toEqual([])
  })

  it("JSON quebrado cai no formato de texto em vez de sumir com o valor", () => {
    expect(lerFichas('["pop", renda')).toEqual(['["pop"', "renda"])
  })
})

describe("fichasNovas", () => {
  it("separa uma colagem com vírgulas", () => {
    expect(fichasNovas("a, b ,c", [])).toEqual(["a", "b", "c"])
  })

  it("não repete o que já está na lista", () => {
    expect(fichasNovas("a, b", ["a"])).toEqual(["b"])
  })

  it("não repete dentro da própria colagem", () => {
    expect(fichasNovas("a, a", [])).toEqual(["a"])
  })

  it("entrada em branco não adiciona nada", () => {
    expect(fichasNovas("  , ,", [])).toEqual([])
  })
})

describe("ChipsField", () => {
  it("mostra uma ficha por coluna", () => {
    montar('["pop","renda"]')
    expect(screen.getByText("pop")).toBeInTheDocument()
    expect(screen.getByText("renda")).toBeInTheDocument()
  })

  it("Enter adiciona e grava como CSV — o formato que TODO leitor entende", () => {
    // Including an executor with a flow/ older than the migration to chips,
    // which still parses with split(","): a JSON string there became a ghost column.
    const setNodeField = montar('["pop"]')
    fireEvent.change(entrada(), { target: { value: "renda" } })
    fireEvent.keyDown(entrada(), { key: "Enter" })
    expect(setNodeField).toHaveBeenCalledWith("columns", "pop, renda")
  })

  it("nome com vírgula (que o CSV nunca representou) cai no JSON", () => {
    const setNodeField = montar('["a,b"]')
    fireEvent.change(entrada(), { target: { value: "c" } })
    fireEvent.keyDown(entrada(), { key: "Enter" })
    expect(setNodeField).toHaveBeenCalledWith("columns", '["a,b","c"]')
  })

  it("a vírgula também fecha a ficha", () => {
    const setNodeField = montar("[]")
    fireEvent.change(entrada(), { target: { value: "pop" } })
    fireEvent.keyDown(entrada(), { key: "," })
    expect(setNodeField).toHaveBeenCalledWith("columns", "pop")
  })

  it("sair do campo com algo digitado adiciona", () => {
    // Losing what you typed because you clicked outside is the classic defect of
    // this kind of field.
    const setNodeField = montar("[]")
    fireEvent.change(entrada(), { target: { value: "renda" } })
    fireEvent.blur(entrada())
    expect(setNodeField).toHaveBeenCalledWith("columns", "renda")
  })

  it("o X remove só aquela coluna", () => {
    const setNodeField = montar('["pop","renda"]')
    fireEvent.click(screen.getByLabelText("Remover pop"))
    expect(setNodeField).toHaveBeenCalledWith("columns", "renda")
  })

  it("remover a última ficha grava \"\" — \"[]\" no split(\",\") antigo virava a coluna fantasma \"[]\"", () => {
    const setNodeField = montar('["pop"]')
    fireEvent.click(screen.getByLabelText("Remover pop"))
    expect(setNodeField).toHaveBeenCalledWith("columns", "")
  })

  it("Backspace no campo vazio remove a última", () => {
    const setNodeField = montar('["pop","renda"]')
    fireEvent.keyDown(entrada(), { key: "Backspace" })
    expect(setNodeField).toHaveBeenCalledWith("columns", "pop")
  })

  it("Backspace com texto digitado NÃO remove ficha", () => {
    const setNodeField = montar('["pop"]')
    fireEvent.change(entrada(), { target: { value: "re" } })
    fireEvent.keyDown(entrada(), { key: "Backspace" })
    expect(setNodeField).not.toHaveBeenCalled()
  })

  it("abre o formato antigo mostrando as fichas", () => {
    montar("pop, renda")
    expect(screen.getByText("pop")).toBeInTheDocument()
    expect(screen.getByText("renda")).toBeInTheDocument()
  })
})

describe("sugestões de coluna", () => {
  function withSuggestions(valor: unknown, sugestoes: string[]) {
    const setNodeField = vi.fn()
    render(
      <ChipsField
        field={campo}
        values={{ columns: valor } as Record<string, string>}
        setNodeField={setNodeField}
        sugestoes={sugestoes}
      />,
    )
    return setNodeField
  }

  it("oferece as colunas vistas na última execução", () => {
    withSuggestions("[]", ["populacao", "renda"])
    expect(screen.getByText(/Vistas na última execução/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "populacao" })).toBeInTheDocument()
  })

  it("clicar na sugestão adiciona a ficha", () => {
    const setNodeField = withSuggestions("[]", ["populacao"])
    fireEvent.click(screen.getByRole("button", { name: "populacao" }))
    expect(setNodeField).toHaveBeenCalledWith("columns", "populacao")
  })

  it("não oferece o que já é ficha", () => {
    // Repeating what has already been chosen just becomes noise in the list.
    withSuggestions('["populacao"]', ["populacao", "renda"])
    expect(screen.queryByRole("button", { name: "populacao" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "renda" })).toBeInTheDocument()
  })

  it("sem execução anterior, nenhum bloco de sugestão aparece", () => {
    // The node has never run: making up a list would be worse than showing nothing.
    withSuggestions("[]", [])
    expect(screen.queryByText(/Vistas na última execução/)).not.toBeInTheDocument()
  })

  it("escrever um nome fora da lista continua valendo", () => {
    // It's a hint, not validation: the workflow may have changed since the last run.
    const setNodeField = withSuggestions("[]", ["populacao"])
    fireEvent.change(entrada(), { target: { value: "coluna_nova" } })
    fireEvent.keyDown(entrada(), { key: "Enter" })
    expect(setNodeField).toHaveBeenCalledWith("columns", "coluna_nova")
  })
})
