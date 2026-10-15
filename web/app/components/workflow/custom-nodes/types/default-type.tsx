import { INodeContext } from "@/context/useFlowContext"
import { useTools } from "@/app/hooks/workflow/useTools"
import { useEdges, NodeProps } from "@xyflow/react"
import { memo, useCallback, useMemo } from "react"
import IconRoot from "../icon-root"
import { PortasDeEntrada, PortasDeSaida } from "../portas"
import ToolsIcon from "../tools"
import { NODE_ICONS } from "@/consts/WorkflowIcons"
import { TbError404 } from "react-icons/tb"
import { INodePortAPI } from "@/service/types"
import { calcNodeHeight } from "../../utils/node-metrics"

// `selected` comes from the React Flow prop. Reading `useNodes()` just to find
// that out subscribed to the whole node array: during a drag React Flow emits a
// position change per pointermove, the array changes identity and the N cards
// re-rendered — each one scanning the N nodes, O(N²) per frame.
const DefaultTypeIcon = ({ id, data, selected }: NodeProps<INodeContext>) => {

  const { toolState, handleToolState } = useTools()
  const edges = useEdges()
  const Icon = NODE_ICONS[data.name] ?? TbError404

  const onEnter = useCallback(() => handleToolState('onFocus'), [handleToolState])
  const onLeave = useCallback(() => handleToolState('leave'), [handleToolState])

  // PERF: indexes edges by source/target for O(1) lookups instead of O(n) per port
  const connectedSources = useMemo(() => {
    const set = new Set<string>()
    for (const e of edges) {
      if (e.source === id) set.add(e.sourceHandle ?? "__default__")
    }
    return set
  }, [edges, id])

  const connectedTargets = useMemo(() => {
    const set = new Set<string>()
    for (const e of edges) {
      if (e.target === id) set.add(e.targetHandle ?? "__default__")
    }
    return set
  }, [edges, id])

  const isOutputNode = data.type === "output"
  const outputs = (data.outputs ?? []) as INodePortAPI[]
  const inputs  = (data.inputs  ?? []) as INodePortAPI[]
  // Output-type nodes are terminal: no output to start a connection from. But an
  // edge can already leave one — written through the MCP or by hand, and the
  // executor runs it — and without a handle React Flow does not draw it: it
  // could be neither seen nor deleted. Those nodes draw their outputs.
  const drawOutputs = !isOutputNode || connectedSources.size > 0

  const title = (data.properties?.["alias"] as string | undefined) || (data.alias as string)
  const nodeHeight = calcNodeHeight(Math.max(drawOutputs ? outputs.length : 0, inputs.length))
  // Stable object: recreating it per render invalidated the card's props
  // comparison on every frame.
  const cardStyle = useMemo(() => ({ height: nodeHeight }), [nodeHeight])

  return (
    <IconRoot
      id={id}
      nodeType={data.type as string}
      title={title}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      data-selected={`${!!selected}`}
      style={cardStyle}
    >
      <ToolsIcon nodeId={id} open={toolState !== "disable"} />

      <Icon className="text-xl" />

      {/* ── Outputs (right) — output-type nodes are terminal, with no output ── */}
      {drawOutputs && (
        <PortasDeSaida nodeId={id} outputs={outputs} nodeHeight={nodeHeight} emUso={connectedSources} />
      )}

      <PortasDeEntrada inputs={inputs} nodeHeight={nodeHeight} emUso={connectedTargets} />

    </IconRoot>
  )

}

export default memo(DefaultTypeIcon)
