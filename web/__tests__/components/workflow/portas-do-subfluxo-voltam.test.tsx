/**
 * A SubWorkflow's ports come from its child's contract, fetched after the
 * canvas is drawn — they never travel in the definition. So every path that
 * rebuilds the nodes from a definition draws the SubWorkflow WITHOUT them:
 * restoring a version, an assistant drawing, and undoing back to the canvas as
 * it opened (the history's first step is taken before the contract arrives).
 * The sync only ran again when a SubWorkflow or its target changed, so the node
 * stayed portless for the rest of the session and its edges collapsed onto one
 * point — their keys survived, a reload fixed it. Putting them back is not an
 * edit, and must not become an undo step: as one, it threw the redo away after
 * an undo, and after an assistant drawing Ctrl+Z could not get past it.
 *
 * And a contract still on its way was taken for "no contract": when anything
 * changed the SubWorkflows mid-request, the new round gave the node empty ports
 * and the round that would have applied the answer was cancelled.
 *
 * The real editor over a real React Flow, with the layout faked enough for
 * edges to be drawn (the same setup as the read-only canvas tests); only the
 * server is in memory.
 */
import React, { useEffect } from "react"
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { render, act, cleanup, fireEvent, screen, waitFor } from "@testing-library/react"
import { ReactFlowProvider, useReactFlow } from "@xyflow/react"

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "wf-1" }),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/workflow/wf-1",
}))
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: "authenticated", data: null }) }))
// The node configuration modal is the only `next/dynamic` in the editor.
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
  getWorkflowContract: vi.fn(),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

