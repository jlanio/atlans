/**
 * Undo/redo on the real editor (`workflow/index.tsx`), over a real React Flow.
 *
 * The history lost edges in the WIRING between the canvas and
 * `useCanvasHistory` — which is why these tests drive the editor itself and not
 * the hook:
 *
 * - a connection pulled between two handles went in through the `useEdgesState`
 *   setter, which emits no change, and only changes schedule a snapshot. Ctrl+Z
 *   took it away together with the step before it, and Ctrl+Y never brought it
 *   back;
 * - undo/redo restore through React Flow's `setNodes`/`setEdges`, which a
 *   controlled flow turns into add/remove/replace changes. 300 ms later those
 *   changes recorded the restored canvas as a NEW step, discarding the future:
 *   Ctrl+Z, a pause, and Ctrl+Y did nothing;
 * - an assistant proposal recorded only the canvas before it — the proposal
 *   itself never had a step, so Ctrl+Z skipped past the canvas the person had;
 * - restoring a version replaces the workflow, but the history (and the "saved"
 *   reference) stayed the pre-restore one.
 *
 * Only the panels around the canvas are stubbed (actions, run panel, drawer,
 * assistant, sub-workflow viewer): none of them takes part in the history, and
 * each one would bring its own services along. The connection uses React Flow's
 * click-to-connect — source handle, then target handle — which ends in the same
 * `onConnect` as a drag.
 */
import React, { useEffect } from "react"
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { render, act, cleanup, fireEvent, screen } from "@testing-library/react"
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
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { aplicarProposta } from "@/app/components/workflow/utils/aplicar-proposta"
import { buildNodes } from "@/app/components/workflow/utils/build-canvas"
import type { INodesAPI, INodesDefinition, IWorkflow } from "@/service/types"

// A single kind of node, with one output and no declared input: every card
// draws one anonymous handle on each side — all a connection needs.
const CATALOGO = [
  { name: "Buffer", alias: "Buffer", description: "", type: "spatial", properties: [], outputs: [{ name: "output" }] },
] as unknown as INodesAPI[]

const definicaoDoNo = (id: string, i: number): INodesDefinition =>
  ({ id, name: "Buffer", alias: id, type: "spatial", properties: {}, position: { x: i * 200, y: 0 } }) as INodesDefinition

/** A fresh object on every call — what a refetch (`reloadWorkflow`) hands the editor. */
const workflow = (ids: string[]): IWorkflow => ({
  id_hash: "wf-1",
  name: "Fluxo",
  flag_ative: true,
  description: "",
  version: "v1",
  priority: 0,
  created_by_id: "u",
  updated_by_id: "u",
  definition: { nodes: ids.map(definicaoDoNo), edges: [] },
})

/** Reads the canvas the way the editor's own code does: from the React Flow store. */
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
const ligacoes = () => canvas.getEdges().map(e => `${e.source}->${e.target}`).sort()

/** The drawer's path for a new node (`nodes-drawer.tsx`): `addNodes`. */
const adicionarNo = (id: string) =>
  act(() => { canvas.addNodes(buildNodes({ nodes: [definicaoDoNo(id, 3)], edges: [] }, CATALOGO)[0]) })

function conectar(container: HTMLElement, origem: string, destino: string) {
  fireEvent.click(container.querySelector(`.react-flow__handle.source[data-nodeid="${origem}"]`)!)
  fireEvent.click(container.querySelector(`.react-flow__handle.target[data-nodeid="${destino}"]`)!)
}

const teclar = (tecla: string) => fireEvent.keyDown(document.body, { key: tecla, ctrlKey: true })

const esperar = (ms: number) => act(async () => { await new Promise(r => setTimeout(r, ms)) })

/** Long enough for the snapshot the editor schedules 300 ms after an edit. */
const PASSO = 400

beforeAll(() => {
  // useIsMobile (the canvas becomes a viewer on a phone).
  window.matchMedia = vi.fn(() => ({ matches: false, addEventListener() {}, removeEventListener() {} })) as never
  // Click-to-connect looks for the handle under the pointer before falling back
  // to the clicked one; jsdom has no layout to answer with.
  document.elementFromPoint = () => null
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
  // The catalog already in memory: the graph hydrates as soon as the workflow arrives.
  useWorkflowCatalogStore.setState({ nodesAPI: CATALOGO, nodesFetchedAt: Date.now() })
})

