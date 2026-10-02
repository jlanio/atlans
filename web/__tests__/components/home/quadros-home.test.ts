import { describe, it, expect } from "vitest"
import { aplicarQuadro, turnoVazio } from "@/app/components/home/assistente/quadros"

/** Os quatro quadros só do assistente da Home, aditivos ao decodificador do editor. */
describe("aplicarQuadro — quadros da Home", () => {
  it("fluxo vira um bloco fluxo", () => {
    const t = aplicarQuadro(turnoVazio("t"), { evento: "fluxo", dados: { workflow_id: "w1", nome: "Focos" } })
    expect(t.blocos).toEqual([{ tipo: "fluxo", fluxo: { workflow_id: "w1", nome: "Focos" } }])
  })

  it("camada vira um bloco camada; sem available explícito é false, hint nulo vira undefined", () => {
    const t = aplicarQuadro(turnoVazio("t"), {
      evento: "camada",
      dados: { artifact_id: "a1", nome: "X", format: "geojson", available: true, hint: null },
    })
    expect(t.blocos[0]).toEqual({
      tipo: "camada",
      camada: { artifact_id: "a1", nome: "X", format: "geojson", available: true, hint: undefined },
    })

    const t2 = aplicarQuadro(turnoVazio("t"), { evento: "camada", dados: { artifact_id: "a2" } })
    expect(t2.blocos[0]).toEqual({
      tipo: "camada",
      camada: { artifact_id: "a2", nome: undefined, format: undefined, available: false, hint: undefined },
    })
  })

  it("confirmacao vira um bloco confirmacao com token e ação (args resumidos)", () => {
    const t = aplicarQuadro(turnoVazio("t"), {
      evento: "confirmacao",
      dados: { tool_use_id: "tu1", token: "TOK", acao: { tool: "delete_schedule", argumentos: { job_id: "j1" }, alvo: "X" } },
    })
    expect(t.blocos[0]).toEqual({
      tipo: "confirmacao",
      confirmacao: { tool_use_id: "tu1", token: "TOK", acao: { tool: "delete_schedule", argumentos: { job_id: "j1" }, alvo: "X" } },
    })
  })

  it("respostas_rapidas vira um bloco com as opções limpas: sem pontas, sem repetida, três no máximo", () => {
    const t = aplicarQuadro(turnoVazio("t"), {
      evento: "respostas_rapidas",
      dados: { opcoes: ["  Só os últimos 7 dias ", "Cruzar com o CAR", "Cruzar com o CAR", 4, "Agendar", "Quinta"] },
    })
    expect(t.blocos).toEqual([
      { tipo: "respostas_rapidas", opcoes: ["Só os últimos 7 dias", "Cruzar com o CAR", "Agendar"] },
    ])
  })

  it("respostas_rapidas sem opção válida não vira bloco nenhum", () => {
    for (const dados of [{}, { opcoes: [] }, { opcoes: ["", "  ", 3] }, { opcoes: "Agendar" }]) {
      const t = aplicarQuadro(turnoVazio("t"), { evento: "respostas_rapidas", dados })
      expect(t.blocos).toEqual([])
    }
  })
})
