/**
 * The "+" next to a port: it opens the node drawer and creates node and edge
 * in one go — without the line ever being dropped on a handle, so without the
 * checks React Flow does on a drag. Three ways it created edges the canvas
 * cannot draw, which stay in the workflow, run, and cannot be deleted:
 *
 * - a TRIGGER picked from the list: triggers have no input handle;
 * - a "+" on an anonymous output right after a "+" on a named port: the URL
 *   kept the previous `ndhid`, and the new edge left from a handle the source
 *   does not have;
 * - a link `validarConexao` refuses on the canvas (a number into a node that
 *   expects a layer) went through here unchecked.
 *
 * Real drawer, real "+" button and the real React Flow store; only the URL
 * (Next's router) is in memory.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { useEffect } from "react"
import { Edge, ReactFlowProvider, useReactFlow, useStoreApi } from "@xyflow/react"
import { toast } from "sonner"

const url = vi.hoisted(() => ({ sp: new URLSearchParams(""), pathname: "/workflow/abc" }))
const replace = vi.hoisted(() => vi.fn())
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  usePathname: () => url.pathname,
  useSearchParams: () => url.sp,
  useParams: () => ({}),
}))

import NodesDrawer from "@/app/components/workflow/drawer/nodes-drawer"
import WorkflowDrawer from "@/app/components/workflow/drawer"
import AddConnectionHandle from "@/app/components/workflow/custom-nodes/add-connection-handle"
import { buildNodes } from "@/app/components/workflow/utils/build-canvas"
import { REJECTION_MESSAGE } from "@/app/components/workflow/utils/valida-conexao"
import { FlowContextProvider, INodeContext, useFlowContext } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { CanvasDefinition, INodesAPI } from "@/service/types"

const def = (d: Partial<INodesAPI> & Pick<INodesAPI, "name" | "type" | "alias">): INodesAPI => ({
  description: "",
  properties: [],
  ...d,
})

const CATALOGO: INodesAPI[] = [
  def({ name: "WebhookTrigger", alias: "Webhook", type: "trigger", outputs: [{ name: "payload", type: "object" }] }),
  def({
    name: "RemoveDuplicates", alias: "Remover duplicados", type: "action",
    outputs: [
      { name: "output", type: "geodataframe", port: true },
      { name: "removed", type: "geodataframe", port: true },
      { name: "removed_count", type: "number", port: true },
    ],
  }),
  def({ name: "ReadGeoJSON", alias: "Ler GeoJSON", type: "datasource", outputs: [{ name: "output", type: "geodataframe" }] }),
  def({
    name: "ConvexHullNode", alias: "Envoltória convexa", type: "spatial",
    inputs: [{ name: "layer", type: "geodataframe" }], outputs: [{ name: "output", type: "geodataframe" }],
  }),
  def({ name: "SaveGeoJSON", alias: "Salvar GeoJSON", type: "output", inputs: [{ name: "input" }] }),
  def({
    name: "SubWorkflow", alias: "Sub-Workflow", type: "control",
    properties: [{ name: "workflowHash", type: "string", default: "", description: null }],
    outputs: [{ name: "subWorkflowResult", type: "object" }],
  }),
]

const no = (id: string, name: string, properties: Record<string, unknown> = {}) =>
  ({ id, name, type: "", properties, position: { x: 0, y: 0 } })

/** The canvas the "+" is pressed on, built the way the editor builds it. */
function canvas(): INodeContext[] {
  const nos = buildNodes({
    nodes: [no("dedup", "RemoveDuplicates"), no("leitura", "ReadGeoJSON"), no("sub", "SubWorkflow", { workflowHash: "filho" })],
  } as CanvasDefinition, CATALOGO)
  // The child's contract, as useSubWorkflowContractSync applies it.
  return nos.map(n => (n.id === "sub" ? { ...n, data: { ...n.data, outputs: [{ name: "r1" }, { name: "r2" }] } } : n))
}

/** The React Flow store, to read what the drawer wrote into it. */
const loja = {} as { api: ReturnType<typeof useStoreApi> }
function Sonda() {
  const api = useStoreApi()
  useEffect(() => { loja.api = api }, [api])
  return null
}

