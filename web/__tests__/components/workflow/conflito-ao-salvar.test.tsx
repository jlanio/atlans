/**
 * Two editors on one workflow: the second save no longer erases the first.
 *
 * The editor saves the whole definition. A tab that opened the workflow before
 * someone else saved it — another tab, another person, the assistant — wrote
 * over that change on its next save and went on showing "Salvo": edges added
 * elsewhere vanished with nothing said. The editor now sends back the
 * `definition_etag` it loaded; the server refuses a stale save with 409
 * `definition_conflict`, and the editor says so, offering to save anyway.
 *
 * Mounted on the real editor — the same setup as the early-save tests.
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
const toasts = vi.hoisted(() => ({ erros: [] as { titulo: string; acao?: { label: string; onClick: () => void } }[] }))
vi.mock("@/utils/createToast", () => ({
  createToast: {
    error: (titulo: string, _descricao?: string, acao?: { label: string; onClick: () => void }) => { toasts.erros.push({ titulo, acao }) },
    warning: () => {}, info: () => {}, success: () => {}, loading: () => {},
  },
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

const adicionarNo = (id: string) =>
  act(() => { canvas.addNodes(buildNodes({ nodes: [definicaoDoNo(id, 3)], edges: [] }, CATALOGO)[0]) })
const ctrlS = () => fireEvent.keyDown(document.body, { key: "s", ctrlKey: true })
const esperar = (ms = 50) => act(async () => { await new Promise(r => setTimeout(r, ms)) })

/** Ids of the nodes sent in the n-th PUT. */
const nosDoPut = (n = 0) =>
  (servico.updateWorkflowById.mock.calls[n][1] as { definition: { nodes: { id: string }[] } })
    .definition.nodes.map(no => no.id).sort()

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


const comEtiqueta = (etiqueta: string) => ({ ...workflow("wf-1", ["A", "B"]), definition_etag: etiqueta })
const etiquetaDoPut = (n = 0) => (servico.updateWorkflowById.mock.calls[n][2] as { expectedEtag?: string | null }).expectedEtag

describe("salvar por cima de outra edição", () => {
  it("o save leva a etiqueta carregada, e o seguinte a do save anterior", async () => {
    servico.updateWorkflowById.mockImplementation(async (id: string) => ({ data: { id_hash: id, definition_etag: "e2" }, error: null }))
    montar(comEtiqueta("e1"))
    await esperar()

    adicionarNo("C")
    await esperar()
    ctrlS()
    await esperar()
    expect(etiquetaDoPut(0)).toBe("e1")

    adicionarNo("D")
    await esperar()
    ctrlS()
    await esperar()
    expect(etiquetaDoPut(1)).toBe("e2")
  })

  it("conflito: não grava, avisa, e 'Salvar mesmo assim' grava sem a etiqueta", async () => {
    toasts.erros = []
    servico.updateWorkflowById.mockResolvedValueOnce({
      data: undefined, status: 409,
      error: { name: "AxiosError", code: "definition_conflict", message: "Este workflow foi alterado em outro lugar." },
    })
    montar(comEtiqueta("e1"))
    await esperar()
    adicionarNo("C")
    await esperar()

    ctrlS()
    await esperar()
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("error")
    expect(toasts.erros.map(t => t.titulo)).toEqual(["Workflow alterado em outro lugar"])

    await act(async () => { toasts.erros[0].acao!.onClick() })
    await esperar()
    expect(servico.updateWorkflowById).toHaveBeenCalledTimes(2)
    expect(etiquetaDoPut(1)).toBeNull()
    expect(nosDoPut(1)).toEqual(["A", "B", "C"])
  })

  it("o save silencioso do Executar também avisa o conflito", async () => {
    // Executar stops on a failed save: the person has to know why.
    toasts.erros = []
    servico.updateWorkflowById.mockResolvedValueOnce({
      data: undefined, status: 409,
      error: { name: "AxiosError", code: "definition_conflict", message: "Alterado em outro lugar." },
    })
    const no = (id: string) =>
      ({ id, position: { x: 0, y: 0 }, data: { name: "Buffer", alias: id, type: "spatial", properties: {} } }) as INodeContext
    useWorkflowSaveStore.setState({ isSaving: false, saveStatus: "idle", workflowName: "Fluxo", definitionEtag: "e1" })
    const { nodesReq, edgesReq } = buildGraphPayload([no("A")], [])
    useWorkflowSaveStore.getState().initSnapshot(nodesReq, edgesReq, "Fluxo")
    const { result } = renderHook(() => ({ salvar: useSaveWorkflow(), canvas: useStoreApi() }), { wrapper: ReactFlowProvider })
    act(() => { result.current.canvas.getState().setNodes([no("A"), no("B")]) })

    let resposta: unknown
    await act(async () => { resposta = await result.current.salvar.saveWorkflow({ silent: true }) })
    expect((resposta as { error?: { code?: string } }).error?.code).toBe("definition_conflict")
    expect(etiquetaDoPut(0)).toBe("e1")
    expect(toasts.erros).toHaveLength(1)
  })
})

