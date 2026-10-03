import { describe, it, expect } from "vitest"
import {
  resolveNodeAlias,
  isValidAlias,
  RESERVED_ALIASES,
  IDENTIFIER_SOURCE,
} from "@/app/components/workflow/utils/node-alias"

/**
 * Regression: the expression autocomplete suggested `data.alias` — the display
 * label — and inserted `{{$Caixa Delimitadora.bbox}}` into the field. The
 * executor registers the node under `_resolve_alias` (flow/executor/core.py),
 * which requires a valid identifier and otherwise falls back to the class's
 * `name`, so the expression pointed to a key that didn't exist in the context.
 *
 * Side effect of the space: the autocomplete trigger scans identifiers, so after
 * inserting the label the text itself stopped matching and the "." never listed
 * the output fields.
 */

describe("isValidAlias", () => {
  it("aceita identificador ASCII", () => {
    expect(isValidAlias("MinhaCaixa")).toBe(true)
    expect(isValidAlias("_interno")).toBe(true)
    expect(isValidAlias("bbox2")).toBe(true)
  })

  it("aceita identificador acentuado, como o str.isidentifier() do Python", () => {
    expect(isValidAlias("Área")).toBe(true)
    expect(isValidAlias("Edificação")).toBe(true)
  })

  it("recusa espaço — o caso que gerava a expressão quebrada", () => {
    expect(isValidAlias("Caixa Delimitadora")).toBe(false)
    expect(isValidAlias("Entrada de Dados")).toBe(false)
  })

  it("recusa início inválido e pontuação", () => {
    expect(isValidAlias("2bbox")).toBe(false)
    expect(isValidAlias("nó-a")).toBe(false)
    expect(isValidAlias("a.b")).toBe(false)
  })

  it("recusa vazio e ausente", () => {
    expect(isValidAlias("")).toBe(false)
    expect(isValidAlias(undefined)).toBe(false)
    expect(isValidAlias(null)).toBe(false)
  })

  it("recusa os nomes reservados do contexto Jinja", () => {
    for (const reservado of RESERVED_ALIASES) {
      expect(isValidAlias(reservado)).toBe(false)
    }
  })
})

describe("resolveNodeAlias", () => {
  it("usa properties.alias só quando data.alias vem vazio", () => {
    expect(resolveNodeAlias({
      alias: "",
      properties: { alias: "Caixa" },
      name: "ComputeBoundingBox",
    })).toBe("Caixa")
  })

  it("data.alias preenchido descarta properties.alias, como o `or` do executor", () => {
    // The executor picks by truthiness: with `alias` filled in it doesn't even
    // look at properties.alias, and the label with a space sends it straight to `name`.
    expect(resolveNodeAlias({
      alias: "Caixa Delimitadora",
      properties: { alias: "Caixa" },
      name: "ComputeBoundingBox",
    })).toBe("ComputeBoundingBox")
  })

  it("acompanha a promoção do alias feita ao salvar o modal", () => {
    // saveNodeConfig copies the typed alias to data.alias — that's the state
    // that reaches the database and, therefore, the executor.
    expect(resolveNodeAlias({
      alias: "Caixa",
      properties: { alias: "Caixa" },
      name: "ComputeBoundingBox",
    })).toBe("Caixa")
  })

  it("usa o alias customizado quando ele é utilizável", () => {
    expect(resolveNodeAlias({ alias: "Caixa", name: "ComputeBoundingBox" })).toBe("Caixa")
  })

  it("cai no name da classe quando o rótulo tem espaço", () => {
    expect(resolveNodeAlias({ alias: "Caixa Delimitadora", name: "ComputeBoundingBox" }))
      .toBe("ComputeBoundingBox")
  })

  it("cai no name quando o alias é reservado", () => {
    expect(resolveNodeAlias({ alias: "inputs", name: "DataInput" })).toBe("DataInput")
  })

  it("cai no name quando não há alias", () => {
    expect(resolveNodeAlias({ name: "ComputeBoundingBox" })).toBe("ComputeBoundingBox")
    expect(resolveNodeAlias({ alias: "", name: "ComputeBoundingBox" })).toBe("ComputeBoundingBox")
  })

  it("ignora alias que não é string", () => {
    expect(resolveNodeAlias({ alias: 42, name: "DataInput" })).toBe("DataInput")
  })

  it("devolve string vazia quando não há nome — chamador deve descartar", () => {
    expect(resolveNodeAlias({})).toBe("")
  })

  it("o resultado é sempre um alias utilizável quando há name", () => {
    const casos = [
      { alias: "Caixa Delimitadora", name: "ComputeBoundingBox" },
      { alias: "now", name: "DataInput" },
      { alias: "1º nó", name: "ReadGeoJSON" },
    ]
    for (const caso of casos) {
      expect(isValidAlias(resolveNodeAlias(caso))).toBe(true)
    }
  })
})

describe("IDENTIFIER_SOURCE", () => {
  it("compõe o varredor de `Alias.campo` usado pelo autocomplete", () => {
    const trigger = new RegExp(`\\$(${IDENTIFIER_SOURCE}(?:\\.[\\p{ID_Continue}]*)*)$`, "u")

    expect("{{$ComputeBoundingBox.bbox".match(trigger)?.[1]).toBe("ComputeBoundingBox.bbox")
    // After the dot, still without a field: this is where the output list appears.
    expect("{{$ComputeBoundingBox.".match(trigger)?.[1]).toBe("ComputeBoundingBox.")
    expect("{{$Área.total".match(trigger)?.[1]).toBe("Área.total")
    // The space cuts the trigger — the reason the label can never go into the text.
    expect("{{$Caixa Delimitadora".match(trigger)).toBeNull()
  })
})
