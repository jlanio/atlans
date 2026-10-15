import { Edge } from "@xyflow/react"
import { IEdgeDefinition } from "@/service/types"
import { INodePortAPI } from "@/service/types"

/**
 * Serialization of the canvas edges — the save/load pair must be symmetric.
 *
 * Asymmetry here is not just a persistence bug: detect-dirty compares the
 * initial snapshot with the current payload using the SAME serialization, so
 * any divergence makes the canvas report "unsaved" as soon as it opens.
 *
 * The regression that gave rise to this module: `condition` was written for any
 * named handle (`sourceHandle === "true"` with sourceHandle="output" → false),
 * which erased the port id. On load that became sourceHandle="false" — a handle
 * that does not exist on a non-conditional node —, React Flow could not anchor
 * the edge and it vanished from the canvas. It only affected nodes with more than
 * one output port; with just one, the handle is anonymous and nothing was written.
 */

/** Routing handles of a conditional node — the only ones that become `condition`. */
function isRoutingHandle(handle?: string | null): boolean {
  return handle === "true" || handle === "false"
}

/**
 * `condition` as a branch, or `undefined` for a data edge — the same spellings
 * the executor accepts (`condicao_do_ramo` in flow/executor/edge_resolver.py),
 * which are the ones the MCP validation lets through. Read as truthy, a
 * `"false"` written as text anchored the edge on the TRUE branch, and the next
 * save wrote `condition: true` — the editor inverted the branch on its own.
 */
export function ramoDaCondicao(condition: unknown): boolean | undefined {
  if (typeof condition === "boolean") return condition
  if (typeof condition === "string") {
    const texto = condition.toLowerCase()
    if (RAMO_VERDADEIRO.has(texto)) return true
    if (RAMO_FALSO.has(texto)) return false
    return undefined
  }
  if (condition === 0 || condition === 1) return condition === 1
  return undefined
}

const RAMO_VERDADEIRO = new Set(["true", "t", "yes", "y", "on", "1"])
const RAMO_FALSO = new Set(["false", "f", "no", "n", "off", "0"])

/** Converts a React Flow edge to the persisted format. */
export function serializeEdge(edge: Edge): IEdgeDefinition {
  const { source, target, sourceHandle, targetHandle, data } = edge
  return {
    source,
    target,
    ...(sourceHandle ? { source_handle: sourceHandle } : {}),
    ...(isRoutingHandle(sourceHandle) ? { condition: sourceHandle === "true" } : {}),
    ...(data?.from_key ? { from_key: data.from_key as string } : {}),
    ...(targetHandle
      ? { to_key: targetHandle }
      : data?.to_key
        ? { to_key: data.to_key as string }
        : {}),
  }
}

/** The SubWorkflow's envelope output: a dict with ALL of the child's ports. */
export const ENVELOPE_DO_SUBFLUXO = "subWorkflowResult"

/**
 * The `from_key` a persisted edge really means.
 *
 * An edge dragged from a SubWorkflow's port `r2` used to be saved with the port
 * as handle and the envelope as key — the candidate list did not know the
 * child's ports — so it delivered the dict of ALL the ports instead of r2, and
 * after a reload it jumped to the first port. The handle is what the person
 * pulled: that pair reads as the port, here and in the run (`Edge.from_dict`
 * in flow/executor/edge_resolver.py), so those edges get their line and their
 * key back without migrating the database. Choosing the envelope on purpose
 * saves it without a handle (`sourceHandleDaChave`), which this leaves alone.
 */
export function chaveEfetiva(edge: Pick<IEdgeDefinition, "from_key" | "source_handle">): string | undefined {
  const handle = edge.source_handle
  if (
    edge.from_key === ENVELOPE_DO_SUBFLUXO
    && handle && handle !== ENVELOPE_DO_SUBFLUXO && handle !== "true" && handle !== "false"
  ) {
    return handle
  }
  return edge.from_key
}

/**
 * Source handle of a persisted edge.
 *
 * `outputsByNodeId` carries the ports declared by each node: without them there
 * is no way to tell a legitimate conditional branch from a spurious `condition`
 * written by the old version.
 */
export function resolveSourceHandle(
  edge: IEdgeDefinition,
  outputsByNodeId: Map<string, INodePortAPI[]>,
): string | undefined {
  const outputs = outputsByNodeId.get(edge.source) ?? []

  // 1. Current format: the persisted handle — as long as it is still a REAL
  //    handle of the node. There is only a NAMED handle with 2+ real outputs
  //    (default-type draws one HandleSource per port only in that case);
  //    true/false are the routing ones. An id outside that — a field without
  //    `port` written by a picker that synced sourceHandle with ANY candidate —
  //    has no connection point: React Flow does not anchor the edge and it
  //    vanishes from the canvas. Ignoring it here brings the line back to the
  //    canvas via the recovery below (from_key / anonymous), without migrating
  //    the database. `data.outputs` is the SAME source the rendering uses, and
  //    it arrives synchronously on load (catalog or `ports`).
  if (edge.source_handle) {
    const isNamed = outputs.length > 1 && outputs.some(p => p.name === edge.source_handle)
    const isRouting = (edge.source_handle === "true" || edge.source_handle === "false")
      && outputs.some(p => p.name === "true" || p.name === "false")
    if (isNamed || isRouting) return edge.source_handle
    // Ghost handle: falls through to the recovery steps.
  }

  // 2. Conditional branch — only if the node REALLY has true/false ports.
  //    Trusting `condition` without checking the node would revive the bug in reverse.
  const isRoutingNode = outputs.some(p => p.name === "true" || p.name === "false")
  const ramo = ramoDaCondicao(edge.condition)
  if (isRoutingNode && ramo !== undefined) {
    return ramo ? "true" : "false"
  }

  // 3. Recovery of edges saved before the fix: the port id was lost, but
  //    `from_key` holds the same information when the handle was a data port.
  //    Brings the edge back to the canvas without migrating the database.
  if (outputs.length > 1 && edge.from_key && outputs.some(p => p.name === edge.from_key)) {
    return edge.from_key
  }

  // 4. Anonymous handle (single-output node) — React Flow anchors on the first one.
  return undefined
}
