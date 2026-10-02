/**
 * Aplicar a proposta do painel no canvas.
 *
 * O que estes testes protegem é uma coisa só, e é a que estraga o trabalho de
 * alguém: a definição proposta NÃO TEM POSIÇÃO. Sem a preservação, `buildNodes`
 * cai no default `{x: 180 * indice, y: 0}` e o clique em Aplicar enfileira doze
 * cards numa linha horizontal, apagando o desenho que a pessoa arrumou à mão.
 *
 * Por isso a asserção central não é "aplicou": é que os nós que sobreviveram
 * continuam EXATAMENTE onde estavam, e que o nó novo não pousa em cima de
 * nenhum deles.
 */
import { describe, it, expect } from "vitest"

import { aplicarProposta } from "@/app/components/workflow/utils/aplicar-proposta"
import { buildNodes, CanvasDefinition } from "@/app/components/workflow/utils/build-canvas"
import { INodeContext } from "@/context/useFlowContext"
import { INodesAPI } from "@/service/types"

const catalogo = [
  {
    name: "DriveFile",
    alias: "Arquivo do Drive",
    description: "Lê um arquivo",
    type: "trigger",
    properties: [{ name: "file_id", label: "Arquivo", type: "string", default: "" }],
    outputs: [{ name: "output" }],
  },
  {
    name: "Buffer",
    alias: "Buffer",
    description: "Aplica buffer",
    type: "action",
    // Duas propriedades de propósito: com uma só, inverter a ordem das chaves
    // não inverte nada e o teste de ordem passaria sem morder.
    properties: [
      { name: "distance", label: "Distância", type: "string", default: "" },
      { name: "unit", label: "Unidade", type: "string", default: "m" },
    ],
    outputs: [{ name: "output" }],
  },
  {
    name: "Dissolve",
    alias: "Dissolver",
    description: "Dissolve por campo",
    type: "action",
    properties: [{ name: "field", label: "Campo", type: "string", default: "" }],
    outputs: [{ name: "output" }],
  },
  {
    name: "DataOutput",
    alias: "Saída de Dados",
    description: "Entrega o resultado",
    type: "output",
    properties: [],
    outputs: [],
  },
] as unknown as INodesAPI[]

/** O canvas de quem já trabalhou no fluxo: três cards arrumados à mão. */
const ARRUMADO = {
  nodes: [
    { id: "a", name: "DriveFile", properties: { file_id: "mun.shp" }, position: { x: 120, y: 480 }, type: "trigger" },
    { id: "b", name: "Buffer", properties: { distance: "500" }, position: { x: 700, y: 96 }, type: "action" },
    { id: "c", name: "Dissolve", properties: { field: "uf" }, position: { x: 1240, y: 820 }, type: "action" },
  ],
  edges: [
    { source: "a", target: "b" },
    { source: "b", target: "c" },
  ],
} as unknown as CanvasDefinition

/** A proposta do assistente: sem posição nenhuma, como ela chega de verdade. */
const PROPOSTA = {
  nodes: [
    { id: "a", name: "DriveFile", properties: { file_id: "mun.shp" } },
    { id: "b", name: "Buffer", properties: { distance: "1000" } }, // mudou
    { id: "c", name: "Dissolve", properties: { field: "uf" } },
    { id: "d", name: "DataOutput", properties: {} }, // novo
  ],
  edges: [
    { source: "a", target: "b" },
    { source: "b", target: "c" },
    { source: "c", target: "d" },
  ],
} as unknown as CanvasDefinition

const noCanvas = () => buildNodes(ARRUMADO, catalogo)

const acharNo = (nodes: INodeContext[], id: string) => {
  const achado = nodes.find(n => n.id === id)
  if (!achado) throw new Error(`nó ${id} não saiu na aplicação`)
  return achado
}

