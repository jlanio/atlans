import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { IWorkflow, IWorkflowGroup } from "@/service/types"
import type { IWorkflowMetricsRow } from "@/service/types"

// ── Dublês ───────────────────────────────────────────────────────────────────
const url = vi.hoisted(() => ({ sp: new URLSearchParams(""), pathname: "/projects" }))
const roteador = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn(), prefetch: vi.fn() }))
vi.mock("next/navigation", () => ({
  useRouter: () => ({ ...roteador, back: vi.fn(), forward: vi.fn(), refresh: vi.fn() }),
  usePathname: () => url.pathname,
  useSearchParams: () => url.sp,
}))

const workspace = vi.hoisted(() => ({
  current: { id_hash: "ws-1", name: "Cadastro" } as { id_hash: string; name: string } | null,
  loading: false, canEdit: true, canExecute: true, canManage: false,
}))
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ ...workspace, workspaces: workspace.current ? [workspace.current] : [] }),
  moveTargets: () => [],
}))

const runs = vi.hoisted(() => ({
  lista: [] as { runId: string; workflowHash: string; name: string; startedAt: string | null; triggerSource: string | null; executorName: string | null }[],
  refresh: vi.fn(),
}))
vi.mock("@/context/ActiveRunsContext", () => ({
  useActiveRuns: () => ({
    runningHashes: new Set(runs.lista.map(r => r.workflowHash)),
    runningRuns: runs.lista,
    runningCount: runs.lista.length,
    refresh: runs.refresh,
  }),
}))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getWorkflows: vi.fn(),
    getWorkflowGroups: vi.fn(),
    getWorkflowMetricsList: vi.fn(),
    updateStatusWorkflow: vi.fn(),
    executeWorkflow: vi.fn(),
    getWorkflowById: vi.fn(),
    duplicateWorkflowById: vi.fn(),
    deleteWorkflowById: vi.fn(),
    updateWorkflowById: vi.fn(),
    deleteWorkflowGroup: vi.fn(),
    updateWorkflowGroup: vi.fn(),
    reorderWorkflowGroups: vi.fn(),
    addWorkflowToGroup: vi.fn(),
    removeWorkflowFromGroup: vi.fn(),
    createWorkflowGroup: vi.fn(),
  },
}))
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), loading: vi.fn() }))
vi.mock("@/utils/createToast", () => ({ createToast: toast }))

import { GisFlowService } from "@/service/GisFlowService"
import ProjectActions from "@/app/components/projects"

const svc = GisFlowService as unknown as Record<string, ReturnType<typeof vi.fn>>

const ok = <T,>(data: T) => ({ success: true, status: 200, data })
const falha = (message = "boom") => ({ success: false, status: 500, error: { name: "AxiosError", message } })

// ── Massa ────────────────────────────────────────────────────────────────────
const agora = new Date()
const haHoras = (h: number) => new Date(agora.getTime() - h * 3_600_000).toISOString()
const haDias = (d: number) => new Date(agora.getTime() - d * 86_400_000).toISOString()

function wf(id: string, name: string, extra: Partial<IWorkflow> = {}): IWorkflow {
  return {
    id_hash: id, flag_ative: true, name, description: "", version: "1", priority: 0,
    definition: { nodes: [], edges: [] }, created_by_id: "u1", updated_by_id: "u1",
    workspace_id: "ws-1", group_id: null, created_at: haDias(40), updated_at: haDias(2),
    updated_by_username: "maria", ...extra,
  }
}

function grupo(id: string, name: string, extra: Partial<IWorkflowGroup> = {}): IWorkflowGroup {
  return { id: 1, id_hash: id, name, workflow_count: 0, active_count: 0, created_at: "", updated_at: "", ...extra }
}

const workflows = () => [
  wf("a", "Consolidação de outorgas", { group_id: "g1", description: "Une as outorgas da ANA e do IGAM" }),
  wf("b", "Cheias", { group_id: "g1", flag_ative: false }),
  wf("c", "Recorte por município", { is_subworkflow: true }),
  wf("d", "Mapa de risco", { has_schedule_trigger: true, schedule: { active: true, next_run_at: haHoras(-6), last_run_at: null, strategy: "cron", cron_expression: "0 6 * * *" } }),
]
const grupos = () => [
  grupo("g1", "Hidrologia", { description: "Rotinas diárias da bacia", workflow_count: 2, active_count: 1 }),
  grupo("g2", "Rascunhos"),
]

