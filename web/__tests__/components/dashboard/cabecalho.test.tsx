import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react"
import { CabecalhoDoDashboard, textoDoSubtitulo } from "@/app/components/dashboard/cabecalho"

afterEach(cleanup)

const base = {
  escopo: "ativo" as const,
  onEscopo: () => {},
  periodo: 30 as const,
  onPeriodo: () => {},
  workspaceNome: "Bacia do Rio Doce",
  workspaces: 3,
  ativos: 8 as number | null,
  atualizando: false,
  onAtualizar: () => {},
}

describe("textoDoSubtitulo", () => {
  it("escopo ativo: nome do workspace e a contagem de ativos", () => {
    expect(textoDoSubtitulo("ativo", { workspaceNome: "Bacia do Rio Doce", workspaces: 3, ativos: 8 }))
      .toBe("«Bacia do Rio Doce» · 8 workflows ativos")
    // Singular do número.
    expect(textoDoSubtitulo("ativo", { workspaceNome: "Cadastro", workspaces: 1, ativos: 1 }))
      .toBe("«Cadastro» · 1 workflow ativo")
  })

  it("escopo todos: contagem de workspaces + ativos somados", () => {
    expect(textoDoSubtitulo("todos", { workspaceNome: null, workspaces: 3, ativos: 20 }))
      .toBe("Todos os workspaces · 3 workspaces · 20 workflows ativos")
  })
})

describe("CabecalhoDoDashboard", () => {
  it("título e subtítulo do escopo ativo", () => {
    render(<CabecalhoDoDashboard {...base} />)
    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument()
    expect(screen.getByText("«Bacia do Rio Doce» · 8 workflows ativos")).toBeInTheDocument()
  })

  it("toggle só com mais de um workspace, e a troca chama onEscopo", () => {
    const onEscopo = vi.fn()
    const { rerender } = render(<CabecalhoDoDashboard {...base} workspaces={1} onEscopo={onEscopo} />)
    expect(screen.queryByRole("group", { name: "Escopo do painel" })).toBeNull()

    rerender(<CabecalhoDoDashboard {...base} workspaces={3} onEscopo={onEscopo} />)
    const grupo = screen.getByRole("group", { name: "Escopo do painel" })
    expect(grupo).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Todos os workspaces" }))
    expect(onEscopo).toHaveBeenCalledWith("todos")
  })

  it("seletor de período: três janelas, a ativa marcada, e a troca chama onPeriodo", () => {
    const onPeriodo = vi.fn()
    render(<CabecalhoDoDashboard {...base} periodo={30} onPeriodo={onPeriodo} />)
    const grupo = screen.getByRole("group", { name: "Período" })
    expect(within(grupo).getAllByRole("button")).toHaveLength(3)
    // A janela ativa fica pressionada; as outras, não.
    expect(screen.getByRole("button", { name: "Últimos 30 dias" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByRole("button", { name: "Últimos 7 dias" })).toHaveAttribute("aria-pressed", "false")
    fireEvent.click(screen.getByRole("button", { name: "Últimos 90 dias" }))
    expect(onPeriodo).toHaveBeenCalledWith(90)
  })

  it("Atualizar dispara e trava enquanto recarrega", () => {
    const onAtualizar = vi.fn()
    const { rerender } = render(<CabecalhoDoDashboard {...base} onAtualizar={onAtualizar} />)
    fireEvent.click(screen.getByRole("button", { name: "Atualizar o painel" }))
    expect(onAtualizar).toHaveBeenCalledTimes(1)

    rerender(<CabecalhoDoDashboard {...base} atualizando />)
    expect(screen.getByRole("button", { name: "Atualizar o painel" })).toBeDisabled()
  })

  it("sem métricas ainda (ativos null) o subtítulo vira esqueleto", () => {
    const { container } = render(<CabecalhoDoDashboard {...base} ativos={null} />)
    expect(container.querySelector("[data-slot='skeleton']")).not.toBeNull()
    expect(screen.queryByText(/workflows ativos/)).toBeNull()
  })
})
