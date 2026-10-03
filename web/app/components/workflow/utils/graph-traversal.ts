import { Edge } from "@xyflow/react"

/**
 * Graph traversal for path highlighting.
 *
 * Given an anchor node, returns everything that feeds it (ancestors) and
 * everything it feeds (descendants), including the edges traversed — the rest
 * of the canvas is dimmed by the CSS layer.
 */

export interface FocusGraph {
  out: Map<string, { edgeId: string; target: string }[]>
  in: Map<string, { edgeId: string; source: string }[]>
}

export function buildFocusGraph(edges: Edge[]): FocusGraph {
  const out: FocusGraph["out"] = new Map()
  const inn: FocusGraph["in"] = new Map()

  for (const edge of edges) {
    const outList = out.get(edge.source)
    if (outList) outList.push({ edgeId: edge.id, target: edge.target })
    else out.set(edge.source, [{ edgeId: edge.id, target: edge.target }])

    const inList = inn.get(edge.target)
    if (inList) inList.push({ edgeId: edge.id, source: edge.source })
    else inn.set(edge.target, [{ edgeId: edge.id, source: edge.source }])
  }

  return { out, in: inn }
}

export interface FocusPath {
  nodes: Set<string>
  edges: Set<string>
}

/**
 * Forward and backward BFS from `nodeId`. Each direction has its own
 * `visited`, so a node reachable from both sides (diamond) enters the sets
 * only once, and cycles do not stall the traversal.
 */
export function collectPath(graph: FocusGraph, nodeId: string): FocusPath {
  const nodes = new Set<string>([nodeId])
  const edges = new Set<string>()

  // Descendentes
  const forward = [nodeId]
  const seenForward = new Set<string>([nodeId])
  while (forward.length) {
    const id = forward.pop()!
    for (const { edgeId, target } of graph.out.get(id) ?? []) {
      edges.add(edgeId)
      nodes.add(target)
      if (seenForward.has(target)) continue
      seenForward.add(target)
      forward.push(target)
    }
  }

  // Ancestrais
  const backward = [nodeId]
  const seenBackward = new Set<string>([nodeId])
  while (backward.length) {
    const id = backward.pop()!
    for (const { edgeId, source } of graph.in.get(id) ?? []) {
      edges.add(edgeId)
      nodes.add(source)
      if (seenBackward.has(source)) continue
      seenBackward.add(source)
      backward.push(source)
    }
  }

  return { nodes, edges }
}
