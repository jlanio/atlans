/**
 * Reading of the assistant stream that the Home and the editor drawer share
 * (`home/assistente/stream.ts`). What the hooks test from the outside — quota, turn,
 * stop — is not repeated here; what stays here is what belongs to the piece itself.
 */
import { describe, it, expect, vi } from "vitest"

import { erroDaResposta, lerQuadrosSSE, type ErrosDaRota } from "@/app/components/home/assistente/stream"
import type { QuadroSSE } from "@/app/components/home/assistente/quadros"

/** A body that delivers exactly the given chunks, and records whether it was canceled. */
function corpoEmPedacos(pedacos: Uint8Array[]) {
  const estado = { cancelado: false }
  let i = 0
  const corpo = new ReadableStream<Uint8Array>({
    pull(controle) {
      if (i < pedacos.length) controle.enqueue(pedacos[i++])
      else controle.close()
    },
    cancel() { estado.cancelado = true },
  })
  return { corpo, estado }
}

describe("lerQuadrosSSE", () => {
  it("um caractere de vários bytes partido entre dois read() chega inteiro", async () => {
    const bytes = new TextEncoder().encode('event: texto\ndata: {"texto":"atenção"}\n\n')
    // Cuts in the middle of the "ç" (two bytes in UTF-8).
    const corte = bytes.indexOf(0xc3) + 1
    const { corpo } = corpoEmPedacos([bytes.slice(0, corte), bytes.slice(corte)])

    const quadros: QuadroSSE[] = []
    await lerQuadrosSSE(corpo, (q) => quadros.push(q))

    expect(quadros).toEqual([{ evento: "texto", dados: { texto: "atenção" } }])
  })

  it("um quadro que o tratar não digere solta o leitor — e o erro chega a quem chamou", async () => {
    const bytes = new TextEncoder().encode('event: texto\ndata: {"texto":"a"}\n\nevent: texto\ndata: {"texto":"b"}\n\n')
    const { corpo, estado } = corpoEmPedacos([bytes, new Uint8Array([0x3a])])

    const tratar = vi.fn(() => { throw new Error("quadro indigesto") })
    await expect(lerQuadrosSSE(corpo, tratar)).rejects.toThrow("quadro indigesto")
    expect(estado.cancelado).toBe(true)
  })
})

describe("erroDaResposta", () => {
  // Two fake tables, like those of the two routes: the same status says different
  // things in each one, and that is why the table comes in as a parameter.
  const HOME: ErrosDaRota = { 409: { code: "expirada", message: "A confirmação expirou." } }
  const EDITOR: ErrosDaRota = { 409: { code: "conversa_em_andamento", message: "Já há uma conversa." } }
  const resposta = (status: number, corpo?: unknown) =>
    ({ status, json: async () => { if (corpo === undefined) throw new SyntaxError("sem corpo"); return corpo } }) as Response

  it("usa a tabela da rota que recusou", async () => {
    expect(await erroDaResposta(resposta(409), HOME)).toEqual({ code: "expirada", message: "A confirmação expirou." })
    expect(await erroDaResposta(resposta(409), EDITOR)).toEqual({ code: "conversa_em_andamento", message: "Já há uma conversa." })
  })

  it("a frase do servidor vence a da tabela — em `message` ou em `detail`", async () => {
    expect(await erroDaResposta(resposta(409, { message: "Outra frase." }), HOME))
      .toEqual({ code: "expirada", message: "Outra frase." })
    expect(await erroDaResposta(resposta(409, { detail: "Pelo detail." }), EDITOR))
      .toEqual({ code: "conversa_em_andamento", message: "Pelo detail." })
  })

  it("status fora da tabela vira erro_http, sem 'undefined'", async () => {
    expect(await erroDaResposta(resposta(502), HOME)).toEqual({ code: "erro_http", message: "A API respondeu 502." })
  })
})
