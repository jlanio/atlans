import { afterEach, describe, expect, it } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import { Indicadores } from "@/app/components/observability/indicadores"
import type { IObservabilityMetrics, IRunsByDay } from "@/service/types"

afterEach(cleanup)

const dias: IRunsByDay[] = [
  { day: "2026-09-01", total: 40, success: 38, failed: 2, running: 0 },
  { day: "2026-09-02", total: 0, success: 0, failed: 0, running: 0 },
  { day: "2026-09-03", total: 50, success: 45, failed: 5, running: 0 },
]

function metricas(extra: Partial<IObservabilityMetrics> = {}): IObservabilityMetrics {
  return {
    period_days: 30,
    total_workflows: 23, active_workflows: 20, total_runs: 1284, failed_runs: 46,
    success_rate: 0.964, avg_duration_seconds: 54, runs_last_24h: 0, runs_last_7d: 0, runs_prev_7d: 0,
    success_rate_prev_7d: null,
    by_status: { success: 1235, failed: 46, running: 3, other: 0 },
    top_failing_workflows: [{
      workflow_hash: "wf-sicar", workflow_name: "Integração SICAR", failure_count: 28, total_runs: 61,
      failure_rate: 0.46, last_error: "Timeout", last_error_category: "timeout", last_failed_at: null,
    }],
    prev_period: { total_runs: 1147, success_runs: 1118, failed_runs: 29, success_rate: 0.975, p50_seconds: 38 },
    duration: { p50_seconds: 42, p95_seconds: 190 },
    ...extra,
  }
}

describe("Indicadores", () => {
  it("os quatro cards, comparados ao período anterior, com aria-label completo", () => {
    render(<Indicadores metrics={metricas()} dias={dias} carregando={false} periodo={30} />)

    const execucoes = screen.getByRole("group", { name: /^Execuções: 1\.284, 12% a mais que o período anterior; 1\.147 no período anterior$/ })
    expect(execucoes).toHaveTextContent("1.284")
    expect(execucoes).toHaveTextContent("12%")

    const taxa = screen.getByRole("group", { name: /^Taxa de sucesso: 96,4%, −1,1 pt em relação ao período anterior; 97,5% no período anterior$/ })
    expect(taxa).toHaveTextContent("96,4%")
    expect(taxa).toHaveTextContent("−1,1 pt")

    const duracao = screen.getByRole("group", { name: /^Duração típica: 42 s, 5% mais lentas acima de 3 min 10 s; mediana; era 38 s no período anterior$/ })
    expect(duracao).toHaveTextContent("42 s")
    expect(duracao).toHaveTextContent("5% mais lentas acima de 3 min 10 s")

    const falhas = screen.getByRole("group", { name: /^Falhas: 46, \+17 em relação ao período anterior; 28 delas em «Integração SICAR»$/ })
    expect(falhas).toHaveTextContent("+17")
    expect(falhas).toHaveTextContent("28 delas em «Integração SICAR»")
  })

  it("menos falhas é verde; mais falhas é vermelho; mais execuções é verde", () => {
    const { container, rerender } = render(
      <Indicadores metrics={metricas({ failed_runs: 20 })} dias={dias} carregando={false} periodo={30} />,
    )
    const selos = () => Array.from(container.querySelectorAll("span[aria-hidden='true'].rounded-full"))
    const seloFalhas = selos().find(s => s.textContent?.includes("−9"))
    expect(seloFalhas?.className).toContain("text-green-700")

    rerender(<Indicadores metrics={metricas({ failed_runs: 46 })} dias={dias} carregando={false} periodo={30} />)
    const seloMais = selos().find(s => s.textContent?.includes("+17"))
    expect(seloMais?.className).toContain("text-red-700")
    const seloExec = selos().find(s => s.textContent?.includes("12%"))
    expect(seloExec?.className).toContain("text-green-700")
  })

  it("sem período anterior nem duração, descreve a janela e cala a tendência", () => {
    render(<Indicadores metrics={metricas({ prev_period: undefined, duration: undefined, top_failing_workflows: [] })} dias={[]} carregando={false} periodo={7} />)
    expect(screen.getByRole("group", { name: /^Execuções: 1\.284; nos últimos 7 dias$/ })).toBeInTheDocument()
    expect(screen.getByRole("group", { name: /^Duração típica: —; mediana das concluídas$/ })).toBeInTheDocument()
    expect(screen.getByRole("group", { name: /^Falhas: 46; nos últimos 7 dias$/ })).toBeInTheDocument()
    expect(screen.queryByText("12%")).toBeNull()
  })

  it("zero falhas diz isso, sem culpar workflow nenhum", () => {
    render(<Indicadores metrics={metricas({ failed_runs: 0, top_failing_workflows: [] })} dias={dias} carregando={false} periodo={30} />)
    expect(screen.getByRole("group", { name: /^Falhas: 0, −29 em relação ao período anterior; nenhuma no período$/ })).toBeInTheDocument()
  })

  it("skeleton só na primeira carga; com dado na tela, a recarga não apaga nada", () => {
    const { container, rerender } = render(<Indicadores metrics={null} dias={[]} carregando periodo={30} />)
    expect(screen.getByLabelText("Indicadores carregando")).toBeInTheDocument()
    expect(container.querySelectorAll("[data-slot='skeleton']").length).toBeGreaterThan(0)

    rerender(<Indicadores metrics={metricas()} dias={dias} carregando periodo={30} />)
    expect(screen.queryByLabelText("Indicadores carregando")).toBeNull()
    expect(screen.getByText("1.284")).toBeInTheDocument()
  })

  it("sem métricas e sem carga (falha total) mostra traços, não zeros", () => {
    render(<Indicadores metrics={null} dias={[]} carregando={false} periodo={30} />)
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3)
    expect(screen.queryByText("0")).toBeNull()
  })

  it("sparklines: total e falhas por dia, e a taxa só nos dias com denominador", () => {
    const { container } = render(<Indicadores metrics={metricas()} dias={dias} carregando={false} periodo={30} />)
    // Three cards have a series (Runs, Rate, Failures); Typical duration doesn't.
    // The count is by attribute, not by selector: jsdom 30
    // (@asamuzakjp/dom-selector 8) doesn't match `svg[preserveAspectRatio='none']`,
    // an SVG attribute with uppercase letters and a value. The browser and jsdom 29 match it.
    const sparklines = [...container.querySelectorAll("svg")].filter((s) => s.getAttribute("preserveAspectRatio") === "none")
    expect(sparklines).toHaveLength(3)
  })
})

describe("Indicadores — período anterior vazio", () => {
  it("sem execuções no período anterior não há seta nem '+81': a descrição diz por quê", () => {
    const m = metricas({ prev_period: { total_runs: 0, success_runs: 0, failed_runs: 0, success_rate: 0, p50_seconds: null } })
    render(<Indicadores metrics={m} dias={[]} carregando={false} periodo={30} />)
    const execucoes = screen.getByRole("group", { name: /^Execuções: 1\.284; nenhuma no período anterior$/ })
    expect(execucoes).not.toHaveTextContent("+")
    expect(screen.getByRole("group", { name: /^Taxa de sucesso: 96,4%; sem período anterior para comparar$/ })).toBeInTheDocument()
    expect(screen.queryByText("0,0% no período anterior")).not.toBeInTheDocument()
  })
})
