/**
 * Saving a sub-workflow that drops ports its callers use says who breaks.
 *
 * Renaming or removing a port in a workflow called by others broke every
 * caller in silence: their edges on the old name delivered nothing at run, and
 * nobody was told when the child was saved. The save still goes through; the
 * PUT now returns `subworkflow_notices` — one per caller node and side — and
 * the editor sums them up in ONE amber toast: how many workflows, which ports,
 * which workflows.
 *
 * Mounted on the real editor — the same setup as the save-conflict tests.
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
const toasts = vi.hoisted(() => ({ avisos: [] as { titulo: string; descricao?: string }[] }))
vi.mock("@/utils/createToast", () => ({
  createToast: {
    warning: (titulo: string, descricao?: string) => { toasts.avisos.push({ titulo, descricao }) },
    error: () => {}, info: () => {}, success: () => {}, loading: () => {},
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
import type { INodesAPI, INodesDefinition, ISubworkflowNotice, IWorkflow } from "@/service/types"

const CATALOGO = [
  { name: "Buffer", alias: "Buffer", description: "", type: "spatial", properties: [], outputs: [{ name: "output" }] },
] as unknown as INodesAPI[]

const definicaoDoNo = (id: string, i: number): INodesDefinition =>
  ({ id, name: "Buffer", alias: id, type: "spatial", properties: {}, position: { x: i * 200, y: 0 } }) as INodesDefinition

const workflow = (id_hash: string, ids: string[]): IWorkflow => ({
  id_hash,
  name: "Filho",
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
  return render(
    <ReactFlowProvider>
      <FlowContextProvider>
        <Sonda />
        <ReactFlowComponent workflow={inicial} />
      </FlowContextProvider>
    </ReactFlowProvider>,
  )
}

const adicionarNo = (id: string) =>
  act(() => { canvas.addNodes(buildNodes({ nodes: [definicaoDoNo(id, 3)], edges: [] }, CATALOGO)[0]) })
const ctrlS = () => fireEvent.keyDown(document.body, { key: "s", ctrlKey: true })
const esperar = (ms = 50) => act(async () => { await new Promise(r => setTimeout(r, ms)) })

const aviso = (workflow_id: string, workflow_name: string, side: "saida" | "entrada", ports: string[], edges = 1): ISubworkflowNotice =>
  ({ workflow_id, workflow_name, node_id: "sub", side, ports, edges })

const salvoCom = (subworkflow_notices: ISubworkflowNotice[]) =>
  servico.updateWorkflowById.mockImplementation(async (id: string) => ({ data: { id_hash: id, subworkflow_notices }, error: null }))

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
  toasts.avisos = []
  rota.params = { id: "wf-1" }
  servico.getNodes.mockResolvedValue({ data: CATALOGO, error: null })
  servico.getCredentials.mockResolvedValue({ data: [], error: null })
  servico.listPinnedNodes.mockResolvedValue({ data: { pinned_nodes: [] }, error: null })
  servico.updateWorkflowById.mockImplementation(async (id: string) => ({ data: { id_hash: id }, error: null }))
  servico.createWorkflow.mockResolvedValue({ data: { id: "wf-novo", name: "Novo fluxo" }, error: null })
  useWorkflowCatalogStore.setState({ nodesAPI: CATALOGO, nodesFetchedAt: Date.now() })
})

describe("salvar um sub-fluxo que tirou portas em uso", () => {
  it("um único aviso âmbar, com quantos workflows, quais portas e quais workflows", async () => {
    salvoCom([
      aviso("pai-1", "Relatório mensal", "saida", ["faixa"], 2),
      aviso("pai-1", "Relatório mensal", "entrada", ["focos"], 0),
      aviso("pai-2", "Alertas", "saida", ["faixa"]),
    ])
    montar(workflow("wf-1", ["A", "B"]))
    await esperar()
    adicionarNo("C")
    await esperar()

    ctrlS()
    await esperar()

    expect(servico.updateWorkflowById).toHaveBeenCalledTimes(1)
    // Saved: the warning is a caveat, not a failure.
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("saved")
    expect(toasts.avisos).toHaveLength(1)
    const [{ titulo, descricao }] = toasts.avisos
    expect(titulo).toContain("2 workflows")
    for (const trecho of ["faixa", "focos", "Relatório mensal", "Alertas"]) expect(descricao).toContain(trecho)
    // Each port once, even when two callers use it.
    expect(descricao!.match(/faixa/g)).toHaveLength(1)
  })

  it("muitos workflows não viram uma lista sem fim", async () => {
    salvoCom(["A", "B", "C", "D", "E"].map((n, i) => aviso(`pai-${i}`, `Fluxo ${n}`, "saida", ["faixa"])))
    montar(workflow("wf-1", ["A", "B"]))
    await esperar()
    adicionarNo("C")
    await esperar()

    ctrlS()
    await esperar()

    const [{ titulo, descricao }] = toasts.avisos
    expect(titulo).toContain("5 workflows")
    expect(descricao).toContain("Fluxo A")
    expect(descricao).not.toContain("Fluxo E")
    expect(descricao).toContain("e mais 2")
  })

  it("save sem pais afetados não mostra aviso", async () => {
    montar(workflow("wf-1", ["A", "B"]))
    await esperar()
    adicionarNo("C")
    await esperar()

    ctrlS()
    await esperar()

    expect(servico.updateWorkflowById).toHaveBeenCalledTimes(1)
    expect(toasts.avisos).toEqual([])
  })

  it("o save silencioso do Executar também avisa", async () => {
    // Executar saves before dispatching: the person still has to know that the
    // save broke the workflows that call this one.
    salvoCom([aviso("pai-1", "Relatório mensal", "saida", ["faixa"])])
    const no = (id: string) =>
      ({ id, position: { x: 0, y: 0 }, data: { name: "Buffer", alias: id, type: "spatial", properties: {} } }) as INodeContext
    useWorkflowSaveStore.setState({ isSaving: false, saveStatus: "idle", workflowName: "Filho" })
    const { nodesReq, edgesReq } = buildGraphPayload([no("A")], [])
    useWorkflowSaveStore.getState().initSnapshot(nodesReq, edgesReq, "Filho")
    const { result } = renderHook(() => ({ salvar: useSaveWorkflow(), canvas: useStoreApi() }), { wrapper: ReactFlowProvider })
    act(() => { result.current.canvas.getState().setNodes([no("A"), no("B")]) })

    await act(async () => { await result.current.salvar.saveWorkflow({ silent: true }) })

    expect(servico.updateWorkflowById).toHaveBeenCalledTimes(1)
    expect(toasts.avisos.map(t => t.titulo)).toEqual([expect.stringContaining("1 workflow")])
  })
})
