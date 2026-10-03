import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react"
import { VisaoExecutores, noTeto, textoDeAgora } from "@/app/components/observability/visao-executores"
import type { IExecutorMetrics } from "@/service/types"

afterEach(cleanup)

function executor(extra: Partial<IExecutorMetrics> = {}): IExecutorMetrics {
  return {
    agent_host: "executor:geo-01",
    display_name: "geo-01",
    total_runs: 120,
    success_runs: 110,
    failed_runs: 10,
    success_rate: 0.917,
    avg_duration_seconds: 50,
    p50_seconds: 42,
    last_run_at: new Date(Date.now() - 2 * 60_000).toISOString(),
    online: true,
    is_default: true,
    capacity: { running: 2, queued: 12, max_concurrent: 4, max_queue: 50 },
    ...extra,
  }
}

describe("VisaoExecutores", () => {
  it("linha do executor: ponto online, selo pool, agora, execuções acessíveis, sucesso, típica, última", () => {
    render(<VisaoExecutores linhas={[executor()]} carregando={false} onVerExecucoes={() => {}} />)
    const tr = screen.getByRole("button", { name: "Ver execuções de geo-01" })
    expect(within(tr).getByRole("img", { name: "online" })).toBeInTheDocument()
    expect(tr).toHaveTextContent("pool")
    expect(tr).toHaveTextContent("2 de 4 em execução · 12 na fila")
    expect(tr).toHaveTextContent("120")
    expect(tr).toHaveTextContent("110 concluídas, 10 falhas")
    expect(within(tr).getByText("92%").className).toContain("text-green")
    expect(tr).toHaveTextContent("42 s")
    expect(tr).toHaveTextContent("há 2 min")
  })

  it("abre pelo clique e pelo teclado", () => {
    const onView = vi.fn()
    render(<VisaoExecutores linhas={[executor()]} carregando={false} onVerExecucoes={onView} />)
    const tr = screen.getByRole("button", { name: "Ver execuções de geo-01" })
    fireEvent.click(tr)
    fireEvent.keyDown(tr, { key: "Enter" })
    expect(onView).toHaveBeenCalledTimes(2)
    expect(onView).toHaveBeenCalledWith("executor:geo-01")
  })

  it("'Sem executor' não abre e explica por quê", () => {
    render(<VisaoExecutores linhas={[executor({ agent_host: null, display_name: "Sem executor", unassigned: true, capacity: null, online: false, is_default: false })]} carregando={false} onVerExecucoes={() => {}} />)
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
    expect(screen.getByTitle(/falhas de despacho/)).toHaveTextContent("Sem executor")
  })

  it("no teto fica âmbar", () => {
    render(<VisaoExecutores linhas={[executor({ capacity: { running: 4, queued: 3, max_concurrent: 4, max_queue: 50 } })]} carregando={false} onVerExecucoes={() => {}} />)
    const celula = screen.getByText(/4 de 4 em execução/)
    expect(celula.className).toContain("text-amber")
  })

  it("skeleton e vazio", () => {
    const { rerender } = render(<VisaoExecutores linhas={[]} carregando onVerExecucoes={() => {}} />)
    expect(screen.getByLabelText("Carregando executores")).toHaveAttribute("aria-busy", "true")
    rerender(<VisaoExecutores linhas={[]} carregando={false} onVerExecucoes={() => {}} />)
    expect(screen.getByText("Nenhum executor no escopo")).toBeInTheDocument()
  })
})

describe("helpers", () => {
  it("textoDeAgora e noTeto", () => {
    expect(textoDeAgora(null)).toBe("—")
    expect(textoDeAgora({ running: 0, queued: 0, max_concurrent: 4, max_queue: 10 })).toBe("0 de 4 em execução")
    expect(textoDeAgora({ running: 2, queued: 1200, max_concurrent: 4, max_queue: 10 })).toBe("2 de 4 em execução · 1.200 na fila")
    expect(noTeto({ running: 4, queued: 0, max_concurrent: 4, max_queue: 10 })).toBe(true)
    expect(noTeto({ running: 3, queued: 0, max_concurrent: 4, max_queue: 10 })).toBe(false)
    expect(noTeto(null)).toBe(false)
  })
})
