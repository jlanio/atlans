import { Edge } from "@xyflow/react"
import dagre from "@dagrejs/dagre"
import { INodeContext } from "@/context/useFlowContext"
import { measuredHeight, measuredWidth } from "./node-metrics"

/**
 * Layout hierárquico da esquerda para a direita, via dagre (`@dagrejs/dagre`).
 *
 * Substitui a versão feita à mão. Aquela alinhava o Y deslocando a COLUNA
 * INTEIRA pela média dos pais (em vez de posicionar cada nó no seu próprio
 * baricentro) e não inseria nós virtuais para arestas que pulam camadas — então
 * ramificações desencontravam e uma aresta longa cortava a coluna do meio (o
 * caso do gatilho ligado direto na junção, com a fonte lateral atrás). O dagre
 * resolve os dois: coordenada por nó (Brandes–Köpf) e roteamento por camadas
 * com nós virtuais, além de uma minimização de cruzamentos madura.
 *
 * Contrapartida de adotar o algoritmo de referência: a ORDEM dos nós dentro de
 * uma camada passa a vir da estrutura do grafo (o dagre reordena para reduzir
 * cruzamentos), não mais da disposição atual do canvas. Em troca, o resultado é
 * estável (mesmo grafo → mesmas posições) e independe de onde os cards estavam.
 *
 * Usa as medidas reais de cada card (`measuredWidth`/`measuredHeight`), então
 * nós altos (muitas portas) não se sobrepõem. Mantém o snap de 8px para que
 * arrastes manuais posteriores continuem alinhados à grade.
 */

export interface LayoutOptions {
  /** Folga entre camadas (`ranksep` do dagre) — horizontal, no sentido LR. */
  hGap?: number
  /** Folga entre nós da mesma camada (`nodesep` do dagre) — vertical, no sentido LR. */
  vGap?: number
  originX?: number
  originY?: number
}

export interface LayoutPosition {
  x: number
  y: number
}

/** Arredonda para a grade de 8px, para que arrastes manuais posteriores alinhem. */
const snap = (v: number) => Math.round(v / 8) * 8

export function computeAutoLayout(
  nodes: INodeContext[],
  edges: Edge[],
  options: LayoutOptions = {},
): Map<string, LayoutPosition> {
  const { hGap = 120, vGap = 32, originX = 40, originY = 40 } = options

  const positions = new Map<string, LayoutPosition>()
  if (!nodes.length) return positions

  const known = new Set(nodes.map(n => n.id))

  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: "LR", nodesep: vGap, ranksep: hGap, marginx: 0, marginy: 0 })
  g.setDefaultEdgeLabel(() => ({}))

  for (const node of nodes) {
    g.setNode(node.id, { width: measuredWidth(node), height: measuredHeight(node) })
  }

  for (const edge of edges) {
    // Arestas órfãs (nó já removido) e self-loops não influenciam o layout — e o
    // self-loop ainda faria o dagre criar um nó virtual inútil ao lado do card.
    if (!known.has(edge.source) || !known.has(edge.target)) continue
    if (edge.source === edge.target) continue
    g.setEdge(edge.source, edge.target)
  }

  dagre.layout(g)

  // O dagre entrega o CENTRO de cada nó; o React Flow posiciona pelo canto
  // superior-esquerdo. Reancoramos ainda o bounding box em (originX, originY),
  // para o resultado não depender de onde o dagre centrou o grafo.
  let minX = Infinity
  let minY = Infinity
  for (const node of nodes) {
    const d = g.node(node.id)
    const left = (d.x ?? 0) - d.width / 2
    const top = (d.y ?? 0) - d.height / 2
    if (left < minX) minX = left
    if (top < minY) minY = top
  }

  for (const node of nodes) {
    const d = g.node(node.id)
    const left = (d.x ?? 0) - d.width / 2 - minX + originX
    const top = (d.y ?? 0) - d.height / 2 - minY + originY
    positions.set(node.id, { x: snap(left), y: snap(top) })
  }

  return positions
}
