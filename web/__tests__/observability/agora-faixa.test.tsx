import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { AgoraFaixa } from "@/app/components/observability/agora-faixa"
import type { INowBlock } from "@/service/types"

afterEach(cleanup)

function now(extra: Partial<INowBlock> = {}): INowBlock {
  return {
    running: 3, pending: 1, stuck_count: 1,
    stuck: [{
      run_id: "run-presa", workflow_hash: "wf", workflow_name: "Cadastro rural · lote 7",
      agent_host: "executor:geo-02", executor_name: "geo-02", started_at: null,
      elapsed_seconds: 8040, typical_seconds: 360,
    }],
    executors: { online: 4, total: 5 },
    queued_on_executors: 12,
    overdue_acks: 2,
    ...extra,
  }
}

describe("AgoraFaixa", () => {
  it("a linha inteira do desenho: em andamento, fila, presa há X, executores, confirmações", () => {
    render(<AgoraFaixa now={now()} carregando={false} onVerEmAndamento={() => {}} onAbrirPresa={() => {}} />)
    const faixa = screen.getByLabelText("Agora")
    expect(faixa).toHaveTextContent("3 em andamento")
    expect(faixa).toHaveTextContent("1 na fila")
    expect(faixa).toHaveTextContent("1 presa há 2 h 14 min")
    expect(faixa).toHaveTextContent("Executores 4 de 5 online")
    expect(faixa).toHaveTextContent("2 confirmações atrasadas")
    expect(screen.getByRole("button", { name: "Ver execuções em andamento" })).toHaveTextContent("Ver em andamento")
  })

  it("some o que é zero, exceto 'em andamento'", () => {
    render(
      <AgoraFaixa
        now={now({ running: 0, pending: 0, stuck_count: 0, stuck: [], executors: { online: 0, total: 0 }, overdue_acks: 0 })}
        carregando={false} onVerEmAndamento={() => {}} onAbrirPresa={() => {}}
      />,
    )
    const faixa = screen.getByLabelText("Agora")
    expect(faixa).toHaveTextContent("0 em andamento")
    expect(faixa).not.toHaveTextContent("na fila")
    expect(faixa).not.toHaveTextContent("presa")
    expect(faixa).not.toHaveTextContent("online")
    expect(faixa).not.toHaveTextContent("confirmações")
  })

  it("confirmações só quando o backend as devolve (admin): null não vira zero", () => {
    render(<AgoraFaixa now={now({ overdue_acks: null })} carregando={false} onVerEmAndamento={() => {}} onAbrirPresa={() => {}} />)
    expect(screen.getByLabelText("Agora")).not.toHaveTextContent("confirmaç")
  })

  it("presas no plural, e o clique abre a mais antiga", () => {
    const onAbrirPresa = vi.fn()
    const stuck = [
      { ...now().stuck[0], run_id: "mais-antiga", elapsed_seconds: 9000 },
      { ...now().stuck[0], run_id: "mais-nova", elapsed_seconds: 1000 },
    ]
    render(<AgoraFaixa now={now({ stuck_count: 2, stuck })} carregando={false} onVerEmAndamento={() => {}} onAbrirPresa={onAbrirPresa} />)
    const botao = screen.getByRole("button", { name: "Abrir a mais antiga das 2 execuções presas" })
    expect(botao).toHaveTextContent("2 presas há 2 h 30 min")
    fireEvent.click(botao)
    expect(onAbrirPresa).toHaveBeenCalledWith("mais-antiga")
  })

  it("'Ver em andamento' aciona o filtro", () => {
    const onView = vi.fn()
    render(<AgoraFaixa now={now()} carregando={false} onVerEmAndamento={onView} onAbrirPresa={() => {}} />)
    fireEvent.click(screen.getByRole("button", { name: "Ver execuções em andamento" }))
    expect(onView).toHaveBeenCalledTimes(1)
  })

  it("skeleton enquanto carrega sem dado; sem dado e sem carga, diz que não há leitura", () => {
    const { container, rerender } = render(<AgoraFaixa now={undefined} carregando onVerEmAndamento={() => {}} onAbrirPresa={() => {}} />)
    expect(container.querySelector("[data-slot='skeleton']")).not.toBeNull()
    expect(screen.getByLabelText("Agora")).toHaveAttribute("aria-busy", "true")

    rerender(<AgoraFaixa now={null} carregando={false} onVerEmAndamento={() => {}} onAbrirPresa={() => {}} />)
    expect(container.querySelector("[data-slot='skeleton']")).toBeNull()
    expect(screen.getByText("Sem leitura do instante.")).toBeInTheDocument()
  })

  it("com dado na tela, a recarga não apaga a faixa", () => {
    render(<AgoraFaixa now={now()} carregando onVerEmAndamento={() => {}} onAbrirPresa={() => {}} />)
    expect(screen.getByLabelText("Agora")).toHaveTextContent("3 em andamento")
    expect(screen.getByLabelText("Agora")).toHaveAttribute("aria-busy", "false")
  })
})
