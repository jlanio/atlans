/**
 * Building a canvas from the persisted definition + catalog.
 *
 * This used to live inside the editor, reading the closure and calling
 * `setNodes`/`setEdges`. It moved out so the sub-workflow viewer can draw the
 * graph of ANOTHER workflow with the same rules — and it's the extraction these
 * tests protect: a `data` built in two places diverges, which is the defect with
 * the bizarre symptom (works on the new node, disappears on reload) that
 * `contratoDoNo` exists to prevent.
 */
import { describe, it, expect } from "vitest"

import { buildEdges, buildNodes } from "@/app/components/workflow/utils/build-canvas"
import { INodesAPI } from "@/service/types"

const catalogo = [
  {
    name: "PythonScript",
    alias: "Script Python",
    description: "Roda um script",
    type: "action",
    properties: [
      { name: "code", label: "Código", type: "string", default: "" },
      { name: "ports", label: "Portas", type: "object", default: [] },
      // A field that asks for a COLUMN NAME — carries the suggestion marker.
      { name: "coluna", label: "Coluna", type: "string", default: "", suggest_columns: "*" },
    ],
    dynamic_inputs: true,
    outputs: [{ name: "output" }],
  },
  {
    name: "Conditional",
    alias: "Condicional",
    description: "Ramifica",
    type: "control",
    properties: [],
    outputs: [{ name: "result", type: "any" }],
    branches: true,
  },
  {
    // Two REAL outputs → named handles (default-type draws one per port).
    // It's the case in which restoring `source_handle` by name makes sense.
    name: "DataInput",
    alias: "Entrada de Dados",
    description: "Duas saídas nomeadas",
    type: "trigger",
    properties: [],
    outputs: [{ name: "output", port: true }, { name: "metadata", port: true }],
  },
] as unknown as INodesAPI[]

