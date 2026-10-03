import { describe, it, expect } from "vitest"
import {
  getCandidateKeys,
  portaDeEntradaPadrao,
  resolveFromKey,
  resolveToKey,
  sourceHandleDaChave,
} from "@/app/components/workflow/utils/resolve-edge-keys"

/**
 * Output fields come in a single shape (`saidas`, the catalog's typed
 * `outputs`) — and it's through them that the edge's key picker and the
 * autocomplete navigate.
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
 * Regression: the edge created by the handle's "+" button was born WITHOUT
 * `to_key`. On a multi-input target (Join layerA/layerB) this has two effects:
 * the executor falls back to `inputs[from_key]` and maps the wrong port, and the
 * PER-PORT column suggestion (colunas-conhecidas indexes by `to_key || from_key`)
 * stays empty forever — only the filter's "*" escaped, which looked like flakiness.
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
 * Regression: choosing the key on the edge badge made it DISAPPEAR. The picker
 * synced `sourceHandle` with ANY candidate (getCandidateKeys includes fields),
 * but the node only draws a named handle with 2+ real ports — a field without
 * `port` isn't a handle. Pointing the sourceHandle at one of them left the edge
 * without an anchor and React Flow stopped drawing it.
 */
describe("sourceHandleDaChave", () => {
  it("nó de saída única (0/1 porta) → null, nunca um campo sem porta", () => {
    // The bug case: the candidate is a field without a port, the handle is the anonymous one.
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
    // Avoids re-anchoring on a nonexistent port; the caller keeps the sourceHandle.
    expect(sourceHandleDaChave([{ name: "focos" }, { name: "bbox" }], "data")).toBeUndefined()
  })
})
