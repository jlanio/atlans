/**
 * Connection validation happens AT THE GESTURE (A16), derived from the catalog.
 *
 * Before, the canvas let you connect any port to any port and the error only
 * arrived at /workflows/validate. The gesture layer refuses only what would
 * CERTAINLY break — validate remains the final judge.
 */
import { describe, it, expect } from "vitest"

import {
  MENSAGEM_DE_RECUSA,
  tipoAceito,
  tipoEmitido,
  validarConexao,
} from "@/app/components/workflow/utils/valida-conexao"

const WFS = {
  id: "wfs",
  data: {
    name: "WFS",
    saidas: [
      { name: "output", type: "geodataframe" },
      { name: "feature_count", type: "number" },
      { name: "crs", type: "string" },
    ],
  },
}
const BUFFER = { id: "buf", data: { name: "Buffer", saidas: [{ name: "output", type: "geodataframe" }] } }
const CLIP = {
  id: "clip",
  data: {
    name: "Clip",
    inputs: [
      { name: "layerA", type: "geodataframe" },
      { name: "layerB", type: "geodataframe" },
    ],
  },
}
const DATA_INPUT = { id: "din", data: { name: "DataInput", saidas: [
  { name: "output", type: "object", port: true },
  { name: "metadata", type: "object", port: true },
] } }
const CONDICIONAL = { id: "cond", data: { name: "Conditional", branches: true, saidas: [
  { name: "result", type: "any" },
  { name: "branch", type: "boolean" },
] } }
const SAIDA_UNICA = { id: "sw-out", data: { name: "SubWorkflowOutput", inputs: [] } }

const NODES = [WFS, BUFFER, CLIP, DATA_INPUT, CONDICIONAL, SAIDA_UNICA]

const con = (source: string, target: string, sourceHandle?: string | null, targetHandle?: string | null) =>
  ({ source, target, sourceHandle: sourceHandle ?? null, targetHandle: targetHandle ?? null })

describe("validarConexao", () => {
  it("camada → camada passa", () => {
    expect(validarConexao(con("buf", "clip", null, "layerA"), NODES, [])).toBeNull()
  })

  it("nó não liga nele mesmo", () => {
    expect(validarConexao(con("buf", "buf"), NODES, [])).toBe("auto-conexao")
  })

  it("conexão repetida (mesmos handles) é recusada — null e undefined são o mesmo anônimo", () => {
    const existente = [{ source: "buf", target: "clip", sourceHandle: undefined, targetHandle: "layerA" }]
    expect(validarConexao(con("buf", "clip", null, "layerA"), NODES, existente)).toBe("duplicada")
  })

  it("mesmo par em handle DIFERENTE é permitido (nós binários)", () => {
    const existente = [{ source: "buf", target: "clip", sourceHandle: null, targetHandle: "layerA" }]
    expect(validarConexao(con("buf", "clip", null, "layerB"), NODES, existente)).toBeNull()
  })

  it("funil sem portas: segunda aresta é recusada", () => {
    const existente = [{ source: "buf", target: "sw-out", sourceHandle: null, targetHandle: null }]
    expect(validarConexao(con("wfs", "sw-out"), NODES, existente)).toBe("destino-de-uma-aresta")
  })

  it("escalar numa entrada de camada é recusado no gesto", () => {
    // feature_count (number) → Clip.layerA (geodataframe): the executor would
    // fail with a TypeError; now the line doesn't even stick.
    expect(validarConexao(con("wfs", "clip", "feature_count", "layerA"), NODES, []))
      .toBe("tipo-incompativel")
  })

  it("object passa onde se exige camada — DataInput PODE carregar uma", () => {
    expect(validarConexao(con("din", "clip", "output", "layerA"), NODES, [])).toBeNull()
  })

  it("handle anônimo de nó multi-campo emite any — não recusa", () => {
    // WFS through the anonymous handle spreads all fields; validate decides.
    expect(validarConexao(con("wfs", "clip", null, "layerA"), NODES, [])).toBeNull()
  })

  it("ramo de condicional repassa o primeiro campo (any) — não recusa", () => {
    expect(validarConexao(con("cond", "clip", "true", "layerA"), NODES, [])).toBeNull()
  })

  it("toda recusa tem mensagem para o toast", () => {
    for (const motivo of ["auto-conexao", "duplicada", "destino-de-uma-aresta", "tipo-incompativel"] as const) {
      expect(MENSAGEM_DE_RECUSA[motivo]).toBeTruthy()
    }
  })
})

describe("tipoEmitido / tipoAceito", () => {
  it("handle nomeado emite o tipo do campo", () => {
    expect(tipoEmitido(WFS.data, "crs")).toBe("string")
  })

  it("anônimo com um campo só emite o tipo dele", () => {
    expect(tipoEmitido(BUFFER.data, null)).toBe("geodataframe")
  })

  it("destino anônimo com entradas homogêneas herda o tipo delas", () => {
    expect(tipoAceito(CLIP.data, null)).toBe("geodataframe")
  })

  it("destino sem inputs declarados aceita qualquer coisa", () => {
    expect(tipoAceito(BUFFER.data, null)).toBe("any")
  })
})