describe("Ctrl+Z / Ctrl+Y no editor", () => {
  it("a ligação puxada entre dois nós é um passo: Ctrl+Z desfaz só ela e Ctrl+Y a devolve", async () => {
    const { container } = montar(workflow(["A", "B"]))
    await esperar(50)

    adicionarNo("C")
    await esperar(PASSO)
    conectar(container, "A", "B")
    await esperar(PASSO)
    conectar(container, "B", "C")
    await esperar(PASSO)
    expect(ligacoes()).toEqual(["A->B", "B->C"])

    teclar("z")
    await esperar(50)
    expect(nos()).toEqual(["A", "B", "C"])
    expect(ligacoes()).toEqual(["A->B"])

    teclar("y")
    await esperar(50)
    expect(nos()).toEqual(["A", "B", "C"])
    expect(ligacoes()).toEqual(["A->B", "B->C"])
  })

  it("o nó adicionado pela paleta (Ctrl+K) é um passo: Ctrl+Z desfaz só ele", async () => {
    const { container } = montar(workflow(["A", "B"]))
    await esperar(50)
    conectar(container, "A", "B")
    await esperar(PASSO)

    act(() => { window.dispatchEvent(new CustomEvent("command-add-node", { detail: { name: "Buffer" } })) })
    await esperar(PASSO)
    expect(nos()).toHaveLength(3)

    teclar("z")
    await esperar(50)
    expect(nos()).toEqual(["A", "B"])
    expect(ligacoes()).toEqual(["A->B"])
  })

  it("Ctrl+Z, uma pausa e Ctrl+Y: o refazer continua lá", async () => {
    montar(workflow(["A", "B"]))
    await esperar(50)

    adicionarNo("C")
    await esperar(PASSO)

    teclar("z")
    // Longer than the snapshot the restore ITSELF schedules — the one that used
    // to record the undone canvas as a new step and discard the redo.
    await esperar(PASSO)
    expect(nos()).toEqual(["A", "B"])
    expect(screen.getByTitle("Refazer (Ctrl+Y)")).toBeEnabled()

    teclar("y")
    await esperar(50)
    expect(nos()).toEqual(["A", "B", "C"])

    // And the next Ctrl+Z still goes one step back, instead of landing on a
    // duplicate of the canvas already on screen.
    await esperar(PASSO)
    teclar("z")
    await esperar(50)
    expect(nos()).toEqual(["A", "B"])
  })

  it("desfazer a proposta do assistente volta ao canvas de antes, com a ligação feita à mão; refazer a devolve", async () => {
    const { container } = montar(workflow(["A", "B"]))
    await esperar(50)

    conectar(container, "A", "B")
    await esperar(PASSO)

    // The proposal keeps A and B, adds D after B — and, like every proposal,
    // brings only the edges it declares.
    const proposta = aplicarProposta(
      { nodes: ["A", "B", "D"].map(definicaoDoNo), edges: [{ source: "B", target: "D", from_key: "output" }] },
      CATALOGO,
      canvas.getNodes() as INodeContext[],
    )
    act(() => { assistente.aplicar!(proposta) })
    await esperar(50)
    expect(nos()).toEqual(["A", "B", "D"])
    expect(ligacoes()).toEqual(["B->D"])

    teclar("z")
    await esperar(50)
    expect(nos()).toEqual(["A", "B"])
    expect(ligacoes()).toEqual(["A->B"])

    teclar("y")
    await esperar(50)
    expect(nos()).toEqual(["A", "B", "D"])
    expect(ligacoes()).toEqual(["B->D"])
  })
})

describe("restaurar uma versão", () => {
  it("o canvas restaurado é o novo ponto de partida: nada a desfazer e nada a salvar", async () => {
    const { trocarWorkflow } = montar(workflow(["A", "B"]))
    await esperar(50)
    // Closes the window in which a difference is credited to React Flow's
    // re-measuring (`autocorrigirSnapshot`): the edit below is the user's.
    act(() => { useWorkflowSaveStore.setState({ snapshotIniciadoEm: null }) })

    adicionarNo("C")
    await esperar(PASSO)
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("unsaved")
    expect(screen.getByTitle("Desfazer (Ctrl+Z)")).toBeEnabled()

    // What `reloadWorkflow` does after the restore: the same workflow, fetched
    // again — a new object, with the restored definition.
    trocarWorkflow(workflow(["A", "E"]))
    await esperar(PASSO)
    expect(nos()).toEqual(["A", "E"])
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("idle")
    expect(screen.getByTitle("Desfazer (Ctrl+Z)")).toBeDisabled()

    // Ctrl+Z does not bring back the graph the restore replaced.
    teclar("z")
    await esperar(50)
    expect(nos()).toEqual(["A", "E"])
  })

  it("a falha ao salvar de antes da restauração não fica no chip", async () => {
    const { trocarWorkflow } = montar(workflow(["A", "B"]))
    await esperar(50)
    act(() => { useWorkflowSaveStore.setState({ snapshotIniciadoEm: null }) })

    servico.updateWorkflowById.mockResolvedValue({ data: null, error: { message: "Servidor indisponível" } })
    adicionarNo("C")
    await esperar(PASSO)
    teclar("s")
    await esperar(50)
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("error")
    expect(screen.getByText("Falha ao salvar")).toBeInTheDocument()

    // The edit that failed to save is gone with the restore: what is on the
    // canvas now is the restored definition, saved by the restore itself.
    trocarWorkflow(workflow(["A", "E"]))
    await esperar(PASSO)
    expect(nos()).toEqual(["A", "E"])
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("idle")
    expect(useWorkflowSaveStore.getState().lastError).toBeNull()
    expect(screen.queryByText("Falha ao salvar")).not.toBeInTheDocument()
  })
})
