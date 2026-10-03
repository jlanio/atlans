import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import type { INowBlock, IStuckRun } from "@/service/types"
import { SaudeHero } from "@/app/components/dashboard/saude-hero"

afterEach(cleanup)

function stuck(extra: Partial<IStuckRun> = {}): IStuckRun {
  return {
    run_id: "run-presa", workflow_hash: "wf", workflow_name: "Cadastro",
    agent_host: null, executor_name: null, started_at: null,
    elapsed_seconds: 1080, typical_seconds: 360, ...extra,
  }
}

function now(extra: Partial<INowBlock> = {}): INowBlock {
  return {
    running: 3, pending: 2, stuck_count: 0, stuck: [],
    executors: { online: 6, total: 6 }, queued_on_executors: 0, overdue_acks: 0, ...extra,
  }
}

const base = {
  resumo: { falhas: 0, saturado: 0 },
  semExecucoes: false,
  escopo: "ativo" as const,
  workspaceId: "ws-1" as string | null,
  carregando: false,
  onVerEmAndamento: () => {},
  onAbrirPresa: () => {},
}

describe("SaudeHero", () => {
  it("calmo: check verde, veredito tranquilo e a linha 'agora'", () => {
    render(<SaudeHero {...base} now={now()} tom="calmo" />)
    expect(screen.getByText("Tudo tranquilo — nada pedindo atenção agora.")).toBeInTheDocument()
    // The "agora" (now) line (NowItems) shows up inside the calm strip.
    expect(screen.getByText("em andamento")).toBeInTheDocument()
    expect(screen.getByText("na fila")).toBeInTheDocument()
  })

  it("calmo sem execuções no período: 'nada rodando ainda'", () => {
    render(<SaudeHero {...base} now={now()} tom="calmo" semExecucoes />)
    expect(screen.getByText("Tudo tranquilo — nada rodando ainda.")).toBeInTheDocument()
  })

  it("atenção/crítico: veredito 'Precisa de você:' com a contagem, e a presa clicável", () => {
    const onAbrirPresa = vi.fn()
    render(
      <SaudeHero
        {...base}
        now={now({ stuck_count: 1, stuck: [stuck()] })}
        tom="critico"
        resumo={{ falhas: 2, saturado: 0 }}
        onAbrirPresa={onAbrirPresa}
      />,
    )
    // The verdict starts with "Precisa de você:" (needs you) and carries the specific count.
    expect(screen.getByText(/Precisa de você:/)).toBeInTheDocument()
    expect(screen.getByText(/2 workflows falhando/)).toBeInTheDocument()
    // The stuck one in the "agora" line opens the oldest run.
    fireEvent.click(screen.getByRole("button", { name: /Abrir a execução presa/ }))
    expect(onAbrirPresa).toHaveBeenCalledWith("run-presa")
  })

  it("'Ver em andamento' dispara o callback nos dois estados", () => {
    const onVerEmAndamento = vi.fn()
    const { rerender } = render(
      <SaudeHero {...base} now={now()} tom="calmo" onVerEmAndamento={onVerEmAndamento} />,
    )
    fireEvent.click(screen.getByRole("button", { name: "Ver execuções em andamento" }))
    rerender(
      <SaudeHero {...base} now={now({ executors: { online: 5, total: 6 } })} tom="atencao" onVerEmAndamento={onVerEmAndamento} />,
    )
    fireEvent.click(screen.getByRole("button", { name: "Ver execuções em andamento" }))
    expect(onVerEmAndamento).toHaveBeenCalledTimes(2)
  })

  it("sem 'now' na 1ª carga mostra esqueleto (aria-busy), não 'sem leitura'", () => {
    const { container } = render(<SaudeHero {...base} now={null} tom="calmo" carregando />)
    expect(screen.queryByText("Sem leitura do instante.")).toBeNull()
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull()
  })
})
