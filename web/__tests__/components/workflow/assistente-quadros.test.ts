/**
 * Decoding the assistant's stream and assembling the conversation.
 *
 * The test that justifies this file's existence is the one for the FRAME SPLIT
 * IN HALF: the network doesn't respect message boundaries, and a `JSON.parse`
 * on half a frame brings down the whole conversation. It's the classic defect
 * of stream readers, and it doesn't show up against a fast local server — it
 * shows up on a bad network, at the user's home.
 */
import { describe, it, expect } from "vitest"

import {
  aplicarQuadro,
  cotaDoQuadro,
  criarDecodificador,
  emptyTurn,
  type AssistantTurn,
} from "@/app/components/home/assistente/quadros"

const quadro = (evento: string, dados: unknown) =>
  `event: ${evento}\ndata: ${JSON.stringify(dados)}\n\n`

describe("criarDecodificador", () => {
  it("lê um quadro inteiro", () => {
    const feed = criarDecodificador()
    expect(feed(quadro("texto", { texto: "oi" }))).toEqual([
      { evento: "texto", dados: { texto: "oi" } },
    ])
  })

  it("quadro partido no meio do JSON entre dois read() sai inteiro", () => {
    // The classic defect. Without remembering the remainder, the first chunk
    // would become a `JSON.parse` of `{"texto": "mun` and the conversation would die here.
    const feed = criarDecodificador()
    const inteiro = quadro("texto", { texto: "municípios" })
    const corte = inteiro.indexOf("munic") + 3

    expect(feed(inteiro.slice(0, corte))).toEqual([])
    expect(feed(inteiro.slice(corte))).toEqual([
      { evento: "texto", dados: { texto: "municípios" } },
    ])
  })

  it("corte exatamente entre o `\\n` e o `\\n` que fecham o quadro", () => {
    // The worst place to cut: the frame is complete but the terminator isn't.
    const feed = criarDecodificador()
    const inteiro = quadro("fim", { ok: true })

    expect(feed(inteiro.slice(0, inteiro.length - 1))).toEqual([])
    expect(feed(inteiro.slice(inteiro.length - 1))).toEqual([
      { evento: "fim", dados: { ok: true } },
    ])
  })

  it("`\\r\\n` partido entre dois pedaços ainda termina a linha", () => {
    const feed = criarDecodificador()
    expect(feed('event: texto\r\ndata: {"texto":"a"}\r')).toEqual([])
    expect(feed("\n\r\n")).toEqual([{ evento: "texto", dados: { texto: "a" } }])
  })

  it("vários quadros num pedaço só saem na ordem", () => {
    const feed = criarDecodificador()
    const saida = feed(
      quadro("pensando", { texto: "hm" }) +
        quadro("ferramenta", { id: "t1", nome: "search_nodes", argumentos: {} }) +
        quadro("ferramenta_fim", { id: "t1", nome: "search_nodes", erro: false }),
    )
    expect(saida.map(q => q.evento)).toEqual(["pensando", "ferramenta", "ferramenta_fim"])
  })

  it("quadro ilegível é descartado sem derrubar os seguintes", () => {
    const feed = criarDecodificador()
    const saida = feed(`event: texto\ndata: {não é json}\n\n${quadro("fim", { ok: true })}`)
    expect(saida).toEqual([{ evento: "fim", dados: { ok: true } }])
  })

  it("comentário de keep-alive não vira quadro", () => {
    const feed = criarDecodificador()
    expect(feed(":\n\n")).toEqual([])
    expect(feed(": ping\n\n")).toEqual([])
  })
})

// ── A conversa ───────────────────────────────────────────────────────────────

const applyAll = (eventos: [string, unknown][]): AssistantTurn =>
  eventos.reduce(
    (turno, [evento, dados]) =>
      aplicarQuadro(turno, { evento, dados: dados as Record<string, unknown> }),
    emptyTurn("t"),
  )

