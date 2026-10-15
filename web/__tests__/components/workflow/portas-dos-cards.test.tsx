/**
 * Every card draws the handles the edge anchoring points at.
 *
 * The editor anchors an edge on a NAMED handle only when the node has 2+ ports
 * (`resolveSourceHandle`, `inputHandle`, `sourceHandleDaChave`), and on the
 * anonymous one otherwise. A card that draws anything else leaves edges pointing
 * at handles that do not exist: React Flow stops drawing them (error 008) while
 * they stay in the workflow and keep running. The HTTP Request card drew one
 * anonymous output for its three ports, so switching an edge's output on the
 * badge made the edge vanish — and so did every reload.
 *
 * The cards are rendered from what `buildNodes` produces, the same `data` the
 * editor gives them; only the handle and its frame are stubbed.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, cleanup } from "@testing-library/react"
import type { ReactNode } from "react"
import type { NodeProps } from "@xyflow/react"

const estado = vi.hoisted(() => ({
  edges: [] as { source: string; target: string; sourceHandle?: string | null; targetHandle?: string | null }[],
}))

vi.mock("@xyflow/react", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@xyflow/react")>()),
  Handle: ({ type, id }: { type: string; id?: string | null }) => (
    <div data-testid="handle" data-type={type} data-id={id ?? ""} />
  ),
  useEdges: () => estado.edges,
  useNodeConnections: ({ id, handleType }: { id: string; handleType: "source" | "target" }) =>
    estado.edges
      .filter(e => (handleType === "source" ? e.source : e.target) === id)
      .map(e => ({ ...e, sourceHandle: e.sourceHandle ?? null, targetHandle: e.targetHandle ?? null })),
}))
vi.mock("@/app/hooks/workflow/useTools", () => ({
  useTools: () => ({ toolState: "disable", handleToolState: () => {} }),
}))
// The frame, the toolbar and the "+" read the execution, catalog and URL state;
// what is under test is which handles the card draws.
vi.mock("@/app/components/workflow/custom-nodes/icon-root", () => ({
  default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))
vi.mock("@/app/components/workflow/custom-nodes/tools", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/custom-nodes/add-connection-handle", () => ({
  default: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

import { nodeTypesFlow } from "@/app/components/workflow/canvas-types"
import { buildEdges, buildNodes } from "@/app/components/workflow/utils/build-canvas"
import { getCandidateKeys, sourceHandleDaChave } from "@/app/components/workflow/utils/resolve-edge-keys"
import { INodeContext } from "@/context/useFlowContext"
import { CanvasDefinition, INodeOutputField, INodePortAPI, INodesAPI } from "@/service/types"

const def = (d: Partial<INodesAPI> & Pick<INodesAPI, "name" | "type">): INodesAPI => ({
  description: "",
  alias: String(d.name),
  properties: [],
  ...d,
})
const porta = (name: string): INodeOutputField => ({ name, port: true })

// Mirrors the catalog (`GET /nodes`) for one node of each shape the cards meet.
const CATALOGO: INodesAPI[] = [
  def({ name: "WebhookTrigger", type: "trigger", outputs: [{ name: "payload" }] }),
  def({ name: "FileTrigger", type: "trigger", outputs: [porta("file_a"), porta("file_b")] }),
  def({ name: "SubWorkflowInput", type: "trigger", outputs_from_ports: true, outputs: [] }),
  def({ name: "HttpRequest", type: "action", outputs: [porta("status_code"), porta("headers"), porta("body")] }),
  def({
    name: "Conditional", type: "control", branches: true,
    outputs: [{ name: "result" }, { name: "branch" }, { name: "value" }],
  }),
  def({ name: "RemoveDuplicates", type: "action", outputs: [porta("output"), porta("removed"), porta("removed_count")] }),
  def({ name: "DataInput", type: "datasource", outputs: [porta("output"), porta("metadata")] }),
  def({ name: "ReadGeoJSON", type: "datasource", outputs: [{ name: "output" }] }),
  def({ name: "PythonScript", type: "action", dynamic_inputs: true, dynamic_output: true, outputs: [{ name: "result" }] }),
  def({ name: "SpatialJoin", type: "spatial", inputs: [{ name: "left" }, { name: "right" }], outputs: [{ name: "output" }] }),
  def({ name: "SubWorkflowOutput", type: "output", dynamic_inputs: true }),
  def({ name: "SaveGeoJSON", type: "output", inputs: [{ name: "input" }] }),
]

const DEFINICAO: CanvasDefinition = {
  nodes: [
    { id: "webhook", name: "WebhookTrigger", type: "trigger", properties: {}, position: { x: 0, y: 0 } },
    { id: "arquivos", name: "FileTrigger", type: "trigger", properties: {}, position: { x: 0, y: 0 } },
    { id: "entrada", name: "SubWorkflowInput", type: "trigger", properties: { ports: '["lotes","zonas"]' }, position: { x: 0, y: 0 } },
    { id: "http", name: "HttpRequest", type: "action", properties: { method: "GET" }, position: { x: 0, y: 0 } },
    { id: "se", name: "Conditional", type: "control", properties: {}, position: { x: 0, y: 0 } },
    { id: "dedup", name: "RemoveDuplicates", type: "action", properties: {}, position: { x: 0, y: 0 } },
    { id: "dados", name: "DataInput", type: "datasource", properties: {}, position: { x: 0, y: 0 } },
    { id: "geojson", name: "ReadGeoJSON", type: "datasource", properties: {}, position: { x: 0, y: 0 } },
    { id: "script", name: "PythonScript", type: "action", properties: { ports: '["a","b"]' }, position: { x: 0, y: 0 } },
    { id: "juncao", name: "SpatialJoin", type: "spatial", properties: {}, position: { x: 0, y: 0 } },
    { id: "saida", name: "SubWorkflowOutput", type: "output", properties: { ports: '["resultado","total"]' }, position: { x: 0, y: 0 } },
    { id: "salvar", name: "SaveGeoJSON", type: "output", properties: {}, position: { x: 0, y: 0 } },
  ],
}

// `buildNodes` only copies the properties the catalog declares; `ports` and the
// HTTP method are fields of these nodes.
for (const d of CATALOGO) {
  d.properties = ["ports", "method"].map(name => ({ name, type: "string", default: "", description: null }))
}

const NOS = buildNodes(DEFINICAO, CATALOGO)
const no = (id: string) => NOS.find(n => n.id === id)!

type Desenhado = { source: string[]; target: string[] }

/** Handle ids the card draws, `""` standing for the anonymous one. */
function desenhar(n: INodeContext): Desenhado {
  cleanup()
  const Card = nodeTypesFlow[n.type as string] ?? nodeTypesFlow["DefaultIcon"]
  const props = { id: n.id, data: n.data, type: n.type, selected: false } as unknown as NodeProps<INodeContext>
  const { container } = render(<Card {...props} />)
  const handles = [...container.querySelectorAll<HTMLElement>('[data-testid="handle"]')]
  const ids = (tipo: string) => handles.filter(h => h.dataset.type === tipo).map(h => h.dataset.id ?? "")
  return { source: ids("source"), target: ids("target") }
}

