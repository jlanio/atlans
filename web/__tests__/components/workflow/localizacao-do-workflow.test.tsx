import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

// A trilha do editor afirma um fato sobre os dados: "este workflow está neste
// workspace". Ela fica ao lado do botão de executar, e é a única indicação de
// escopo na rota — o cabeçalho do dashboard não é renderizado em /workflow/*.
// Se ela mostrar o workspace ATIVO em vez do workspace do WORKFLOW, a afirmação
// pode ser falsa: /workflow/[id] busca por id, sem filtro de workspace, e o
// ativo é reidratado do localStorage (pode ter mudado em outra aba).

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
    // Ativo é o B; o workflow pertence ao A. Dizer "Cadastro Urbano" aqui seria
    // mentir sobre onde a execução vai acontecer.
    render(<WorkflowLocation workspaceId="ws-a" />)
    expect(screen.getByText("Bacia do Paranapanema")).toBeTruthy()
    expect(screen.queryByText("Cadastro Urbano")).toBeNull()
  })

  it("não afirma workspace nenhum enquanto a lista não resolveu", () => {
    // Lista vazia + id conhecido: o certo é ficar calado, não cair no ativo.
    lista = []
    render(<WorkflowLocation workspaceId="ws-a" />)
    expect(screen.queryByText("Cadastro Urbano")).toBeNull()
    expect(screen.getByText("imóveis")).toBeTruthy()
  })

  it("cai no workspace ativo quando ainda não há workflow (tela de criação)", () => {
    // Em /workflow/create é o ativo que `useSaveWorkflow` manda como
    // workspace_id ao criar — aí ele é a resposta certa.
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
    // Antes da busca responder, a trilha dizia "Sem nome" e o workspace ATIVO
    // — duas afirmações que podiam ser falsas por alguns segundos.
    nomeDoWorkflow = ""
    render(<WorkflowLocation carregando />)
    expect(screen.queryByText("Sem nome")).toBeNull()
    expect(screen.queryByText("Cadastro Urbano")).toBeNull()
    expect(document.querySelectorAll('[data-slot="skeleton"]').length).toBe(2)
    expect(screen.getByText("Carregando workflow.")).toBeTruthy()
  })
})
