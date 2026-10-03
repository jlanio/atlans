import { INodeContext } from "@/context/useFlowContext"
import { useTools } from "@/app/hooks/workflow/useTools"
import { useEdges, NodeProps } from "@xyflow/react"
import { memo, useCallback, useMemo } from "react"
import AddConnectionHandle from "../add-connection-handle"
import AddInputHandle from "../add-input-handle"
import { HandleSource, HandleTarget } from "../handle"
import IconRoot from "../icon-root"
import ToolsIcon from "../tools"
import { NODE_ICONS } from "@/consts/WorkflowIcons"
import { TbError404 } from "react-icons/tb"
import { INodePortAPI } from "@/service/types"
import { calcNodeHeight, portTopStyle } from "../../utils/node-metrics"

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

  const title = (data.properties?.["alias"] as string | undefined) || (data.alias as string)
  const nodeHeight = calcNodeHeight(Math.max(isOutputNode ? 0 : outputs.length, inputs.length))
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
      {!isOutputNode && (
        outputs.length > 1 ? (
          outputs.map((port, i) => {
            const ts = portTopStyle(i, outputs.length, nodeHeight)
            return (
              <AddConnectionHandle
                key={port.name}
                nodeId={id}
                label={port.name}
                handleId={port.name}
                connectionVisible={!connectedSources.has(port.name)}
                style={ts}
              >
                <HandleSource
                  id={port.name}
                  className="port-top"
                  livre={!connectedSources.has(port.name)}
                  style={ts}
                />
              </AddConnectionHandle>
            )
          })
        ) : (
          <AddConnectionHandle
            nodeId={id}
            connectionVisible={!connectedSources.has("__default__")}
          >
            <HandleSource livre={!connectedSources.has("__default__")} />
          </AddConnectionHandle>
        )
      )}

      {/* ── Inputs (left) — a dashed line distinguishes them from outputs ── */}
      {inputs.length > 1 ? (
        inputs.map((port, i) => {
          const ts = portTopStyle(i, inputs.length, nodeHeight)
          return (
            <AddInputHandle
              key={port.name}
              label={port.name}
              connectionVisible={!connectedTargets.has(port.name)}
              style={ts}
            >
              <HandleTarget
                id={port.name}
                className="port-top"
                livre={!connectedTargets.has(port.name)}
                style={ts}
                title={port.name}
              />
            </AddInputHandle>
          )
        })
      ) : (
        <HandleTarget livre={!connectedTargets.has("__default__")} />
      )}


    </IconRoot>
  )

}

export default memo(DefaultTypeIcon)
