import { INodeContext, useFlowContext } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { useMemo } from "react"
import { IconType } from "react-icons"
import { v4 as uuid } from "uuid"
import { Edge, useReactFlow, useStore } from "@xyflow/react"
import { NODE_ICONS } from "@/consts/WorkflowIcons"
import { useLinkNodeParams } from "@/app/hooks/workflow/useLinkNodeParams"
import { INodesAPI } from "@/service/types"
import { TbError404, TbSearch } from "react-icons/tb"
import { getTypeIcon } from "@/utils/getTypeIconsUtils"
import IconDrawer from "./components/icon-drawer"
import { getCandidateKeys, resolveFromKey, portaDeEntradaPadrao } from "../utils/resolve-edge-keys"
import { contratoDoNo } from "../utils/node-ports"
import { typeStyle, typeName } from "@/consts/NodeTypeStyles"
import { cn } from "@/lib/utils"

export interface INodesItemsDrawer extends INodesAPI<string> {
  icon: IconType
}

// The type color is NOT decided here. `TYPE_STYLES` declares itself the "single
// source of truth" and is what paints the card on the canvas and the modal
// header; this file kept two tables of its own that disagreed with it on FOUR of
// the six types — trigger was blue here and violet there, action amber here and
// sky blue there. Clicking an amber item got you a blue node on the canvas.

interface NodesDrawerProps {
  aliasFilter: string
}

