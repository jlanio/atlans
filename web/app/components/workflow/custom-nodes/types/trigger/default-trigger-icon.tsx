import { NodeProps, useEdges } from "@xyflow/react";
import IconRoot from "../../icon-root";
import AddConnectionHandle from "../../add-connection-handle";
import { INodeContext } from "@/context/useFlowContext";
import { HandleSource } from "../../handle";
import ToolsIcon from "../../tools";
import { useTools } from "@/app/hooks/workflow/useTools";
import { TRIGGER_ICONS, TriggersType } from "@/consts/WorkflowIcons";
import { TbError404 } from "react-icons/tb";
import { INodePortAPI } from "@/service/types";
import { memo, useCallback, useMemo } from "react";
import { calcNodeHeight, portTopStyle } from "../../../utils/node-metrics";

// `selected` vem da prop do React Flow — ver o comentário em default-type.tsx.
const DefaultTriggerIcon = ({ id, data, selected }: NodeProps<INodeContext>) => {

  const { toolState, handleToolState } = useTools()
  const edges = useEdges()
  const Icon = TRIGGER_ICONS[data.name as TriggersType] ?? TbError404

  const onEnter = useCallback(() => handleToolState('onFocus'), [handleToolState])
  const onLeave = useCallback(() => handleToolState('leave'), [handleToolState])

  // PERF: indexa edges por sourceHandle em Set para lookups O(1) por port.
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

      {outputs.length > 1 ? (
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
              <HandleSource id={port.name} className="port-top" livre={!connectedSources.has(port.name)} style={ts} />
            </AddConnectionHandle>
          )
        })
      ) : (
        <AddConnectionHandle nodeId={id} connectionVisible={!connectedSources.has("__default__")}>
          <HandleSource livre={!connectedSources.has("__default__")} />
        </AddConnectionHandle>
      )}

    </IconRoot>
  )
}

export default memo(DefaultTriggerIcon);
