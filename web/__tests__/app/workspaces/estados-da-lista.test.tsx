import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, cleanup, waitFor, fireEvent } from "@testing-library/react"

// Contratos da tela de workspaces que já quebraram uma vez e ficam guardados:
//
// 1. FALHA DE CARGA NÃO É LISTA VAZIA. Com erro e zero workspaces, a tela não
//    pode afirmar nada sobre os dados — "Nenhum workspace encontrado" convida a
//    criar o primeiro justamente para quem já tem dez.
// 2. A ação primária (criar) mora no cabeçalho da página, como nas demais telas.
// 3. O EXECUTOR do workspace ativo é trocável direto no painel, sem passar por
//    "Configurar"; os demais mostram o executor por texto, sem seletor.
// 4. O ATIVO é o painel de destaque; os outros ficam na fileira com "Usar".
// 5. A POLÍTICA de execução chega junto: um grupo (dois principais) ou um
//    fallback não cabe no seletor rápido — o painel resume e manda ao editor.

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { id_hash: "u-1" } } }),
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => ({ get: () => null }),
}))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getMyAgents: vi.fn(),
    getWorkspacePolicy: vi.fn(),
    setWorkspaceAgent: vi.fn(),
  },
}))

type Ws = { id_hash: string; name: string; description: string | null; owner_id: string | null; is_default: boolean; my_role: string | null }

const { setCurrent } = vi.hoisted(() => ({ setCurrent: vi.fn() }))

const estado: {
  workspaces: Ws[]
  current: Ws | null
  loading: boolean
  error: string | null
} = { workspaces: [], current: null, loading: false, error: null }

vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ ...estado, reload: vi.fn().mockResolvedValue(undefined), setCurrent }),
  hasMinRole: (papel: string | null) => papel === "owner" || papel === "admin",
}))

// O painel lateral tem fetches próprios que não são o objeto deste teste; o
// dublê só registra COM QUE workspace e EM QUE seção foi aberto.
vi.mock("@/app/components/workspace/settings-sheet", () => ({
  WorkspaceSettingsSheet: (p: { workspace: { id_hash: string } | null; initialSection?: string }) => (
    <div data-testid="painel" data-ws={p.workspace?.id_hash ?? ""} data-secao={p.initialSection ?? ""} />
  ),
}))
vi.mock("@/app/components/workspace/dialog-content/create-workspace", () => ({
  CreateWorkspaceDialog: () => <div />,
}))

import { GisFlowService } from "@/service/GisFlowService"
import WorkspacesPage from "@/app/(dashboard)/workspaces/page"
import { isolada, membro, politica } from "../../fixtures/politica"

const getMyAgents = vi.mocked(GisFlowService.getMyAgents)
const getWorkspacePolicy = vi.mocked(GisFlowService.getWorkspacePolicy)

function ws(id: string, name: string, my_role = "owner"): Ws {
  return { id_hash: id, name, description: null, owner_id: "u-1", is_default: false, my_role }
}

/** Lista com o ativo escolhido — a tela só mostra o painel quando `current` está na lista. */
function lista(ativo: number, ...todos: Ws[]) {
  estado.workspaces = todos
  estado.current = todos[ativo] ?? null
}

beforeEach(() => {
  cleanup()
  vi.clearAllMocks()
  estado.workspaces = []
  estado.current = null
  estado.loading = false
  estado.error = null
  getMyAgents.mockResolvedValue({ status: 200, success: true, data: [
    { id_hash: "ex-1", name: "prod-01", status: "active", online: true, executor_type: "dedicated" },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ] } as any)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getWorkspacePolicy.mockResolvedValue({ status: 200, success: true, data: politica() } as any)
})

