import { describe, it, expect } from "vitest"
import {
  resolveNodeAlias,
  isValidAlias,
  RESERVED_ALIASES,
  IDENTIFIER_SOURCE,
} from "@/app/components/workflow/utils/node-alias"

/**
 * Regressão: o autocomplete de expressões sugeria `data.alias` — o rótulo de
 * exibição — e inseria `{{$Caixa Delimitadora.bbox}}` no campo. O executor
 * registra o nó sob `_resolve_alias` (flow/executor/core.py), que exige
 * identificador válido e senão cai no `name` da classe, então a expressão
 * apontava para uma chave inexistente no contexto.
 *
 * Efeito colateral do espaço: o gatilho do autocomplete varre identificadores,
 * então depois de inserir o rótulo o próprio texto deixava de casar e o "."
 * nunca listava os campos de saída.
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
    // O executor escolhe por veracidade: com `alias` preenchido ele nem olha
    // properties.alias, e o rótulo com espaço o joga direto no `name`.
    expect(resolveNodeAlias({
      alias: "Caixa Delimitadora",
      properties: { alias: "Caixa" },
      name: "ComputeBoundingBox",
    })).toBe("ComputeBoundingBox")
  })

  it("acompanha a promoção do alias feita ao salvar o modal", () => {
    // saveNodeConfig copia o alias digitado para data.alias — é esse o estado
    // que chega ao banco e, portanto, ao executor.
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
    // Depois do ponto, ainda sem campo: é aqui que a lista de saídas aparece.
    expect("{{$ComputeBoundingBox.".match(trigger)?.[1]).toBe("ComputeBoundingBox.")
    expect("{{$Área.total".match(trigger)?.[1]).toBe("Área.total")
    // O espaço corta o gatilho — motivo pelo qual o rótulo nunca pode ir ao texto.
    expect("{{$Caixa Delimitadora".match(trigger)).toBeNull()
  })
})
