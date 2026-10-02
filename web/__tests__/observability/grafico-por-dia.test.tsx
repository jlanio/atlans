import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import type { IRunsByDay } from "@/service/types"

// O Recharts entra por `dynamic()` e não pinta nada em jsdom (ResponsiveContainer
// mede 0×0). O que se testa aqui é o card: título, subtítulo, legenda, estados.
vi.mock("next/dynamic", () => ({
  default: () => function BarrasDubladas({ dias }: { dias: IRunsByDay[] }) {
    return <div data-testid="barras">{dias.length} dias</div>
  },
}))

import { GraficoPorDia, subtituloDoGrafico } from "@/app/components/observability/grafico-por-dia"
import { intervaloDosTicks } from "@/app/components/observability/grafico-por-dia-barras"

afterEach(cleanup)

const dias: IRunsByDay[] = [
  { day: "2026-08-08", total: 40, success: 38, failed: 2, running: 0, cancelled: 0 },
  { day: "2026-08-09", total: 70, success: 65, failed: 4, running: 1, cancelled: 0 },
  { day: "2026-08-10", total: 12, success: 12, failed: 0, running: 0, cancelled: 0 },
]

describe("GraficoPorDia", () => {
  it("título, subtítulo com faixa e pico, legenda das quatro séries e o corpo", () => {
    render(<GraficoPorDia dias={dias} periodo={7} carregando={false} />)
    expect(screen.getByRole("heading", { name: "Execuções por dia" })).toBeInTheDocument()
    expect(screen.getByText("de 8 ago a 10 ago · pico de 70 em 9 ago")).toBeInTheDocument()
    const legenda = screen.getByLabelText("Legenda")
    expect(Array.from(legenda.querySelectorAll("li")).map(li => li.textContent)).toEqual(["Concluídas", "Falhas", "Em andamento", "Canceladas"])
    expect(screen.getByTestId("barras")).toHaveTextContent("3 dias")
  })

  it("skeleton na primeira carga; 'sem execuções' quando a janela está zerada", () => {
    const { container, rerender } = render(<GraficoPorDia dias={[]} periodo={30} carregando />)
    expect(container.querySelector("[data-slot='skeleton']")).not.toBeNull()
    expect(screen.getByText("últimos 30 dias")).toBeInTheDocument()

    rerender(<GraficoPorDia dias={dias.map(d => ({ ...d, total: 0, success: 0, failed: 0, running: 0 }))} periodo={30} carregando={false} />)
    expect(screen.getByText("Sem execuções no período.")).toBeInTheDocument()
    expect(screen.queryByTestId("barras")).toBeNull()
  })

  it("falha parcial: aviso e a última leitura continua desenhada", () => {
    render(<GraficoPorDia dias={dias} periodo={30} carregando={false} falha="Não foi possível carregar as execuções por dia." />)
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível carregar as execuções por dia. Mostrando a última leitura.")
    expect(screen.getByTestId("barras")).toBeInTheDocument()
  })

  it("subtítulo e ticks", () => {
    expect(subtituloDoGrafico([])).toBeNull()
    expect(subtituloDoGrafico([dias[0]])).toBe("8 ago · pico de 40 em 8 ago")
    expect(subtituloDoGrafico(dias.map(d => ({ ...d, total: 0 })))).toBe("de 8 ago a 10 ago")
    expect(intervaloDosTicks(7)).toBe(0)
    expect(intervaloDosTicks(30)).toBe(4)
    expect(intervaloDosTicks(90)).toBe(12)
  })
})
