/**
 * A save that arrives before the canvas has the workflow's graph must not
 * write anything.
 *
 * On `/workflow/[id]` the workflow request and the node catalog come in
 * separately, and the graph only reaches the canvas when BOTH have arrived.
 * In between, the name is already known and the canvas is empty — and Ctrl+S
 * saved exactly that: the workflow's nodes and edges gone on the server. The
 * "never save an empty graph" rail did not hold, because it only ran when a
 * reference snapshot existed, and the snapshot only exists after hydration.
 * Switching workflows had the same hole with a worse payload: the previous
 * workflow's graph, still on screen, written over the new one.
 *
 * The refusal lives in the save itself, not in the shortcut: Ctrl+S, the Save
 * button, the retry on the state chip and the silent save before Executar all
 * go through `saveWorkflow`.
 */
import React, { useEffect } from "react"
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { render, renderHook, act, cleanup, fireEvent } from "@testing-library/react"
import { ReactFlowProvider, useReactFlow, useStoreApi } from "@xyflow/react"

const rota = vi.hoisted(() => ({ params: {} as { id?: string } }))
vi.mock("next/navigation", () => ({
  useParams: () => rota.params,
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/workflow",
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
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

// The panels around the canvas: none of them saves anything by itself, and each
// one would bring its own services along.
vi.mock("@/app/components/workflow/buttons", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/run-panel", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/drawer", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/subflow-viewer", () => ({ default: () => null }))
vi.mock("@/app/components/workflow/assistente", () => ({ default: () => null }))

import ReactFlowComponent from "@/app/components/workflow"
import { FlowContextProvider, INodeContext } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { buildGraphPayload, useSaveWorkflow } from "@/app/hooks/workflow/useSaveWorkflow"
import { buildNodes } from "@/app/components/workflow/utils/build-canvas"
import type { INodesAPI, INodesDefinition, IWorkflow } from "@/service/types"

const CATALOGO = [
  { name: "Buffer", alias: "Buffer", description: "", type: "spatial", properties: [], outputs: [{ name: "output" }] },
] as unknown as INodesAPI[]

const definicaoDoNo = (id: string, i: number): INodesDefinition =>
  ({ id, name: "Buffer", alias: id, type: "spatial", properties: {}, position: { x: i * 200, y: 0 } }) as INodesDefinition

const workflow = (id_hash: string, ids: string[]): IWorkflow => ({
  id_hash,
  name: "Fluxo",
  flag_ative: true,
  description: "",
  version: "v1",
  priority: 0,
  created_by_id: "u",
  updated_by_id: "u",
  definition: { nodes: ids.map(definicaoDoNo), edges: [] },
})

let canvas: ReturnType<typeof useReactFlow>
function Sonda() {
  const instancia = useReactFlow()
  useEffect(() => { canvas = instancia }, [instancia])
  return null
}

function montar(inicial?: IWorkflow) {
  const tela = (w?: IWorkflow) => (
    <ReactFlowProvider>
      <FlowContextProvider>
        <Sonda />
        <ReactFlowComponent workflow={w} />
      </FlowContextProvider>
    </ReactFlowProvider>
  )
  const r = render(tela(inicial))
  return { ...r, trocarWorkflow: (w?: IWorkflow) => r.rerender(tela(w)) }
}

const nos = () => canvas.getNodes().map(n => n.id).sort()
const adicionarNo = (id: string) =>
  act(() => { canvas.addNodes(buildNodes({ nodes: [definicaoDoNo(id, 3)], edges: [] }, CATALOGO)[0]) })
const ctrlS = () => fireEvent.keyDown(document.body, { key: "s", ctrlKey: true })
const esperar = (ms = 50) => act(async () => { await new Promise(r => setTimeout(r, ms)) })

/** Ids of the nodes sent in the n-th PUT. */
const nosDoPut = (n = 0) =>
  (servico.updateWorkflowById.mock.calls[n][1] as { definition: { nodes: { id: string }[] } })
    .definition.nodes.map(no => no.id).sort()

function adiado<T>() {
  let resolve!: (valor: T) => void
  const promise = new Promise<T>(r => { resolve = r })
  return { promise, resolve }
}

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
  rota.params = { id: "wf-1" }
  servico.getNodes.mockResolvedValue({ data: CATALOGO, error: null })
  servico.getCredentials.mockResolvedValue({ data: [], error: null })
  servico.listPinnedNodes.mockResolvedValue({ data: { pinned_nodes: [] }, error: null })
  servico.updateWorkflowById.mockImplementation(async (id: string) => ({ data: { id_hash: id }, error: null }))
  servico.createWorkflow.mockResolvedValue({ data: { id_hash: "wf-novo" }, error: null })
  useWorkflowCatalogStore.setState({ nodesAPI: CATALOGO, nodesFetchedAt: Date.now() })
})

describe("Ctrl+S no editor enquanto o workflow carrega", () => {
  it("antes de o catálogo chegar não grava nada — e depois grava o grafo de verdade", async () => {
    // GET /nodes still in flight: the workflow came, its graph cannot be drawn yet.
    useWorkflowCatalogStore.setState({ nodesAPI: [], nodesFetchedAt: null })
    const catalogo = adiado<{ data: INodesAPI[]; error: null }>()
    servico.getNodes.mockReturnValue(catalogo.promise)

    montar(workflow("wf-1", ["A", "B"]))
    await esperar()
    expect(nos()).toEqual([])

    ctrlS()
    await esperar()
    expect(servico.updateWorkflowById).not.toHaveBeenCalled()

    await act(async () => { catalogo.resolve({ data: CATALOGO, error: null }) })
    await esperar()
    expect(nos()).toEqual(["A", "B"])
    // The reference for "saved" is the graph that just loaded, not the empty
    // canvas from before it.
    const { nodesReq, edgesReq } = buildGraphPayload(canvas.getNodes() as INodeContext[], canvas.getEdges())
    expect(useWorkflowSaveStore.getState().isDirty(nodesReq, edgesReq, "Fluxo")).toBe(false)

    adicionarNo("C")
    await esperar()
    ctrlS()
    await esperar()
    expect(servico.updateWorkflowById).toHaveBeenCalledTimes(1)
    expect(nosDoPut()).toEqual(["A", "B", "C"])
  })

  it("trocar de workflow volta a esperar: o grafo do anterior não é gravado no novo", async () => {
    const wf1 = workflow("wf-1", ["A", "B"])
    const { trocarWorkflow } = montar(wf1)
    await esperar()

    // The route already points to wf-2; the page still holds the same wf-1
    // object until wf-2's request returns — and wf-1's graph is what is on screen.
    rota.params = { id: "wf-2" }
    trocarWorkflow(wf1)
    await esperar()
    ctrlS()
    await esperar()
    expect(servico.updateWorkflowById).not.toHaveBeenCalled()

    trocarWorkflow(workflow("wf-2", ["X"]))
    await esperar()
    expect(nos()).toEqual(["X"])
    adicionarNo("Y")
    await esperar()
    ctrlS()
    await esperar()
    expect(servico.updateWorkflowById).toHaveBeenCalledTimes(1)
    expect(servico.updateWorkflowById.mock.calls[0][0]).toBe("wf-2")
    expect(nosDoPut()).toEqual(["X", "Y"])
  })

  it("um workflow que abriu vazio salva os primeiros nós", async () => {
    montar(workflow("wf-1", []))
    await esperar()

    adicionarNo("A")
    await esperar()
    ctrlS()
    await esperar()
    expect(servico.updateWorkflowById).toHaveBeenCalledTimes(1)
    expect(nosDoPut()).toEqual(["A"])
  })

  it("a tela de criação nasce pronta: Ctrl+S cria o workflow", async () => {
    rota.params = {}
    montar()
    await esperar()

    act(() => { useWorkflowSaveStore.getState().setWorkflowName("Novo fluxo") })
    adicionarNo("A")
    await esperar()
    ctrlS()
    await esperar()
    expect(servico.createWorkflow).toHaveBeenCalledTimes(1)
    const corpo = servico.createWorkflow.mock.calls[0][0] as { name: string; definition: { nodes: { id: string }[] } }
    expect(corpo.name).toBe("Novo fluxo")
    expect(corpo.definition.nodes.map(n => n.id)).toEqual(["A"])
  })
})

describe("o save de qualquer chamador", () => {
  function montarSave() {
    return renderHook(() => ({ salvar: useSaveWorkflow(), canvas: useStoreApi() }), { wrapper: ReactFlowProvider })
  }

  const no = (id: string) =>
    ({ id, position: { x: 0, y: 0 }, data: { name: "Buffer", alias: id, type: "spatial", properties: {} } }) as INodeContext

  beforeEach(() => {
    useWorkflowSaveStore.setState({ isSaving: false, saveStatus: "idle", workflowName: "Fluxo", lastError: null })
  })

  it("o save silencioso do Executar também espera o canvas hidratar", async () => {
    // Where the editor stands right after the workflow request returned: name
    // known, no reference snapshot, graph not on the canvas yet.
    useWorkflowSaveStore.setState({ lastSavedSnapshot: null, canvasHidratado: false })
    const { result } = montarSave()

    await act(async () => { await result.current.salvar.saveWorkflow({ silent: true }) })

    expect(servico.updateWorkflowById).not.toHaveBeenCalled()
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("idle")
  })

  it("sem snapshot de referência, um grafo vazio não sobrescreve um workflow existente", async () => {
    // A missing snapshot is "the saved state is unknown", not "nothing was saved".
    useWorkflowSaveStore.setState({ lastSavedSnapshot: null, canvasHidratado: true })
    const { result } = montarSave()

    await act(async () => { await result.current.salvar.saveWorkflow() })

    expect(servico.updateWorkflowById).not.toHaveBeenCalled()
  })

  it("com o canvas hidratado, o save silencioso grava o grafo que mudou", async () => {
    const { nodesReq, edgesReq } = buildGraphPayload([no("A")], [])
    useWorkflowSaveStore.getState().initSnapshot(nodesReq, edgesReq, "Fluxo")
    const { result } = montarSave()
    act(() => { result.current.canvas.getState().setNodes([no("A"), no("B")]) })

    await act(async () => { await result.current.salvar.saveWorkflow({ silent: true }) })

    expect(servico.updateWorkflowById).toHaveBeenCalledTimes(1)
    expect(nosDoPut()).toEqual(["A", "B"])
  })
})
