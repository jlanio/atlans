import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import {
  ErroDeCarga, MetricasIndisponiveis, SemResultado, SkeletonDeProjetos, VazioPrimeiroUso, textoDeSemResultado,
} from "@/app/components/projects/estados"

afterEach(cleanup)

describe("SkeletonDeProjetos", () => {
  it("marca a região como ocupada e desenha um grupo com três linhas mais duas soltas", () => {
    const { container } = render(<SkeletonDeProjetos />)
    expect(screen.getByLabelText("Carregando projetos")).toHaveAttribute("aria-busy", "true")
    expect(container.querySelectorAll(".h-14")).toHaveLength(5)
    expect(container.querySelectorAll("[data-slot='skeleton']").length).toBeGreaterThan(5)
  })
})

describe("VazioPrimeiroUso", () => {
  it("com permissão: título, explicação, três passos e o botão de criar", () => {
    const onCriar = vi.fn()
    render(<VazioPrimeiroUso canEdit onCriar={onCriar} />)
    expect(screen.getByText("Comece pelo primeiro workflow")).toBeInTheDocument()
    expect(screen.getByText(/Um workflow encadeia nós de leitura, processamento e saída/)).toBeInTheDocument()
    expect(screen.getAllByRole("listitem").map(li => li.querySelector(".font-medium")?.textContent))
      .toEqual(["Desenhe", "Execute uma vez", "Agende ou exponha"])
    fireEvent.click(screen.getByRole("button", { name: "Criar o primeiro workflow" }))
    expect(onCriar).toHaveBeenCalledTimes(1)
  })

  it("sem permissão: pede a um editor, sem botão", () => {
    render(<VazioPrimeiroUso canEdit={false} onCriar={() => {}} />)
    expect(screen.getByText("Peça a um editor do workspace para criar o primeiro workflow.")).toBeInTheDocument()
    expect(screen.queryByRole("button")).toBeNull()
  })
})

describe("SemResultado", () => {
  it("textoDeSemResultado cobre busca, filtro e os dois juntos", () => {
    expect(textoDeSemResultado("bacia", "todos")).toBe("Nenhum workflow com «bacia»")
    expect(textoDeSemResultado("", "falha")).toBe("Nenhum workflow com este filtro")
    expect(textoDeSemResultado(" bacia ", "falha")).toBe("Nenhum workflow com «bacia» e este filtro")
    expect(textoDeSemResultado("", "todos")).toBe("Nenhum workflow")
  })

  it("diz quantos há sem o filtro e oferece limpar", () => {
    const onLimpar = vi.fn()
    render(<SemResultado q="bacia" filtro="falha" semFiltro={3} onLimpar={onLimpar} />)
    expect(screen.getByText("Nenhum workflow com «bacia» e este filtro")).toBeInTheDocument()
    expect(screen.getByText("Há 3 com «bacia» sem o filtro.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }))
    expect(onLimpar).toHaveBeenCalledTimes(1)
  })

  it("sem contagem alternativa, a frase extra não aparece", () => {
    render(<SemResultado q="" filtro="webhook" semFiltro={null} onLimpar={() => {}} />)
    expect(screen.getByText("Nenhum workflow com este filtro")).toBeInTheDocument()
    expect(screen.queryByText(/sem o filtro/)).toBeNull()
  })
})

describe("ErroDeCarga e MetricasIndisponiveis", () => {
  it("erro: título, mensagem e Tentar de novo", () => {
    const onTentar = vi.fn()
    render(<ErroDeCarga mensagem="Falha de rede" onTentar={onTentar} />)
    expect(screen.getByText("Não foi possível carregar os projetos")).toBeInTheDocument()
    expect(screen.getByText("Falha de rede")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }))
    expect(onTentar).toHaveBeenCalledTimes(1)
  })

  it("métricas: aviso de uma linha, com status e Tentar de novo", () => {
    const onTentar = vi.fn()
    render(<MetricasIndisponiveis onTentar={onTentar} />)
    expect(screen.getByRole("status")).toHaveTextContent("Sem dados de execução agora — a lista continua completa.")
    fireEvent.click(screen.getByRole("button", { name: "Tentar de novo" }))
    expect(onTentar).toHaveBeenCalledTimes(1)
  })
})