const NodesDrawer = ({ aliasFilter }: NodesDrawerProps) => {
  const { flowRef, reactFlowInstance } = useFlowContext()
  const nodesAPI = useWorkflowCatalogStore(s => s.nodesAPI)
  const nodesDrawerState = useWorkflowCatalogStore(s => s.nodesDrawerState)
  const setNodesDrawerState = useWorkflowCatalogStore(s => s.setNodesDrawerState)
  const setNewlyAddedNodeId = useWorkflowCatalogStore(s => s.setNewlyAddedNodeId)
  const { addEdges, addNodes, getNode } = useReactFlow<INodeContext, Edge>()
  const { linkHandleIdParam, linkNodeIdParam, removeLinkNodeParam } = useLinkNodeParams()
  // The canvas node list only serves two specific questions: "is it empty?"
  // (here) and "where is the node the + came from?" (inside addNode, via
  // getNode). Subscribing to `useNodes()` refiltered the whole catalog on every
  // drag frame, with the drawer closed and off screen.
  const canvasEmpty = useStore(s => s.nodeLookup.size === 0)

  const drawerType = canvasEmpty ? "trigger" : nodesDrawerState
  const hasTypeFilter = drawerType !== "closed" && drawerType !== "opened"

  // Derived, not state + effect: the computation is synchronous and `setItems`
  // only served to store it, at the cost of a second render of the whole drawer.
  const items = useMemo<INodesItemsDrawer[]>(() => {
    const filtro = aliasFilter.toLowerCase()
    return (nodesAPI ?? [])
      .filter(item => item.alias.toLowerCase().includes(filtro))
      .filter(item => hasTypeFilter ? item.type === drawerType : true)
      .map(item => ({ ...item, icon: NODE_ICONS[item.name as string] ?? TbError404 })) as INodesItemsDrawer[]
  }, [nodesAPI, aliasFilter, hasTypeFilter, drawerType])

  function addNode(item: INodesItemsDrawer) {
    const viewPort = reactFlowInstance.getViewport()
    const clientWidth = flowRef.current?.clientWidth ?? 0
    const clientHeight = flowRef.current?.clientHeight ?? 0

    let position = {
      x: (clientWidth / 2) - viewPort.x - 80,
      y: (clientHeight / 2) - viewPort.y - 30,
    }

    const nodeFound = linkNodeIdParam ? getNode(linkNodeIdParam) : undefined
    if (nodeFound) {
      position = { x: nodeFound.position.x + 180, y: nodeFound.position.y }
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { icon, properties: fields, ...data } = item
    const properties = {} as Record<string, string>
    fields.forEach(field => {
      const isObject = typeof field.default === "object"
      properties[field.name] = isObject ? field.default as string : field.default as string ?? ""
    })

    const newNode: INodeContext = {
      id: uuid(),
      type: getTypeIcon(item),
      // The contract comes AFTER the `item` spread: in a node with dynamic inputs
      // the catalog list is empty and the user's ports are what counts.
      data: { ...data, fields, properties, ...contratoDoNo(item, properties) },
      position,
    }

    addNodes(newNode)
    setNodesDrawerState("closed")
    setNewlyAddedNodeId(newNode.id)
    removeLinkNodeParam()

    if (nodeFound) {
      // Without from_key the executor spreads ALL of the parent's outputs into the
      // child (inputs.update), ignoring the port the user pulled the "+" from.
      // Same rule as the canvas drag-and-drop.
      //
      // `resolveFromKey` returns undefined when the choice is ambiguous. The
      // canvas resolved that by opening a picker; here the edge was born WITHOUT
      // a key — silently, and precisely in the case that needed one most. Now
      // both paths use the first candidate and the edge badge lets you change
      // it later.
      const candidatos = getCandidateKeys(nodeFound.data)
      const from_key = resolveFromKey(linkHandleIdParam, candidatos) ?? candidatos[0]?.name
      // Multi-input target (Join layerA/layerB): the edge is born on the FIRST
      // declared port — without `to_key`, `colunas-conhecidas` indexes by the
      // wrong key and the per-port suggestion stays empty forever; and the
      // executor falls back to `inputs[from_key]`. Same rule as drag-and-drop
      // (`resolveToKey`), which here has no chosen handle to consult.
      const to_key = portaDeEntradaPadrao(newNode.data.inputs)
      const newEdge: Edge = {
        id: uuid(),
        source: nodeFound.id,
        sourceHandle: linkHandleIdParam,
        target: newNode.id,
        // The named handle exists whenever there are 2+ declared inputs — anchoring
        // the line on it keeps the visual and the data (`to_key`) telling the
        // same story.
        ...(to_key ? { targetHandle: to_key } : {}),
        type: "custom",
        ...(from_key || to_key
          ? { data: { ...(from_key ? { from_key } : {}), ...(to_key ? { to_key } : {}) } }
          : {}),
      }
      addEdges(newEdge)
    }
  }

  // Decides whether to group (no specific type filter, and with a search or no type selected)
  const shouldGroup = !hasTypeFilter && aliasFilter !== ""

  // Groups by type when searching without a category
  const grouped = shouldGroup
    ? items.reduce<Record<string, INodesItemsDrawer[]>>((acc, item) => {
        const key = item.type as string
        acc[key] = acc[key] ?? []
        acc[key].push(item)
        return acc
      }, {})
    : null

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted-foreground">
        <TbSearch className="h-8 w-8 opacity-30" />
        <p className="text-sm">Nenhum nó encontrado</p>
        {aliasFilter && (
          <p className="text-xs opacity-70">para &ldquo;{aliasFilter}&rdquo;</p>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1 py-2">
      {grouped ? (
        // Modo grouped (busca global)
        Object.entries(grouped).map(([type, groupItems]) => (
          <div key={type} className="mb-1">
            <div className="flex items-center gap-2 px-4 py-1.5">
              <IconDrawer type={type} fontSize={12} className={typeStyle(type).icon} />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                {typeName(type)}
              </span>
              <div className="flex-1 border-t border-border/50" />
            </div>
            {groupItems.map(item => (
              <NodeCard key={item.name} item={item} onAdd={addNode} mostrarTipo={false} />
            ))}
          </div>
        ))
      ) : (
        // Modo plano (categoria selecionada ou canvas vazio)
        items.map(item => (
          <NodeCard key={item.name} item={item} onAdd={addNode} mostrarTipo={!hasTypeFilter} />
        ))
      )}
    </div>
  )
}

/**
 * A catalog node, ready to go onto the canvas.
 *
 * The icon tile repeats the type's `bg`/`icon` — the same classes the canvas
 * card uses — so the list item LOOKS LIKE the node it creates. It used to be a
 * neutral `bg-muted`, and the only type cue was the icon color, which disagreed
 * with the canvas's.
 */
function NodeCard({ item, onAdd, mostrarTipo }: {
  item: INodesItemsDrawer
  onAdd: (item: INodesItemsDrawer) => void
  /** The type badge only informs when the list mixes types. Under a category
   *  filter they are all the same, and repeating it on every row is noise. */
  mostrarTipo: boolean
}) {
  const estilo = typeStyle(item.type as string)

  return (
    <div
      onClick={() => onAdd(item)}
      className="flex gap-3 mx-2 px-3 py-2.5 cursor-pointer items-start rounded-lg hover:bg-accent transition-colors duration-150 group"
    >
      <div className={cn(
        "min-w-9 min-h-9 flex items-center justify-center rounded-lg shrink-0 border border-border/60 shadow-sm",
        "group-hover:border-border transition-colors duration-150",
        estilo.bg,
      )}>
        <item.icon fontSize={17} className={estilo.icon} />
      </div>
      <div className="flex flex-col gap-0.5 min-w-0 flex-1 pt-0.5">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-medium text-foreground truncate leading-tight">
            {item.alias}
          </h4>
          {/* Always present, not `hidden group-hover:inline-flex`: appearing on
              hover changed the width available to the title, which is truncated —
              hovering shrank the node name. */}
          {mostrarTipo && item.type && (
            <span className={cn(
              "text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0",
              estilo.bg, estilo.icon,
            )}>
              {typeName(item.type as string)}
            </span>
          )}
        </div>
        <p className="text-[12px] text-muted-foreground leading-tight line-clamp-2">
          {item.description ?? "Sem descrição"}
        </p>
      </div>
    </div>
  )
}

export default NodesDrawer
