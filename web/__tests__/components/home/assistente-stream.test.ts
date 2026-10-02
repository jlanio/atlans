/**
 * A leitura do stream do assistente que a Home e a gaveta do editor dividem
 * (`home/assistente/stream.ts`). O que os hooks testam por fora — cota, turno,
 * parar — não se repete aqui; aqui fica o que é da peça em si.
 */
import { describe, it, expect, vi } from "vitest"

import { erroDaResposta, lerQuadrosSSE, type ErrosDaRota } from "@/app/components/home/assistente/stream"
import type { QuadroSSE } from "@/app/components/home/assistente/quadros"

/** Um corpo que entrega exatamente os pedaços dados, e anota se foi cancelado. */
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
    // Corta no meio do "ç" (dois bytes em UTF-8).
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
  // Duas tabelas de mentira, como as das duas rotas: o mesmo status diz coisas
  // diferentes em cada uma, e é por isso que a tabela entra por parâmetro.
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
