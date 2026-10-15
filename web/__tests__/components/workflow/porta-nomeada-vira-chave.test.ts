/**
 * A named output port is a key an edge can carry.
 *
 * The SubWorkflow node draws one output handle per port of the CHILD's contract
 * (`data.outputs`, which arrives asynchronously from useSubWorkflowContractSync),
 * but its only catalog field is `subWorkflowResult`. The from_key candidates
 * knew only the catalog, so dragging from port `r2` recorded
 * `from_key: "subWorkflowResult"`. At run the node returns
 * `{subWorkflowResult, **child_ports}` (flow/nodes/control/sub_workflow.py), so
 * the edge delivered the WHOLE result instead of r2 — and after a reload the
 * line jumped to the first port, because `from_key` was not a port name for
 * `reancorarArestasDoNo` to put it back on.
 *
 * Every other shape must keep its list: catalog ports are already catalog
 * fields, SubWorkflowInput's ports are its outputs, the Python Script's outputs
 * are its `output_vars`, and a branch node's true/false handles route the
 * execution — they never become data keys.
 */
import { describe, it, expect } from "vitest"

import { buildEdges, buildNodes } from "@/app/components/workflow/utils/build-canvas"
import { serializeEdge } from "@/app/components/workflow/utils/edge-persistence"
import { reancorarArestasDoNo } from "@/app/components/workflow/utils/node-ports"
import { getCandidateKeys, resolveFromKey } from "@/app/components/workflow/utils/resolve-edge-keys"
import { INodeContext } from "@/context/useFlowContext"
import { CanvasDefinition, INodeOutputField, INodesAPI } from "@/service/types"

const def = (d: Partial<INodesAPI> & Pick<INodesAPI, "name" | "type">): INodesAPI => ({
  description: "",
  alias: String(d.name),
  // `buildNodes` only copies the properties the catalog declares.
  properties: ["ports", "output_vars", "workflowHash"].map(name => ({ name, type: "string", default: "", description: null })),
  ...d,
})
const porta = (name: string, type = "any"): INodeOutputField => ({ name, type, port: true })

// Mirrors the backend catalog (`GET /nodes`) of each shape the editor meets.
const CATALOGO: INodesAPI[] = [
  def({ name: "HttpRequest", type: "action", outputs: [porta("status_code", "number"), porta("headers", "object"), porta("body")] }),
  def({ name: "DataInput", type: "datasource", dynamic_output: true, outputs: [porta("output", "object"), porta("metadata", "object")] }),
  def({ name: "FileTrigger", type: "trigger", outputs: [porta("file_a", "geodataframe"), porta("file_b", "geodataframe")] }),
  def({
    name: "RemoveDuplicates", type: "action",
    outputs: [porta("output", "geodataframe"), porta("removed", "geodataframe"), porta("removed_count", "number")],
  }),
  def({
    name: "FilterByGeometryType", type: "spatial",
    outputs: [porta("points", "geodataframe"), porta("lines", "geodataframe"), porta("polygons", "geodataframe"), porta("other", "geodataframe")],
  }),
  def({ name: "SubWorkflowInput", type: "trigger", outputs_from_ports: true, outputs: [] }),
  def({ name: "PythonScript", type: "action", dynamic_inputs: true, dynamic_output: true, outputs: [{ name: "result", type: "any" }] }),
  def({
    name: "Conditional", type: "control", branches: true,
    outputs: [{ name: "result", type: "any" }, { name: "branch", type: "boolean" }, { name: "value", type: "number" }],
  }),
  def({ name: "SubWorkflow", type: "control", outputs: [{ name: "subWorkflowResult", type: "object" }] }),
  def({ name: "ReadGeoJSON", type: "datasource", dynamic_output: true, outputs: [{ name: "output", type: "geodataframe" }] }),
]

const no = (id: string, name: string, properties: Record<string, unknown> = {}) =>
  ({ id, name, type: "", properties, position: { x: 0, y: 0 } })

const DEFINICAO: CanvasDefinition = {
  nodes: [
    no("http", "HttpRequest"),
    no("dados", "DataInput"),
    no("arquivos", "FileTrigger"),
    no("dedup", "RemoveDuplicates"),
    no("filtro", "FilterByGeometryType"),
    no("entrada", "SubWorkflowInput", { ports: '["lotes","zonas"]' }),
    no("script", "PythonScript", { output_vars: "recorte, total" }),
    no("se", "Conditional"),
    no("sub", "SubWorkflow", { workflowHash: "filho" }),
    no("geojson", "ReadGeoJSON"),
  ],
} as CanvasDefinition

/** The canvas right after opening: the child's contract has not arrived yet. */
const AO_ABRIR = buildNodes(DEFINICAO, CATALOGO)

/**
 * The canvas once the contract arrives — what `applyPorts`
 * (useSubWorkflowContractSync) writes into the SubWorkflow's `data`.
 */
const CONTRATO = { inputs: [{ name: "geom" }, { name: "raio" }], outputs: [{ name: "r1" }, { name: "r2" }] }
const NOS: INodeContext[] = AO_ABRIR.map(n => (n.id === "sub" ? { ...n, data: { ...n.data, ...CONTRATO } } : n))

