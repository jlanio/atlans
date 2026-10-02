import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { IRunDetail } from "@/service/types"

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getRunDetail: vi.fn(),
    getRunEvents: vi.fn(),
    retryRun: vi.fn(),
  },
}))
// O StatusBadge em português é colateral de outra frente (spec §4.4); aqui
// ele é dublado com o mesmo contrato (rotuloDoStatus) para o teste não
// depender da ordem de integração.
vi.mock("@/app/components/shared/StatusBadge", async () => {
  const { rotuloDoStatus } = await import("@/app/components/shared/status-rotulos")
  return { StatusBadge: ({ status }: { status: string }) => <span>{rotuloDoStatus(status)}</span> }
})
vi.mock("@/utils/createToast", () => ({
  createToast: { success: vi.fn(), error: vi.fn(), info: vi.fn(), loading: vi.fn() },
}))

import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { PainelExecucao, nosDaExecucao } from "@/app/components/observability/painel-execucao"

const svc = GisFlowService as unknown as {
  getRunDetail: ReturnType<typeof vi.fn>
  getRunEvents: ReturnType<typeof vi.fn>
  retryRun: ReturnType<typeof vi.fn>
}
const toast = createToast as unknown as { success: ReturnType<typeof vi.fn>; error: ReturnType<typeof vi.fn> }

const ok = <T,>(data: T) => ({ success: true, status: 200, data })

function detalhe(extra: Partial<IRunDetail> = {}): IRunDetail {
  return {
    run_id: "run-7f3a",
    workflow_hash: "wf-1",
    status: "failed",
    started_at: "2026-09-06T03:00:04Z",
    finished_at: "2026-09-06T03:00:35Z",
    duration_seconds: 31,
    error_message: "TimeoutError: consulta ao WFS do SICAR não respondeu em 30 s\n  nó: «Buscar imóveis SICAR» (2/6)",
    retry_count: 1,
    agent_host: "executor:geo-03",
    executor_name: "geo-03",
    dispatch_tier: "fallback",
    workflow_name: "Integração SICAR",
    workspace_name: "Cadastro",
    trigger_source: "schedule",
    triggered_by_username: null,
    error_category: "timeout",
    typical_seconds: 170,
    node_stats: {
      "n1": { node_name: "Ler limites municipais", duration_ms: 800, status: "success", cache_hit: false, input_features: null, output_features: null, error: null, started_at: null, output_keys: [] },
      "n2": { node_name: "Buscar imóveis SICAR", duration_ms: 30100, status: "failed", cache_hit: false, input_features: null, output_features: null, error: "TimeoutError", started_at: null, output_keys: [] },
      "__meta__": { node_name: "meta", duration_ms: 0, status: "success", cache_hit: false, input_features: null, output_features: null, error: null, started_at: null, output_keys: [] },
    },
    ...extra,
  }
}

beforeEach(() => {
  vi.resetAllMocks()
  window.HTMLElement.prototype.scrollIntoView = vi.fn()
  window.HTMLElement.prototype.hasPointerCapture = vi.fn()
})
afterEach(cleanup)

