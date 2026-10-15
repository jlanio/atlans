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
import { serializeEdge } from "@/app/components/workflow/utils/edge-persistence"
import { CanvasDefinition, INodesAPI } from "@/service/types"

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

/**
 * A node the catalog does not list — disabled by an admin in /admin/nodes,
 * renamed or removed. Rebuilt from a schema that is not there, it lost its
 * properties and became a "trigger", and the next save of anything else in the
 * workflow persisted both: the configuration was gone for good, the executor
 * ignored its incoming edges and the trigger card drew no input for them.
 */
describe("buildNodes — nó fora do catálogo", () => {
  const salvo = {
    id: "buf", name: "Buffer", type: "spatial", alias: "Faixa de 30 m",
    properties: { distance: "30", unit: "m" }, position: { x: 5, y: 6 },
  }

  it("mantém propriedades, tipo e apelido como foram salvos", () => {
    const [no] = buildNodes({ nodes: [salvo] }, catalogo)
    expect(no.data.properties).toEqual({ distance: "30", unit: "m" })
    expect(no.data.type).toBe("spatial")
    expect(no.data.alias).toBe("Faixa de 30 m")
    // The card with both handles, not the trigger one (no input handle).
    expect(no.type).toBe("DefaultIcon")
  })

  it("sem tipo salvo, não vira gatilho", () => {
    const [no] = buildNodes({ nodes: [{ ...salvo, type: undefined as unknown as string }] }, catalogo)
    expect(no.data.type).toBe("action")
    expect(no.type).toBe("DefaultIcon")
  })

  it("não divide o objeto de propriedades com a definition", () => {
    const definition = { nodes: [salvo] }
    const [no] = buildNodes(definition, catalogo)
    no.data.properties.distance = "50"
    expect(salvo.properties.distance).toBe("30")
  })

  it("as arestas de ramo continuam ramo depois de salvar", () => {
    // A Conditional that left the catalog: its branch edges kept their anchor
    // only by luck of the true handle, and the save dropped `condition`.
    const definition = {
      nodes: [
        { id: "se", name: "CondicionalAntigo", type: "control", properties: {}, position: { x: 0, y: 0 } },
        { id: "b", name: "PythonScript", type: "action", properties: {}, position: { x: 0, y: 0 } },
        { id: "c", name: "PythonScript", type: "action", properties: {}, position: { x: 0, y: 0 } },
      ],
      edges: [
        { source: "se", target: "b", source_handle: "true", condition: true, from_key: "result" },
        { source: "se", target: "c", condition: false, from_key: "result" },
      ],
    }
    const nodes = buildNodes(definition, catalogo)
    expect(nodes[0].data.outputs).toEqual([{ name: "true" }, { name: "false" }])
    // Still a branch node: true/false route, they are not data keys.
    expect(nodes[0].data.branches).toBe(true)
    const salvas = buildEdges(definition, nodes).map(e => serializeEdge(e))
    expect(salvas).toEqual([
      { source: "se", target: "b", source_handle: "true", condition: true, from_key: "result" },
      { source: "se", target: "c", source_handle: "false", condition: false, from_key: "result" },
    ])
  })

  it("as portas nomeadas em uso continuam ancoradas depois de salvar", () => {
    const definition = {
      nodes: [
        { id: "d", name: "EntradaDesativada", type: "datasource", properties: {}, position: { x: 0, y: 0 } },
        { id: "b", name: "PythonScript", type: "action", properties: {}, position: { x: 0, y: 0 } },
      ],
      edges: [
        { source: "d", target: "b", source_handle: "output", from_key: "output", to_key: "a" },
        { source: "d", target: "b", source_handle: "metadata", from_key: "metadata", to_key: "b" },
      ],
    }
    const nodes = buildNodes(definition, catalogo)
    const salvas = buildEdges(definition, nodes).map(e => serializeEdge(e))
    expect(salvas.map(e => e.source_handle)).toEqual(["output", "metadata"])
    expect(salvas.map(e => e.to_key)).toEqual(["a", "b"])
  })

  it("nó do catálogo salvo com o tipo errado volta ao tipo do catálogo", () => {
    // What the fallback above wrote: a PythonScript persisted as "trigger".
    const [no] = buildNodes(
      { nodes: [{ id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "trigger" }] },
      catalogo,
    )
    expect(no.data.type).toBe("action")
    expect(no.type).toBe("DefaultIcon")
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

  it("aresta sem as duas pontas fica de fora, para não voltar no próximo salvar", () => {
    // Saved by hand or by another client. It cannot be drawn and the executor
    // skips it; kept, it went back in every save, which the server refuses (422).
    const salvas = [
      { source: "a", target: "b" }, { source: "a" }, { target: "b" }, { source: "", target: "b" }, null,
    ] as unknown as CanvasDefinition["edges"]
    const arestas = buildEdges({ edges: salvas }, [])
    expect(arestas.map(e => [e.source, e.target])).toEqual([["a", "b"]])
    expect(buildNodes({ nodes: [{ id: "x", name: "Sumiu", type: "action", properties: {}, position: { x: 0, y: 0 } }], edges: salvas }, [{ name: "Outro" } as INodesAPI]))
      .toHaveLength(1)
  })
})
