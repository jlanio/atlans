/**
 * Structured editor for the Switch's `rules`.
 *
 * The contract: it persists the SAME list of dicts that execute reads
 * (`{field, operator, value, output}`), so workflows saved by the JSON editor
 * open here and vice versa.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen, cleanup, fireEvent } from "@testing-library/react"

import SwitchRulesField, { lerRegras, serializarRegras } from "@/app/components/workflow/nodes-configuration/fields/switch-rules-field"
import { INodesPropertyAPI } from "@/service/types"

afterEach(cleanup)

const campo = {
  name: "rules",
  label: "Regras",
  type: "object",
  default: [],
  description: null,
  suggest_columns: "*",
} as unknown as INodesPropertyAPI

function montar(valor: unknown, sugestoes: string[] = []) {
  const setNodeField = vi.fn()
  render(
    <SwitchRulesField
      field={campo}
      values={{ rules: valor } as unknown as Record<string, string>}
      setNodeField={setNodeField}
      sugestoes={sugestoes}
    />,
  )
  return setNodeField
}

describe("lerRegras", () => {
  it("normaliza só o que o execute também normaliza — output ausente fica ausente", () => {
    // In execute, a rule without `output` routes to the FALLBACK
    // (`rule.get("output", fallback)`) and ends the evaluation. Making up
    // "output_1" here changed the routing on the first saved edit.
    expect(lerRegras([{ field: "uf", value: "MT" }])).toEqual([
      { field: "uf", operator: "==", value: "MT", output: "" },
    ])
  })

  it("lê JSON-string", () => {
    expect(lerRegras('[{"field":"uf","operator":"!=","value":"GO","output":"output_2"}]')).toEqual([
      { field: "uf", operator: "!=", value: "GO", output: "output_2" },
    ])
  })

  it.each([undefined, null, "", "{}", 7])("%s vira lista vazia", (v) => {
    expect(lerRegras(v)).toEqual([])
  })
})

describe("serializarRegras", () => {
  it("regra de fallback vai SEM a chave output — o contrato exato do execute", () => {
    expect(serializarRegras([{ field: "uf", operator: "==", value: "MT", output: "" }]))
      .toEqual([{ field: "uf", operator: "==", value: "MT" }])
  })

  it("round-trip da definition legada preserva o roteamento", () => {
    const legada = [{ field: "uf", operator: "==", value: "MT" }]
    expect(serializarRegras(lerRegras(legada))).toEqual(legada)
  })
})

describe("SwitchRulesField", () => {
  const regra = { field: "uf", operator: "==", value: "MT", output: "output_1" }

  it("editar o valor grava a LISTA com a regra atualizada", () => {
    const setNodeField = montar([regra])
    fireEvent.change(screen.getByDisplayValue("MT"), { target: { value: "GO" } })
    expect(setNodeField).toHaveBeenCalledWith("rules", [
      { ...regra, value: "GO" },
    ])
  })

  it("clicar numa sugestão abre uma regra nova com defaults", () => {
    const setNodeField = montar([], ["uf", "pop"])
    fireEvent.click(screen.getByRole("button", { name: "uf" }))
    expect(setNodeField).toHaveBeenCalledWith("rules", [
      { field: "uf", operator: "==", value: "", output: "output_1" },
    ])
  })

  it("a MESMA coluna pode reger várias regras — a sugestão não some ao usar", () => {
    // uf == MT → output 1, uf == GO → output 2: filtering out "uf" would break
    // the Switch's central use case.
    montar([regra], ["uf", "pop"])
    expect(screen.getByRole("button", { name: "uf" })).toBeInTheDocument()
  })

  it("com uma regra sem campo, a sugestão a preenche em vez de duplicar", () => {
    const setNodeField = montar(
      [{ field: "", operator: ">", value: "10", output: "output_3" }],
      ["pop"],
    )
    fireEvent.click(screen.getByRole("button", { name: "pop" }))
    expect(setNodeField).toHaveBeenCalledWith("rules", [
      { field: "pop", operator: ">", value: "10", output: "output_3" },
    ])
  })

  it("remover uma regra grava a lista sem ela", () => {
    const setNodeField = montar([
      regra,
      { field: "pop", operator: ">", value: "10", output: "output_2" },
    ])
    fireEvent.click(screen.getByRole("button", { name: "Remover regra 2" }))
    expect(setNodeField).toHaveBeenCalledWith("rules", [regra])
  })

  it("editar OUTRA regra não carimba output na regra legada sem ele", () => {
    // The regression that matters: the legacy definition [{uf==MT}] routes to
    // the fallback; rewriting it with output_1 would silently change the
    // destination of records the edit didn't even touch.
    const setNodeField = montar([
      { field: "uf", operator: "==", value: "MS" },
      regra,
    ])
    // Edits the SECOND rule (the one with output) — the legacy one must not change.
    fireEvent.change(screen.getByDisplayValue("MT"), { target: { value: "GO" } })
    const gravado = setNodeField.mock.calls[0][1] as Record<string, string>[]
    expect(gravado[0]).toEqual({ field: "uf", operator: "==", value: "MS" })
    expect(gravado[0]).not.toHaveProperty("output")
    expect(gravado[1]).toMatchObject({ value: "GO", output: "output_1" })
  })

  it("operador fora do vocabulário aparece e sobrevive à edição", () => {
    // Hand-edited definition: a mute Select would erase the choice on the
    // first save.
    const setNodeField = montar([
      { field: "uf", operator: "regex", value: "^M", output: "output_2" },
    ])
    expect(screen.getByText("regex")).toBeInTheDocument()
    fireEvent.change(screen.getByDisplayValue("^M"), { target: { value: "^G" } })
    expect(setNodeField).toHaveBeenCalledWith("rules", [
      { field: "uf", operator: "regex", value: "^G", output: "output_2" },
    ])
  })

  it("saída fora do vocabulário aparece e sobrevive à edição", () => {
    const setNodeField = montar([
      { field: "uf", operator: "==", value: "MT", output: "minha_saida" },
    ])
    expect(screen.getByText("minha_saida")).toBeInTheDocument()
    fireEvent.change(screen.getByDisplayValue("MT"), { target: { value: "GO" } })
    expect(setNodeField).toHaveBeenCalledWith("rules", [
      { field: "uf", operator: "==", value: "GO", output: "minha_saida" },
    ])
  })
})
