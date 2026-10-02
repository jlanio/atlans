import { describe, it, expect } from "vitest"
import {
  getCandidateKeys,
  portaDeEntradaPadrao,
  resolveFromKey,
  resolveToKey,
  sourceHandleDaChave,
} from "@/app/components/workflow/utils/resolve-edge-keys"

/**
 * Os campos de saída vêm numa forma só (`saidas`, os `outputs` tipados do
 * catálogo) — e é por eles que o seletor de chave da aresta e o autocomplete
 * navegam.
 */

const CAMPOS = [
  { name: "output", type: "geodataframe", description: "Polígonos de bbox" },
  { name: "bbox_string", type: "string" },
]

describe("getCandidateKeys", () => {
  it("oferece os campos declarados, na ordem", () => {
    const nomes = getCandidateKeys({ saidas: CAMPOS }).map(f => f.name)

    expect(nomes).toEqual(["output", "bbox_string"])
  })

  it("deduplica por nome e descarta entrada sem nome", () => {
    const nomes = getCandidateKeys({
      saidas: [{ name: "output" }, { name: "output" }, { name: "" }],
    }).map(f => f.name)

    expect(nomes).toEqual(["output"])
  })

  it("nó de ramo não oferece true/false: os campos são o dado", () => {
    // Conditional: handles true/false roteiam; a aresta carrega os CAMPOS.
    const nomes = getCandidateKeys({
      saidas: [{ name: "result", type: "any" }, { name: "branch", type: "boolean" }],
    }).map(f => f.name)

    expect(nomes).toEqual(["result", "branch"])
  })
})

describe("resolveFromKey", () => {
  it("usa o próprio handle quando ele é porta de dado", () => {
    expect(resolveFromKey("bbox_string", getCandidateKeys({ saidas: CAMPOS })))
      .toBe("bbox_string")
  })

  it("resolve sozinho quando há um candidato só", () => {
    expect(resolveFromKey(null, [{ name: "output" }])).toBe("output")
  })

  it("devolve undefined na ambiguidade — o chamador abre o seletor", () => {
    expect(resolveFromKey(null, getCandidateKeys({ saidas: CAMPOS })))
      .toBeUndefined()
  })
})

/**
 * Regressão: a aresta criada pelo botão "+" do handle nascia SEM `to_key`.
 * Num destino multi-input (Join layerA/layerB) isso tem dois efeitos: o
 * executor cai em `inputs[from_key]` e mapeia a porta errada, e a sugestão de
 * colunas POR PORTA (colunas-conhecidas indexa por `to_key || from_key`) fica
 * vazia para sempre — só o "*" do filtro escapava, o que parecia instabilidade.
 */
describe("resolveToKey", () => {
  const doisInputs = [{ name: "layerA" }, { name: "layerB" }]

  it("usa o handle quando o destino declara múltiplos inputs nomeados", () => {
    expect(resolveToKey("layerB", doisInputs)).toBe("layerB")
  })

  it("input único → undefined (o executor resolve sozinho; to_key seria ruído)", () => {
    expect(resolveToKey("input", [{ name: "input" }])).toBeUndefined()
    expect(resolveToKey("input", [])).toBeUndefined()
    expect(resolveToKey("input", undefined)).toBeUndefined()
  })

  it("handle que não é porta declarada → undefined", () => {
    expect(resolveToKey("outra", doisInputs)).toBeUndefined()
  })

  it("sem handle → undefined", () => {
    expect(resolveToKey(null, doisInputs)).toBeUndefined()
    expect(resolveToKey(undefined, doisInputs)).toBeUndefined()
  })
})

describe("portaDeEntradaPadrao", () => {
  it("destino multi-input: a primeira porta declarada — o badge permite trocar", () => {
    expect(portaDeEntradaPadrao([{ name: "layerA" }, { name: "layerB" }])).toBe("layerA")
  })

  it("um input só (ou nenhum): undefined, mesma regra do resolveToKey", () => {
    expect(portaDeEntradaPadrao([{ name: "input" }])).toBeUndefined()
    expect(portaDeEntradaPadrao([])).toBeUndefined()
    expect(portaDeEntradaPadrao(undefined)).toBeUndefined()
  })
})

/**
 * Regressão: escolher a chave no badge da aresta a fazia SUMIR. O seletor
 * sincronizava o `sourceHandle` com QUALQUER candidato (getCandidateKeys inclui
 * campos), mas o nó só desenha handle nomeado com 2+ portas reais — campo
 * sem `port` não é handle. Apontar o sourceHandle para um deles
 * deixava a aresta sem âncora e o React Flow parava de desenhá-la.
 */
describe("sourceHandleDaChave", () => {
  it("nó de saída única (0/1 porta) → null, nunca um campo sem porta", () => {
    // O caso do bug: candidato é um campo sem porta, o handle é o anônimo.
    expect(sourceHandleDaChave([], "previous_hash")).toBeNull()
    expect(sourceHandleDaChave([{ name: "output" }], "previous_hash")).toBeNull()
    expect(sourceHandleDaChave(undefined, "output")).toBeNull()
  })

  it("nó multi-saída: o handle nomeado quando `nome` é uma porta real", () => {
    const outs = [{ name: "focos" }, { name: "bbox" }]
    expect(sourceHandleDaChave(outs, "bbox")).toBe("bbox")
    expect(sourceHandleDaChave(outs, "focos")).toBe("focos")
  })

  it("nó multi-saída, `nome` não é porta → undefined (não mexe no handle atual)", () => {
    // Evita reancorar numa porta inexistente; o chamador mantém o sourceHandle.
    expect(sourceHandleDaChave([{ name: "focos" }, { name: "bbox" }], "data")).toBeUndefined()
  })
})