describe("aplicarQuadro", () => {
  it("texto em pedaços vira UM bloco, e não um bloco por delta", () => {
    const turno = applyAll([
      ["texto", { texto: "Vou " }],
      ["texto", { texto: "montar " }],
      ["texto", { texto: "o fluxo." }],
    ])
    expect(turno.blocos).toEqual([{ tipo: "texto", texto: "Vou montar o fluxo." }])
  })

  it("a linha do tempo preserva o que veio antes e depois de cada ferramenta", () => {
    // It's what keeps someone from applying a workflow without understanding
    // it: the explanation lives between the steps, not in a single field at the end.
    const turno = applyAll([
      ["pensando", { texto: "preciso do catálogo" }],
      ["texto", { texto: "Procurando nós…" }],
      ["ferramenta", { id: "t1", nome: "search_nodes", argumentos: { query: "buffer" } }],
      ["ferramenta_fim", { id: "t1", nome: "search_nodes", erro: false }],
      ["texto", { texto: "Achei." }],
    ])

    expect(turno.blocos.map(b => b.tipo)).toEqual([
      "pensando",
      "texto",
      "ferramenta",
      "texto",
    ])
    expect(turno.blocos[3]).toEqual({ tipo: "texto", texto: "Achei." })
  })

  it("ferramenta corre, recebe progresso e fecha em ok", () => {
    const turno = applyAll([
      ["ferramenta", { id: "t1", nome: "run_workflow", argumentos: { workflow_id: "abc" } }],
      ["progresso", { concluidos: 2, total: 5, mensagem: "Buffer: completed (1.2s)" }],
      ["ferramenta_fim", { id: "t1", nome: "run_workflow", erro: false }],
    ])

    expect(turno.blocos[0]).toEqual({
      tipo: "ferramenta",
      id: "t1",
      nome: "run_workflow",
      argumentos: { workflow_id: "abc" },
      estado: "ok",
      progresso: { concluidos: 2, total: 5, mensagem: "Buffer: completed (1.2s)" },
    })
  })

  it("progresso com `id` pinta a dona certa, mesmo com duas correndo", () => {
    // The tools of one round run in parallel on the backend: two are "running"
    // at the same time, and the `progresso` frame carries its owner's id.
    const turno = applyAll([
      ["ferramenta", { id: "t1", nome: "run_workflow", argumentos: {} }],
      ["ferramenta", { id: "t2", nome: "describe_node", argumentos: {} }],
      ["progresso", { id: "t1", concluidos: 3, total: 5, mensagem: "nó 3/5" }],
    ])

    expect(turno.blocos[0]).toMatchObject({
      id: "t1",
      progresso: { concluidos: 3, total: 5, mensagem: "nó 3/5" },
    })
    // t2 (the last one to "run", which the old criterion would pick) stays clean.
    expect(turno.blocos[1]).not.toHaveProperty("progresso")
  })

  it("progresso sem `id` segue no critério antigo (replay de conversa gravada)", () => {
    const turno = applyAll([
      ["ferramenta", { id: "t1", nome: "run_workflow", argumentos: {} }],
      ["progresso", { concluidos: 1, total: 4, mensagem: null }],
    ])
    expect(turno.blocos[0]).toMatchObject({
      progresso: { concluidos: 1, total: 4, mensagem: null },
    })
  })

  it("`erro: true` no fim da ferramenta marca o passo, não a conversa", () => {
    const turno = applyAll([
      ["ferramenta", { id: "t1", nome: "validate_workflow", argumentos: {} }],
      ["ferramenta_fim", { id: "t1", nome: "validate_workflow", erro: true }],
      ["fim", { ok: true, uso: { total: 10 }, voltas: 1 }],
    ])
    expect(turno.blocos[0]).toMatchObject({ estado: "erro" })
    // No error block in the conversation: the failure belongs to the step only.
    expect(turno.blocos.map(b => b.tipo)).toEqual(["ferramenta"])
  })

  it("a proposta chega inteira, com a contagem e o veredito", () => {
    const definicao = { nodes: [{ id: "a", name: "Buffer", properties: {} }], edges: [] }
    const turno = applyAll([
      ["proposta", { definicao, nos: 1, arestas: 0, ok: true, erros: 0, avisos: 1 }],
    ])

    expect(turno.blocos[0]).toEqual({
      tipo: "proposta",
      proposta: {
        definicao,
        nos: 1,
        arestas: 0,
        // Came from `validate_workflow`: it's a verdict on what is already drawn,
        // not an order to draw.
        desenhar: false,
        nota: undefined,
        ok: true,
        erros: 0,
        avisos: 1,
      },
    })
  })

  it("a ordem de DESENHAR chega marcada, com a nota do passo", () => {
    // The frame serves two roles since delivering stopped being a side effect
    // of validating. Without the flag, the panel couldn't tell "put this on
    // the screen now" from "here's what validation found" — and would redraw
    // on every verdict, undoing what the person changed in between.
    const definicao = { nodes: [{ id: "a", name: "Buffer", properties: {} }], edges: [] }
    const turno = applyAll([
      ["proposta", { definicao, nos: 1, arestas: 0, desenhar: true, nota: "liguei o buffer" }],
    ])

    expect(turno.blocos[0]).toMatchObject({
      tipo: "proposta",
      proposta: {
        desenhar: true,
        nota: "liguei o buffer",
        // No verdict: whoever draws doesn't validate.
        ok: null,
      },
    })
  })

  it("relatório ilegível vira veredito desconhecido, e não 'passou'", () => {
    // `null` is "don't know", and the card disables Apply because of it. Treating
    // it as `ok` would offer to apply a workflow nobody confirmed validates.
    const turno = applyAll([
      ["proposta", { definicao: {}, nos: 0, arestas: 0, ok: null, erros: null, avisos: null }],
    ])
    expect(turno.blocos[0]).toMatchObject({ tipo: "proposta", proposta: { ok: null, erros: null, avisos: null } })
  })

  it("o `fim` fecha ferramenta que ficou girando", () => {
    // Round ceiling, model down, tab closed: the turn can end in the middle of
    // a call. A step spinning forever would lie about what happened.
    const turno = applyAll([
      ["ferramenta", { id: "t1", nome: "run_workflow", argumentos: {} }],
      ["erro", { code: "loop_limit", message: "passou das rodadas", hint: "em partes menores" }],
      ["fim", { ok: false, uso: { entrada: 1, saida: 2, cache_leitura: 3, cache_escrita: 4, total: 10 }, voltas: 12 }],
    ])

    expect(turno.blocos[0]).toMatchObject({ estado: "erro" })
    expect(turno.blocos[1]).toEqual({
      tipo: "erro",
      erro: { code: "loop_limit", message: "passou das rodadas", hint: "em partes menores" },
    })
  })

  it("o `teto` do loop_limit atravessa até o bloco — a frase traduzida o cita", () => {
    // In English and Spanish the sentence comes from the dictionary and cites
    // the ceiling ("went past 28 tool rounds"); if the frame lost it, the
    // sentence would fall back to the text without a number.
    const turno = applyAll([["erro", { code: "loop_limit", message: "passou de 28 rodadas", teto: 28 }]])
    expect(turno.blocos[0]).toEqual({ tipo: "erro", erro: { code: "loop_limit", message: "passou de 28 rodadas", teto: 28 } })
    // A ceiling that isn't a number doesn't get in (the server sends an integer).
    const withoutCeiling = applyAll([["erro", { code: "loop_limit", message: "…", teto: "28" }]])
    expect(withoutCeiling.blocos[0]).toEqual({ tipo: "erro", erro: { code: "loop_limit", message: "…" } })
  })

  it("quadro desconhecido não quebra o painel", () => {
    // Server newer than the panel: ignoring keeps the conversation working
    // instead of bringing it down on an update.
    const turno = applyAll([
      ["texto", { texto: "oi" }],
      ["quadro_do_futuro", { seja_o_que_for: 1 }],
    ])
    expect(turno.blocos).toEqual([{ tipo: "texto", texto: "oi" }])
  })

  it("não muta o turno que recebe", () => {
    // The panel re-renders by identity: mutating in place would make React see
    // no change at all over an entire stream.
    const antes = emptyTurn("t")
    const depois = aplicarQuadro(antes, { evento: "texto", dados: { texto: "oi" } })
    expect(antes.blocos).toEqual([])
    expect(depois).not.toBe(antes)
  })
})

describe("cotaDoQuadro", () => {
  it("lê o acumulado e o teto do quadro `cota`", () => {
    expect(cotaDoQuadro({ evento: "cota", dados: { gasto: 620, teto: 1_500_000 } }))
      .toEqual({ gasto: 620, teto: 1_500_000 })
  })

  it("qualquer outro quadro, ou um `cota` malformado, vale como nenhum", () => {
    expect(cotaDoQuadro({ evento: "texto", dados: { gasto: 1, teto: 2 } })).toBeNull()
    expect(cotaDoQuadro({ evento: "cota", dados: { gasto: "620", teto: 1 } })).toBeNull()
    expect(cotaDoQuadro({ evento: "cota", dados: { gasto: 1 } })).toBeNull()
    expect(cotaDoQuadro({ evento: "cota", dados: { gasto: 1, teto: 0 } })).toBeNull()
    expect(cotaDoQuadro({ evento: "cota", dados: { gasto: -1, teto: 10 } })).toBeNull()
  })

  it("o quadro `cota` nunca vira bloco da conversa", () => {
    const turno = emptyTurn("t1")
    expect(aplicarQuadro(turno, { evento: "cota", dados: { gasto: 620, teto: 1_500_000 } })).toEqual(turno)
  })
})
