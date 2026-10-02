/**
 * Decodificar o stream do assistente e montar a conversa.
 *
 * O teste que justifica este arquivo existir é o do QUADRO PARTIDO AO MEIO: a
 * rede não respeita fronteira de mensagem, e um `JSON.parse` em cima de meio
 * quadro derruba a conversa inteira. É o defeito clássico de quem lê stream, e
 * ele não aparece contra um servidor local rápido — aparece em rede ruim, na
 * casa de quem está usando.
 */
import { describe, it, expect } from "vitest"

import {
  aplicarQuadro,
  cotaDoQuadro,
  criarDecodificador,
  turnoVazio,
  type TurnoDoAssistente,
} from "@/app/components/home/assistente/quadros"

const quadro = (evento: string, dados: unknown) =>
  `event: ${evento}\ndata: ${JSON.stringify(dados)}\n\n`

describe("criarDecodificador", () => {
  it("lê um quadro inteiro", () => {
    const alimentar = criarDecodificador()
    expect(alimentar(quadro("texto", { texto: "oi" }))).toEqual([
      { evento: "texto", dados: { texto: "oi" } },
    ])
  })

  it("quadro partido no meio do JSON entre dois read() sai inteiro", () => {
    // O defeito clássico. Sem a memória do resto, o primeiro pedaço viraria um
    // `JSON.parse` de `{"texto": "mun` e a conversa morreria aqui.
    const alimentar = criarDecodificador()
    const inteiro = quadro("texto", { texto: "municípios" })
    const corte = inteiro.indexOf("munic") + 3

    expect(alimentar(inteiro.slice(0, corte))).toEqual([])
    expect(alimentar(inteiro.slice(corte))).toEqual([
      { evento: "texto", dados: { texto: "municípios" } },
    ])
  })

  it("corte exatamente entre o `\\n` e o `\\n` que fecham o quadro", () => {
    // O pior lugar para cortar: o quadro está completo mas o terminador não.
    const alimentar = criarDecodificador()
    const inteiro = quadro("fim", { ok: true })

    expect(alimentar(inteiro.slice(0, inteiro.length - 1))).toEqual([])
    expect(alimentar(inteiro.slice(inteiro.length - 1))).toEqual([
      { evento: "fim", dados: { ok: true } },
    ])
  })

  it("`\\r\\n` partido entre dois pedaços ainda termina a linha", () => {
    const alimentar = criarDecodificador()
    expect(alimentar('event: texto\r\ndata: {"texto":"a"}\r')).toEqual([])
    expect(alimentar("\n\r\n")).toEqual([{ evento: "texto", dados: { texto: "a" } }])
  })

  it("vários quadros num pedaço só saem na ordem", () => {
    const alimentar = criarDecodificador()
    const saida = alimentar(
      quadro("pensando", { texto: "hm" }) +
        quadro("ferramenta", { id: "t1", nome: "search_nodes", argumentos: {} }) +
        quadro("ferramenta_fim", { id: "t1", nome: "search_nodes", erro: false }),
    )
    expect(saida.map(q => q.evento)).toEqual(["pensando", "ferramenta", "ferramenta_fim"])
  })

  it("quadro ilegível é descartado sem derrubar os seguintes", () => {
    const alimentar = criarDecodificador()
    const saida = alimentar(`event: texto\ndata: {não é json}\n\n${quadro("fim", { ok: true })}`)
    expect(saida).toEqual([{ evento: "fim", dados: { ok: true } }])
  })

  it("comentário de keep-alive não vira quadro", () => {
    const alimentar = criarDecodificador()
    expect(alimentar(":\n\n")).toEqual([])
    expect(alimentar(": ping\n\n")).toEqual([])
  })
})

// ── A conversa ───────────────────────────────────────────────────────────────

const aplicarTodos = (eventos: [string, unknown][]): TurnoDoAssistente =>
  eventos.reduce(
    (turno, [evento, dados]) =>
      aplicarQuadro(turno, { evento, dados: dados as Record<string, unknown> }),
    turnoVazio("t"),
  )

