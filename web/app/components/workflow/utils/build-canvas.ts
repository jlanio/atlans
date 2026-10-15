// web/app/components/workflow/utils/build-canvas.ts
//
// Building a canvas from a persisted `definition` + the node catalog.
//
// The definition stores only the node's serializable state (id, name, properties,
// position); the whole schema — fields, ports, type, description — comes from the
// `GET /nodes` catalog at open time. Joining the two is what turns the database
// JSON into something React Flow can draw.
//
// Pure on purpose: besides the editor, the sub-workflow viewer builds the canvas
// of ANOTHER workflow (the child) to paint what happened inside it. While this
// lived inside the component, reading `workflow`/`nodesAPI` from the closure and
// calling `setNodes`/`setEdges`, there was no way to build a second graph without
// duplicating the rule — and `data` built in two places is exactly the defect
// that `contratoDoNo` exists to prevent.
import { Edge } from "@xyflow/react"
import { v4 as uuid } from "uuid"
import { INodeContext } from "@/context/useFlowContext"
import { CanvasDefinition, IEdgeDefinition, INodePortAPI, INodesAPI } from "@/service/types"
import { getTypeIcon } from "@/utils/getTypeIconsUtils"
import { contratoDoNo, inputHandle } from "./node-ports"
import { chaveEfetiva, ramoDaCondicao, resolveSourceHandle } from "./edge-persistence"

/**
 * Output handles a node missing from the catalog had in use, read from its
 * saved edges.
 *
 * Without its schema the node declares no port, so every edge leaving it was
 * anchored on the anonymous handle and the next save dropped its
 * `source_handle` — and with it a branch's `condition`, which `serializeEdge`
 * only writes for a true/false handle: the branch edges of a disabled
 * Conditional came back as plain data edges, and both branches ran. The
 * handles the edges point at are what the card has to draw for them to keep
 * their anchor. A branch handle brings both, as on any branch node.
 */
function saidasDasArestasSalvas(
  edges: CanvasDefinition["edges"],
  nodeId: string,
): INodePortAPI[] {
  const nomes = new Set<string>()
  let ramo = false
  for (const e of edges ?? []) {
    if (e?.source !== nodeId) continue
    if (e.source_handle === "true" || e.source_handle === "false" || ramoDaCondicao(e.condition) !== undefined) {
      ramo = true
    } else if (e.source_handle) {
      nomes.add(e.source_handle)
    }
  }
  const portas = [...nomes].map(name => ({ name }))
  return ramo ? [{ name: "true" }, { name: "false" }, ...portas] : portas
}

/** The output side of a node missing from the catalog, from its saved edges:
 *  the handles, and whether it routes — so true/false stay branches and never
 *  become data keys (`getCandidateKeys`). */
function contratoDasArestasSalvas(edges: CanvasDefinition["edges"], nodeId: string) {
  const outputs = saidasDasArestasSalvas(edges, nodeId)
  const ramifica = outputs.some(p => p.name === "true" || p.name === "false")
  return { outputs, ...(ramifica ? { branches: true } : {}) }
}

/**
 * Canvas nodes for a definition.
 *
 * `properties` is rebuilt field by field from the catalog — and not copied from
 * the definition — so that a new field in the schema reaches the node already
 * with the backend's default, without a data migration.
 *
 * A node the catalog does not list (disabled by an admin, renamed or removed)
 * is kept exactly as saved. Rebuilt from a schema that is not there, its
 * properties came out empty and its type fell back to "trigger", and the next
 * save — of anything else in the workflow — persisted both: the configuration
 * was gone for good, and as a "trigger" the executor ignores its incoming edges
 * and the card draws no input, so those edges vanished from the canvas.
 */
