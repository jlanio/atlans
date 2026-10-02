import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { IWorkflow, IWorkflowSchedule } from "@/service/types"
import type { IObservabilityMetrics, INowBlock } from "@/service/types"

// ── Dublês ───────────────────────────────────────────────────────────────────
// URL e roteador: o escopo vive na query (`?escopo=`) e as ações roteiam por
// push. `replace` é o que o toggle usa (mesma tela, sem empilhar histórico).
const url = vi.hoisted(() => ({ sp: new URLSearchParams(""), pathname: "/dashboard" }))
const roteador = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn(), prefetch: vi.fn() }))
vi.mock("next/navigation", () => ({
  useRouter: () => ({ ...roteador, back: vi.fn(), forward: vi.fn(), refresh: vi.fn() }),
  usePathname: () => url.pathname,
  useSearchParams: () => url.sp,
}))

// WorkspaceContext com dois workspaces (o toggle de escopo só existe com > 1).
const workspace = vi.hoisted(() => ({
  current: { id_hash: "ws-1", name: "Bacia" } as { id_hash: string; name: string } | null,
  setCurrent: vi.fn(),
  canEdit: true,
}))
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({
    ...workspace,
    workspaces: [
      { id_hash: "ws-1", name: "Bacia" },
      { id_hash: "ws-2", name: "Segundo WS" },
    ],
  }),
}))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getObservabilityMetrics: vi.fn(),
    getRunsByDay: vi.fn(),
    getObservabilityRuns: vi.fn(),
    getExecutorMetrics: vi.fn(),
    getWorkflows: vi.fn(),
  },
}))

import { GisFlowService } from "@/service/GisFlowService"
import DashboardView from "@/app/components/dashboard"

const svc = GisFlowService as unknown as Record<string, ReturnType<typeof vi.fn>>

const ok = <T,>(data: T) => ({ success: true, status: 200, data })
const falhou = (message = "boom") => ({ success: false, status: 500, error: { name: "AxiosError", message } })

// ── Massa ────────────────────────────────────────────────────────────────────
const daquiUmaHora = new Date(Date.now() + 3_600_000).toISOString()

function now(extra: Partial<INowBlock> = {}): INowBlock {
  return {
    running: 0, pending: 0, stuck_count: 0, stuck: [],
    executors: { online: 2, total: 2 }, queued_on_executors: 0, overdue_acks: 0, ...extra,
  }
}

function metrics(extra: Partial<IObservabilityMetrics> = {}): IObservabilityMetrics {
  return {
    total_workflows: 4, active_workflows: 8, total_runs: 120, failed_runs: 3, success_rate: 0.95,
    avg_duration_seconds: 12, runs_last_24h: 5, runs_last_7d: 40, runs_prev_7d: 30,
    success_rate_prev_7d: 0.9, by_status: { success: 100, failed: 3, running: 0, other: 0 },
    top_failing_workflows: [], now: now(), ...extra,
  }
}

function agendamento(extra: Partial<IWorkflowSchedule> = {}): IWorkflowSchedule {
  return { active: true, next_run_at: daquiUmaHora, last_run_at: null, strategy: "interval", interval: 6, unit: "hours", ...extra }
}

function wf(id: string, extra: Partial<IWorkflow> = {}): IWorkflow {
  return {
    id_hash: id, flag_ative: true, name: `Fluxo ${id}`, description: "", version: "1", priority: 0,
    definition: { nodes: [], edges: [] }, created_by_id: "u1", updated_by_id: "u1",
    workspace_id: "ws-1", has_schedule_trigger: true, schedule: agendamento(), ...extra,
  }
}

function respostasBoas() {
  svc.getObservabilityMetrics.mockResolvedValue(ok(metrics()))
  svc.getRunsByDay.mockResolvedValue(ok({ days: [{ day: "2026-09-01", total: 2, success: 2, failed: 0, running: 0, cancelled: 0 }] }))
  svc.getObservabilityRuns.mockResolvedValue(ok({
    total: 1, limit: 6, offset: 0,
    runs: [{ run_id: "run-abcdef12", status: "success", started_at: null, finished_at: null, duration_seconds: 42, error_message: null, retry_count: 0, agent_host: null, workflow_name: "Consolidação", workspace_name: "Bacia", trigger_source: "schedule" }],
  }))
  svc.getExecutorMetrics.mockResolvedValue(ok({ executores: [] }))
  svc.getWorkflows.mockResolvedValue(ok([wf("a")]))
}

