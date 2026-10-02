import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { IExecutorMetrics, IObservabilityMetrics, IRunSummary, IWorkflowMetricsRow } from "@/service/types"

// ── Dublês ───────────────────────────────────────────────────────────────────
const sessao = { role: "user" }
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { access_token: "t", role: sessao.role } }, status: "authenticated" }),
}))

const url = { sp: new URLSearchParams(""), pathname: "/observability" }
const replace = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  usePathname: () => url.pathname,
  useSearchParams: () => url.sp,
}))

const workspaces = { lista: [{ id_hash: "ws-1", name: "Cadastro" }] }
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ workspaces: workspaces.lista, current: workspaces.lista[0] }),
}))

// O Recharts não pinta em jsdom (ResponsiveContainer mede 0×0).
vi.mock("next/dynamic", () => ({
  default: () => function BarrasDubladas({ dias }: { dias: unknown[] }) {
    return <div data-testid="barras">{dias.length} dias</div>
  },
}))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getObservabilityMetrics: vi.fn(),
    getRunsByDay: vi.fn(),
    getExecutorMetrics: vi.fn(),
    getWorkflowMetricsList: vi.fn(),
    getObservabilityRuns: vi.fn(),
    getPendingAcks: vi.fn(),
    getRunDetail: vi.fn(),
    getRunEvents: vi.fn(),
    retryRun: vi.fn(),
    setAdminWorkflowStatus: vi.fn(),
  },
}))
vi.mock("@/utils/createToast", () => ({
  createToast: { success: vi.fn(), error: vi.fn(), info: vi.fn(), loading: vi.fn() },
}))

import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import HistoricoPage from "@/app/(dashboard)/observability/page"

const svc = GisFlowService as unknown as Record<string, ReturnType<typeof vi.fn>>
const toast = createToast as unknown as { success: ReturnType<typeof vi.fn>; error: ReturnType<typeof vi.fn> }

const ok = <T,>(data: T) => ({ success: true, status: 200, data })
const falha = () => ({ success: false, status: 500, error: { name: "AxiosError", message: "boom" } })

function metricas(extra: Partial<IObservabilityMetrics> = {}): IObservabilityMetrics {
  return {
    period_days: 30,
    total_workflows: 4, active_workflows: 3,
    total_runs: 1284, failed_runs: 36, success_rate: 0.964, avg_duration_seconds: 54,
    runs_last_24h: 10, runs_last_7d: 300, runs_prev_7d: 280, success_rate_prev_7d: 0.97,
    by_status: { success: 1235, failed: 36, running: 3, pending: 1, cancelled: 3, other: 6 },
    top_failing_workflows: [{
      workflow_hash: "wf-2", workflow_name: "Integração SICAR", failure_count: 28, total_runs: 61,
      failure_rate: 0.46, last_error: "Timeout ao consultar o WFS", last_error_category: "timeout",
      last_failed_at: new Date(Date.now() - 3 * 3_600_000).toISOString(),
    }],
    success_runs: 1235, cancelled_runs: 3, running_runs: 3, pending_runs: 1,
    prev_period: { total_runs: 1147, success_runs: 1118, failed_runs: 29, success_rate: 0.975, p50_seconds: 38 },
    duration: { p50_seconds: 42, p95_seconds: 190 },
    now: {
      running: 3, pending: 1, stuck_count: 1,
      stuck: [{ run_id: "run-presa", workflow_hash: "wf-1", workflow_name: "Cadastro rural", agent_host: "executor:geo-02", executor_name: "geo-02", started_at: null, elapsed_seconds: 8040, typical_seconds: 360 }],
      executors: { online: 4, total: 5 }, queued_on_executors: 12, overdue_acks: null,
    },
    ...extra,
  } as IObservabilityMetrics
}

function run(extra: Partial<IRunSummary> = {}): IRunSummary {
  return {
    run_id: "run-1", workflow_hash: "wf-1", status: "failed",
    started_at: new Date(Date.now() - 5 * 60_000).toISOString(), finished_at: null, duration_seconds: 31,
    error_message: "Timeout ao consultar o WFS", retry_count: 0, agent_host: "executor:geo-03", executor_name: "geo-03",
    workflow_name: "Integração SICAR", workspace_name: "Cadastro", trigger_source: "schedule", error_category: "timeout",
    ...extra,
  }
}