export function buildNodes(
  definition: CanvasDefinition | undefined,
  nodesAPI: INodesAPI[] | undefined,
): INodeContext[] {
  if (!definition?.nodes?.length || !nodesAPI?.length) return []

  return definition.nodes.map((node, indice) => {
    const nodeApiFound = nodesAPI.find(n => n.name === node.name)
    const properties = nodeApiFound ? {} as Record<string, string> : { ...(node.properties ?? {}) }
    // The catalog's type wins: a type persisted wrong (the fallback above
    // wrote "trigger" for nodes that are not) is corrected on the next save.
    const type = nodeApiFound?.type ?? node.type ?? "action"

    nodeApiFound?.properties.forEach(field => {
      properties[field.name] = (node.properties?.[field.name] ?? field.default) as string
    })

    return {
      id: node.id,
      data: {
        // Uses the custom alias saved by the user; falls back to the schema default if there is none
        alias: node.alias ?? nodeApiFound?.alias ?? "",
        description: nodeApiFound?.description ?? "",
        name: node.name,
        fields: nodeApiFound?.properties.map((prop) => ({
          name: prop.name,
          label: prop.label,
          default: prop.default,
          type: prop.type,
          description: prop.description ?? "",
          credential_types: prop.credential_types,
          drive_extensions: prop.drive_extensions,
          options: prop.options,
          visibleWhen: prop.visibleWhen,
          // Without this line the marker died HERE on the first reload: the freshly
          // dragged node suggested columns (the drawer copies the whole catalog
          // object) and the same node, saved and reloaded, never again — the
          // projection dropped the field and `sugerirColunas()` returned [] for
          // good. It was the "sometimes it works" of column suggestions.
          suggest_columns: prop.suggest_columns,
        })) ?? [],
        properties,
        type,
        ...contratoDoNo(nodeApiFound, properties),
        ...(nodeApiFound ? {} : contratoDasArestasSalvas(definition.edges, node.id)),
      },
      // The card follows the same type: with the persisted one, a node saved as
      // "trigger" by mistake got the trigger card, which has no input handle.
      type: getTypeIcon({ ...node, type }),
      position: node.position ?? { x: 0 + (180 * indice), y: 0 },
    } satisfies INodeContext
  })
}

/**
 * An edge with both ends. One saved without `source` or `target` (by hand, by
 * another client) cannot be drawn and the executor skips it; kept on the
 * canvas it went back in every save, which the server now refuses (422), and
 * the workflow could no longer be saved at all.
 */
function ligaDoisNos(edge: IEdgeDefinition | null | undefined): edge is IEdgeDefinition {
  return Boolean(edge && edge.source != null && edge.source !== "" && edge.target != null && edge.target !== "")
}

/**
 * Canvas edges. Depends on the nodes already built: the source and target
 * handles can only be resolved knowing which ports each node declares.
 */
export function buildEdges(
  definition: CanvasDefinition | undefined,
  nodes: INodeContext[],
): Edge[] {
  if (!definition?.edges?.length) return []

  const outputsByNodeId = new Map<string, INodePortAPI[]>(
    nodes.map(n => [n.id, (n.data?.outputs ?? []) as INodePortAPI[]]),
  )
  const inputsByNodeId = new Map<string, string[]>(
    nodes.map(n => [n.id, ((n.data?.inputs ?? []) as INodePortAPI[]).map(p => p.name)]),
  )

  return definition.edges.filter(ligaDoisNos).map(salva => {
    // The key the edge really means (see `chaveEfetiva`): from here on the
    // canvas, the anchoring and the next save all use it.
    const edge = { ...salva, from_key: chaveEfetiva(salva) }
    return {
      id: uuid(),
      source: edge.source,
      target: edge.target,
      sourceHandle: resolveSourceHandle(edge, outputsByNodeId),
      targetHandle: inputHandle(edge, inputsByNodeId),
      type: "custom",
      data: {
        ...(edge.from_key ? { from_key: edge.from_key } : {}),
        ...(edge.to_key ? { to_key: edge.to_key } : {}),
      },
    } satisfies Edge
  })
}

export type { CanvasDefinition } from "@/service/types"