vi.mock("@/app/components/workflow/buttons", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/run-panel", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/drawer", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/subflow-viewer", () => ({ default: () => null }))
// The assistant panel is where `onAplicar` comes from: the stub keeps it so the
// test can apply a proposal exactly as the proposal card does.
const assistente = vi.hoisted(() => ({ aplicar: null as null | ((resultado: unknown) => void) }))
vi.mock("@/app/components/workflow/assistente", () => ({
  default: ({ onAplicar }: { onAplicar: (resultado: unknown) => void }) => {
    assistente.aplicar = onAplicar
    return null
  },
}))

import ReactFlowComponent from "@/app/components/workflow"
import { FlowContextProvider, INodeContext } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { aplicarProposta } from "@/app/components/workflow/utils/aplicar-proposta"
import { buildNodes } from "@/app/components/workflow/utils/build-canvas"
import type { INodesAPI, INodesDefinition, IWorkflow } from "@/service/types"

const CATALOGO = [
  {
    name: "SubWorkflow", alias: "Sub-Workflow", description: "", type: "control",
    properties: [{ name: "workflowHash", label: "Sub-workflow", type: "string", default: "", description: null }],
    outputs: [{ name: "subWorkflowResult", type: "object" }],
  },
  { name: "Buffer", alias: "Buffer", description: "", type: "spatial", properties: [], outputs: [{ name: "output" }] },
] as unknown as INodesAPI[]

const subfluxo = (id: string, hash: string, x = 0): INodesDefinition =>
  ({ id, name: "SubWorkflow", alias: id, type: "control", properties: { workflowHash: hash }, position: { x, y: 0 } }) as INodesDefinition
const buffer = (id: string, y: number): INodesDefinition =>
  ({ id, name: "Buffer", alias: id, type: "spatial", properties: {}, position: { x: 300, y } }) as INodesDefinition

/** The child returns two ports; one edge leaves each. */
const DEFINICAO: IWorkflow["definition"] = {
  nodes: [subfluxo("sub", "filho"), buffer("r1", 0), buffer("r2", 150)],
  edges: [
    { source: "sub", target: "r1", source_handle: "r1", from_key: "r1" },
    { source: "sub", target: "r2", source_handle: "r2", from_key: "r2" },
  ],
}

const contrato = (...saidas: string[]) => ({
  data: { inputs: [], outputs: saidas.map(name => ({ name })), has_input_node: true, has_output_node: true },
  error: null,
})

/** A fresh object on every call — what a refetch (`reloadWorkflow`) hands the editor. */
const workflow = (definition: IWorkflow["definition"] = DEFINICAO): IWorkflow => ({
  id_hash: "wf-1",
  name: "Fluxo",
  flag_ative: true,
  description: "",
  version: "v1",
  priority: 0,
  created_by_id: "u",
  updated_by_id: "u",
  definition,
})

let canvas: ReturnType<typeof useReactFlow>
function Sonda() {
  const instancia = useReactFlow()
  useEffect(() => { canvas = instancia }, [instancia])
  return null
}

function montar(inicial: IWorkflow) {
  const tela = (w: IWorkflow) => (
    <ReactFlowProvider>
      <FlowContextProvider>
        <Sonda />
        <ReactFlowComponent workflow={w} />
      </FlowContextProvider>
    </ReactFlowProvider>
  )
  const r = render(tela(inicial))
  return { ...r, trocarWorkflow: (w: IWorkflow) => r.rerender(tela(w)) }
}

const nos = () => canvas.getNodes().map(n => n.id).sort()
/** The output ports the SubWorkflow `id` draws. */
const portas = (id = "sub") =>
  ((canvas.getNode(id)?.data as { outputs?: { name: string }[] }).outputs ?? []).map(p => p.name)
/** Which handle each edge leaving `sub` hangs from ("-": the anonymous one). */
const ancoras = () => canvas.getEdges()
  .filter(e => e.source === "sub")
  .map(e => `${e.target}:${e.sourceHandle ?? "-"}`)
  .sort()
/** Edges React Flow actually drew: one on an id the node lacks is not. */
const desenhadas = (container: HTMLElement) => container.querySelectorAll(".react-flow__edge").length

const teclar = (tecla: string) => fireEvent.keyDown(document.body, { key: tecla, ctrlKey: true })
const esperar = (ms: number) => act(async () => { await new Promise(r => setTimeout(r, ms)) })

/** Long enough for the snapshot the editor schedules 300 ms after an edit. */
const PASSO = 400

/** These tests wait in real time, at the pace of a person: each step settles
 *  before the next, which is what lets a history step show up where it should not. */
const DEMORADO = { timeout: 20_000 }

/** Until the SubWorkflow `id` draws its child's ports — they come after the
 *  sync's 300 ms pause and the request —, then long enough for a history step
 *  that putting them on the canvas could schedule. */
async function comPortas(id = "sub") {
  await waitFor(() => expect(portas(id)).toEqual(["r1", "r2"]), { timeout: 2500 })
  await esperar(PASSO)
}

function adiado<T>() {
  let resolve!: (valor: T) => void
  const promise = new Promise<T>(r => { resolve = r })
  return { promise, resolve }
}

/** Undoes until there is nothing left to undo — the canvas as it opened —, at
 *  the pace of a person: each step has time to settle before the next. */
async function desfazerTudo() {
  for (let i = 0; i < 6 && !screen.getByTitle("Desfazer (Ctrl+Z)").hasAttribute("disabled"); i++) {
    teclar("z")
    await esperar(3 * PASSO)
  }
}

beforeAll(() => {
  // useIsMobile (the canvas becomes a viewer on a phone).
  window.matchMedia = vi.fn(() => ({ matches: false, addEventListener() {}, removeEventListener() {} })) as never
  // React Flow only draws an edge between MEASURED nodes; jsdom measures
  // nothing. Enough of a layout for the edges to be drawn.
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, get() { return 120 } })
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, get() { return 60 } })
  globalThis.ResizeObserver = class {
    cb: ResizeObserverCallback
    constructor(cb: ResizeObserverCallback) { this.cb = cb }
    observe(target: Element) {
      setTimeout(() => this.cb([{ target, contentRect: { width: 800, height: 600 } } as unknown as ResizeObserverEntry], this as unknown as ResizeObserver), 0)
    }
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
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
  servico.getWorkflowContract.mockResolvedValue(contrato("r1", "r2"))
  useWorkflowCatalogStore.setState({ nodesAPI: CATALOGO, nodesFetchedAt: Date.now() })
})

