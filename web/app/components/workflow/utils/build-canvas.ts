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
import { CanvasDefinition, INodePortAPI, INodesAPI } from "@/service/types"
import { getTypeIcon } from "@/utils/getTypeIconsUtils"
import { contratoDoNo, inputHandle } from "./node-ports"
import { resolveSourceHandle } from "./edge-persistence"

/**
 * Canvas nodes for a definition.
 *
 * `properties` is rebuilt field by field from the catalog — and not copied from
 * the definition — so that a new field in the schema reaches the node already
 * with the backend's default, without a data migration.
 */
export function buildNodes(
  definition: CanvasDefinition | undefined,
  nodesAPI: INodesAPI[] | undefined,
): INodeContext[] {
  if (!definition?.nodes?.length || !nodesAPI?.length) return []

  return definition.nodes.map((node, indice) => {
    const nodeApiFound = nodesAPI.find(n => n.name === node.name)
    const properties = {} as Record<string, string>

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
        type: nodeApiFound?.type ?? "trigger",
        ...contratoDoNo(nodeApiFound, properties),
      },
      type: getTypeIcon(node),
      position: node.position ?? { x: 0 + (180 * indice), y: 0 },
    } satisfies INodeContext
  })
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

  return definition.edges.map(edge => ({
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
  } satisfies Edge))
}

export type { CanvasDefinition } from "@/service/types"
