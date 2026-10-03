import { afterEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { Filtros } from "@/app/components/observability/filtros"
import { ESTADO_PADRAO, type EstadoDoHistorico } from "@/app/components/observability/historico-url"
import type { IExecutorMetrics, IWorkflowMetricsRow } from "@/service/types"

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

function estado(extra: Partial<EstadoDoHistorico> = {}): EstadoDoHistorico {
  return { ...ESTADO_PADRAO, ...extra }
}

const contagens = { success: 1235, failed: 46, running: 3, cancelled: 0, pending: 0, other: 0 }

const workflows = [
  { workflow_hash: "wf-a", workflow_name: "Integração SICAR", workspace_id: "ws-1" },
  { workflow_hash: "wf-b", workflow_name: "Malha viária", workspace_id: "ws-2" },
] as IWorkflowMetricsRow[]

const executores = [
  { agent_host: "executor:geo-01", display_name: "geo-01", total_runs: 1 },
  { agent_host: null, display_name: "Sem executor", unassigned: true, total_runs: 4 },
] as IExecutorMetrics[]

describe("Filtros", () => {
  it("chips de status com contagens; o ativo tem aria-pressed e o clique escreve o estado", () => {
    const onEstado = vi.fn()
    render(<Filtros estado={estado()} onEstado={onEstado} contagens={contagens} />)
    const todas = screen.getByRole("button", { name: /Todas/ })
    expect(todas).toHaveAttribute("aria-pressed", "true")
    expect(todas).toHaveTextContent("1.284")
    const falhas = screen.getByRole("button", { name: /Falhas/ })
    expect(falhas).toHaveAttribute("aria-pressed", "false")
    expect(falhas).toHaveTextContent("46")
    expect(screen.getByRole("button", { name: /Em andamento/ })).toHaveTextContent("3")
    expect(screen.getByRole("button", { name: /Concluídas/ })).toHaveTextContent("1.235")
    expect(screen.getByRole("button", { name: /Canceladas/ })).toBeInTheDocument()

    fireEvent.click(falhas)
    expect(onEstado).toHaveBeenCalledWith({ status: "failed" })
    fireEvent.click(todas)
    expect(onEstado).toHaveBeenCalledWith({ status: null })
  })

  it("selects Workflow/Executor/Origem existem; Workspace só quando pedido; a linha 'Sem executor' fica de fora", () => {
    const { rerender } = render(<Filtros estado={estado()} onEstado={() => {}} workflows={workflows} executores={executores} />)
    expect(screen.queryByRole("combobox", { name: "Workspace" })).not.toBeInTheDocument()
    expect(screen.getByRole("combobox", { name: "Workflow" })).toHaveTextContent("todos")
    expect(screen.getByRole("combobox", { name: "Executor" })).toHaveTextContent("todos")
    expect(screen.getByRole("combobox", { name: "Origem" })).toHaveTextContent("todas")

    rerender(<Filtros estado={estado({ executor: "executor:geo-01", origem: "schedule" })} onEstado={() => {}} workflows={workflows} executores={executores} mostrarWorkspace workspaces={[{ id: "ws-1", name: "Cadastro" }]} />)
    expect(screen.getByRole("combobox", { name: "Workspace" })).toBeInTheDocument()
    expect(screen.getByRole("combobox", { name: "Executor" })).toHaveTextContent("geo-01")
    expect(screen.getByRole("combobox", { name: "Origem" })).toHaveTextContent("agendado")
  })

  it("busca espera 300 ms parada antes de subir", () => {
    vi.useFakeTimers()
    const onEstado = vi.fn()
    render(<Filtros estado={estado()} onEstado={onEstado} />)
    const busca = screen.getByRole("searchbox", { name: "Buscar execuções" })
    expect(busca).toHaveAttribute("placeholder", "Buscar por erro, workflow ou ID")
    fireEvent.change(busca, { target: { value: "tim" } })
    fireEvent.change(busca, { target: { value: "timeout" } })
    act(() => { vi.advanceTimersByTime(200) })
    expect(onEstado).not.toHaveBeenCalled()
    act(() => { vi.advanceTimersByTime(150) })
    expect(onEstado).toHaveBeenCalledTimes(1)
    expect(onEstado).toHaveBeenCalledWith({ q: "timeout" })
  })

  it("o chip Assistente é um alternador próprio e combina com o status", () => {
    const onEstado = vi.fn()
    const { rerender } = render(<Filtros estado={estado({ status: "failed" })} onEstado={onEstado} contagens={contagens} />)
    const chip = screen.getByRole("button", { name: /Assistente/ })
    expect(chip).toHaveAttribute("aria-pressed", "false")
    // No number: the count the screen has is of workflows, and these chips count
    // runs — a number here would lie next to the others.
    expect(chip).toHaveTextContent(/^Assistente$/)

    fireEvent.click(chip)
    expect(onEstado).toHaveBeenCalledWith({ assistente: true })

    // When on, it doesn't turn off the status: they're different axes, and
    // "Falhas do assistente" (assistant failures) is exactly the question the
    // screen needs to answer.
    rerender(<Filtros estado={estado({ status: "failed", assistente: true })} onEstado={onEstado} contagens={contagens} />)
    expect(screen.getByRole("button", { name: /Assistente/ })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByRole("button", { name: /Falhas/ })).toHaveAttribute("aria-pressed", "true")
    fireEvent.click(screen.getByRole("button", { name: /Assistente/ }))
    expect(onEstado).toHaveBeenLastCalledWith({ assistente: false })
  })

  it("'Limpar filtros' só aparece com filtro ativo e zera tudo de uma vez", () => {
    const onEstado = vi.fn()
    const { rerender } = render(<Filtros estado={estado()} onEstado={onEstado} />)
    expect(screen.queryByRole("button", { name: /Limpar filtros/ })).not.toBeInTheDocument()
    rerender(<Filtros estado={estado({ status: "failed", q: "sicar" })} onEstado={onEstado} />)
    expect(screen.getByText("2 filtros ativos")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Limpar filtros/ }))
    expect(onEstado).toHaveBeenCalledWith({ status: null, workspace: null, workflow: null, executor: null, origem: null, assistente: false, q: "" })
  })

  it("quando a URL zera a busca por fora, o campo acompanha", () => {
    const { rerender } = render(<Filtros estado={estado({ q: "sicar" })} onEstado={() => {}} />)
    expect(screen.getByRole("searchbox")).toHaveValue("sicar")
    rerender(<Filtros estado={estado({ q: "" })} onEstado={() => {}} />)
    expect(screen.getByRole("searchbox")).toHaveValue("")
  })
})