function metrica(hash: string, extra: Partial<IWorkflowMetricsRow> = {}): IWorkflowMetricsRow {
  return {
    workflow_hash: hash, workflow_name: hash, workspace_id: "ws-1", workspace_name: "Cadastro", active: true,
    total_runs: 61, success_runs: 58, failed_runs: 3, running_runs: 0, success_rate: 0.95, p50_seconds: 180,
    last_run_at: haHoras(0.5), last_status: "success", last_error: null, last_error_category: null, ...extra,
  }
}
const metricas = () => [
  metrica("a"),
  metrica("d", { last_status: "failed", last_error: "Timeout ao consultar o WFS", last_run_at: haHoras(1) }),
]

function respostasBoas() {
  svc.getWorkflows.mockResolvedValue(ok(workflows()))
  svc.getWorkflowGroups.mockResolvedValue(ok(grupos()))
  svc.getWorkflowMetricsList.mockResolvedValue(ok({ period_days: 30, workflows: metricas() }))
  svc.updateStatusWorkflow.mockResolvedValue(ok(undefined))
}

beforeEach(() => {
  vi.resetAllMocks()
  respostasBoas()
  url.sp = new URLSearchParams("")
  runs.lista = []
  workspace.canEdit = true
  workspace.canExecute = true
  window.localStorage.clear()
})
afterEach(cleanup)

const ultimaUrl = () => roteador.replace.mock.calls.at(-1)![0] as string

/** A linha de um workflow, pelo botão do nome. */
async function linha(nome: string, opcoes: { hidden?: boolean } = {}) {
  const botao = await screen.findByRole("button", { name: `Abrir ${nome} no editor`, ...opcoes })
  return botao.closest("[data-workflow]") as HTMLElement
}

function abrirMenu(nome: string) {
  fireEvent.keyDown(screen.getByRole("button", { name: `Mais ações de ${nome}` }), { key: "Enter" })
}