describe("as portas do SubWorkflow voltam quando o nó é reconstruído sem elas", () => {
  it("ao abrir, cada aresta sai da sua porta", DEMORADO, async () => {
    const { container } = montar(workflow())
    await comPortas()

    expect(ancoras()).toEqual(["r1:r1", "r2:r2"])
    expect(desenhadas(container)).toBe(2)
  })

  it("depois de restaurar uma versão", DEMORADO, async () => {
    const { container, trocarWorkflow } = montar(workflow())
    await comPortas()

    // What `reloadWorkflow` does after the restore: a new object, rebuilt from
    // the definition — the SubWorkflow without its ports.
    trocarWorkflow(workflow())
    await comPortas()

    expect(ancoras()).toEqual(["r1:r1", "r2:r2"])
    expect(desenhadas(container)).toBe(2)
  })

  it("depois de desfazer até o canvas de abertura — e refazer continua trazendo o que foi feito", DEMORADO, async () => {
    montar(workflow())
    await comPortas()
    act(() => { canvas.addNodes(buildNodes({ nodes: [buffer("C", 300)], edges: [] }, CATALOGO)[0]) })
    await esperar(PASSO)

    await desfazerTudo()
    expect(nos()).toEqual(["r1", "r2", "sub"])
    await comPortas()
    expect(ancoras()).toEqual(["r1:r1", "r2:r2"])

    // Putting the ports back is not an edit: it must not become a step that
    // throws away what there is to redo.
    teclar("y")
    await esperar(PASSO)
    expect(nos()).toEqual(["C", "r1", "r2", "sub"])
    expect(portas()).toEqual(["r1", "r2"])
  })

  it("depois de um desenho do assistente — e Ctrl+Z ainda volta ao canvas de antes dele", DEMORADO, async () => {
    montar(workflow())
    await comPortas()

    // The proposal keeps the SubWorkflow and its edges, and adds D.
    const proposta = aplicarProposta(
      { nodes: [...DEFINICAO.nodes, buffer("D", 300)], edges: DEFINICAO.edges },
      CATALOGO,
      canvas.getNodes() as INodeContext[],
    )
    act(() => { assistente.aplicar!(proposta) })
    await comPortas()
    expect(nos()).toEqual(["D", "r1", "r2", "sub"])
    expect(ancoras()).toEqual(["r1:r1", "r2:r2"])

    // One step back is the canvas before the drawing — not the drawing again,
    // which is where a step recorded for the ports would leave it.
    teclar("z")
    await esperar(3 * PASSO)
    expect(nos()).toEqual(["r1", "r2", "sub"])
    expect(portas()).toEqual(["r1", "r2"])
  })
})

describe("um contrato ainda a caminho não vira 'sem contrato'", () => {
  it("outro SubWorkflow entrando no meio da busca não deixa o primeiro sem portas", DEMORADO, async () => {
    const filho = adiado<ReturnType<typeof contrato>>()
    servico.getWorkflowContract.mockImplementation((hash: string) =>
      hash === "filho" ? filho.promise : Promise.resolve(contrato()))
    montar(workflow())
    // The first round is waiting for "filho".
    await waitFor(() => expect(servico.getWorkflowContract).toHaveBeenCalledTimes(1), { timeout: 2500 })

    // A second SubWorkflow, whose child declares no ports, changes the set
    // while that request is still out: a new round starts before the answer.
    act(() => { canvas.addNodes(buildNodes({ nodes: [subfluxo("outro", "vazio", 600)], edges: [] }, CATALOGO)[0]) })
    await waitFor(() => expect(servico.getWorkflowContract).toHaveBeenCalledTimes(2), { timeout: 2500 })
    await esperar(PASSO)

    await act(async () => { filho.resolve(contrato("r1", "r2")) })
    await comPortas("sub")

    expect(ancoras()).toEqual(["r1:r1", "r2:r2"])
    expect(portas("outro")).toEqual([])
    // Waiting for the request already out, not asking again.
    expect(servico.getWorkflowContract.mock.calls.map(c => c[0])).toEqual(["filho", "vazio"])
  })

  it("um filho que demora a responder não segura as portas dos outros SubWorkflows", DEMORADO, async () => {
    const lento = adiado<ReturnType<typeof contrato>>()
    servico.getWorkflowContract.mockImplementation((hash: string) =>
      hash === "lento" ? lento.promise : Promise.resolve(contrato("r1", "r2")))
    montar(workflow({ ...DEFINICAO, nodes: [...DEFINICAO.nodes, subfluxo("devagar", "lento", 600)] }))

    await comPortas("sub")
    expect(portas("devagar")).toEqual([])

    await act(async () => { lento.resolve(contrato("r1", "r2")) })
    await comPortas("devagar")
  })
})