/** What the editor does on mount: hands the React Flow instance to the drawer. */
function RegistraInstancia() {
  const instancia = useReactFlow()
  const { setFlowContext } = useFlowContext()
  useEffect(() => {
    setFlowContext({ reactFlowInstance: instancia as never, flowRef: { current: null } })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return null
}

function montar(conteudo: React.ReactNode) {
  return render(
    <FlowContextProvider>
      <ReactFlowProvider defaultNodes={canvas()} defaultEdges={[]}>
        <RegistraInstancia />
        <Sonda />
        {conteudo}
      </ReactFlowProvider>
    </FlowContextProvider>,
  )
}

const arestas = () => loja.api.getState().edges as Edge[]
const nos = () => loja.api.getState().nodes as INodeContext[]
const novoNo = (name: string) => nos().find(n => n.data.name === name)

function escolher(alias: string) {
  fireEvent.click(screen.getByText(alias))
}

beforeEach(() => {
  url.sp = new URLSearchParams("")
  replace.mockReset()
  replace.mockImplementation((destino: string) => {
    url.sp = new URLSearchParams(destino.split("?")[1] ?? "")
  })
  useWorkflowCatalogStore.setState({ nodesAPI: CATALOGO, nodesDrawerState: "opened" })
})
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe("'+' de uma porta — a lista não oferece triggers", () => {
  it("ligando a partir de um nó, nenhum trigger aparece: ele não tem entrada para a aresta", () => {
    url.sp = new URLSearchParams("ndid=leitura")
    montar(<NodesDrawer aliasFilter="" />)

    expect(screen.queryByText("Webhook")).not.toBeInTheDocument()
    expect(screen.getByText("Envoltória convexa")).toBeInTheDocument()
  })

  it("as categorias também não oferecem Triggers enquanto se liga", () => {
    url.sp = new URLSearchParams("ndid=leitura")
    montar(<WorkflowDrawer />)

    expect(screen.queryByText("Triggers")).not.toBeInTheDocument()
    expect(screen.getByText("Ações")).toBeInTheDocument()
  })

  it("sem ligação (o botão 'Adicionar nó'), os triggers seguem na lista", () => {
    montar(<NodesDrawer aliasFilter="" />)

    expect(screen.getByText("Webhook")).toBeInTheDocument()
  })

  it("um ndid de nó que já não existe não esconde os triggers", () => {
    // Nothing would be linked — `addNode` only creates the edge when the source
    // exists — so there is nothing to protect.
    url.sp = new URLSearchParams("ndid=apagado")
    montar(<NodesDrawer aliasFilter="" />)

    expect(screen.getByText("Webhook")).toBeInTheDocument()
  })
})

describe("'+' de uma saída anônima logo depois do '+' de uma porta nomeada", () => {
  it("o novo vínculo não herda o handle da porta anterior", () => {
    // 1. "+" on RemoveDuplicates' `removed` port.
    url.sp = new URLSearchParams("ndid=dedup&ndhid=removed")
    // 2. "+" on ReadGeoJSON's single (anonymous) output.
    const { container } = montar(
      <AddConnectionHandle nodeId="leitura" connectionVisible>
        <span />
      </AddConnectionHandle>,
    )
    fireEvent.click(container.querySelector("button")!)

    expect(url.sp.get("ndid")).toBe("leitura")
    expect(url.sp.get("ndhid")).toBeNull()

    // 3. Picking the node: the edge leaves ReadGeoJSON's anonymous handle.
    cleanup()
    montar(<NodesDrawer aliasFilter="" />)
    escolher("Envoltória convexa")

    expect(arestas()).toHaveLength(1)
    expect(arestas()[0].source).toBe("leitura")
    expect(arestas()[0].sourceHandle ?? null).toBeNull()
    expect(arestas()[0].data).toEqual({ from_key: "output" })
  })
})

describe("'+' cuja ligação a validação recusa", () => {
  it("o nó entra, a aresta não, e o motivo aparece", () => {
    const aviso = vi.spyOn(toast, "warning")
    // `removed_count` is a number; the convex hull expects a layer.
    url.sp = new URLSearchParams("ndid=dedup&ndhid=removed_count")
    montar(<NodesDrawer aliasFilter="" />)
    escolher("Envoltória convexa")

    expect(novoNo("ConvexHullNode")).toBeDefined()
    expect(arestas()).toEqual([])
    expect(aviso).toHaveBeenCalledTimes(1)
    expect(aviso.mock.calls[0][0]).toBe(REJECTION_MESSAGE["tipo-incompativel"])
  })

  it("uma ligação aceita segue nascendo pela porta escolhida", () => {
    const aviso = vi.spyOn(toast, "warning")
    url.sp = new URLSearchParams("ndid=dedup&ndhid=removed")
    montar(<NodesDrawer aliasFilter="" />)
    escolher("Envoltória convexa")

    expect(arestas()).toHaveLength(1)
    expect(arestas()[0]).toMatchObject({
      source: "dedup", sourceHandle: "removed", target: novoNo("ConvexHullNode")!.id,
      data: { from_key: "removed" },
    })
    expect(aviso).not.toHaveBeenCalled()
  })
})

describe("'+' de uma porta do SubWorkflow", () => {
  it("a aresta leva a própria porta como from_key, não o resultado inteiro", () => {
    url.sp = new URLSearchParams("ndid=sub&ndhid=r2")
    montar(<NodesDrawer aliasFilter="" />)
    escolher("Salvar GeoJSON")

    expect(arestas()).toHaveLength(1)
    expect(arestas()[0]).toMatchObject({ source: "sub", sourceHandle: "r2", data: { from_key: "r2" } })
  })
})