beforeEach(() => {
  vi.resetAllMocks()
  respostasBoas()
  url.sp = new URLSearchParams("")
  workspace.current = { id_hash: "ws-1", name: "Bacia" }
})
afterEach(cleanup)

const ultimaReplace = () => roteador.replace.mock.calls.at(-1)![0] as string

// ── Testes ───────────────────────────────────────────────────────────────────
describe("Dashboard — página", () => {
  it("compõe as seções e chama as cinco fontes escopadas ao workspace ativo", async () => {
    render(<DashboardView />)
    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument()

    // Saúde (calma), atenção, próximas e resumo do período.
    await waitFor(() => expect(screen.getByText("Tudo tranquilo — nada pedindo atenção agora.")).toBeInTheDocument())
    expect(screen.getByRole("region", { name: "Precisa de atenção" })).toBeInTheDocument()
    expect(screen.getByRole("region", { name: "Próximas execuções" })).toBeInTheDocument()
    expect(screen.getByRole("region", { name: "Resumo do período · últimos 30 dias" })).toBeInTheDocument()

    // Subtítulo do escopo ativo, com a contagem de ativos das métricas.
    expect(screen.getByText("«Bacia» · 8 workflows ativos")).toBeInTheDocument()

    // As cinco fontes, por workspace, com a janela de 30 dias.
    expect(svc.getObservabilityMetrics).toHaveBeenCalledWith(30, false, { workspace_id: "ws-1" })
    expect(svc.getRunsByDay).toHaveBeenCalledWith(30, expect.objectContaining({ workspace_id: "ws-1" }))
    expect(svc.getObservabilityRuns).toHaveBeenCalledWith(expect.objectContaining({ limit: 6, workspace_id: "ws-1" }))
    expect(svc.getExecutorMetrics).toHaveBeenCalledWith(30, false, { workspace_id: "ws-1" })
    expect(svc.getWorkflows).toHaveBeenCalledWith("ws-1", { incluirDoAssistente: true })
  })

  it("o toggle troca o escopo e vai à URL (replace, sem empilhar)", async () => {
    render(<DashboardView />)
    await screen.findByRole("region", { name: "Precisa de atenção" })

    const grupo = screen.getByRole("group", { name: "Escopo do painel" })
    fireEvent.click(within(grupo).getByRole("button", { name: "Todos os workspaces" }))
    expect(ultimaReplace()).toBe("/dashboard?escopo=todos")
  })

  it("o seletor de período troca a janela e vai à URL (replace, sem empilhar)", async () => {
    render(<DashboardView />)
    await screen.findByRole("region", { name: "Precisa de atenção" })

    const grupo = screen.getByRole("group", { name: "Período" })
    fireEvent.click(within(grupo).getByRole("button", { name: "Últimos 7 dias" }))
    expect(ultimaReplace()).toBe("/dashboard?periodo=7")
  })

  it("período da URL escopa as fontes de janela e ecoa no resumo (?periodo=90)", async () => {
    url.sp = new URLSearchParams("periodo=90")
    render(<DashboardView />)
    await screen.findByRole("region", { name: "Precisa de atenção" })

    // As três fontes de janela na janela de 90 dias; execuções recentes (limit) e
    // workflows (futuras) não têm período.
    expect(svc.getObservabilityMetrics).toHaveBeenCalledWith(90, false, { workspace_id: "ws-1" })
    expect(svc.getRunsByDay).toHaveBeenCalledWith(90, expect.objectContaining({ workspace_id: "ws-1" }))
    expect(svc.getExecutorMetrics).toHaveBeenCalledWith(90, false, { workspace_id: "ws-1" })
    // O eyebrow do resumo ecoa a janela escolhida.
    expect(screen.getByRole("region", { name: "Resumo do período · últimos 90 dias" })).toBeInTheDocument()
  })

  it("escopo 'todos': fontes sem workspace_id e etiqueta do workspace nas próximas", async () => {
    // A próxima é de outro workspace, para a etiqueta ter o que mostrar.
    svc.getWorkflows.mockResolvedValue(ok([wf("a", { workspace_id: "ws-2" })]))
    url.sp = new URLSearchParams("escopo=todos")
    render(<DashboardView />)

    await waitFor(() => expect(svc.getWorkflows).toHaveBeenLastCalledWith(undefined, { incluirDoAssistente: true }))
    expect(svc.getObservabilityMetrics).toHaveBeenLastCalledWith(30, false, { workspace_id: undefined })

    // Espera o CONTEÚDO montar, não só as chamadas dispararem: a chamada de
    // serviço acontece durante a carga, mas as seções só renderizam quando o
    // `carregando` zera. Consultar de forma síncrona aqui corria com o skeleton
    // (verde local, vermelho sob a lentidão do CI). `findBy*` reintenta até pintar.
    const proximas = await screen.findByRole("region", { name: "Próximas execuções" })
    expect(await within(proximas).findByText("Segundo WS")).toBeInTheDocument()
  })

  it("saúde reflete o tom: presa deixa o veredito 'Precisa de você' e a presa roteia", async () => {
    svc.getObservabilityMetrics.mockResolvedValue(ok(metrics({
      now: now({ running: 1, stuck_count: 1, stuck: [{ run_id: "run-presa", workflow_hash: "a", workflow_name: "Fluxo a", agent_host: null, executor_name: null, started_at: null, elapsed_seconds: 1080, typical_seconds: 360 }] }),
    })))
    render(<DashboardView />)

    await waitFor(() => expect(screen.getByText(/Precisa de você:/)).toBeInTheDocument())
    fireEvent.click(screen.getByRole("button", { name: /Abrir a execução presa/ }))
    expect(roteador.push).toHaveBeenCalledWith("/observability/run/run-presa")
  })

  it("atenção roteia: uma falha repetida deep-linka ao Histórico filtrado", async () => {
    svc.getObservabilityMetrics.mockResolvedValue(ok(metrics({
      failed_runs: 6,
      top_failing_workflows: [{
        workflow_hash: "wf-fail", workflow_name: "Cadastro", failure_count: 6, failure_rate: 0.6,
        total_runs: 10, last_error: "Timeout", last_error_category: null, last_failed_at: new Date().toISOString(),
      } as unknown as IObservabilityMetrics["top_failing_workflows"][number]],
    })))
    render(<DashboardView />)

    const atencao = await screen.findByRole("region", { name: "Precisa de atenção" })
    fireEvent.click(within(atencao).getByRole("button", { name: /Ver falhas/ }))
    // Visão padrão (execuções) aplica workflow+status; `&workspace=` preserva o escopo ativo.
    expect(roteador.push).toHaveBeenCalledWith("/observability?workflow=wf-fail&status=failed&workspace=ws-1")
  })

  it("vazio de primeiro uso: sem workflows nem execuções, só o convite", async () => {
    svc.getObservabilityMetrics.mockResolvedValue(ok(metrics({ total_runs: 0, active_workflows: 0 })))
    svc.getObservabilityRuns.mockResolvedValue(ok({ total: 0, limit: 6, offset: 0, runs: [] }))
    svc.getWorkflows.mockResolvedValue(ok([]))
    render(<DashboardView />)

    expect(await screen.findByText("Nada rodou ainda")).toBeInTheDocument()
    expect(screen.queryByRole("region", { name: "Precisa de atenção" })).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: "Criar workflow" }))
    expect(roteador.push).toHaveBeenCalledWith("/workflow/create")
  })

  it("erro de espinha: métricas caem na 1ª carga e o bloco de erro toma a tela", async () => {
    svc.getObservabilityMetrics.mockResolvedValue(falhou("Sem permissão"))
    render(<DashboardView />)

    expect(await screen.findByText("Não foi possível carregar o painel")).toBeInTheDocument()
    expect(screen.getByText("Sem permissão")).toBeInTheDocument()
    expect(screen.queryByRole("region", { name: "Precisa de atenção" })).toBeNull()

    svc.getObservabilityMetrics.mockResolvedValue(ok(metrics()))
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }))
    expect(await screen.findByRole("region", { name: "Precisa de atenção" })).toBeInTheDocument()
  })
})