const dataDe = (id: string) => NOS.find(n => n.id === id)!.data as Parameters<typeof getCandidateKeys>[0]
const candidatas = (id: string) => getCandidateKeys(dataDe(id)).map(c => c.name)

/**
 * The key a drag records. Mirrors `handleConnectNodes` (workflow/index.tsx):
 * a source handle that is a candidate IS the key; any other handle (true/false)
 * or no handle at all falls to the first candidate.
 */
function chaveDoArraste(id: string, sourceHandle: string | null): string | undefined {
  const chaves = getCandidateKeys(dataDe(id))
  if (sourceHandle && chaves.some(c => c.name === sourceHandle)) return sourceHandle
  return chaves[0]?.name
}

/** The key the handle's "+" records — the same expression as `nodes-drawer`. */
function chaveDoMais(id: string, sourceHandle: string | null): string | undefined {
  const chaves = getCandidateKeys(dataDe(id))
  return resolveFromKey(sourceHandle, chaves) ?? chaves[0]?.name
}

describe("candidatas a from_key — cada forma de nó mantém a sua lista", () => {
  it.each([
    ["HttpRequest (portas = saídas do catálogo)", "http", ["status_code", "headers", "body"]],
    ["DataInput", "dados", ["output", "metadata"]],
    ["FileTrigger", "arquivos", ["file_a", "file_b"]],
    ["RemoveDuplicates", "dedup", ["output", "removed", "removed_count"]],
    ["FilterByGeometryType", "filtro", ["points", "lines", "polygons", "other"]],
    ["SubWorkflowInput (outputs_from_ports)", "entrada", ["lotes", "zonas"]],
    ["PythonScript (dynamic_output + output_vars)", "script", ["recorte", "total"]],
    ["ReadGeoJSON (saída anônima)", "geojson", ["output"]],
  ])("%s", (_, id, esperadas) => {
    expect(candidatas(id)).toEqual(esperadas)
  })

  it("Conditional: os handles true/false roteiam, não viram chave", () => {
    // `data.outputs` of a branch node is [true, false] — the 2+ handles that
    // must NOT be read as named data ports.
    expect(NOS.find(n => n.id === "se")!.data.outputs?.map(p => p.name)).toEqual(["true", "false"])
    expect(candidatas("se")).toEqual(["result", "branch", "value"])
  })

  it("SubWorkflow antes do contrato chegar: só o resultado inteiro", () => {
    expect(getCandidateKeys(AO_ABRIR.find(n => n.id === "sub")!.data as Parameters<typeof getCandidateKeys>[0]).map(c => c.name))
      .toEqual(["subWorkflowResult"])
  })

  it("SubWorkflow com o contrato do filho: as portas também são chaves (o badge da aresta as oferece)", () => {
    // The envelope stays: the node still returns it, and from the anonymous
    // handle it is what an edge carries.
    expect(candidatas("sub")).toEqual(["subWorkflowResult", "r1", "r2"])
  })
})

describe("SubWorkflow — a aresta puxada da porta r2 leva r2", () => {
  it("arrastar da porta r2 grava from_key r2", () => {
    expect(chaveDoArraste("sub", "r2")).toBe("r2")
  })

  it("o '+' ao lado da porta r2 (drawer) grava from_key r2", () => {
    expect(chaveDoMais("sub", "r2")).toBe("r2")
  })

  it("depois do F5 a aresta volta para a porta r2, e não para a primeira", () => {
    const arrastada = {
      id: "e1", source: "sub", sourceHandle: "r2", target: "geojson", targetHandle: null,
      type: "custom", data: { from_key: chaveDoArraste("sub", "r2") },
    }
    const salva = serializeEdge(arrastada)

    // On load the contract has not arrived: the handle is dropped (it is not a
    // port yet) and the edge waits on the anonymous point...
    const [carregada] = buildEdges({ edges: [salva] } as CanvasDefinition, AO_ABRIR)
    expect(carregada.sourceHandle).toBeUndefined()

    // ...until the ports arrive and `reancorarArestasDoNo` puts it back by `from_key`.
    const [reancorada] = reancorarArestasDoNo([carregada], "sub", ["geom", "raio"], ["r1", "r2"])
    expect(reancorada.sourceHandle).toBe("r2")
    expect(reancorada.data).toEqual({ from_key: "r2" })
  })

  it("o handle de ramo não vira chave: do true sai o primeiro campo, como antes", () => {
    expect(chaveDoArraste("se", "true")).toBe("result")
    expect(chaveDoMais("se", "false")).toBe("result")
  })

  it("as portas de catálogo seguem gravando a si mesmas", () => {
    expect(chaveDoArraste("http", "headers")).toBe("headers")
    expect(chaveDoArraste("filtro", "polygons")).toBe("polygons")
    expect(chaveDoMais("dedup", "removed")).toBe("removed")
    expect(chaveDoMais("entrada", "zonas")).toBe("zonas")
  })
})
