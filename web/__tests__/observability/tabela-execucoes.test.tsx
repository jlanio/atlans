import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react"
import { TabelaExecucoes, duracaoDaExecucao, sublinhaDoWorkflow } from "@/app/components/observability/tabela-execucoes"
import type { IRunSummary } from "@/service/types"

// The Portuguese StatusBadge is a side effect of another workstream (spec
// §4.4); here it's doubled with the same contract (rotuloDoStatus) so the test
// doesn't depend on the integration order.
vi.mock("@/app/components/shared/StatusBadge", async () => {
  const { rotuloDoStatus } = await import("@/app/components/shared/status-rotulos")
  return { StatusBadge: ({ status }: { status: string }) => <span>{rotuloDoStatus(status)}</span> }
})

afterEach(cleanup)

function run(extra: Partial<IRunSummary> = {}): IRunSummary {
  return {
    run_id: "run-1",
    workflow_hash: "wf-1",
    status: "failed",
    started_at: new Date(Date.now() - 5 * 60_000).toISOString(),
    finished_at: null,
    duration_seconds: 31,
    error_message: "Timeout ao consultar o WFS do SICAR (30 s)",
    retry_count: 0,
    agent_host: "executor:geo-03",
    executor_name: "geo-03",
    dispatch_tier: "fallback",
    workflow_name: "Integração SICAR",
    workspace_name: "Cadastro",
    trigger_source: "schedule",
    error_category: "timeout",
    ...extra,
  }
}

const base = {
  total: 1284, hasMore: true, carregando: false, carregandoMais: false, falhou: false, filtrado: false,
  onCarregarMais: () => {}, onAbrir: () => {},
}

