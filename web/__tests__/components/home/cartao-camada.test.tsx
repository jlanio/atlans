import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"

import CartaoCamada from "@/app/components/home/assistente/cartao-camada"

/** O cartão de camada pipoca ao chegar (`home-pop`) — nos dois ramos. */
describe("CartaoCamada", () => {
  it("disponível: 'no globo', com o pop", () => {
    render(<CartaoCamada camada={{ artifact_id: "a1", nome: "Focos", available: true }} />)
    expect(screen.getByText(/Focos no globo/).closest("div")!.classList.contains("home-pop")).toBe(true)
  })

  it("sem prévia: o motivo, com o pop", () => {
    render(<CartaoCamada camada={{ artifact_id: "a1", nome: "Malha", available: false, hint: "fica no executor" }} />)
    expect(screen.getByText(/fica no executor/).closest("div")!.classList.contains("home-pop")).toBe(true)
  })
})
