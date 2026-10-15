/**
 * Renaming a Python Script output variable takes the edges that read it along.
 *
 * The outputs of a node with `dynamic_output` are the variables typed in its
 * `output_vars`, and an edge leaving it carries the variable's NAME in
 * `from_key` — at run, the executor picks that key from the node's result.
 * Applying a new name in the configuration kept the edges on the old one: they
 * stayed on the canvas, were saved and ran, and delivered nothing (the run
 * panel's "entrada vazia"), with nothing in the editor pointing at the cause.
 *
 * A one-to-one rename now moves those edges to the new name, in the same undo
 * step as the configuration. A change that drops a name some edge reads with no
 * one-to-one counterpart is announced in the form before applying, naming the
 * connections that would come out empty — and applying stays possible.
 *
 * The real editor over a real React Flow, with the real configuration modal
 * mounted next to it (the editor loads it through `next/dynamic`) — the same
 * setup as the undo/redo tests.
 */
import React, { useEffect } from "react"
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { render, act, cleanup, fireEvent, screen } from "@testing-library/react"
import { ReactFlowProvider, useReactFlow } from "@xyflow/react"

// The modal opens from the URL (`?cn=<node id>`) and closes by rewriting it.
const url = vi.hoisted(() => ({ sp: new URLSearchParams("") }))
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "wf-1" }),
  useRouter: () => ({
    replace: (destino: string) => { url.sp = new URLSearchParams(destino.split("?")[1] ?? "") },
    push: vi.fn(),
  }),
  useSearchParams: () => url.sp,
  usePathname: () => "/workflow/wf-1",
}))
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: "authenticated", data: null }) }))
// The editor's own modal (mounted by hand below) and Monaco, in the code field.
vi.mock("next/dynamic", () => ({ default: () => () => null }))
vi.mock("@/context/ThemeContext", () => ({ useTheme: () => ({ theme: "light" }) }))
vi.mock("@/app/components/ui/sidebar", () => ({ useSidebar: () => ({ setOpen: () => {} }) }))
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: { id_hash: "ws-1", name: "Equipe" }, workspaces: [] }),
}))

