import { Edge } from "@xyflow/react"

/**
 * Separates into lanes the edges that connect the same pair of nodes.
 *
 * Concrete case: a `Conditional` with `true` and `false` pointing at the same
 * target draws two nearly touching lines, with the label badges stacked at the
 * same point. The offset goes in as `getSmoothStepPath`'s `centerX`: in a
 * left-to-right layout that is where the step's vertical segment sits — and,
 * along with it, the label. Shifting `centerY` would move only the label, off
 * its own line.
 *
 * The result is NOT stored in `edge.data`: that would require a `setEdges` on
 * every topology change, and `useSaveWorkflow`'s change detector would see a
 * new array and mark the workflow as "unsaved" without any user edit.
 */

/** Distance between neighboring lanes, in flow-space pixels. */
const LANE_PX = 22

export function computeLaneOffsets(edges: Edge[], lanePx = LANE_PX): Map<string, number> {
  // Two-level grouping (source → target → edges) instead of a concatenated key:
  // no need to pick a separator the ids cannot contain.
  const groups = new Map<string, Map<string, string[]>>()

  for (const edge of edges) {
    let byTarget = groups.get(edge.source)
    if (!byTarget) {
      byTarget = new Map()
      groups.set(edge.source, byTarget)
    }

    const group = byTarget.get(edge.target)
    if (group) group.push(edge.id)
    else byTarget.set(edge.target, [edge.id])
  }

  const offsets = new Map<string, number>()
  for (const byTarget of groups.values()) {
    for (const group of byTarget.values()) {
      // A single-edge group is the majority case — it leaves with no offset and no sorting.
      if (group.length === 1) continue

      // Order by id: arbitrary, but stable across renders (ids are uuids).
      group.sort()
      group.forEach((id, i) => {
        offsets.set(id, (i - (group.length - 1) / 2) * lanePx)
      })
    }
  }

  return offsets
}

// Memo by array identity: without it, each of the E edges would recompute
// the whole grouping in its own render — O(E²) per frame.
//
// WeakMap, and not a pair of module variables: the sub-workflow viewer mounts a
// SECOND React Flow with the same edge component, and with the variable pair the
// two canvases invalidated each other — each editor edge threw away the cache
// filled by the child's edges and vice versa, bringing back the O(E²) this memo
// exists to avoid. Each array keeps its own result and the entry is released on
// its own when the array is discarded.
const cache = new WeakMap<Edge[], Map<string, number>>()

export function getLaneOffset(edges: Edge[], edgeId: string): number {
  let offsets = cache.get(edges)
  if (!offsets) {
    offsets = computeLaneOffsets(edges)
    cache.set(edges, offsets)
  }
  return offsets.get(edgeId) ?? 0
}