describe("aplicarProposta", () => {
  it("preserva a posição de quem sobreviveu e dá layout só ao nó novo", () => {
    const atuais = noCanvas()
    const { nodes } = aplicarProposta(PROPOSTA, catalogo, atuais)

    // A asserção que importa: os três cards não se mexeram um pixel.
    expect(acharNo(nodes, "a").position).toEqual({ x: 120, y: 480 })
    expect(acharNo(nodes, "b").position).toEqual({ x: 700, y: 96 })
    expect(acharNo(nodes, "c").position).toEqual({ x: 1240, y: 820 })

    // E o novo NÃO nasceu na fila horizontal do default do `buildNodes`
    // (`d` é o índice 3 → x = 540, y = 0).
    const novo = acharNo(nodes, "d").position
    expect(novo).not.toEqual({ x: 540, y: 0 })
    expect(Number.isFinite(novo.x) && Number.isFinite(novo.y)).toBe(true)
  })

  it("o valor alterado chega ao canvas — preservar posição não é congelar o nó", () => {
    const { nodes } = aplicarProposta(PROPOSTA, catalogo, noCanvas())
    expect(acharNo(nodes, "b").data.properties.distance).toBe("1000")
  })

  it("nó novo não pousa em cima de um card preservado", () => {
    // Primeiro descobrimos onde o layout quer pôr o `d`, com os preservados
    // longe demais para atrapalhar.
    const longe = noCanvas().map(no => ({ ...no, position: { x: 4000, y: 4000 } }))
    const alvo = acharNo(aplicarProposta(PROPOSTA, catalogo, longe).nodes, "d").position

    // Agora um card preservado está EXATAMENTE nesse ponto.
    const emCima = noCanvas().map(no => (no.id === "a" ? { ...no, position: { ...alvo } } : no))
    const { nodes } = aplicarProposta(PROPOSTA, catalogo, emCima)

    // O preservado manda: quem desce é o novo.
    expect(acharNo(nodes, "a").position).toEqual(alvo)
    expect(acharNo(nodes, "d").position.y).toBeGreaterThan(alvo.y)
  })

  it("conta o que vai acontecer: novos, alterados e removidos", () => {
    // É a contagem que o cartão mostra ANTES do clique. Aplicar com o canvas
    // cheio é destrutivo por decisão, então o número precisa estar certo.
    const { resumo } = aplicarProposta(PROPOSTA, catalogo, noCanvas())
    expect(resumo).toEqual({ novos: 1, alterados: 1, removidos: 0 })
  })

  it("nó que o assistente não trouxe conta como removido", () => {
    const semOC = {
      nodes: [{ id: "a", name: "DriveFile", properties: { file_id: "mun.shp" } }],
      edges: [],
    } as unknown as CanvasDefinition

    const { resumo } = aplicarProposta(semOC, catalogo, noCanvas())
    expect(resumo).toEqual({ novos: 0, alterados: 0, removidos: 2 })
  })

  it("ordem das chaves de `properties` não é alteração", () => {
    // O editor monta `properties` pela ordem do catálogo; o drawer copia o
    // objeto do catálogo inteiro. Ordem diferente não é mudança nenhuma, e
    // contar como tal faria o cartão anunciar alteração em nó que ninguém tocou.
    const atuais = noCanvas().map(no => ({
      ...no,
      data: { ...no.data, properties: Object.fromEntries(Object.entries(no.data.properties).reverse()) },
    }))
    const igual = {
      nodes: ARRUMADO.nodes?.map(({ id, name, properties }) => ({ id, name, properties })),
      edges: ARRUMADO.edges,
    } as unknown as CanvasDefinition

    expect(aplicarProposta(igual, catalogo, atuais).resumo.alterados).toBe(0)
  })

  it("monta as arestas da proposta, e não as do canvas", () => {
    const { edges } = aplicarProposta(PROPOSTA, catalogo, noCanvas())
    expect(edges).toHaveLength(3)
    expect(edges.map(e => `${e.source}→${e.target}`)).toEqual(["a→b", "b→c", "c→d"])
  })

  it("mantém a ordem da definição, para o canvas não embaralhar a cada aplicação", () => {
    const { nodes } = aplicarProposta(PROPOSTA, catalogo, noCanvas())
    expect(nodes.map(n => n.id)).toEqual(["a", "b", "c", "d"])
  })

  it("sem catálogo, avisa em vez de esvaziar o canvas", () => {
    // `buildNodes` sem catálogo devolve []. Aplicar nesse instante APAGARIA o
    // fluxo inteiro, em silêncio — o pior desfecho possível deste botão.
    const semCatalogo = aplicarProposta(PROPOSTA, [], noCanvas())
    expect(semCatalogo.catalogoPronto).toBe(false)
    expect(semCatalogo.nodes).toEqual([])

    expect(aplicarProposta(PROPOSTA, catalogo, noCanvas()).catalogoPronto).toBe(true)
  })

  it("proposta vazia é aplicável — é assim que se limpa o canvas", () => {
    const vazia = aplicarProposta({ nodes: [], edges: [] }, catalogo, noCanvas())
    expect(vazia.catalogoPronto).toBe(true)
    expect(vazia.nodes).toEqual([])
    expect(vazia.resumo.removidos).toBe(3)
  })

  it("só quem chegou AGORA entra na animação", () => {
    // O assistente desenha a cada passo, e cada desenho manda a definição
    // INTEIRA. Sem a lista de quem é novo, o canvas animaria o fluxo todo a
    // cada nó acrescentado — um piscar completo doze vezes seguidas, que é o
    // oposto de acompanhar a montagem.
    const jaNaTela = aplicarProposta(PROPOSTA, catalogo, []).nodes
    const idJaNaTela = jaNaTela[0].id

    // O mesmo fluxo, de novo: nada mudou, então nada é novo.
    const denovo = aplicarProposta(PROPOSTA, catalogo, jaNaTela)
    expect(denovo.idsNovos.size).toBe(0)
    expect(denovo.idsArestasNovas.size).toBe(0)

    // Agora com um nó a menos no canvas: só ele reaparece como novo.
    const semUm = aplicarProposta(PROPOSTA, catalogo, jaNaTela.slice(1))
    expect([...semUm.idsNovos]).toEqual([idJaNaTela])
    // E as arestas que TOCAM esse nó — uma ligação entre dois nós que já
    // estavam ali não é novidade e não deve se redesenhar.
    for (const id of semUm.idsArestasNovas) {
      const aresta = semUm.edges.find(e => e.id === id)!
      expect(aresta.source === idJaNaTela || aresta.target === idJaNaTela).toBe(true)
    }
  })

  it("canvas vazio: tudo é novo e tudo ganha posição do layout", () => {
    const { nodes, resumo } = aplicarProposta(PROPOSTA, catalogo, [])
    expect(resumo).toEqual({ novos: 4, alterados: 0, removidos: 0 })

    // Nenhum par de cards sobreposto — é o que o layout garante e o que a
    // pessoa vai ver ao pedir um fluxo do zero.
    const caixas = nodes.map(n => ({ ...n.position, w: 158, h: 60 }))
    for (let i = 0; i < caixas.length; i++) {
      for (let j = i + 1; j < caixas.length; j++) {
        const a = caixas[i]
        const b = caixas[j]
        const sobrepoe = a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
        expect(sobrepoe).toBe(false)
      }
    }
  })
})
