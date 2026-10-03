import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import type { IWorkflow, IWorkflowSchedule } from "@/service/types"
import { ProximasLista } from "@/app/components/dashboard/proximas-lista"

afterEach(cleanup)

// A date far in the future so `resumirAgendamento` marks "ativo" (with an upcoming one),
// regardless of the clock the test runs on.
const daquiUmaHora = new Date(Date.now() + 3_600_000).toISOString()

function agendamento(extra: Partial<IWorkflowSchedule> = {}): IWorkflowSchedule {
  return { active: true, next_run_at: daquiUmaHora, last_run_at: null, strategy: "interval", interval: 6, unit: "hours", ...extra }
}

function wf(id: string, extra: Partial<IWorkflow> = {}): IWorkflow {
  return {
    id_hash: id, flag_ative: true, name: `Fluxo ${id}`, description: "", version: "1", priority: 0,
    definition: { nodes: [], edges: [] }, created_by_id: "u1", updated_by_id: "u1",
    has_schedule_trigger: true, schedule: agendamento(), workspace_id: "ws-1", ...extra,
  }
}

describe("ProximasLista", () => {
  it("vazio: 'Nenhuma execução agendada.'", () => {
    render(<ProximasLista workflows={[]} escopo="ativo" onAbrir={() => {}} />)
    expect(screen.getByText("Nenhuma execução agendada.")).toBeInTheDocument()
  })

  it("desenha nome + agendamento e o nome abre o editor", () => {
    const onAbrir = vi.fn()
    render(<ProximasLista workflows={[wf("a")]} escopo="ativo" onAbrir={onAbrir} />)
    expect(screen.getByText("Fluxo a")).toBeInTheDocument()
    expect(screen.getByText(/a cada 6 h/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Abrir Fluxo a no editor" }))
    expect(onAbrir).toHaveBeenCalledWith("a")
  })

  it("escopo 'todos': etiqueta do workspace; escopo 'ativo': sem etiqueta", () => {
    const nomeDoWorkspace = (id: string | null | undefined) => (id === "ws-1" ? "Bacia do Rio Doce" : null)
    const { rerender } = render(
      <ProximasLista workflows={[wf("a")]} escopo="todos" nomeDoWorkspace={nomeDoWorkspace} onAbrir={() => {}} />,
    )
    expect(screen.getByText("Bacia do Rio Doce")).toBeInTheDocument()
    rerender(
      <ProximasLista workflows={[wf("a")]} escopo="ativo" nomeDoWorkspace={nomeDoWorkspace} onAbrir={() => {}} />,
    )
    expect(screen.queryByText("Bacia do Rio Doce")).toBeNull()
  })

  it("o ponteiro sobre o item aquece a rota (onPrefetch)", () => {
    const onPrefetch = vi.fn()
    render(<ProximasLista workflows={[wf("a")]} escopo="ativo" onAbrir={() => {}} onPrefetch={onPrefetch} />)
    fireEvent.pointerEnter(screen.getByRole("button", { name: "Abrir Fluxo a no editor" }))
    expect(onPrefetch).toHaveBeenCalledWith("a")
  })
})
