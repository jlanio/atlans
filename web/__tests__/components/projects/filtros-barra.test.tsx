import { afterEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react"
import { BarraDeFiltros } from "@/app/components/projects/filtros-barra"
import { ESTADO_PADRAO, FILTROS, type EstadoDeProjetos, type Filtro } from "@/app/components/projects/projetos-url"

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

function estado(extra: Partial<EstadoDeProjetos> = {}): EstadoDeProjetos {
  return { ...ESTADO_PADRAO, ...extra }
}

const contagens = Object.fromEntries(FILTROS.map(f => [f, 0])) as Record<Filtro, number>
Object.assign(contagens, { todos: 10, ativos: 8, inativos: 2, executando: 1, falha: 2, agendados: 4, webhook: 1, subfluxos: 1, portal: 2, assistente: 3, pausado: 1, nunca: 3 })

const base = {
  onEstado: () => {}, onLimpar: () => {}, contagens, temGrupos: true, todosRecolhidos: false,
  onRecolherTodos: () => {}, onExpandirTodos: () => {},
}

describe("BarraDeFiltros", () => {
  it("dez chips na ordem da tela, com contagem; o ativo tem aria-pressed; o clique escreve o estado", () => {
    const onEstado = vi.fn()
    render(<BarraDeFiltros {...base} estado={estado()} onEstado={onEstado} />)
    const grupo = screen.getByRole("group", { name: "Filtros" })
    const chips = within(grupo).getAllByRole("button")
    expect(chips.map(c => c.textContent)).toEqual([
      "Todos10", "Ativos8", "Inativos2", "Em execução1", "Com falha2", "Agendados4", "Webhook1", "Sub-fluxos1", "Com portal2",
      "Assistente3",
    ])
    expect(chips.map(c => c.getAttribute("aria-pressed")))
      .toEqual(["true", ...Array(9).fill("false")])

    fireEvent.click(screen.getByRole("button", { name: /Com falha/ }))
    expect(onEstado).toHaveBeenCalledWith({ filtro: "falha" })
  })

  it("clicar no chip já ativo volta para Todos", () => {
    const onEstado = vi.fn()
    render(<BarraDeFiltros {...base} estado={estado({ filtro: "falha" })} onEstado={onEstado} />)
    const falha = screen.getByRole("button", { name: /Com falha/ })
    expect(falha).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByRole("button", { name: /^Todos/ })).toHaveAttribute("aria-pressed", "false")
    fireEvent.click(falha)
    expect(onEstado).toHaveBeenCalledWith({ filtro: "todos" })
  })

  it("filtro que só existe na URL (pausado) ganha um chip provisório marcado, e Todos fica desmarcado", () => {
    render(<BarraDeFiltros {...base} estado={estado({ filtro: "pausado" })} />)
    const chip = screen.getByRole("button", { name: /Agendamento pausado/ })
    expect(chip).toHaveAttribute("aria-pressed", "true")
    expect(chip).toHaveTextContent("1")
    expect(screen.getByRole("button", { name: /^Todos/ })).toHaveAttribute("aria-pressed", "false")
    expect(screen.getByRole("button", { name: /Limpar filtros/ })).toBeInTheDocument()
  })

  it("'Limpar filtros' só aparece com busca ou chip ativo", () => {
    const onLimpar = vi.fn()
    const { rerender } = render(<BarraDeFiltros {...base} estado={estado()} onLimpar={onLimpar} />)
    expect(screen.queryByRole("button", { name: /Limpar filtros/ })).toBeNull()
    rerender(<BarraDeFiltros {...base} estado={estado({ ordem: "alterado" })} onLimpar={onLimpar} />)
    expect(screen.queryByRole("button", { name: /Limpar filtros/ })).toBeNull()
    rerender(<BarraDeFiltros {...base} estado={estado({ q: "bacia" })} onLimpar={onLimpar} />)
    fireEvent.click(screen.getByRole("button", { name: /Limpar filtros/ }))
    expect(onLimpar).toHaveBeenCalledTimes(1)
  })

  it("busca com o placeholder da spec, esperando um instante parada antes de subir", () => {
    vi.useFakeTimers()
    const onEstado = vi.fn()
    render(<BarraDeFiltros {...base} estado={estado()} onEstado={onEstado} />)
    const busca = screen.getByRole("searchbox", { name: "Buscar workflow ou grupo" })
    expect(busca).toHaveAttribute("placeholder", "Buscar workflow ou grupo…")
    fireEvent.change(busca, { target: { value: "hidro" } })
    fireEvent.change(busca, { target: { value: "hidrologia" } })
    act(() => { vi.advanceTimersByTime(100) })
    expect(onEstado).not.toHaveBeenCalled()
    act(() => { vi.advanceTimersByTime(150) })
    expect(onEstado).toHaveBeenCalledTimes(1)
    expect(onEstado).toHaveBeenCalledWith({ q: "hidrologia" })
  })

  it("quando a URL zera a busca por fora, o campo acompanha", () => {
    const { rerender } = render(<BarraDeFiltros {...base} estado={estado({ q: "bacia" })} />)
    expect(screen.getByRole("searchbox")).toHaveValue("bacia")
    rerender(<BarraDeFiltros {...base} estado={estado({ q: "" })} />)
    expect(screen.getByRole("searchbox")).toHaveValue("")
  })

  it("ordenação mostra o rótulo em vigor", () => {
    const { rerender } = render(<BarraDeFiltros {...base} estado={estado()} />)
    expect(screen.getByRole("combobox", { name: "Ordenar" })).toHaveTextContent("Ordenar:Nome")
    rerender(<BarraDeFiltros {...base} estado={estado({ ordem: "execucao" })} />)
    expect(screen.getByRole("combobox", { name: "Ordenar" })).toHaveTextContent("Última execução")
  })

  it("Recolher/Expandir todos só com grupos, e o rótulo segue o estado", () => {
    const onRecolher = vi.fn()
    const onExpandir = vi.fn()
    const { rerender } = render(<BarraDeFiltros {...base} estado={estado()} temGrupos={false} />)
    expect(screen.queryByRole("button", { name: /todos$/ })).toBeNull()

    rerender(<BarraDeFiltros {...base} estado={estado()} onRecolherTodos={onRecolher} onExpandirTodos={onExpandir} />)
    fireEvent.click(screen.getByRole("button", { name: "Recolher todos" }))
    expect(onRecolher).toHaveBeenCalledTimes(1)

    rerender(<BarraDeFiltros {...base} estado={estado()} todosRecolhidos onRecolherTodos={onRecolher} onExpandirTodos={onExpandir} />)
    fireEvent.click(screen.getByRole("button", { name: "Expandir todos" }))
    expect(onExpandir).toHaveBeenCalledTimes(1)
  })
})
