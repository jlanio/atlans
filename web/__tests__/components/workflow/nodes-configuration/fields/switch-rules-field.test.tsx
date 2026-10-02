/**
 * Editor estruturado das `rules` do Switch.
 *
 * O contrato: persiste a MESMA lista de dicts que o execute lê
 * (`{field, operator, value, output}`), então fluxos salvos pelo editor de
 * JSON abrem aqui e vice-versa.
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
    // No execute, regra sem `output` roteia para o FALLBACK
    // (`rule.get("output", fallback)`) e encerra a avaliação. Inventar
    // "output_1" aqui mudava o roteamento na primeira edição salva.
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
    // uf == MT → saída 1, uf == GO → saída 2: filtrar "uf" quebraria o caso
    // de uso central do Switch.
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
    // A regressão que importa: a definition legada [{uf==MT}] roteia para o
    // fallback; regravá-la com output_1 mudaria silenciosamente o destino
    // de registros que a edição nem tocou.
    const setNodeField = montar([
      { field: "uf", operator: "==", value: "MS" },
      regra,
    ])
    // Edita a SEGUNDA regra (a que tem output) — a legada não pode mudar.
    fireEvent.change(screen.getByDisplayValue("MT"), { target: { value: "GO" } })
    const gravado = setNodeField.mock.calls[0][1] as Record<string, string>[]
    expect(gravado[0]).toEqual({ field: "uf", operator: "==", value: "MS" })
    expect(gravado[0]).not.toHaveProperty("output")
    expect(gravado[1]).toMatchObject({ value: "GO", output: "output_1" })
  })

  it("operador fora do vocabulário aparece e sobrevive à edição", () => {
    // Definition editada à mão: um Select mudo apagaria a escolha na
    // primeira gravação.
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
