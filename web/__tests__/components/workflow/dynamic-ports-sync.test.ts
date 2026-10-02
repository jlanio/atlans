/**
 * `data.inputs` acompanha a propriedade `ports`.
 *
 * Quem monta os pontos de conexão a partir de `ports` é o `loadNodes` (ao abrir
 * o fluxo) e o `addNode` (ao criar o nó). Mas o "Aplicar" do painel grava
 * `data.properties` e NÃO recalcula `data.inputs` — sem este sincronismo a
 * pessoa definiria as portas, aplicaria, e o nó continuaria com um único ponto
 * de conexão anônimo até recarregar a página.
 *
 * O que se testa aqui é a REGRA de reconciliação, não o hook do React: dado o
 * estado dos nós, quais precisam mudar e quais precisam ficar intocados. A
 * segunda metade é o que impede o efeito de se realimentar a cada render.
 */
import { describe, it, expect } from "vitest"

import { reconciliarPortas } from "@/app/components/workflow/utils/node-ports"

type No = {
  id: string
  data: { dynamic_inputs?: boolean; properties?: Record<string, unknown>; inputs?: { name: string }[] }
}

const dinamico = (id: string, ports: unknown, inputs: { name: string }[] = []): No =>
  ({ id, data: { dynamic_inputs: true, properties: { ports }, inputs } })

describe("reconciliação das portas", () => {
  it("cria os pontos de conexão quando as portas são definidas", () => {
    const antes = [dinamico("n1", '["pontos","poligonos"]')]
    const nos = reconciliarPortas(antes)
    expect(nos).not.toBe(antes)
    expect(nos[0].data.inputs).toEqual([{ name: "pontos" }, { name: "poligonos" }])
  })

  it("remove os pontos quando as portas são apagadas", () => {
    const nos = reconciliarPortas([dinamico("n1", [], [{ name: "antiga" }])])
    expect(nos[0].data.inputs).toEqual([])
  })

  it("acompanha a renomeação", () => {
    const nos = reconciliarPortas([dinamico("n1", ["novo"], [{ name: "velho" }])])
    expect(nos[0].data.inputs).toEqual([{ name: "novo" }])
  })

  it("deduplica", () => {
    const nos = reconciliarPortas([dinamico("n1", ["a", "a", "b"])])
    expect(nos[0].data.inputs).toEqual([{ name: "a" }, { name: "b" }])
  })
})

describe("não mexe no que já está certo", () => {
  it("nó já sincronizado não é recriado", () => {
    // Identidade referencial: devolver um objeto novo faria o ReactFlow
    // re-renderizar o nó a cada passagem do efeito, e o efeito depende do
    // estado dos nós — é o laço que a comparação evita.
    const antes = [dinamico("n1", ["a"], [{ name: "a" }])]
    const nos = reconciliarPortas(antes)
    expect(nos).toBe(antes)
    expect(nos[0]).toBe(antes[0])
  })

  it("nó comum não é tocado", () => {
    const comum: No = { id: "n2", data: { properties: { ports: ["x"] }, inputs: [{ name: "layerA" }] } }
    const antes = [comum]
    const nos = reconciliarPortas(antes)
    expect(nos).toBe(antes)
    expect(nos[0].data.inputs).toEqual([{ name: "layerA" }])
  })

  it("ordem diferente conta como mudança", () => {
    const antes = [dinamico("n1", ["b", "a"], [{ name: "a" }, { name: "b" }])]
    const nos = reconciliarPortas(antes)
    expect(nos).not.toBe(antes)
    expect(nos[0].data.inputs).toEqual([{ name: "b" }, { name: "a" }])
  })
})
