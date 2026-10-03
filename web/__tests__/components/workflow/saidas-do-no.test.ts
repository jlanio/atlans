/**
 * The helper boxes need to reflect what was CONFIGURED, not the catalog.
 *
 * The Python Script declares `dynamic_output`: the real outputs are in
 * `output_vars`. The right-hand panel always showed "result" — the catalog's
 * fixed name — even after the person had renamed the script's own variables.
 * And the edge badge offered that same "result" as a key, which the executor
 * doesn't find in the result: it logs a warning and uses the first value, so it
 * "works" by accident and the panel keeps lying.
 */
import { describe, it, expect } from "vitest"

import { saidasDoNo } from "@/app/components/workflow/utils/node-ports"
import { getCandidateKeys } from "@/app/components/workflow/utils/resolve-edge-keys"

const CATALOGO = [{ name: "result", type: "any" }]

describe("saidasDoNo", () => {
  it("usa output_vars quando o nó é de saída dinâmica", () => {
    const r = saidasDoNo(
      { dynamic_output: true, saidas: CATALOGO, properties: { output_vars: "pontos, poligonos" } },
    )
    expect(r.map(f => f.name)).toEqual(["pontos", "poligonos"])
  })

  it("nó comum continua vindo do catálogo", () => {
    const r = saidasDoNo(
      { saidas: CATALOGO, properties: { output_vars: "ignorado" } },
    )
    expect(r.map(f => f.name)).toEqual(["result"])
  })

  it("saída dinâmica SEM output_vars cai no catálogo", () => {
    // ReadGeoJSON and friends also declare `dynamic_output` — in the sense that
    // the data's SHAPE varies — but don't have the property. Deriving from them
    // would erase the outputs they actually declare.
    const r = saidasDoNo({ dynamic_output: true, saidas: CATALOGO })
    expect(r.map(f => f.name)).toEqual(["result"])
  })

  it("output_vars vazio cai no catálogo", () => {
    const r = saidasDoNo(
      { dynamic_output: true, saidas: CATALOGO, properties: { output_vars: "  ,  " } },
    )
    expect(r.map(f => f.name)).toEqual(["result"])
  })

  it("outputs_from_ports: as saídas são as portas declaradas pelo usuário", () => {
    // SubWorkflowInput — the catalog declares [] on purpose. The F6 review
    // caught the key picker with no candidates and the edge born without from_key.
    const r = saidasDoNo({
      outputs_from_ports: true,
      saidas: [],
      properties: { ports: ["geometry", "raio"] },
    })
    expect(r.map(f => f.name)).toEqual(["geometry", "raio"])
  })

  it("deduplica e tolera espaços", () => {
    const r = saidasDoNo(
      { dynamic_output: true, properties: { output_vars: " a , b ,a " } },
    )
    expect(r.map(f => f.name)).toEqual(["a", "b"])
  })
})

describe("badge da aresta oferece as saídas reais", () => {
  it("Script Python com output_vars renomeado", () => {
    const chaves = getCandidateKeys({
      dynamic_output: true,
      saidas: CATALOGO,
      properties: { output_vars: "recorte" },
    })
    expect(chaves.map(c => c.name)).toEqual(["recorte"])
    expect(chaves.map(c => c.name)).not.toContain("result")
  })

  it("nó comum não muda", () => {
    const chaves = getCandidateKeys({
      saidas: [{ name: "output", port: true }],
    })
    expect(chaves.map(c => c.name)).toEqual(["output"])
  })
})