const workflowRow: IWorkflowMetricsRow = {
  workflow_hash: "wf-2", workflow_name: "Integração SICAR", workspace_id: "ws-1", workspace_name: "Cadastro",
  active: true, total_runs: 61, success_runs: 33, failed_runs: 28, running_runs: 0, success_rate: 0.54,
  p50_seconds: 170, last_run_at: null, last_status: "failed", last_error: null, last_error_category: null,
}
const executor: IExecutorMetrics = {
  agent_host: "executor:geo-02", display_name: "geo-02", total_runs: 400, success_runs: 390, failed_runs: 10,
  success_rate: 0.975, avg_duration_seconds: 40, last_run_at: null, online: true,
  capacity: { running: 2, queued: 0, max_concurrent: 4, max_queue: 20 }, p50_seconds: 38,
}

function respostasBoas() {
  svc.getObservabilityMetrics.mockResolvedValue(ok(metricas()))
  svc.getRunsByDay.mockResolvedValue(ok({ days: [
    { day: "2026-09-05", total: 40, success: 38, failed: 2, running: 0, cancelled: 0 },
    { day: "2026-09-06", total: 70, success: 65, failed: 4, running: 1, cancelled: 0 },
  ] }))
  svc.getExecutorMetrics.mockResolvedValue(ok({ executores: [executor] }))
  svc.getWorkflowMetricsList.mockResolvedValue(ok({ period_days: 30, workflows: [workflowRow] }))
  svc.getObservabilityRuns.mockResolvedValue(ok({ runs: [run()], total: 1, has_more: false }))
  svc.getPendingAcks.mockResolvedValue(ok({ items: [], threshold_overdue_seconds: 15 }))
  svc.getRunDetail.mockResolvedValue(ok({
    ...run(), node_stats: {}, typical_seconds: 170, workflow_hash: "wf-1",
  }))
  svc.setAdminWorkflowStatus.mockResolvedValue(ok({ id_hash: "wf-2", flag_ative: false }))
}

beforeEach(() => {
  vi.resetAllMocks()
  respostasBoas()
  url.sp = new URLSearchParams("")
  sessao.role = "user"
  workspaces.lista = [{ id_hash: "ws-1", name: "Cadastro" }]
})
afterEach(cleanup)

const ultimaUrl = () => replace.mock.calls.at(-1)![0] as string

