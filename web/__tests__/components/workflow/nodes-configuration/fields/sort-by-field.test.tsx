/**
 * Editor estruturado do `sort_by` do Ordenar.
 *
 * O contrato que importa: o valor persiste como a MESMA lista
 * `[{field, direction}]` que o execute do backend lê — um fluxo salvo pelo
 * editor de JSON antigo abre aqui, e um salvo aqui roda em executor antigo.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen, cleanup, fireEvent } from "@testing-library/react"

import SortByField, { lerCriterios } from "@/app/components/workflow/nodes-configuration/fields/sort-by-field"
import { INodesPropertyAPI } from "@/service/types"

afterEach(cleanup)

const campo = {
  name: "sort_by",
  label: "Ordenar Por",
  type: "object",
  default: [],
  description: null,
  suggest_columns: "*",
} as unknown as INodesPropertyAPI

function montar(valor: unknown, sugestoes: string[] = []) {
  const setNodeField = vi.fn()
  render(
    <SortByField
      field={campo}
      values={{ sort_by: valor } as unknown as Record<string, string>}
      setNodeField={setNodeField}
      sugestoes={sugestoes}
    />,
  )
  return setNodeField
}

describe("lerCriterios", () => {
  it("lê a lista de verdade (definition salva pelo editor de JSON)", () => {
    expect(lerCriterios([{ field: "area", direction: "desc" }])).toEqual([
      { field: "area", direction: "desc" },
    ])
  })

  it("lê JSON-string e normaliza a direção", () => {
    expect(lerCriterios('[{"field":"nome","direction":"DESC"},{"field":"uf"}]')).toEqual([
      { field: "nome", direction: "desc" },
      { field: "uf", direction: "asc" },
    ])
  })

  it.each([undefined, null, "", "{}", "não é lista", 42])("%s vira lista vazia", (v) => {
    expect(lerCriterios(v)).toEqual([])
  })

  it("entradas que não são objeto são descartadas sem derrubar o resto", () => {
    expect(lerCriterios([null, "x", { field: "ok" }])).toEqual([
      { field: "ok", direction: "asc" },
    ])
  })
})

describe("SortByField", () => {
  it("mostra os critérios salvos como linhas editáveis", () => {
    montar([{ field: "area", direction: "desc" }])
    expect(screen.getByDisplayValue("area")).toBeInTheDocument()
  })

  it("editar o campo grava a LISTA (não JSON-string) com o resto preservado", () => {
    const setNodeField = montar([{ field: "area", direction: "desc" }])
    fireEvent.change(screen.getByDisplayValue("area"), { target: { value: "nome" } })
    expect(setNodeField).toHaveBeenCalledWith("sort_by", [
      { field: "nome", direction: "desc" },
    ])
  })

  it("clicar numa sugestão abre um critério novo com a coluna", () => {
    const setNodeField = montar([], ["pop", "renda"])
    fireEvent.click(screen.getByRole("button", { name: "pop" }))
    expect(setNodeField).toHaveBeenCalledWith("sort_by", [
      { field: "pop", direction: "asc" },
    ])
  })

  it("com uma linha vazia aberta, a sugestão a preenche em vez de duplicar", () => {
    const setNodeField = montar([{ field: "", direction: "desc" }], ["pop"])
    fireEvent.click(screen.getByRole("button", { name: "pop" }))
    // A direção que a pessoa já escolheu na linha vazia não é resetada.
    expect(setNodeField).toHaveBeenCalledWith("sort_by", [
      { field: "pop", direction: "desc" },
    ])
  })

  it("coluna já usada some das sugestões", () => {
    montar([{ field: "pop", direction: "asc" }], ["pop", "renda"])
    expect(screen.queryByRole("button", { name: "pop" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "renda" })).toBeInTheDocument()
  })

  it("remover uma linha grava a lista sem ela", () => {
    const setNodeField = montar([
      { field: "a", direction: "asc" },
      { field: "b", direction: "desc" },
    ])
    fireEvent.click(screen.getByRole("button", { name: "Remover critério 1" }))
    expect(setNodeField).toHaveBeenCalledWith("sort_by", [
      { field: "b", direction: "desc" },
    ])
  })
})
