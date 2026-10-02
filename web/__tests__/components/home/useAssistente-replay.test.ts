import { describe, it, expect } from "vitest"
import { reconstruirTurnos } from "@/app/hooks/home/useAssistente"
import type { IQuadroDoReplay } from "@/service/types"

const q = (tipo: string, dados: Record<string, unknown> = {}): IQuadroDoReplay => ({ tipo, dados })

/** O replay reconstrói a conversa a partir dos quadros de GET /conversas/{id}. */
describe("reconstruirTurnos", () => {
  it("usuário → assistente, com o fim no último turno do assistente", () => {
    const turnos = reconstruirTurnos([
      q("usuario", { texto: "oi" }),
      q("texto", { texto: "olá" }),
      q("ferramenta", { id: "f1", nome: "run_workflow", argumentos: {} }),
      q("fim", { uso: { total: 42 }, ok: true }),
    ])
    expect(turnos).toHaveLength(2)
    expect(turnos[0]).toMatchObject({ papel: "user", texto: "oi" })
    expect(turnos[1].papel).toBe("assistant")
    expect(turnos[1].blocos.map((b) => b.tipo)).toEqual(["texto", "ferramenta"])
    // O `fim` chegou ao turno do assistente: a ferramenta que ficou aberta fecha.
    expect(turnos[1].blocos[1]).toMatchObject({ estado: "erro" })
  })

  it("pula a mensagem sintética de confirmação e o quadro conversa", () => {
    const turnos = reconstruirTurnos([
      q("conversa", { conversa_id: "c1" }),
      q("usuario", { texto: "[Ação confirmada pela pessoa pelo botão]…", meta: { tipo: "confirmacao" } }),
      q("texto", { texto: "feito" }),
      q("fim", { uso: { total: 1 } }),
    ])
    expect(turnos).toHaveLength(1)
    expect(turnos[0].papel).toBe("assistant")
    expect(turnos[0].blocos[0]).toMatchObject({ tipo: "texto", texto: "feito" })
  })

  it("reabre a confirmação e o fluxo como blocos", () => {
    const turnos = reconstruirTurnos([
      q("usuario", { texto: "pausa X" }),
      q("fluxo", { workflow_id: "w1", nome: "A" }),
      q("confirmacao", { tool_use_id: "tu1", token: "TOK", acao: { tool: "delete_schedule", argumentos: {}, alvo: "X" } }),
      q("fim", { uso: { total: 0 } }),
    ])
    const assistente = turnos[1]
    expect(assistente.blocos.map((b) => b.tipo)).toEqual(["fluxo", "confirmacao"])
  })

  it("dois pares usuário/assistente", () => {
    const turnos = reconstruirTurnos([
      q("usuario", { texto: "a" }), q("texto", { texto: "1" }),
      q("usuario", { texto: "b" }), q("texto", { texto: "2" }),
      q("fim", { uso: { total: 0 } }),
    ])
    expect(turnos.map((t) => t.papel)).toEqual(["user", "assistant", "user", "assistant"])
  })
})