describe("aplicarQuadro", () => {
  it("texto em pedaços vira UM bloco, e não um bloco por delta", () => {
    const turno = aplicarTodos([
      ["texto", { texto: "Vou " }],
      ["texto", { texto: "montar " }],
      ["texto", { texto: "o fluxo." }],
    ])
    expect(turno.blocos).toEqual([{ tipo: "texto", texto: "Vou montar o fluxo." }])
  })

  it("a linha do tempo preserva o que veio antes e depois de cada ferramenta", () => {
    // É o que impede alguém de aplicar um fluxo sem entender: a explicação mora
    // entre os passos, não num campo único no fim.
    const turno = aplicarTodos([
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
    const turno = aplicarTodos([
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
    // As ferramentas de uma volta rodam em paralelo no backend: duas ficam
    // "correndo" ao mesmo tempo, e o quadro `progresso` traz o id da dona.
    const turno = aplicarTodos([
      ["ferramenta", { id: "t1", nome: "run_workflow", argumentos: {} }],
      ["ferramenta", { id: "t2", nome: "describe_node", argumentos: {} }],
      ["progresso", { id: "t1", concluidos: 3, total: 5, mensagem: "nó 3/5" }],
    ])

    expect(turno.blocos[0]).toMatchObject({
      id: "t1",
      progresso: { concluidos: 3, total: 5, mensagem: "nó 3/5" },
    })
    // A t2 (a última a "correr", que o critério antigo escolheria) fica limpa.
    expect(turno.blocos[1]).not.toHaveProperty("progresso")
  })

  it("progresso sem `id` segue no critério antigo (replay de conversa gravada)", () => {
    const turno = aplicarTodos([
      ["ferramenta", { id: "t1", nome: "run_workflow", argumentos: {} }],
      ["progresso", { concluidos: 1, total: 4, mensagem: null }],
    ])
    expect(turno.blocos[0]).toMatchObject({
      progresso: { concluidos: 1, total: 4, mensagem: null },
    })
  })

  it("`erro: true` no fim da ferramenta marca o passo, não a conversa", () => {
    const turno = aplicarTodos([
      ["ferramenta", { id: "t1", nome: "validate_workflow", argumentos: {} }],
      ["ferramenta_fim", { id: "t1", nome: "validate_workflow", erro: true }],
      ["fim", { ok: true, uso: { total: 10 }, voltas: 1 }],
    ])
    expect(turno.blocos[0]).toMatchObject({ estado: "erro" })
    // Nenhum bloco de erro da conversa: a falha é só do passo.
    expect(turno.blocos.map(b => b.tipo)).toEqual(["ferramenta"])
  })

  it("a proposta chega inteira, com a contagem e o veredito", () => {
    const definicao = { nodes: [{ id: "a", name: "Buffer", properties: {} }], edges: [] }
    const turno = aplicarTodos([
      ["proposta", { definicao, nos: 1, arestas: 0, ok: true, erros: 0, avisos: 1 }],
    ])

    expect(turno.blocos[0]).toEqual({
      tipo: "proposta",
      proposta: {
        definicao,
        nos: 1,
        arestas: 0,
        // Veio de `validate_workflow`: e veredito do que ja esta desenhado, nao
        // ordem de desenhar.
        desenhar: false,
        nota: undefined,
        ok: true,
        erros: 0,
        avisos: 1,
      },
    })
  })

  it("a ordem de DESENHAR chega marcada, com a nota do passo", () => {
    // O quadro serve a dois papeis desde que entregar deixou de ser efeito
    // colateral de validar. Sem a marca, o painel nao saberia distinguir
    // "poe isto na tela agora" de "eis o que a validacao achou" — e desenharia
    // de novo a cada veredito, desfazendo o que a pessoa mexeu no meio.
    const definicao = { nodes: [{ id: "a", name: "Buffer", properties: {} }], edges: [] }
    const turno = aplicarTodos([
      ["proposta", { definicao, nos: 1, arestas: 0, desenhar: true, nota: "liguei o buffer" }],
    ])

    expect(turno.blocos[0]).toMatchObject({
      tipo: "proposta",
      proposta: {
        desenhar: true,
        nota: "liguei o buffer",
        // Sem veredito: quem desenha nao valida.
        ok: null,
      },
    })
  })

  it("relatório ilegível vira veredito desconhecido, e não 'passou'", () => {
    // `null` é "não sei", e o cartão desliga o Aplicar por isso. Tratar como
    // `ok` seria oferecer aplicar um fluxo que ninguém confirmou que valida.
    const turno = aplicarTodos([
      ["proposta", { definicao: {}, nos: 0, arestas: 0, ok: null, erros: null, avisos: null }],
    ])
    expect(turno.blocos[0]).toMatchObject({ tipo: "proposta", proposta: { ok: null, erros: null, avisos: null } })
  })

  it("o `fim` fecha ferramenta que ficou girando", () => {
    // Teto de voltas, modelo fora do ar, aba fechada: o turno pode acabar no
    // meio de uma chamada. Um passo girando para sempre mentiria sobre o que
    // aconteceu.
    const turno = aplicarTodos([
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
    // Em inglês e espanhol a frase é do dicionário e cita o teto ("went past 28
    // tool rounds"); se o quadro o perdesse, a frase cairia no texto sem número.
    const turno = aplicarTodos([["erro", { code: "loop_limit", message: "passou de 28 rodadas", teto: 28 }]])
    expect(turno.blocos[0]).toEqual({ tipo: "erro", erro: { code: "loop_limit", message: "passou de 28 rodadas", teto: 28 } })
    // Teto que não é número não entra (o servidor manda inteiro).
    const semTeto = aplicarTodos([["erro", { code: "loop_limit", message: "…", teto: "28" }]])
    expect(semTeto.blocos[0]).toEqual({ tipo: "erro", erro: { code: "loop_limit", message: "…" } })
  })

  it("quadro desconhecido não quebra o painel", () => {
    // Servidor mais novo que o painel: ignorar mantém a conversa funcionando
    // em vez de derrubá-la numa atualização.
    const turno = aplicarTodos([
      ["texto", { texto: "oi" }],
      ["quadro_do_futuro", { seja_o_que_for: 1 }],
    ])
    expect(turno.blocos).toEqual([{ tipo: "texto", texto: "oi" }])
  })

  it("não muta o turno que recebe", () => {
    // O painel re-renderiza por identidade: mutar no lugar faria o React não
    // ver mudança nenhuma num stream inteiro.
    const antes = turnoVazio("t")
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
    const turno = turnoVazio("t1")
    expect(aplicarQuadro(turno, { evento: "cota", dados: { gasto: 620, teto: 1_500_000 } })).toEqual(turno)
  })
})
