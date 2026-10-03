import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { VisaoWorkflows } from "@/app/components/observability/visao-workflows"
import type { IWorkflowMetricsRow } from "@/service/types"

// The Portuguese StatusBadge is a side effect of another workstream (spec
// §4.4); here it's doubled with the same contract (rotuloDoStatus) so the test
// doesn't depend on the integration order.
vi.mock("@/app/components/shared/StatusBadge", async () => {
  const { rotuloDoStatus } = await import("@/app/components/shared/status-rotulos")
  return { StatusBadge: ({ status }: { status: string }) => <span>{rotuloDoStatus(status)}</span> }
})

afterEach(cleanup)

function linha(extra: Partial<IWorkflowMetricsRow> = {}): IWorkflowMetricsRow {
  return {
    workflow_hash: "wf-1",
    workflow_name: "Integração SICAR",
    workspace_id: "ws-1",
    workspace_name: "Cadastro",
    active: true,
    total_runs: 61,
    success_runs: 33,
    failed_runs: 28,
    running_runs: 0,
    success_rate: 0.54,
    p50_seconds: 170,
    last_run_at: new Date(Date.now() - 3 * 60_000).toISOString(),
    last_status: "failed",
    last_error: "Timeout ao consultar o WFS do SICAR (30 s)",
    last_error_category: "timeout",
    ...extra,
  }
}

describe("VisaoWorkflows", () => {
  it("colunas: workflow com workspace, execuções, sucesso colorido, típica, última com status, falhas com último erro", () => {
    render(<VisaoWorkflows linhas={[linha()]} carregando={false} isAdmin={false} onVerExecucoes={() => {}} onAlternarAtivo={() => {}} />)
    expect(screen.getByRole("columnheader", { name: "Duração típica" })).toBeInTheDocument()
    expect(screen.queryByRole("columnheader", { name: "Ativo" })).not.toBeInTheDocument()
    const tr = screen.getByRole("button", { name: "Ver execuções de Integração SICAR" }).closest("tr")!
    expect(tr).toHaveTextContent("Cadastro")
    expect(tr).toHaveTextContent("61")
    const taxa = within(tr).getByText("54%")
    expect(taxa.className).toContain("text-red")
    expect(tr).toHaveTextContent("2 min 50 s")
    expect(tr).toHaveTextContent("há 3 min")
    expect(tr).toHaveTextContent("Falhou")
    expect(tr).toHaveTextContent("28")
    expect(within(tr).getByTitle("tempo esgotado · Timeout ao consultar o WFS do SICAR (30 s)")).toBeInTheDocument()
  })

  it("último erro longo: o limite de largura fica no bloco da célula, não no <td>", () => {
    const url = "HTTPError: 503 Server Error: Service Unavailable for url: https://geoservicos.ibge.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=CGEO:ANMS2010_06_grade_estatistica"
    render(<VisaoWorkflows linhas={[linha({ last_error: url, last_error_category: "transient" })]} carregando={false} isAdmin={false} onVerExecucoes={() => {}} onAlternarAtivo={() => {}} />)
    const erro = screen.getByTitle(`transitório · ${url}`)
    expect(erro.className).toContain("truncate")
    expect(erro.parentElement!.className).toContain("max-w-[240px]")
    expect(erro.closest("td")!.className).not.toMatch(/(^|\s)max-w-/)
  })

  it("clique na linha e no nome levam às execuções do workflow", () => {
    const onView = vi.fn()
    render(<VisaoWorkflows linhas={[linha()]} carregando={false} isAdmin={false} onVerExecucoes={onView} onAlternarAtivo={() => {}} />)
    const botao = screen.getByRole("button", { name: "Ver execuções de Integração SICAR" })
    fireEvent.click(botao)
    fireEvent.click(botao.closest("tr")!)
    expect(onView).toHaveBeenCalledTimes(2)
    expect(onView).toHaveBeenCalledWith("wf-1")
  })

  it("admin: desligar pede confirmação; ligar não", async () => {
    const onAlternar = vi.fn().mockResolvedValue(undefined)
    const { rerender } = render(<VisaoWorkflows linhas={[linha()]} carregando={false} isAdmin onVerExecucoes={() => {}} onAlternarAtivo={onAlternar} />)
    const interruptor = screen.getByRole("switch", { name: "Desativar Integração SICAR" })
    expect(interruptor).toBeChecked()
    fireEvent.click(interruptor)
    expect(onAlternar).not.toHaveBeenCalled()
    const dialogo = await screen.findByRole("dialog")
    expect(dialogo).toHaveTextContent("Desativar «Integração SICAR»?")
    expect(dialogo).toHaveTextContent("Novas execuções, inclusive agendadas, não vão rodar.")
    fireEvent.click(within(dialogo).getByRole("button", { name: "Desativar" }))
    await waitFor(() => expect(onAlternar).toHaveBeenCalledWith("wf-1", false))
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    expect(screen.getByRole("switch", { name: "Ativar Integração SICAR" })).not.toBeChecked()

    // Turning it back on: direct.
    rerender(<VisaoWorkflows linhas={[linha({ active: false })]} carregando={false} isAdmin onVerExecucoes={() => {}} onAlternarAtivo={onAlternar} />)
    fireEvent.click(screen.getByRole("switch", { name: "Ativar Integração SICAR" }))
    await waitFor(() => expect(onAlternar).toHaveBeenCalledWith("wf-1", true))
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("cancelar a confirmação mantém ligado; falha na API desfaz o interruptor", async () => {
    const onAlternar = vi.fn().mockResolvedValue(false)
    render(<VisaoWorkflows linhas={[linha()]} carregando={false} isAdmin onVerExecucoes={() => {}} onAlternarAtivo={onAlternar} />)
    fireEvent.click(screen.getByRole("switch", { name: "Desativar Integração SICAR" }))
    const dialogo = await screen.findByRole("dialog")
    fireEvent.click(within(dialogo).getByRole("button", { name: "Cancelar" }))
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    expect(screen.getByRole("switch", { name: "Desativar Integração SICAR" })).toBeChecked()

    fireEvent.click(screen.getByRole("switch", { name: "Desativar Integração SICAR" }))
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Desativar" }))
    await waitFor(() => expect(onAlternar).toHaveBeenCalledWith("wf-1", false))
    await waitFor(() => expect(screen.getByRole("switch", { name: "Desativar Integração SICAR" })).toBeChecked())
  })

  it("skeleton e vazio", () => {
    const { rerender } = render(<VisaoWorkflows linhas={[]} carregando isAdmin={false} onVerExecucoes={() => {}} onAlternarAtivo={() => {}} />)
    expect(screen.getByLabelText("Carregando workflows")).toHaveAttribute("aria-busy", "true")
    rerender(<VisaoWorkflows linhas={[]} carregando={false} isAdmin={false} onVerExecucoes={() => {}} onAlternarAtivo={() => {}} />)
    expect(screen.getByText("Nenhum workflow no escopo")).toBeInTheDocument()
  })

  it("sem execução na janela, sucesso vira travessão", () => {
    render(<VisaoWorkflows linhas={[linha({ total_runs: 0, success_runs: 0, failed_runs: 0, success_rate: 0, last_run_at: null, last_status: null, last_error: null })]} carregando={false} isAdmin={false} onVerExecucoes={() => {}} onAlternarAtivo={() => {}} />)
    const tr = screen.getByRole("button", { name: "Ver execuções de Integração SICAR" }).closest("tr")!
    expect(within(tr).queryByText("0%")).not.toBeInTheDocument()
  })
})