// ── Testes ───────────────────────────────────────────────────────────────────
describe("Projetos — página", () => {
  it("compõe cabeçalho com contagens, as seções dos grupos (vazio inclusive) e a seção Sem grupo", async () => {
    render(<ProjectActions />)
    expect(screen.getByRole("heading", { level: 1, name: "Projetos" })).toBeInTheDocument()

    const hidrologia = await screen.findByRole("region", { name: "Hidrologia" })
    expect(hidrologia).toHaveTextContent("2 workflows · 1 ativo")
    expect(hidrologia).toHaveTextContent("Rotinas diárias da bacia")
    expect(within(hidrologia).getByRole("button", { name: "Abrir Consolidação de outorgas no editor" })).toBeInTheDocument()
    expect(within(hidrologia).getByRole("button", { name: "Abrir Cheias no editor" })).toBeInTheDocument()

    const rascunhos = screen.getByRole("region", { name: "Rascunhos" })
    expect(rascunhos).toHaveTextContent("vazio")
    expect(rascunhos).toHaveTextContent("Nenhum workflow aqui.")

    const semGrupo = screen.getByRole("region", { name: "Sem grupo" })
    expect(semGrupo).toHaveTextContent("2 workflows · 2 ativos")
    expect(within(semGrupo).getByRole("button", { name: "Abrir Recorte por município no editor" })).toBeInTheDocument()
    expect(within(semGrupo).getByRole("button", { name: "Abrir Mapa de risco no editor" })).toBeInTheDocument()

    // "Sem grupo" vem ANTES dos grupos.
    expect(semGrupo.compareDocumentPosition(hidrologia) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()

    // Subtítulo sobre a lista inteira; "como anda" veio das métricas.
    expect(screen.getByText("4 workflows em 2 grupos · 3 ativos · 1 agendado")).toBeInTheDocument()
    expect(await linha("Consolidação de outorgas")).toHaveTextContent("Concluída há 30 min")
    expect(await linha("Mapa de risco")).toHaveTextContent("Timeout ao consultar o WFS")

    // As três chamadas, por workspace, com a janela de 30 dias.
    expect(svc.getWorkflows).toHaveBeenCalledWith("ws-1", { incluirDoAssistente: true })
    expect(svc.getWorkflowGroups).toHaveBeenCalledWith("ws-1")
    expect(svc.getWorkflowMetricsList).toHaveBeenCalledWith(30, false, { workspace_id: "ws-1" })
  })

  it("chip filtra e vai para a URL; com o filtro na URL, só as linhas que casam e os grupos com linha", async () => {
    const { unmount } = render(<ProjectActions />)
    await screen.findByRole("region", { name: "Hidrologia" })
    const chips = screen.getByRole("group", { name: "Filtros" })
    expect(within(chips).getByRole("button", { name: /^Todos/ })).toHaveTextContent("4")
    const inativos = within(chips).getByRole("button", { name: /^Inativos/ })
    expect(inativos).toHaveTextContent("1")
    fireEvent.click(inativos)
    expect(roteador.replace).toHaveBeenCalledWith("/projects?filtro=inativos", { scroll: false })
    unmount()

    url.sp = new URLSearchParams("filtro=inativos")
    render(<ProjectActions />)
    const hidrologia = await screen.findByRole("region", { name: "Hidrologia" })
    await waitFor(() => expect(hidrologia).toHaveTextContent("2 workflows · 1 ativo · 1 com este filtro"))
    expect(within(hidrologia).getByRole("button", { name: "Abrir Cheias no editor" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Abrir Consolidação de outorgas no editor" })).toBeNull()
    expect(screen.queryByRole("region", { name: "Rascunhos" })).toBeNull()
    expect(screen.queryByRole("region", { name: "Sem grupo" })).toBeNull()
    expect(within(screen.getByRole("group", { name: "Filtros" })).getByRole("button", { name: /^Inativos/ })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByRole("button", { name: "Limpar filtros" })).toBeInTheDocument()
  })

  it("busca pelo nome do grupo mostra todos os workflows dele", async () => {
    url.sp = new URLSearchParams("q=hidrologia")
    render(<ProjectActions />)
    const hidrologia = await screen.findByRole("region", { name: "Hidrologia" })
    await waitFor(() => expect(screen.queryByRole("button", { name: "Abrir Mapa de risco no editor" })).toBeNull())
    expect(within(hidrologia).getByRole("button", { name: "Abrir Consolidação de outorgas no editor" })).toBeInTheDocument()
    expect(within(hidrologia).getByRole("button", { name: "Abrir Cheias no editor" })).toBeInTheDocument()
    expect(screen.queryByRole("region", { name: "Sem grupo" })).toBeNull()
    expect(screen.getByRole("searchbox", { name: "Buscar workflow ou grupo" })).toHaveValue("hidrologia")
  })

  it("busca sem resultado: vazio com o termo e Limpar filtros", async () => {
    url.sp = new URLSearchParams("q=inexistente")
    render(<ProjectActions />)
    expect(await screen.findByText("Nenhum workflow com «inexistente»")).toBeInTheDocument()
    expect(screen.queryByRole("region", { name: "Hidrologia" })).toBeNull()
    fireEvent.click(screen.getAllByRole("button", { name: "Limpar filtros" })[0])
    expect(ultimaUrl()).toBe("/projects")
  })

  it("Desativar… pede confirmação, troca otimista e reverte quando a API falha", async () => {
    let responder: (v: unknown) => void = () => {}
    svc.updateStatusWorkflow.mockImplementation(() => new Promise(r => { responder = r }))
    render(<ProjectActions />)
    await linha("Consolidação de outorgas")

    abrirMenu("Consolidação de outorgas")
    fireEvent.click(screen.getByRole("menuitem", { name: "Desativar…" }))
    // Nada muda antes da confirmação.
    expect(svc.updateStatusWorkflow).not.toHaveBeenCalled()
    const dialogo = screen.getByRole("dialog", { name: "Desativar «Consolidação de outorgas»?" })
    expect(dialogo).toHaveTextContent("Ele some dos gatilhos e não pode ser executado até você ativar de novo.")
    fireEvent.click(within(dialogo).getByRole("button", { name: "Desativar" }))

    expect(svc.updateStatusWorkflow).toHaveBeenCalledWith("a", { flag_ative: false })
    // Otimista: a linha já aparece inativa enquanto o servidor responde.
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())
    expect(await linha("Consolidação de outorgas")).toHaveTextContent("Inativo")

    responder(falha("sem permissão"))
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Erro ao atualizar status do workflow.", "sem permissão"))
    expect(await linha("Consolidação de outorgas")).not.toHaveTextContent("Inativo")
    expect(toast.success).not.toHaveBeenCalled()
  })

  it("Ativar é direto: sem diálogo, PUT e toast com o nome", async () => {
    render(<ProjectActions />)
    await linha("Cheias")
    fireEvent.click(screen.getByRole("button", { name: "Ativar Cheias" }))
    expect(screen.queryByRole("dialog")).toBeNull()
    expect(svc.updateStatusWorkflow).toHaveBeenCalledWith("b", { flag_ative: true })
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("«Cheias» ativado"))
    expect(await linha("Cheias")).not.toHaveTextContent("Inativo")
    // Agora que está ativa, o lugar do Ativar é o Executar.
    expect(screen.getByRole("button", { name: "Executar Cheias agora" })).toBeInTheDocument()
  })

  it("vazio de primeiro uso: sem workflows e sem grupos, o convite no lugar da lista e da barra", async () => {
    svc.getWorkflows.mockResolvedValue(ok([]))
    svc.getWorkflowGroups.mockResolvedValue(ok([]))
    svc.getWorkflowMetricsList.mockResolvedValue(ok({ period_days: 30, workflows: [] }))
    render(<ProjectActions />)
    expect(await screen.findByText("Comece pelo primeiro workflow")).toBeInTheDocument()
    expect(screen.getByText("Nenhum workflow ainda")).toBeInTheDocument()
    expect(screen.queryByRole("searchbox")).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: "Criar o primeiro workflow" }))
    expect(roteador.push).toHaveBeenCalledWith("./workflow/create")
  })

  it("métricas indisponíveis: aviso discreto e a lista completa, sem dados de execução", async () => {
    svc.getWorkflowMetricsList.mockResolvedValue(falha())
    render(<ProjectActions />)
    // Por texto, não por role="status": o skeleton de carregamento também é
    // uma live region e apareceria primeiro numa busca genérica por role.
    const aviso = (await screen.findByText("Sem dados de execução agora — a lista continua completa.")).closest<HTMLElement>('[role="status"]')!
    expect(aviso).not.toBeNull()
    expect(await linha("Consolidação de outorgas")).toHaveTextContent("Sem dados de execução")
    expect(await linha("Mapa de risco")).toHaveTextContent("Sem dados de execução")

    fireEvent.click(within(aviso).getByRole("button", { name: "Tentar de novo" }))
    await waitFor(() => expect(svc.getWorkflowMetricsList).toHaveBeenLastCalledWith(30, true, { workspace_id: "ws-1" }))
  })

  it("run vivo: a linha vira 'Em execução' e o botão leva à execução", async () => {
    runs.lista = [{ runId: "run-9", workflowHash: "a", name: "Consolidação de outorgas", startedAt: haHoras(0.1), triggerSource: "schedule", executorName: "geo-01" }]
    render(<ProjectActions />)
    const l = await linha("Consolidação de outorgas")
    expect(l).toHaveTextContent("Em execução há 6 min")
    fireEvent.click(within(l).getByRole("button", { name: "Ver execução de Consolidação de outorgas" }))
    expect(roteador.push).toHaveBeenCalledWith("/observability?execucao=run-9")
    expect(within(screen.getByRole("group", { name: "Filtros" })).getByRole("button", { name: /^Em execução/ })).toHaveTextContent("1")
  })

  it("erro na listagem: bloco de erro com Tentar de novo, anunciado uma vez só (sem toast)", async () => {
    svc.getWorkflows.mockResolvedValue(falha("API fora do ar"))
    render(<ProjectActions />)
    expect(await screen.findByText("Não foi possível carregar os projetos")).toBeInTheDocument()
    expect(screen.getByText("API fora do ar")).toBeInTheDocument()
    // O cartão é o anúncio (role="alert"); o toast leria a mesma falha de novo.
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível carregar os projetos")
    expect(toast.error).not.toHaveBeenCalled()
    svc.getWorkflows.mockResolvedValue(ok(workflows()))
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }))
    expect(await screen.findByRole("region", { name: "Hidrologia" })).toBeInTheDocument()
  })

  it("viewer: sem Executar, sem Ativar, sem menu de grupo e sem Novo grupo", async () => {
    workspace.canEdit = false
    workspace.canExecute = false
    render(<ProjectActions />)
    await linha("Cheias")
    expect(screen.queryByRole("button", { name: /^Executar/ })).toBeNull()
    expect(screen.queryByRole("button", { name: /^Ativar/ })).toBeNull()
    expect(screen.queryByRole("button", { name: /^Ações do grupo/ })).toBeNull()
    expect(screen.queryByRole("button", { name: "Novo grupo" })).toBeNull()
    expect(screen.queryByRole("button", { name: "Criar workflow" })).toBeNull()
  })
})
