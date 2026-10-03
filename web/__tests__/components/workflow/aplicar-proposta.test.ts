/**
 * Applying the panel's proposal to the canvas.
 *
 * What these tests protect is a single thing, and it's the one that ruins
 * someone's work: the proposed definition HAS NO POSITION. Without preservation,
 * `buildNodes` falls back to the default `{x: 180 * indice, y: 0}` and clicking
 * Apply lines up twelve cards in a horizontal row, erasing the layout the person
 * arranged by hand.
 *
 * That's why the central assertion isn't "it applied": it's that the nodes that
 * survived stay EXACTLY where they were, and that the new node doesn't land on
 * top of any of them.
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
    // Two properties on purpose: with only one, reversing the key order
    // reverses nothing and the order test would pass without biting.
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

/** The canvas of someone who has already worked on the workflow: three cards arranged by hand. */
const ARRANGED = {
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

/** The assistant's proposal: no position at all, as it really arrives. */
const PROPOSAL = {
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

const noCanvas = () => buildNodes(ARRANGED, catalogo)

const findNode = (nodes: INodeContext[], id: string) => {
  const achado = nodes.find(n => n.id === id)
  if (!achado) throw new Error(`nó ${id} não saiu na aplicação`)
  return achado
}

describe("aplicarProposta", () => {
  it("preserva a posição de quem sobreviveu e dá layout só ao nó novo", () => {
    const atuais = noCanvas()
    const { nodes } = aplicarProposta(PROPOSAL, catalogo, atuais)

    // The assertion that matters: the three cards didn't move a pixel.
    expect(findNode(nodes, "a").position).toEqual({ x: 120, y: 480 })
    expect(findNode(nodes, "b").position).toEqual({ x: 700, y: 96 })
    expect(findNode(nodes, "c").position).toEqual({ x: 1240, y: 820 })

    // And the new one was NOT born in the horizontal row of `buildNodes`'s
    // default (`d` is index 3 → x = 540, y = 0).
    const novo = findNode(nodes, "d").position
    expect(novo).not.toEqual({ x: 540, y: 0 })
    expect(Number.isFinite(novo.x) && Number.isFinite(novo.y)).toBe(true)
  })

  it("o valor alterado chega ao canvas — preservar posição não é congelar o nó", () => {
    const { nodes } = aplicarProposta(PROPOSAL, catalogo, noCanvas())
    expect(findNode(nodes, "b").data.properties.distance).toBe("1000")
  })

  it("nó novo não pousa em cima de um card preservado", () => {
    // First we find out where the layout wants to put `d`, with the preserved
    // ones too far away to get in the way.
    const farAway = noCanvas().map(no => ({ ...no, position: { x: 4000, y: 4000 } }))
    const alvo = findNode(aplicarProposta(PROPOSAL, catalogo, farAway).nodes, "d").position

    // Now a preserved card is EXACTLY at that point.
    const onTop = noCanvas().map(no => (no.id === "a" ? { ...no, position: { ...alvo } } : no))
    const { nodes } = aplicarProposta(PROPOSAL, catalogo, onTop)

    // The preserved one wins: the new one is the one that moves down.
    expect(findNode(nodes, "a").position).toEqual(alvo)
    expect(findNode(nodes, "d").position.y).toBeGreaterThan(alvo.y)
  })

  it("conta o que vai acontecer: novos, alterados e removidos", () => {
    // It's the count the card shows BEFORE the click. Applying with a full
    // canvas is destructive by decision, so the number has to be right.
    const { resumo } = aplicarProposta(PROPOSAL, catalogo, noCanvas())
    expect(resumo).toEqual({ novos: 1, alterados: 1, removidos: 0 })
  })

  it("nó que o assistente não trouxe conta como removido", () => {
    const onlyA = {
      nodes: [{ id: "a", name: "DriveFile", properties: { file_id: "mun.shp" } }],
      edges: [],
    } as unknown as CanvasDefinition

    const { resumo } = aplicarProposta(onlyA, catalogo, noCanvas())
    expect(resumo).toEqual({ novos: 0, alterados: 0, removidos: 2 })
  })

  it("ordem das chaves de `properties` não é alteração", () => {
    // The editor builds `properties` in catalog order; the drawer copies the
    // whole catalog object. A different order is no change at all, and
    // counting it as one would make the card announce a change on a node nobody touched.
    const atuais = noCanvas().map(no => ({
      ...no,
      data: { ...no.data, properties: Object.fromEntries(Object.entries(no.data.properties).reverse()) },
    }))
    const igual = {
      nodes: ARRANGED.nodes?.map(({ id, name, properties }) => ({ id, name, properties })),
      edges: ARRANGED.edges,
    } as unknown as CanvasDefinition

    expect(aplicarProposta(igual, catalogo, atuais).resumo.alterados).toBe(0)
  })

  it("monta as arestas da proposta, e não as do canvas", () => {
    const { edges } = aplicarProposta(PROPOSAL, catalogo, noCanvas())
    expect(edges).toHaveLength(3)
    expect(edges.map(e => `${e.source}→${e.target}`)).toEqual(["a→b", "b→c", "c→d"])
  })

  it("mantém a ordem da definição, para o canvas não embaralhar a cada aplicação", () => {
    const { nodes } = aplicarProposta(PROPOSAL, catalogo, noCanvas())
    expect(nodes.map(n => n.id)).toEqual(["a", "b", "c", "d"])
  })

  it("sem catálogo, avisa em vez de esvaziar o canvas", () => {
    // `buildNodes` without a catalog returns []. Applying at that moment WOULD
    // ERASE the whole workflow, silently — the worst possible outcome for this button.
    const withoutCatalog = aplicarProposta(PROPOSAL, [], noCanvas())
    expect(withoutCatalog.catalogoPronto).toBe(false)
    expect(withoutCatalog.nodes).toEqual([])

    expect(aplicarProposta(PROPOSAL, catalogo, noCanvas()).catalogoPronto).toBe(true)
  })

  it("proposta vazia é aplicável — é assim que se limpa o canvas", () => {
    const vazia = aplicarProposta({ nodes: [], edges: [] }, catalogo, noCanvas())
    expect(vazia.catalogoPronto).toBe(true)
    expect(vazia.nodes).toEqual([])
    expect(vazia.resumo.removidos).toBe(3)
  })

  it("só quem chegou AGORA entra na animação", () => {
    // The assistant draws at every step, and each drawing sends the WHOLE
    // definition. Without the list of what's new, the canvas would animate the
    // whole workflow on every added node — a full flicker twelve times in a
    // row, which is the opposite of following the build.
    const alreadyOnCanvas = aplicarProposta(PROPOSAL, catalogo, []).nodes
    const idAlreadyOnCanvas = alreadyOnCanvas[0].id

    // The same workflow, again: nothing changed, so nothing is new.
    const denovo = aplicarProposta(PROPOSAL, catalogo, alreadyOnCanvas)
    expect(denovo.idsNovos.size).toBe(0)
    expect(denovo.idsArestasNovas.size).toBe(0)

    // Now with one node fewer on the canvas: only it reappears as new.
    const missingOne = aplicarProposta(PROPOSAL, catalogo, alreadyOnCanvas.slice(1))
    expect([...missingOne.idsNovos]).toEqual([idAlreadyOnCanvas])
    // And the edges that TOUCH that node — a link between two nodes that were
    // already there isn't new and shouldn't be redrawn.
    for (const id of missingOne.idsArestasNovas) {
      const aresta = missingOne.edges.find(e => e.id === id)!
      expect(aresta.source === idAlreadyOnCanvas || aresta.target === idAlreadyOnCanvas).toBe(true)
    }
  })

  it("canvas vazio: tudo é novo e tudo ganha posição do layout", () => {
    const { nodes, resumo } = aplicarProposta(PROPOSAL, catalogo, [])
    expect(resumo).toEqual({ novos: 4, alterados: 0, removidos: 0 })

    // No pair of overlapping cards — that's what the layout guarantees and
    // what the person will see when asking for a workflow from scratch.
    const caixas = nodes.map(n => ({ ...n.position, w: 158, h: 60 }))
    for (let i = 0; i < caixas.length; i++) {
      for (let j = i + 1; j < caixas.length; j++) {
        const a = caixas[i]
        const b = caixas[j]
        const overlaps = a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
        expect(overlaps).toBe(false)
      }
    }
  })
})