describe("PainelExecucao", () => {
  it("carrega o detalhe ao abrir e mostra cabeçalho, fatos, erro e nós", async () => {
    svc.getRunDetail.mockResolvedValue(ok(detalhe()))
    render(<PainelExecucao runId="run-7f3a" onFechar={() => {}} />)
    expect(svc.getRunDetail).toHaveBeenCalledWith("run-7f3a")

    const painel = await screen.findByRole("dialog")
    await within(painel).findByText("Integração SICAR")
    expect(painel).toHaveTextContent("Execução · run-7f3a")
    expect(painel).toHaveTextContent("Falhou")
    expect(painel).toHaveTextContent("2ª tentativa")
    expect(painel).toHaveTextContent("rodou na reserva")
    expect(painel).toHaveTextContent("agendado")
    // Fatos
    expect(painel).toHaveTextContent("31 s")
    expect(painel).toHaveTextContent("típica 2 min 50 s")
    expect(painel).toHaveTextContent("Cadastro")
    expect(painel).toHaveTextContent("tempo esgotado")
    // Erro inteiro
    expect(within(painel).getByText(/TimeoutError: consulta ao WFS/)).toBeInTheDocument()
    // Nós: os "__" ficam de fora, o que falhou fica marcado
    expect(painel).toHaveTextContent("2 executados")
    expect(painel).toHaveTextContent("Buscar imóveis SICAR")
    // Duração na escala do resto da página ("30 s"), não "30.10s".
    expect(painel).toHaveTextContent("30 s · falhou")
    expect(painel).not.toHaveTextContent("meta")
    // Ações
    expect(within(painel).getByRole("button", { name: /Executar de novo/ })).toBeInTheDocument()
    expect(within(painel).getByRole("link", { name: "Abrir workflow" })).toHaveAttribute("href", "/workflow/wf-1")
    expect(within(painel).getByRole("link", { name: /Abrir em página/ })).toHaveAttribute("href", "/observability/run/run-7f3a")
    expect(within(painel).getByRole("button", { name: /Copiar ID/ })).toBeInTheDocument()
  })

  it("mostra a mensagem quando o detalhe falha", async () => {
    svc.getRunDetail.mockResolvedValue({ success: false, status: 404, error: { name: "AxiosError", message: "Execução não encontrada." } })
    render(<PainelExecucao runId="x" onFechar={() => {}} />)
    expect(await screen.findByRole("alert")).toHaveTextContent("Execução não encontrada.")
  })

  it("'Executar de novo' confirma antes de chamar a API e avisa por toast", async () => {
    svc.getRunDetail.mockResolvedValue(ok(detalhe()))
    svc.retryRun.mockResolvedValue(ok({ task_id: "t", message: "ok" }))
    render(<PainelExecucao runId="run-7f3a" onFechar={() => {}} />)
    const painel = await screen.findByRole("dialog")
    await within(painel).findByText("Integração SICAR")

    fireEvent.click(within(painel).getByRole("button", { name: /Executar de novo/ }))
    expect(svc.retryRun).not.toHaveBeenCalled()
    const confirmacao = await screen.findByRole("alertdialog").catch(() => screen.getAllByRole("dialog").at(-1)!)
    expect(confirmacao).toHaveTextContent("Executar «Integração SICAR» de novo?")
    fireEvent.click(within(confirmacao).getByRole("button", { name: "Executar" }))
    await waitFor(() => expect(svc.retryRun).toHaveBeenCalledWith("wf-1", "run-7f3a"))
    await waitFor(() => expect(toast.success).toHaveBeenCalled())
  })

  it("403 na reexecução vira toast com a mensagem da API e esconde o botão", async () => {
    svc.getRunDetail.mockResolvedValue(ok(detalhe()))
    svc.retryRun.mockResolvedValue({ success: false, status: 403, error: { name: "AxiosError", message: "Requer role 'operator' ou superior para executar workflows." } })
    render(<PainelExecucao runId="run-7f3a" onFechar={() => {}} />)
    const painel = await screen.findByRole("dialog")
    await within(painel).findByText("Integração SICAR")
    fireEvent.click(within(painel).getByRole("button", { name: /Executar de novo/ }))
    const confirmacao = screen.getAllByRole("dialog").at(-1)!
    fireEvent.click(within(confirmacao).getByRole("button", { name: "Executar" }))
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Não foi possível executar de novo", "Requer role 'operator' ou superior para executar workflows."))
    await waitFor(() => expect(within(painel).queryByRole("button", { name: /Executar de novo/ })).not.toBeInTheDocument())
  })

  it("'Ver log' busca os eventos; log expirado avisa", async () => {
    svc.getRunDetail.mockResolvedValue(ok(detalhe()))
    svc.getRunEvents.mockResolvedValue(ok({ run_id: "run-7f3a", events: [], expired: true }))
    render(<PainelExecucao runId="run-7f3a" onFechar={() => {}} />)
    const painel = await screen.findByRole("dialog")
    await within(painel).findByText("Integração SICAR")
    fireEvent.click(within(painel).getByRole("button", { name: /Ver log/ }))
    expect(svc.getRunEvents).toHaveBeenCalledWith("run-7f3a")
    expect(await within(painel).findByText(/O log expirou/)).toBeInTheDocument()
  })

  it("'Ver log' lista os eventos quando há", async () => {
    svc.getRunDetail.mockResolvedValue(ok(detalhe()))
    svc.getRunEvents.mockResolvedValue(ok({ run_id: "run-7f3a", expired: false, events: [
      { node: "Ler limites municipais", kind: "node_end", timestamp: 1757127604, duration_ms: 800 },
      { node: "Buscar imóveis SICAR", status: "failed", level: "error", timestamp: 1757127635, error: "TimeoutError" },
    ] }))
    render(<PainelExecucao runId="run-7f3a" onFechar={() => {}} />)
    const painel = await screen.findByRole("dialog")
    await within(painel).findByText("Integração SICAR")
    fireEvent.click(within(painel).getByRole("button", { name: /Ver log/ }))
    // Em português, com o nome do nó: `kind` lifecycle não aparece; `status` sim.
    // A lista do log só renderiza depois de getRunEvents resolver. Espera por um
    // texto que SÓ existe nela — o formato "nome · falhou · erro" (a seção "Nós"
    // acima usa outro layout). O findByText(/Ler limites municipais/) anterior
    // casava na seção "Nós" (renderiza antes) e deixava as asserções síncronas
    // rodarem antes de a lista existir — flake em runner mais lento (CI).
    await waitFor(() => expect(painel).toHaveTextContent("Buscar imóveis SICAR · falhou · TimeoutError"))
    expect(painel).toHaveTextContent("(800ms)")
    expect(painel).not.toHaveTextContent("node_end")
  })

  it("'Copiar ID' usa a área de transferência e confirma por toast", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    svc.getRunDetail.mockResolvedValue(ok(detalhe()))
    render(<PainelExecucao runId="run-7f3a" onFechar={() => {}} />)
    const painel = await screen.findByRole("dialog")
    await within(painel).findByText("Integração SICAR")
    fireEvent.click(within(painel).getByRole("button", { name: /Copiar ID/ }))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("run-7f3a"))
    expect(toast.success).toHaveBeenCalledWith("ID copiado", "run-7f3a")
  })

  it("Esc fecha (onFechar); runId nulo não abre nem busca", async () => {
    svc.getRunDetail.mockResolvedValue(ok(detalhe()))
    const onFechar = vi.fn()
    const { rerender } = render(<PainelExecucao runId="run-7f3a" onFechar={onFechar} />)
    const painel = await screen.findByRole("dialog")
    fireEvent.keyDown(painel, { key: "Escape" })
    await waitFor(() => expect(onFechar).toHaveBeenCalled())
    svc.getRunDetail.mockClear()
    rerender(<PainelExecucao runId={null} onFechar={onFechar} />)
    expect(svc.getRunDetail).not.toHaveBeenCalled()
  })
})

describe("nosDaExecucao", () => {
  it("tira as chaves internas e ordena por duração, como a página da execução", () => {
    expect(nosDaExecucao(detalhe()).map(n => n.node_name)).toEqual(["Buscar imóveis SICAR", "Ler limites municipais"])
    expect(nosDaExecucao(null)).toEqual([])
  })
})