describe("buildNodes", () => {
  it("resolve o schema do catálogo e preserva os valores salvos", () => {
    const [no] = buildNodes(
      { nodes: [{ id: "a", name: "PythonScript", properties: { code: "print(1)" }, position: { x: 10, y: 20 }, type: "action" }] },
      catalogo,
    )

    expect(no.id).toBe("a")
    expect(no.data.properties.code).toBe("print(1)")
    expect(no.data.description).toBe("Roda um script")
    expect(no.position).toEqual({ x: 10, y: 20 })
  })

  it("campo ausente na definition nasce com o default do catálogo", () => {
    // It's what allows adding a property to the schema without migrating
    // already-saved workflows.
    const [no] = buildNodes(
      { nodes: [{ id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" }] },
      catalogo,
    )
    expect(no.data.properties.code).toBe("")
  })

  it("preserva `suggest_columns` na projeção dos campos", () => {
    // The classic regression of this projection: the freshly dragged node
    // suggested columns (the drawer copies the whole catalog object) and the
    // SAME node, saved and reloaded, never again — the whitelist dropped the
    // marker and `sugerirColunas()` returned [] forever.
    const [no] = buildNodes(
      { nodes: [{ id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" }] },
      catalogo,
    )
    const campo = no.data.fields.find(f => f.name === "coluna")
    expect(campo?.suggest_columns).toBe("*")
  })

  it("entradas dinâmicas viram pontos de conexão a partir de `ports`", () => {
    const [no] = buildNodes(
      {
        nodes: [{
          id: "a",
          name: "PythonScript",
          properties: { ports: JSON.stringify(["focos", "bbox"]) },
          position: { x: 0, y: 0 },
          type: "action",
        }],
      },
      catalogo,
    )
    expect(no.data.inputs).toEqual([{ name: "focos" }, { name: "bbox" }])
  })

  it("sem catálogo não monta nada — o schema não teria de onde vir", () => {
    const definition = { nodes: [{ id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" }] }
    expect(buildNodes(definition, [])).toEqual([])
    expect(buildNodes(definition, undefined)).toEqual([])
  })

  it("definition sem nós devolve lista vazia, e não undefined", () => {
    // The editor passes the return value straight to `setNodes`; an undefined
    // here would become a broken canvas instead of an empty one.
    expect(buildNodes(undefined, catalogo)).toEqual([])
    expect(buildNodes({}, catalogo)).toEqual([])
  })
})

describe("buildEdges", () => {
  it("restaura o handle de origem persistido (porta nomeada de nó multi-saída)", () => {
    const nodes = buildNodes(
      { nodes: [
        { id: "a", name: "DataInput", properties: {}, position: { x: 0, y: 0 }, type: "trigger" },
        { id: "b", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
      ] },
      catalogo,
    )
    const [aresta] = buildEdges(
      { edges: [{ source: "a", target: "b", source_handle: "output", from_key: "output" }] },
      nodes,
    )
    expect(aresta.sourceHandle).toBe("output")
    expect(aresta.data).toEqual({ from_key: "output" })
    expect(aresta.type).toBe("custom")
  })

  it("saída anônima: source_handle fantasma (bug do picker) volta a anônimo", () => {
    // PythonScript (action) draws an ANONYMOUS handle — "output" is not a named
    // handle. The old picker saved that name anyway and the edge disappeared;
    // now it comes back to the canvas anchored on the anonymous handle (null sourceHandle).
    const nodes = buildNodes(
      { nodes: [
        { id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
        { id: "b", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
      ] },
      catalogo,
    )
    const [aresta] = buildEdges(
      { edges: [{ source: "a", target: "b", source_handle: "output", from_key: "output" }] },
      nodes,
    )
    expect(aresta.sourceHandle).toBeUndefined()
    expect(aresta.data).toEqual({ from_key: "output" })
  })

  it("ramo de condicional só vira handle quando o nó tem as portas true/false", () => {
    const nodes = buildNodes(
      { nodes: [
        { id: "c", name: "Conditional", properties: {}, position: { x: 0, y: 0 }, type: "control" },
        { id: "b", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
      ] },
      catalogo,
    )
    const [aresta] = buildEdges({ edges: [{ source: "c", target: "b", condition: true }] }, nodes)
    expect(aresta.sourceHandle).toBe("true")
  })

  it("porta ÚNICA: a aresta ancora no handle anônimo, não no nome da porta", () => {
    // With ONE port, `default-type` draws an ANONYMOUS HandleTarget (no id) — the
    // named handle only exists with 2+ ports. Returning "focos" would point the
    // edge at a nonexistent id: React Flow doesn't draw it, it disappears from the
    // canvas while still executing, and with no line there's no way to delete it.
    // `targetHandle` stays undefined (anchors on the anonymous one) and `to_key`
    // survives in `data`, so the executor still routes by the key.
    //
    // REGRESSION of this fix: removing the `> 1` from `handleDeEntrada` makes
    // `targetHandle` go back to "focos" and breaks ONLY this test.
    const nodes = buildNodes(
      { nodes: [
        { id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
        {
          id: "b",
          name: "PythonScript",
          properties: { ports: JSON.stringify(["focos"]) },
          position: { x: 0, y: 0 },
          type: "action",
        },
      ] },
      catalogo,
    )

    const [aresta] = buildEdges({ edges: [{ source: "a", target: "b", to_key: "focos" }] }, nodes)
    expect(aresta.targetHandle).toBeUndefined()
    // The data key remains: the executor still routes; only the visual anchor goes away.
    expect(aresta.data).toEqual({ to_key: "focos" })
  })

  it("2+ portas: `to_key` vira o handle nomeado que existe; fora da lista fica órfã", () => {
    // With 2+ ports, `default-type` draws one HandleTarget per port (id = name),
    // so anchoring by name is legitimate — the connection point exists.
    const nodes = buildNodes(
      { nodes: [
        { id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
        {
          id: "b",
          name: "PythonScript",
          properties: { ports: JSON.stringify(["focos", "alertas"]) },
          position: { x: 0, y: 0 },
          type: "action",
        },
      ] },
      catalogo,
    )

    const [declarada] = buildEdges({ edges: [{ source: "a", target: "b", to_key: "focos" }] }, nodes)
    expect(declarada.targetHandle).toBe("focos")

    const [orfa] = buildEdges({ edges: [{ source: "a", target: "b", to_key: "inexistente" }] }, nodes)
    expect(orfa.targetHandle).toBeUndefined()
    // The data key remains: the only thing that would be lost is the visual anchor.
    expect(orfa.data).toEqual({ to_key: "inexistente" })
  })

  it("definition sem arestas devolve lista vazia", () => {
    expect(buildEdges(undefined, [])).toEqual([])
    expect(buildEdges({}, [])).toEqual([])
  })
})
