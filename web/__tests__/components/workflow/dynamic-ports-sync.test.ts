/**
 * `data.inputs` follows the `ports` property.
 *
 * What builds the connection points from `ports` is `loadNodes` (when opening
 * the workflow) and `addNode` (when creating the node). But the panel's
 * "Aplicar" (Apply) writes `data.properties` and does NOT recompute
 * `data.inputs` — without this sync the person would define the ports, apply,
 * and the node would keep a single anonymous connection point until the page
 * was reloaded.
 *
 * What's tested here is the reconciliation RULE, not the React hook: given the
 * state of the nodes, which ones need to change and which must stay untouched.
 * The second half is what keeps the effect from feeding itself on every render.
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
    // Referential identity: returning a new object would make ReactFlow
    // re-render the node on every pass of the effect, and the effect depends
    // on the nodes' state — it's the loop the comparison avoids.
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