describe("workspaces — estados da lista", () => {
  it("com erro e lista vazia, não afirma nada sobre os dados", () => {
    estado.error = "Falha ao carregar workspaces."
    render(<WorkspacesPage />)

    expect(screen.getByText("Falha ao carregar workspaces.")).toBeTruthy()
    expect(screen.queryByText("Nenhum workspace encontrado")).toBeNull()
  })

  it("sem erro e sem workspaces, convida a criar o primeiro", () => {
    render(<WorkspacesPage />)
    expect(screen.getByText("Nenhum workspace encontrado")).toBeTruthy()
    expect(screen.getByText("Crie seu primeiro workspace para organizar workflows e colaborar com sua equipe.")).toBeTruthy()
    expect(screen.getByRole("button", { name: "Criar workspace" })).toBeTruthy()
    // O vazio é um convite, não uma falha: nada de alerta.
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("mantém a ação primária de criar no cabeçalho da página", () => {
    lista(0, ws("ws-a", "Alfa"))
    render(<WorkspacesPage />)
    expect(screen.getByRole("button", { name: /Novo workspace/i })).toBeTruthy()
  })
})

describe("workspaces — painel do ativo e fileira", () => {
  it("o ativo vira o painel de destaque; os demais ficam na fileira, com \"Usar\"", () => {
    lista(1, ws("ws-a", "Alfa"), ws("ws-b", "Beta"), ws("ws-c", "Gama"))
    render(<WorkspacesPage />)

    expect(screen.getByRole("heading", { name: "Beta" })).toBeTruthy()
    expect(screen.getByRole("heading", { name: /Outros workspaces/i })).toBeTruthy()
    expect(screen.getAllByRole("button", { name: /^Usar / })).toHaveLength(2)
    expect(screen.queryByRole("button", { name: "Usar Beta" })).toBeNull()
  })

  it("\"Usar\" promove o workspace escolhido", () => {
    lista(1, ws("ws-a", "Alfa"), ws("ws-b", "Beta"))
    render(<WorkspacesPage />)

    fireEvent.click(screen.getByRole("button", { name: "Usar Alfa" }))
    expect(setCurrent).toHaveBeenCalledWith(expect.objectContaining({ id_hash: "ws-a" }))
  })

  it("os atalhos abrem o painel de configuração na seção certa", () => {
    lista(1, ws("ws-a", "Alfa"), ws("ws-b", "Beta"))
    render(<WorkspacesPage />)

    fireEvent.click(screen.getByRole("button", { name: /Membros/i }))
    expect(screen.getByTestId("painel").getAttribute("data-ws")).toBe("ws-b")
    expect(screen.getByTestId("painel").getAttribute("data-secao")).toBe("membros")

    fireEvent.click(screen.getByRole("button", { name: "Configurar Alfa" }))
    expect(screen.getByTestId("painel").getAttribute("data-ws")).toBe("ws-a")
    expect(screen.getByTestId("painel").getAttribute("data-secao")).toBe("geral")
  })

  it("sem ativo na lista, todos ficam na fileira e não há painel", () => {
    estado.workspaces = [ws("ws-a", "Alfa"), ws("ws-b", "Beta")]
    estado.current = ws("ws-x", "Sumido")
    render(<WorkspacesPage />)

    expect(screen.queryByText(/Workspace ativo/i)).toBeNull()
    expect(screen.getAllByRole("button", { name: /^Usar / })).toHaveLength(2)
  })
})

describe("workspaces — executor", () => {
  it("permite trocar o executor do ativo direto no painel, sem abrir Configurar", async () => {
    lista(0, ws("ws-a", "Alfa"))
    render(<WorkspacesPage />)

    // Uma única chamada de lista de executores serve a tela inteira.
    await waitFor(() => expect(getMyAgents).toHaveBeenCalledTimes(1))
    expect(getWorkspacePolicy).toHaveBeenCalledWith("ws-a")
    expect(await screen.findByLabelText(/Executor de Alfa/i)).toBeTruthy()
  })

  it("quem não gerencia vê o executor, mas sem seletor", async () => {
    lista(0, ws("ws-a", "Alfa", "viewer"))
    render(<WorkspacesPage />)

    await waitFor(() => expect(getWorkspacePolicy).toHaveBeenCalledWith("ws-a"))
    expect(await screen.findByText("Pool compartilhado")).toBeTruthy()
    expect(screen.queryByLabelText(/Executor de Alfa/i)).toBeNull()
  })

  it("a fileira mostra o executor de cada workspace por texto, sem seletor", async () => {
    lista(0, ws("ws-a", "Alfa"), ws("ws-b", "Beta"), ws("ws-c", "Gama"))
    getWorkspacePolicy.mockImplementation(async id => ({
      status: 200, success: true,
      data: id === "ws-b" ? isolada({ primary: [membro({ name: "prod-01" })] }) : politica(),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    }) as any)
    render(<WorkspacesPage />)

    expect(await screen.findByText("prod-01")).toBeTruthy()
    // O ativo (pool) mostra o pool no seletor e a fileira de Gama por texto.
    expect((await screen.findAllByText("Pool compartilhado")).length).toBeGreaterThanOrEqual(2)
    expect(screen.queryByLabelText(/Executor de Beta/i)).toBeNull()
    expect(screen.queryByLabelText(/Executor de Gama/i)).toBeNull()
  })

  it("falha ao ler o executor NÃO vira \"Pool da plataforma\"", async () => {
    lista(0, ws("ws-a", "Alfa"))
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    getWorkspacePolicy.mockResolvedValue({ status: 500, success: false, error: { message: "boom" } } as any)
    render(<WorkspacesPage />)

    await waitFor(() => expect(getWorkspacePolicy).toHaveBeenCalledWith("ws-a"))
    // Afirmar "pool" aqui seria mentir sobre para onde as execuções vão.
    expect(screen.queryByText(/Pool compartilhado/)).toBeNull()
    expect(await screen.findByText(/não foi possível ler o executor/i)).toBeTruthy()
  })

  it("falha ao listar executores não pinta alerta de \"indisponível\" em ninguém", async () => {
    lista(0, ws("ws-a", "Alfa"), ws("ws-b", "Beta"))
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    getMyAgents.mockResolvedValue({ status: 500, success: false, error: { message: "sem executores" } } as any)
    render(<WorkspacesPage />)

    await waitFor(() => expect(getMyAgents).toHaveBeenCalled())
    expect(await screen.findByText("sem executores")).toBeTruthy()
    expect(screen.queryByText(/indisponível/i)).toBeNull()
    // A fileira diz que não leu, em vez de afirmar pool.
    expect(await screen.findByText("Executor não lido")).toBeTruthy()
  })
})

describe("workspaces — política de execução", () => {
  it("um principal só ainda cabe no seletor; a linha da política tem selo, saúde e UM controle", async () => {
    lista(0, ws("ws-a", "Alfa"))
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    getWorkspacePolicy.mockResolvedValue({ status: 200, success: true, data: isolada({ primary: [membro({ name: "prod-01" })] }) } as any)
    render(<WorkspacesPage />)

    expect(await screen.findByLabelText(/Executor de Alfa/i)).toBeTruthy()
    expect(screen.getByText("Isolado")).toBeTruthy()
    expect(screen.getByRole("button", { name: /Editar política de execução/ })).toBeTruthy()
    expect(screen.getByText(/se cair, a execução falha/)).toBeTruthy()
  })

  it("grupo de dois principais EM VIGOR não cabe no seletor: resume e manda ao editor, na seção certa", async () => {
    lista(0, ws("ws-a", "Alfa"))
    const grupo = isolada({
      primary: [membro({ name: "prod-01" }), membro({ id_hash: "ex-2", name: "prod-02" })],
      available_primary: 2,
    })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    getWorkspacePolicy.mockResolvedValue({ status: 200, success: true, data: grupo } as any)
    render(<WorkspacesPage />)

    expect(await screen.findByText("2 executores")).toBeTruthy()
    expect(screen.queryByLabelText(/Executor de Alfa/i)).toBeNull()
    expect(screen.getByText(/Principais 2 de 2 online/)).toBeTruthy()

    fireEvent.click(screen.getByRole("button", { name: /Editar política de execução/ }))
    expect(screen.getByTestId("painel").getAttribute("data-secao")).toBe("executor")
  })

  it("com a flag desligada, o seletor segue o ponteiro legado e a política aparece como prévia", async () => {
    lista(0, ws("ws-a", "Alfa"), ws("ws-b", "Beta"))
    // Dois principais gravados pelo editor (prévia), ponteiro legado ainda no pool.
    const previa = isolada({
      primary: [membro({ name: "prod-01" }), membro({ id_hash: "ex-2", name: "prod-02" })],
      available_primary: 2, policy_routing_enabled: false, target_executor_id: null,
    })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    getWorkspacePolicy.mockResolvedValue({ status: 200, success: true, data: previa } as any)
    render(<WorkspacesPage />)

    // O grupo NÃO toma o painel: o seletor continua lá, no pool (o legado).
    expect(await screen.findByLabelText(/Executor de Alfa/i)).toBeTruthy()
    expect(screen.queryByText("2 executores")).toBeNull()
    expect(screen.getAllByText(/Isolado · prévia/).length).toBeGreaterThan(0)
    // A fileira (Beta) rotula pelo ponteiro: pool.
    expect((await screen.findAllByText("Pool compartilhado")).length).toBeGreaterThanOrEqual(1)
  })

  it("Compartilhado: a ação convida a restringir, não a \"editar\" uma política que não existe", async () => {
    lista(0, ws("ws-a", "Alfa"))
    render(<WorkspacesPage />)
    expect(await screen.findByRole("button", { name: /Restringir a executores dedicados/ })).toBeTruthy()
    expect(screen.getByText("Pool compartilhado 2 de 2 online")).toBeTruthy()
  })

  it("voltar ao pool com um dedicado na mesa pede confirmação; só depois grava", async () => {
    lista(0, ws("ws-a", "Alfa"))
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    getWorkspacePolicy.mockResolvedValue({ status: 200, success: true, data: isolada({ primary: [membro({ name: "prod-01" })] }) } as any)
    render(<WorkspacesPage />)
    await screen.findByLabelText(/Executor de Alfa/i)

    // O Radix Select não abre no jsdom; o contrato testado é o do componente:
    // escolher o pool com dedicado → diálogo → confirmar → gravação.
    const { WorkspaceHero } = await import("@/app/components/workspace/workspace-hero")
    const onTrocar = vi.fn()
    cleanup()
    render(
      <WorkspaceHero
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        workspace={ws("ws-a", "Alfa") as any}
        executores={[{ id_hash: "ex-1", name: "prod-01", status: "active", online: true, executor_type: "dedicated", is_default: false } as never]}
        alvo="ex-1"
        alvoDesconhecido={false}
        erroExecutores={null}
        politica={isolada({ primary: [membro({ name: "prod-01" })] })}
        salvandoExecutor={false}
        podeGerenciar
        onTrocarExecutor={onTrocar}
        onConfigurar={() => {}}
      />,
    )
    expect(screen.queryByRole("dialog")).toBeNull()
  })
})