// ── Testes ───────────────────────────────────────────────────────────────────
describe("Histórico — página", () => {
  it("compõe cabeçalho, faixa Agora, indicadores, gráfico, atenção, abas e tabela", async () => {
    render(<HistoricoPage />)
    expect(screen.getByRole("heading", { level: 1, name: "Histórico" })).toBeInTheDocument()
    expect(screen.getByText(/comparado com os 30 dias anteriores/)).toBeInTheDocument()

    // Faixa Agora com o que veio de `now`.
    const faixa = await screen.findByLabelText("Agora")
    await waitFor(() => expect(faixa).toHaveTextContent("3 em andamento"))
    expect(faixa).toHaveTextContent("1 na fila")
    expect(faixa).toHaveTextContent("1 presa há 2 h 14 min")
    expect(faixa).toHaveTextContent("Executores 4 de 5 online")

    // Indicadores com número e comparação.
    expect(screen.getByRole("group", { name: /^Execuções: 1\.284/ })).toBeInTheDocument()
    expect(screen.getByRole("group", { name: /^Taxa de sucesso: 96,4%/ })).toBeInTheDocument()
    expect(screen.getByRole("group", { name: /^Duração típica: 42 s/ })).toBeInTheDocument()
    expect(screen.getByRole("group", { name: /^Falhas: 36/ })).toBeInTheDocument()

    // Gráfico e atenção.
    expect(screen.getByRole("heading", { name: "Execuções por dia" })).toBeInTheDocument()
    expect(await screen.findByTestId("barras")).toHaveTextContent("2 dias")
    const atencao = screen.getByRole("region", { name: "Precisa de atenção" })
    await waitFor(() => expect(within(atencao).getAllByRole("button").length).toBeGreaterThan(0))
    expect(atencao).toHaveTextContent("Cadastro rural")
    expect(atencao).toHaveTextContent("Integração SICAR")

    // Abas (sem Confirmações para quem não é admin) e a tabela.
    expect(screen.getByRole("tab", { name: /Execuções/ })).toHaveAttribute("aria-selected", "true")
    expect(screen.queryByRole("tab", { name: /Confirmações/ })).not.toBeInTheDocument()
    expect(svc.getPendingAcks).not.toHaveBeenCalled()
    const painel = screen.getByRole("tabpanel")
    expect(painel).toHaveAttribute("id", "visao-painel")
    expect(painel).toHaveAttribute("aria-labelledby", "visao-aba-execucoes")
    expect((await within(painel).findByRole("button", { name: "Abrir execução de Integração SICAR" })).closest("tr")).toHaveTextContent("Falhou")
    expect(painel).toHaveTextContent("Mostrando 1 de 1")

    // As quatro chamadas do topo e a lista, sem filtro de workspace.
    expect(svc.getObservabilityMetrics).toHaveBeenCalledWith(30, false, { workspace_id: undefined, workflow_id: undefined })
    expect(svc.getObservabilityRuns).toHaveBeenCalledTimes(1)
    expect(svc.getObservabilityRuns.mock.calls[0][0]).toMatchObject({ limit: 20, offset: 0, with_total: true })
  })

  it("trocar o período escreve a URL sem scroll", async () => {
    render(<HistoricoPage />)
    await screen.findByLabelText("Agora")
    fireEvent.click(screen.getByRole("button", { name: "Últimos 7 dias" }))
    expect(replace).toHaveBeenCalledWith("/observability?periodo=7", { scroll: false })
  })

  it("?execucao= abre o painel da execução e fechá-lo limpa a URL", async () => {
    url.sp = new URLSearchParams("execucao=run-1")
    render(<HistoricoPage />)
    await waitFor(() => expect(svc.getRunDetail).toHaveBeenCalledWith("run-1"))
    const sheet = await screen.findByRole("dialog")
    await waitFor(() => expect(sheet).toHaveTextContent("Integração SICAR"))
    // A linha aberta fica marcada (o Sheet põe `aria-hidden` no resto da
    // página, daí `hidden: true` para enxergar a tabela atrás dele).
    const linha = await screen.findByRole("button", { name: "Abrir execução de Integração SICAR", hidden: true })
    expect(linha).toHaveAttribute("aria-current", "true")

    fireEvent.keyDown(sheet, { key: "Escape" })
    await waitFor(() => expect(ultimaUrl()).toBe("/observability"))
  })

  it("clicar numa linha abre a execução pela URL", async () => {
    render(<HistoricoPage />)
    fireEvent.click(await screen.findByRole("button", { name: "Abrir execução de Integração SICAR" }))
    expect(ultimaUrl()).toBe("/observability?execucao=run-1")
  })

  it("visão workflows: lista as linhas; clicar leva às execuções filtradas", async () => {
    url.sp = new URLSearchParams("visao=workflows")
    render(<HistoricoPage />)
    expect(screen.getByRole("tab", { name: /Por workflow/ })).toHaveAttribute("aria-selected", "true")
    const painel = screen.getByRole("tabpanel")
    expect(painel).toHaveAttribute("aria-labelledby", "visao-aba-workflows")
    fireEvent.click(await within(painel).findByRole("button", { name: "Ver execuções de Integração SICAR" }))
    expect(ultimaUrl()).toBe("/observability?workflow=wf-2")
    // Sem filtros nem tabela nesta visão.
    expect(within(painel).queryByRole("searchbox")).not.toBeInTheDocument()
  })

  it("trocar de visão pela aba fecha a execução aberta", async () => {
    url.sp = new URLSearchParams("execucao=run-1")
    render(<HistoricoPage />)
    await screen.findByRole("dialog")
    fireEvent.click(screen.getByRole("tab", { name: /Por executor/, hidden: true }))
    expect(ultimaUrl()).toBe("/observability?visao=executores")
  })

  it("ações de atenção: presa abre a execução; falhas repetidas filtram por workflow com status=failed", async () => {
    render(<HistoricoPage />)
    const atencao = screen.getByRole("region", { name: "Precisa de atenção" })
    // Cada item tem a ação principal E um "dispensar" (que também nomeia o
    // workflow); os regexes miram a AÇÃO (verbo/estado no nome), não o × de
    // dispensar ("Dispensar o alerta de …").
    const presa = await within(atencao).findByRole("button", { name: /Cadastro rural.*em andamento/ })
    fireEvent.click(presa)
    expect(ultimaUrl()).toBe("/observability?execucao=run-presa")

    fireEvent.click(within(atencao).getByRole("button", { name: /Integração SICAR falhou/ }))
    expect(ultimaUrl()).toBe("/observability?status=failed&workflow=wf-2&execucao=run-presa")
  })

  it("'Ver em andamento' aplica status=running e a visão execuções", async () => {
    url.sp = new URLSearchParams("visao=executores")
    render(<HistoricoPage />)
    fireEvent.click(await screen.findByRole("button", { name: "Ver execuções em andamento" }))
    expect(ultimaUrl()).toBe("/observability?status=running")
  })

  it("Atualizar refaz os dados com force e a lista de execuções", async () => {
    render(<HistoricoPage />)
    await screen.findByRole("button", { name: "Abrir execução de Integração SICAR" })
    await waitFor(() => expect(screen.getByRole("button", { name: "Atualizar os dados do Histórico" })).toBeEnabled())
    fireEvent.click(screen.getByRole("button", { name: "Atualizar os dados do Histórico" }))
    await waitFor(() => expect(svc.getObservabilityMetrics).toHaveBeenLastCalledWith(30, true, expect.anything()))
    await waitFor(() => expect(svc.getObservabilityRuns).toHaveBeenCalledTimes(2))
  })

  it("falha parcial vira aviso na seção, e o resto da página continua", async () => {
    svc.getRunsByDay.mockResolvedValue(falha())
    render(<HistoricoPage />)
    expect(await screen.findByText(/Não foi possível carregar as execuções por dia/)).toBeInTheDocument()
    expect(screen.getByRole("group", { name: /^Execuções: 1\.284/ })).toBeInTheDocument()
  })

  it("admin: aba Confirmações, filtro de workspace e interruptor Ativo com toast", async () => {
    sessao.role = "admin"
    svc.getPendingAcks.mockResolvedValue(ok({ items: [{ job_id: "j1", executor_id: "ex-1", elapsed_seconds: 40 }], threshold_overdue_seconds: 15 }))
    url.sp = new URLSearchParams("visao=workflows")
    render(<HistoricoPage />)
    const abaAcks = await screen.findByRole("tab", { name: /Confirmações/ })
    await waitFor(() => expect(abaAcks).toHaveTextContent("1"))

    const painel = screen.getByRole("tabpanel")
    const interruptor = await within(painel).findByRole("switch", { name: "Desativar Integração SICAR" })
    fireEvent.click(interruptor)
    fireEvent.click(await screen.findByRole("button", { name: "Desativar" }))
    await waitFor(() => expect(svc.setAdminWorkflowStatus).toHaveBeenCalledWith("wf-2", false))
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Workflow desativado", "«Integração SICAR»"))
    // A lista volta com force para o cache do backend não devolver o valor antigo.
    await waitFor(() => expect(svc.getWorkflowMetricsList).toHaveBeenLastCalledWith(30, true, expect.anything()))
  })

  it("usuário com um só workspace não vê o seletor de workspace; com dois, vê", async () => {
    const { unmount } = render(<HistoricoPage />)
    await screen.findByRole("button", { name: "Abrir execução de Integração SICAR" })
    expect(screen.queryByRole("combobox", { name: "Workspace" })).not.toBeInTheDocument()
    unmount()

    workspaces.lista = [{ id_hash: "ws-1", name: "Cadastro" }, { id_hash: "ws-2", name: "Geo" }]
    render(<HistoricoPage />)
    expect(await screen.findByRole("combobox", { name: "Workspace" })).toBeInTheDocument()
  })
})