/**
 * A save still in flight when the person opens another workflow answers about
 * the workflow it was sent for. Its answer used to land in the save state of
 * the canvas now on screen: the next save there carried the previous
 * workflow's tag and was refused as a conflict nobody caused, and the change
 * detector compared against the previous graph.
 */
describe("save que volta depois de trocar de workflow", () => {
  const comEtiquetaEm = (id: string, nos: string[], etiqueta: string) => ({ ...workflow(id, nos), definition_etag: etiqueta })

  it("não deixa a etiqueta nem o snapshot do workflow anterior no novo", async () => {
    let responder: (r: unknown) => void = () => {}
    servico.updateWorkflowById.mockImplementationOnce(() => new Promise(r => { responder = r }))
    const tela = montar(comEtiquetaEm("wf-1", ["A", "B"], "e1"))
    await esperar()
    adicionarNo("C")
    await esperar()
    ctrlS()
    await esperar()

    rota.params = { id: "wf-2" }
    tela.trocarWorkflow(comEtiquetaEm("wf-2", ["X"], "e2"))
    await esperar()
    await act(async () => { responder({ data: { id_hash: "wf-1", definition_etag: "e1-novo" }, error: null }) })
    await esperar()

    const estado = useWorkflowSaveStore.getState()
    expect(estado.definitionEtag).toBe("e2")
    expect(JSON.parse(estado.lastSavedSnapshot!).nodes.map((n: { id: string }) => n.id)).toEqual(["X"])

    adicionarNo("Y")
    await esperar()
    ctrlS()
    await esperar()
    expect(servico.updateWorkflowById.mock.calls[1][0]).toBe("wf-2")
    expect(etiquetaDoPut(1)).toBe("e2")
  })

  it("o 'Salvar mesmo assim' de um conflito anterior não grava o canvas novo por cima", async () => {
    toasts.erros = []
    servico.updateWorkflowById.mockResolvedValueOnce({
      data: undefined, status: 409,
      error: { name: "AxiosError", code: "definition_conflict", message: "Alterado em outro lugar." },
    })
    const tela = montar(comEtiquetaEm("wf-1", ["A", "B"], "e1"))
    await esperar()
    adicionarNo("C")
    await esperar()
    ctrlS()
    await esperar()
    expect(toasts.erros.map(t => t.titulo)).toEqual(["Workflow alterado em outro lugar"])

    // The toast outlives the switch: clicked on the other workflow, it built
    // the payload from the canvas on screen and sent it to the first one.
    rota.params = { id: "wf-2" }
    tela.trocarWorkflow(comEtiquetaEm("wf-2", ["X"], "e2"))
    await esperar()
    await act(async () => { toasts.erros[0].acao!.onClick() })
    await esperar()
    expect(servico.updateWorkflowById).toHaveBeenCalledTimes(1)
  })
})
