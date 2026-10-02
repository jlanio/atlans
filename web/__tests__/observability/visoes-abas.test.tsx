import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { VisoesAbas } from "@/app/components/observability/visoes-abas"

afterEach(cleanup)

const contagens = { execucoes: 1284, workflows: 23, executores: 5, confirmacoes: 2 }

describe("VisoesAbas", () => {
  it("tablist com as quatro visões para admin, contagens em pílula e a de confirmações vermelha com atraso", () => {
    render(<VisoesAbas visao="execucoes" onVisao={() => {}} contagens={contagens} isAdmin alerta />)
    expect(screen.getByRole("tablist", { name: "Visões do histórico" })).toBeInTheDocument()
    const abas = screen.getAllByRole("tab")
    expect(abas.map(a => a.textContent)).toEqual(["Execuções1.284", "Por workflow23", "Por executor5", "Confirmações2 atrasadas"])
    expect(abas[0]).toHaveAttribute("aria-selected", "true")
    expect(abas[1]).toHaveAttribute("aria-selected", "false")
    expect(screen.getByText("atrasadas", { exact: false }).parentElement!.className).toContain("text-red")
    abas.forEach(a => expect(a).toHaveAttribute("aria-controls", "visao-painel"))
  })

  it("sem admin, Confirmações não existe", () => {
    render(<VisoesAbas visao="execucoes" onVisao={() => {}} contagens={contagens} isAdmin={false} />)
    expect(screen.getAllByRole("tab")).toHaveLength(3)
    expect(screen.queryByRole("tab", { name: /Confirmações/ })).not.toBeInTheDocument()
  })

  it("clique e setas trocam a visão; só a ativa entra no tab order", () => {
    const onVisao = vi.fn()
    render(<VisoesAbas visao="workflows" onVisao={onVisao} contagens={contagens} isAdmin={false} />)
    const [execucoes, workflows, executores] = screen.getAllByRole("tab")
    expect(execucoes).toHaveAttribute("tabindex", "-1")
    expect(workflows).toHaveAttribute("tabindex", "0")
    fireEvent.click(executores)
    expect(onVisao).toHaveBeenCalledWith("executores")
    fireEvent.keyDown(workflows, { key: "ArrowRight" })
    expect(onVisao).toHaveBeenCalledWith("executores")
    fireEvent.keyDown(workflows, { key: "ArrowLeft" })
    expect(onVisao).toHaveBeenCalledWith("execucoes")
    fireEvent.keyDown(executores, { key: "ArrowRight" })
    // Circular: da última volta para a primeira.
    expect(onVisao).toHaveBeenLastCalledWith("execucoes")
    fireEvent.keyDown(execucoes, { key: "End" })
    expect(onVisao).toHaveBeenLastCalledWith("executores")
  })
})