describe("TabelaExecucoes", () => {
  it("execução de fluxo do assistente leva o selo ao lado do nome; as outras não", () => {
    render(<TabelaExecucoes {...base} runs={[
      run({ run_id: "r-assist", workflow_name: "Embargos no Brasil", workflow_origem: "assistente" }),
      run({ run_id: "r-usuario", workflow_origem: "usuario" }),
    ]} />)
    const selos = screen.getAllByLabelText("Fluxo criado pelo assistente")
    expect(selos).toHaveLength(1)
    // On the right row: the assistant workflow's, not the one above or below.
    expect(selos[0].closest("tr")).toHaveTextContent("Embargos no Brasil")
  })

  it("renderiza as colunas do desenho: status em português, workflow com contexto, nível, erro com categoria", () => {
    render(<TabelaExecucoes {...base} runs={[run()]} />)
    expect(screen.getByRole("columnheader", { name: "Status" })).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "Workflow" })).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "Erro" })).toBeInTheDocument()

    // The button sits on the workflow name; the row (cell by cell) stays
    // readable for screen readers — that's why the text is read on the <tr>.
    const botao = screen.getByRole("button", { name: "Abrir execução de Integração SICAR" })
    const linha = botao.closest("tr")!
    expect(linha).toHaveTextContent("Falhou")
    expect(linha).toHaveTextContent("Cadastro · agendado")
    expect(linha).toHaveTextContent("há 5 min")
    expect(linha).toHaveTextContent("31 s")
    expect(linha).toHaveTextContent("geo-03")
    expect(linha).toHaveTextContent("reserva")
    const erro = within(linha).getByTitle("tempo esgotado · Timeout ao consultar o WFS do SICAR (30 s)")
    expect(erro.className).toContain("text-red")
    // Footer with the first page's total.
    expect(screen.getByText("Mostrando 1 de 1.284")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Ver mais" })).toBeInTheDocument()
  })

  it("clique na linha e ativação do botão do nome abrem a execução, sem role na <tr>", () => {
    const onAbrir = vi.fn()
    render(<TabelaExecucoes {...base} runs={[run()]} onAbrir={onAbrir} />)
    const botao = screen.getByRole("button", { name: "Abrir execução de Integração SICAR" })
    const linha = botao.closest("tr")!
    expect(linha).not.toHaveAttribute("role")
    fireEvent.click(linha)
    fireEvent.click(botao)   // Enter/Space on a native <button> become a click
    expect(onAbrir).toHaveBeenCalledTimes(2)
    expect(onAbrir).toHaveBeenCalledWith("run-1")
  })

  it("erro com URL longa: o limite de largura fica no texto, não no <td>", () => {
    // `max-width` on a table cell isn't defined by the specification; with the
    // limit on the <td>, a URL without spaces could widen the column until the
    // table scrolled sideways. On the <span> the rule is that of a regular block.
    const url = "HTTPError: 503 Server Error: Service Unavailable for url: https://geoservicos.ibge.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=CGEO:ANMS2010_06_grade_estatistica"
    render(<TabelaExecucoes {...base} runs={[run({ error_message: url, error_category: "transient" })]} />)
    const erro = screen.getByTitle(`transitório · ${url}`)
    expect(erro.className).toContain("max-w-[220px]")
    expect(erro.className).toContain("truncate")
    expect(erro.closest("td")!.className).not.toMatch(/(^|\s)max-w-/)
  })

  it("executor ausente vira travessão; erro de execução concluída não fica vermelho", () => {
    render(<TabelaExecucoes {...base} runs={[run({ status: "success", agent_host: null, executor_name: null, error_message: null, error_category: null, dispatch_tier: "primary" })]} />)
    const linha = screen.getByRole("button", { name: "Abrir execução de Integração SICAR" }).closest("tr")!
    expect(linha).toHaveTextContent("Concluída")
    expect(linha).toHaveTextContent("—")
    expect(linha).not.toHaveTextContent("reserva")
  })

  it("skeleton enquanto carrega a primeira página", () => {
    render(<TabelaExecucoes {...base} runs={[]} carregando />)
    expect(screen.getByLabelText("Carregando execuções")).toHaveAttribute("aria-busy", "true")
  })

  it("falha precede o vazio", () => {
    const onRecarregar = vi.fn()
    render(<TabelaExecucoes {...base} runs={[]} falhou onRecarregar={onRecarregar} />)
    expect(screen.getByText("Não foi possível carregar as execuções")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }))
    expect(onRecarregar).toHaveBeenCalled()
  })

  it("vazio sem filtro e vazio com filtro dizem coisas diferentes", () => {
    const onLimpar = vi.fn()
    const { rerender } = render(<TabelaExecucoes {...base} runs={[]} total={0} hasMore={false} />)
    expect(screen.getByText("Nenhuma execução no período")).toBeInTheDocument()
    rerender(<TabelaExecucoes {...base} runs={[]} total={0} hasMore={false} filtrado onLimparFiltros={onLimpar} />)
    expect(screen.getByText("Nada com esses filtros")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }))
    expect(onLimpar).toHaveBeenCalled()
  })

  it("'Ver mais' chama onCarregarMais e trava enquanto carrega", () => {
    const onCarregarMais = vi.fn()
    const { rerender } = render(<TabelaExecucoes {...base} runs={[run()]} onCarregarMais={onCarregarMais} />)
    fireEvent.click(screen.getByRole("button", { name: "Ver mais" }))
    expect(onCarregarMais).toHaveBeenCalledTimes(1)
    rerender(<TabelaExecucoes {...base} runs={[run()]} onCarregarMais={onCarregarMais} carregandoMais />)
    expect(screen.getByRole("button", { name: "Carregando…" })).toBeDisabled()
  })
})

describe("helpers da tabela", () => {
  it("em andamento mostra o decorrido desde o início", () => {
    const agora = Date.parse("2026-09-06T12:00:00Z")
    const r = run({ status: "running", duration_seconds: null, started_at: "2026-09-06T11:57:58Z" })
    expect(duracaoDaExecucao(r, agora)).toBe("2 min 02 s")
    expect(duracaoDaExecucao(run({ status: "success", duration_seconds: 3661 }), agora)).toBe("1 h 1 min")
  })

  it("sublinha junta workspace, origem e quem disparou, pulando o que falta", () => {
    expect(sublinhaDoWorkflow(run({ trigger_source: "manual", triggered_by_username: "fulana" }))).toBe("Cadastro · manual · fulana")
    expect(sublinhaDoWorkflow(run({ workspace_name: null, trigger_source: null }))).toBe("")
  })
})
