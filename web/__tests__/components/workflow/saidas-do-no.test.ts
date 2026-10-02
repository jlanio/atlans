/**
 * As caixas de auxílio precisam refletir o que foi CONFIGURADO, não o catálogo.
 *
 * O Script Python declara `dynamic_output`: as saídas de verdade estão em
 * `output_vars`. O painel da direita mostrava sempre "result" — o nome fixo do
 * catálogo — mesmo depois de a pessoa ter renomeado as variáveis do próprio
 * script. E o badge da aresta oferecia esse mesmo "result" como chave, que o
 * executor não encontra no resultado: ele loga um aviso e usa o primeiro valor,
 * então "funciona" por acidente e o painel segue mentindo.
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
    // ReadGeoJSON e companhia também declaram `dynamic_output` — no sentido de
    // que a FORMA do dado varia — mas não têm a propriedade. Derivar deles
    // apagaria as saídas que eles de fato declaram.
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
    // SubWorkflowInput — o catálogo declara [] de propósito. A revisão da F6
    // pegou o seletor de chave sem candidatos e a aresta nascendo sem from_key.
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