/** One named handle per port with 2+ ports; a single anonymous one otherwise. */
const pelaRegra = (portas: INodePortAPI[] | undefined) =>
  (portas ?? []).length > 1 ? (portas ?? []).map(p => p.name) : [""]

/**
 * Whether React Flow can draw this end of an edge. A named handle must exist on
 * the card; with no name it takes the card's first handle of that type
 * (`getHandle` in @xyflow/system), so the card only needs to draw one.
 */
const ancora = (desenhadas: string[], handle: string | null | undefined) =>
  handle ? desenhadas.includes(handle) : desenhadas.length > 0

beforeEach(() => {
  estado.edges = []
})

describe("cada card desenha as portas que a ancoragem usa", () => {
  it.each(NOS.map(n => [n.data.name as string, n] as const))("%s", (_, n) => {
    const desenhado = desenhar(n)
    const saidas = n.data.outputs as INodePortAPI[] | undefined
    const entradas = n.data.inputs as INodePortAPI[] | undefined

    // Output-type nodes are terminal and triggers have no input — by design.
    expect(desenhado.source).toEqual(n.data.type === "output" ? [] : pelaRegra(saidas))
    expect(desenhado.target).toEqual(n.type === "DefaultTriggerIcon" ? [] : pelaRegra(entradas))
  })

  it("o HTTP Request desenha uma saída por porta declarada", () => {
    expect(no("http").type).toBe("HttpRequest")
    expect(desenhar(no("http")).source).toEqual(["status_code", "headers", "body"])
  })

  it("nó de saída com uma aresta já saindo dele desenha a saída", () => {
    // Written through the MCP or by hand, and the executor runs it: without a
    // handle the edge could be neither seen nor deleted.
    expect(desenhar(no("salvar")).source).toEqual([])
    estado.edges = [{ source: "salvar", target: "script" }]
    expect(desenhar(no("salvar")).source).toEqual([""])
  })

  it("gatilho com uma aresta chegando desenha uma entrada para ela", () => {
    expect(desenhar(no("webhook")).target).toEqual([])
    estado.edges = [{ source: "geojson", target: "webhook" }]
    expect(desenhar(no("webhook")).target).toEqual([""])
  })

  it("um card de nó desconhecido do catálogo desenha a porta anônima", () => {
    const desconhecido = { ...no("http"), type: "NotFound", data: { ...no("http").data, outputs: [], inputs: [] } }
    expect(desenhar(desconhecido)).toEqual({ source: [""], target: [""] })
  })
})