const servico = vi.hoisted(() => ({
  getNodes: vi.fn(),
  getCredentials: vi.fn(),
  listPinnedNodes: vi.fn(),
  updateWorkflowById: vi.fn(),
  createWorkflow: vi.fn(),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

vi.mock("@/app/components/workflow/buttons", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/run-panel", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/drawer", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/subflow-viewer", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/assistente", () => ({ default: () => null }))

import ReactFlowComponent from "@/app/components/workflow"
import NodeConfigModal from "@/app/components/workflow/node-config-modal"
import { FlowContextProvider, INodeContext } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { buildGraphPayload } from "@/app/hooks/workflow/useSaveWorkflow"
import type { IEdgeDefinition, INodesAPI, INodesDefinition, IWorkflow } from "@/service/types"

const campo = (name: string, label: string, type: string, padrao: unknown) =>
  ({ name, label, type, default: padrao, description: null })

const CATALOGO = [
  {
    name: "PythonScript", alias: "Script Python", description: "", type: "action",
    properties: [
      campo("code", "Código Python", "code", "result = None\n"),
      campo("output_vars", "Variável de saída", "string", "result"),
      campo("ports", "Portas de entrada", "ports", []),
    ],
    dynamic_inputs: true,
    dynamic_output: true,
    outputs: [{ name: "result", type: "any" }],
  },
  // `dynamic_output` WITHOUT `output_vars`: the shape of its data varies, its
  // output is still the catalog's.
  {
    name: "ReadGeoJSON", alias: "Ler GeoJSON", description: "", type: "action",
    properties: [campo("path", "Arquivo", "string", "")],
    dynamic_output: true,
    outputs: [{ name: "output" }],
  },
  { name: "Buffer", alias: "Buffer", description: "", type: "spatial", properties: [], outputs: [{ name: "output" }] },
] as unknown as INodesAPI[]

const no = (id: string, name: string, properties: Record<string, string>, x: number): INodesDefinition =>
  ({ id, name, alias: id[0].toUpperCase() + id.slice(1), type: "action", properties, position: { x, y: 0 } }) as INodesDefinition

/** The script delivers `a` and `b`. */
function workflow(edges: IEdgeDefinition[]): IWorkflow {
  return {
    id_hash: "wf-1",
    name: "Fluxo",
    flag_ative: true,
    description: "",
    version: "v1",
    priority: 0,
    created_by_id: "u",
    updated_by_id: "u",
    definition: {
      nodes: [
        no("script", "PythonScript", { code: "a = 1\nb = 2", output_vars: "a, b" }, 0),
        no("leitor", "ReadGeoJSON", { path: "x.geojson" }, 0),
        no("recorte", "Buffer", {}, 300),
        no("total", "Buffer", {}, 300),
        no("espalha", "Buffer", {}, 300),
      ],
      edges,
    },
  }
}

const LIGACOES: IEdgeDefinition[] = [
  { source: "script", target: "recorte", from_key: "a" },
  // As the MCP may write it: a `source_handle` the script does not draw.
  { source: "script", target: "total", source_handle: "b", from_key: "b" },
  // No key: "espalha" receives every output, whatever their names.
  { source: "script", target: "espalha" },
]

let canvas: ReturnType<typeof useReactFlow>
function Sonda() {
  const instancia = useReactFlow()
  useEffect(() => { canvas = instancia }, [instancia])
  return null
}

/** Mounts the editor with the configuration of `noAberto` open. */
function montar(w: IWorkflow, noAberto: string) {
  url.sp = new URLSearchParams(`cn=${noAberto}`)
  return render(
    <ReactFlowProvider>
      <FlowContextProvider>
        <Sonda />
        <ReactFlowComponent workflow={w} />
        <NodeConfigModal />
      </FlowContextProvider>
    </ReactFlowProvider>,
  )
}

/** What each edge reads from its source, by target. */
const chaves = () => canvas.getEdges().map(e => `${e.target}:${e.data?.from_key ?? "-"}`).sort()
const propriedade = (id: string, nome: string) =>
  (canvas.getNode(id)?.data as { properties: Record<string, string> }).properties[nome]

async function preencher(rotulo: string, valor: string) {
  const entrada = await screen.findByRole("textbox", { name: rotulo })
  fireEvent.change(entrada, { target: { value: valor } })
}
const clicarAplicar = () => fireEvent.click(screen.getByRole("button", { name: "Aplicar" }))
/** The form's warning about connections that would come out empty; "" when there is none. */
const aviso = () => screen.queryByText(/de existir/)?.textContent ?? ""

const teclar = (tecla: string) => fireEvent.keyDown(document.body, { key: tecla, ctrlKey: true })
const esperar = (ms: number) => act(async () => { await new Promise(r => setTimeout(r, ms)) })

/** Long enough for the snapshot the editor schedules 300 ms after an edit. */
const PASSO = 400

beforeAll(() => {
  // useIsMobile (the canvas becomes a viewer on a phone).
  window.matchMedia = vi.fn(() => ({ matches: false, addEventListener() {}, removeEventListener() {} })) as never
  // updateNodeInternals reads the zoom from the viewport's CSS transform.
  // @ts-expect-error jsdom has no DOMMatrix
  globalThis.DOMMatrixReadOnly = class { m22 = 1 }
})

beforeEach(() => {
  cleanup()
  vi.clearAllMocks()
  servico.getNodes.mockResolvedValue({ data: CATALOGO, error: null })
  servico.getCredentials.mockResolvedValue({ data: [], error: null })
  servico.listPinnedNodes.mockResolvedValue({ data: { pinned_nodes: [] }, error: null })
  useWorkflowCatalogStore.setState({ nodesAPI: CATALOGO, nodesFetchedAt: Date.now() })
})

describe("renomear uma variável de saída do Script Python", () => {
  it("as arestas que liam o nome antigo passam a ler o novo — num passo só de Ctrl+Z", async () => {
    montar(workflow(LIGACOES), "script")
    await esperar(50)

    await preencher("Variável de saída", "a, soma")
    // A rename: nothing in the form to warn about, the edges follow it.
    expect(aviso()).toBe("")
    clicarAplicar()
    await esperar(PASSO)

    expect(propriedade("script", "output_vars")).toBe("a, soma")
    expect(chaves()).toEqual(["espalha:-", "recorte:a", "total:soma"])
    // What gets saved: the new key, and no handle the script does not draw.
    const { edgesReq } = buildGraphPayload(canvas.getNodes() as INodeContext[], canvas.getEdges())
    expect(edgesReq.find(e => e.target === "total")).toEqual({ source: "script", target: "total", from_key: "soma" })

    // Configuration and edges go back together — never a script that delivers
    // `soma` with an edge still reading `b`, or the other way around.
    teclar("z")
    await esperar(50)
    expect(propriedade("script", "output_vars")).toBe("a, b")
    expect(chaves()).toEqual(["espalha:-", "recorte:a", "total:b"])
    // One step: that undo already reached the canvas as it opened.
    expect(screen.getByTitle("Desfazer (Ctrl+Z)")).toBeDisabled()

    teclar("y")
    await esperar(50)
    expect(propriedade("script", "output_vars")).toBe("a, soma")
    expect(chaves()).toEqual(["espalha:-", "recorte:a", "total:soma"])
  })

  it("um nome que some sem outro no lugar é avisado antes de aplicar, com a conexão que ficaria sem dado", async () => {
    montar(workflow(LIGACOES), "script")
    await esperar(50)

    const entrada = await screen.findByRole("textbox", { name: "Variável de saída" })
    act(() => entrada.focus())
    await preencher("Variável de saída", "a")
    expect(aviso()).toContain("b → Total")
    expect(aviso()).not.toContain("Recorte")
    // The notice shows up while the name is being typed: the field must stay
    // the same element, with the focus, or typing would stop mid-word.
    expect(document.activeElement).toBe(entrada)

    // A warning, not a lock: applying stays possible, and the edge is not
    // touched — choosing what it reads now is up to the person.
    clicarAplicar()
    await esperar(PASSO)
    expect(propriedade("script", "output_vars")).toBe("a")
    expect(chaves()).toEqual(["espalha:-", "recorte:a", "total:b"])
  })

  it("trocar mais de um nome de uma vez não é uma renomeação: o aviso nomeia cada conexão", async () => {
    montar(workflow(LIGACOES), "script")
    await esperar(50)

    await preencher("Variável de saída", "x, y")
    expect(aviso()).toContain("a → Recorte")
    expect(aviso()).toContain("b → Total")

    clicarAplicar()
    await esperar(PASSO)
    expect(chaves()).toEqual(["espalha:-", "recorte:a", "total:b"])
  })

  it("um nó de saída dinâmica sem output_vars não mexe nas arestas", async () => {
    montar(workflow([{ source: "leitor", target: "recorte", from_key: "output" }]), "leitor")
    await esperar(50)

    await preencher("Arquivo", "y.geojson")
    expect(aviso()).toBe("")
    clicarAplicar()
    await esperar(PASSO)

    expect(propriedade("leitor", "path")).toBe("y.geojson")
    expect(chaves()).toEqual(["recorte:output"])
  })
})
