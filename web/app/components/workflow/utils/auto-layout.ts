import { Edge } from "@xyflow/react"
import dagre from "@dagrejs/dagre"
import { INodeContext } from "@/context/useFlowContext"
import { measuredHeight, measuredWidth } from "./node-metrics"

/**
 * Left-to-right hierarchical layout, via dagre (`@dagrejs/dagre`).
 *
 * Replaces the hand-written version. That one aligned Y by shifting the WHOLE
 * COLUMN by the parents' average (instead of placing each node at its own
 * barycenter) and did not insert virtual nodes for edges that skip layers — so
 * branches went out of line and a long edge cut through the middle column (the
 * case of the trigger wired straight into the join, with the side source behind
 * it). dagre solves both: per-node coordinates (Brandes–Köpf) and layered
 * routing with virtual nodes, plus mature crossing minimization.
 *
 * The trade-off of adopting the reference algorithm: the ORDER of nodes within a
 * layer now comes from the graph structure (dagre reorders to reduce
 * crossings), no longer from the canvas's current arrangement. In exchange, the
 * result is stable (same graph → same positions) and independent of where the
 * cards were.
 *
 * Uses each card's real measurements (`measuredWidth`/`measuredHeight`), so
 * tall nodes (many ports) do not overlap. Keeps the 8px snap so that later
 * manual drags stay aligned to the grid.
 */

export interface LayoutOptions {
  /** Gap between layers (dagre's `ranksep`) — horizontal, in the LR direction. */
  hGap?: number
  /** Gap between nodes of the same layer (dagre's `nodesep`) — vertical, in the LR direction. */
  vGap?: number
  originX?: number
  originY?: number
}

export interface LayoutPosition {
  x: number
  y: number
}

/** Rounds to the 8px grid, so that later manual drags line up. */
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
    // Orphan edges (node already removed) and self-loops do not influence the
    // layout — and a self-loop would also make dagre create a useless virtual
    // node next to the card.
    if (!known.has(edge.source) || !known.has(edge.target)) continue
    if (edge.source === edge.target) continue
    g.setEdge(edge.source, edge.target)
  }

  dagre.layout(g)

  // dagre returns the CENTER of each node; React Flow positions by the top-left
  // corner. We also re-anchor the bounding box at (originX, originY), so the
  // result does not depend on where dagre centered the graph.
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