describe("uma aresta carregada sempre ancora numa porta desenhada", () => {
  // Every key an edge can carry out of each node (the badge's candidates) and
  // every declared input, persisted the way the editor saves them.
  const arestas: { rotulo: string; aresta: NonNullable<CanvasDefinition["edges"]>[number] }[] = []
  for (const n of NOS) {
    if (n.data.type !== "output") {
      for (const c of getCandidateKeys(n.data as Parameters<typeof getCandidateKeys>[0])) {
        const handle = sourceHandleDaChave(n.data.outputs as INodePortAPI[], c.name)
        arestas.push({
          rotulo: `${n.data.name}.${c.name} →`,
          aresta: { source: n.id, target: "geojson", from_key: c.name, ...(handle ? { source_handle: handle } : {}) },
        })
        // The same edge as saved before the handle was persisted.
        arestas.push({ rotulo: `${n.data.name}.${c.name} → (sem source_handle)`, aresta: { source: n.id, target: "geojson", from_key: c.name } })
      }
    }
    if (n.type !== "DefaultTriggerIcon") {
      for (const p of (n.data.inputs as INodePortAPI[] | undefined) ?? []) {
        arestas.push({ rotulo: `→ ${n.data.name}.${p.name}`, aresta: { source: "geojson", target: n.id, to_key: p.name } })
      }
    }
  }
  arestas.push(
    { rotulo: "Conditional true", aresta: { source: "se", target: "geojson", source_handle: "true", condition: true, from_key: "result" } },
    { rotulo: "Conditional false (legado, só condition)", aresta: { source: "se", target: "geojson", condition: false } },
  )

  it.each(arestas.map(a => [a.rotulo, a.aresta] as const))("%s", (_, aresta) => {
    const [rf] = buildEdges({ edges: [aresta] }, NOS)
    const origem = desenhar(no(aresta.source)).source
    const destino = desenhar(no(aresta.target)).target
    expect(ancora(origem, rf.sourceHandle), `saída "${rf.sourceHandle}" entre ${JSON.stringify(origem)}`).toBe(true)
    expect(ancora(destino, rf.targetHandle), `entrada "${rf.targetHandle}" entre ${JSON.stringify(destino)}`).toBe(true)
  })

  it("trocar a saída no rótulo da aresta do HTTP Request mantém a porta desenhada", () => {
    const portas = no("http").data.outputs as INodePortAPI[]
    const desenhadas = desenhar(no("http")).source
    for (const nome of ["status_code", "headers", "body"]) {
      expect(desenhadas).toContain(sourceHandleDaChave(portas, nome))
    }
  })
})
