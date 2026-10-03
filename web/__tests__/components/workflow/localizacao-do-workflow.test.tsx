import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

// The editor's breadcrumb states a fact about the data: "this workflow is in
// this workspace". It sits next to the run button, and it's the only indication
// of scope on the route — the dashboard header isn't rendered on /workflow/*.
// If it shows the ACTIVE workspace instead of the WORKFLOW's workspace, the
// statement can be false: /workflow/[id] fetches by id, with no workspace filter,
// and the active one is rehydrated from localStorage (it may have changed in
// another tab).

let nomeDoWorkflow = "imóveis"
vi.mock("@/app/stores/workflowSaveStore", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useWorkflowSaveStore: (seletor: any) => seletor({ workflowName: nomeDoWorkflow }),
}))

const WS_A = { id_hash: "ws-a", name: "Bacia do Paranapanema", description: null, owner_id: "u-1", is_default: false, my_role: "owner" }
const WS_B = { id_hash: "ws-b", name: "Cadastro Urbano", description: null, owner_id: "u-9", is_default: false, my_role: "admin" }

let ativo: typeof WS_A | null = WS_B
let lista: (typeof WS_A)[] = [WS_A, WS_B]
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ workspaces: lista, current: ativo }),
}))

import WorkflowLocation from "@/app/components/workflow/workflow-location"

beforeEach(() => {
  cleanup()
  nomeDoWorkflow = "imóveis"
  ativo = WS_B
  lista = [WS_A, WS_B]
})

describe("trilha do editor de workflow", () => {
  it("mostra o workspace do workflow aberto, não o workspace ativo", () => {
    // The active one is B; the workflow belongs to A. Saying "Cadastro Urbano"
    // here would be lying about where the run will happen.
    render(<WorkflowLocation workspaceId="ws-a" />)
    expect(screen.getByText("Bacia do Paranapanema")).toBeTruthy()
    expect(screen.queryByText("Cadastro Urbano")).toBeNull()
  })

  it("não afirma workspace nenhum enquanto a lista não resolveu", () => {
    // Empty list + known id: the right thing is to stay silent, not fall back to the active one.
    lista = []
    render(<WorkflowLocation workspaceId="ws-a" />)
    expect(screen.queryByText("Cadastro Urbano")).toBeNull()
    expect(screen.getByText("imóveis")).toBeTruthy()
  })

  it("cai no workspace ativo quando ainda não há workflow (tela de criação)", () => {
    // On /workflow/create it's the active one that `useSaveWorkflow` sends as
    // workspace_id on creation — there it's the right answer.
    nomeDoWorkflow = ""
    render(<WorkflowLocation />)
    expect(screen.getByText("Cadastro Urbano")).toBeTruthy()
    expect(screen.getByText("Sem nome")).toBeTruthy()
  })

  it("mostra o nome do workflow como degrau final", () => {
    render(<WorkflowLocation workspaceId="ws-a" />)
    expect(screen.getByText("imóveis")).toBeTruthy()
  })

  it("enquanto o workflow não chega, mostra esqueletos e não afirma nada", () => {
    // Before the fetch answered, the breadcrumb said "Sem nome" (untitled) and the
    // ACTIVE workspace — two statements that could be false for a few seconds.
    nomeDoWorkflow = ""
    render(<WorkflowLocation carregando />)
    expect(screen.queryByText("Sem nome")).toBeNull()
    expect(screen.queryByText("Cadastro Urbano")).toBeNull()
    expect(document.querySelectorAll('[data-slot="skeleton"]').length).toBe(2)
    expect(screen.getByText("Carregando workflow.")).toBeTruthy()
  })
})
