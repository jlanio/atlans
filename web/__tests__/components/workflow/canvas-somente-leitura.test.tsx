/**
 * On a phone the canvas is a viewer: no dragging, no connecting — and no
 * deleting. The read-only flag lived in a provider placed INSIDE <ReactFlow>,
 * and React Flow renders its children next to the nodes and edges, not around
 * them: from inside the cards and edges the canvas read "editable". The node
 * toolbar kept its trash can, the edge its delete button, and Save/Run
 * persisted what was deleted on a "read-only" canvas.
 *
 * Mounted on the real editor, over a real React Flow — the same setup as the
 * undo/redo tests.
 */
import React from "react"
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { render, act, cleanup, screen } from "@testing-library/react"
import { ReactFlowProvider } from "@xyflow/react"

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
import { FlowContextProvider } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
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

function montar(inicial: IWorkflow) {
  const tela = (w: IWorkflow) => (
    <ReactFlowProvider>
      <FlowContextProvider>
        <ReactFlowComponent workflow={w} />
      </FlowContextProvider>
    </ReactFlowProvider>
  )
  const r = render(tela(inicial))
  return { ...r, trocarWorkflow: (w: IWorkflow) => r.rerender(tela(w)) }
}

const esperar = (ms: number) => act(async () => { await new Promise(r => setTimeout(r, ms)) })

beforeAll(() => {
  // useIsMobile (the canvas becomes a viewer on a phone).
  window.matchMedia = vi.fn(() => ({ matches: false, addEventListener() {}, removeEventListener() {} })) as never
  // React Flow only draws an edge between MEASURED nodes; jsdom measures
  // nothing. Enough of a layout for the edges to be drawn — the edge's delete
  // button is what is checked.
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


function workflowLigado(): IWorkflow {
  const w = workflow(["A", "B"])
  return { ...w, definition: { ...w.definition, edges: [{ source: "A", target: "B" }] } }
}

describe("canvas somente leitura no celular", () => {
  // `useIsMobile` decides by the window width.
  const larguraDaJanela = (px: number) =>
    Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: px })

  it("no celular, nem o nó nem a aresta oferecem excluir", async () => {
    larguraDaJanela(390)
    try {
      const { container } = montar(workflowLigado())
      await esperar(100)
      // The edge IS drawn — only the edit actions are gone.
      expect(container.querySelectorAll(".react-flow__edge")).toHaveLength(1)
      expect(screen.queryAllByTitle("Fixar output")).toHaveLength(0)
      expect(document.querySelectorAll('[data-role="edge-delete"]')).toHaveLength(0)
    } finally {
      larguraDaJanela(1024)
    }
  })

  it("no computador, os dois continuam lá", async () => {
    larguraDaJanela(1024)
    const { container } = montar(workflowLigado())
    await esperar(100)
    expect(container.querySelectorAll(".react-flow__edge")).toHaveLength(1)
    expect(screen.queryAllByTitle("Fixar output").length).toBeGreaterThan(0)
    expect(document.querySelectorAll('[data-role="edge-delete"]')).toHaveLength(1)
  })
})
