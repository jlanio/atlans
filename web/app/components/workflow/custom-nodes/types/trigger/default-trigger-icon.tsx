import { NodeProps, useEdges } from "@xyflow/react";
import IconRoot from "../../icon-root";
import { INodeContext } from "@/context/useFlowContext";
import { PortasDeSaida } from "../../portas";
import ToolsIcon from "../../tools";
import { useTools } from "@/app/hooks/workflow/useTools";
import { TRIGGER_ICONS, TriggersType } from "@/consts/WorkflowIcons";
import { TbError404 } from "react-icons/tb";
import { INodePortAPI } from "@/service/types";
import { memo, useCallback, useMemo } from "react";
import { calcNodeHeight } from "../../../utils/node-metrics";

// `selected` comes from the React Flow prop — see the comment in default-type.tsx.
const DefaultTriggerIcon = ({ id, data, selected }: NodeProps<INodeContext>) => {

  const { toolState, handleToolState } = useTools()
  const edges = useEdges()
  const Icon = TRIGGER_ICONS[data.name as TriggersType] ?? TbError404

  const onEnter = useCallback(() => handleToolState('onFocus'), [handleToolState])
  const onLeave = useCallback(() => handleToolState('leave'), [handleToolState])

  // PERF: indexes edges by sourceHandle in a Set for O(1) lookups per port.
  const connectedSources = useMemo(() => {
    const set = new Set<string>()
    for (const e of edges) {
      if (e.source === id) set.add(e.sourceHandle ?? "__default__")
    }
    return set
  }, [edges, id])

  const outputs = (data.outputs ?? []) as INodePortAPI[]
  const title = (data.properties?.["alias"] as string | undefined) || (data.alias as string)
  const nodeHeight = calcNodeHeight(outputs.length)
  const cardStyle = useMemo(() => ({ height: nodeHeight }), [nodeHeight])

  return (
    <IconRoot
      id={id}
      nodeType="trigger"
      title={title}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      data-selected={`${!!selected}`}
      style={cardStyle}
    >
      <ToolsIcon nodeId={id} open={toolState !== "disable"} />

      <Icon className="text-xl" />

      <PortasDeSaida nodeId={id} outputs={outputs} nodeHeight={nodeHeight} emUso={connectedSources} />

    </IconRoot>
  )
}

export default memo(DefaultTriggerIcon);
