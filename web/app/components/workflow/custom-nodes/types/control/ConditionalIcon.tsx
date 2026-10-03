import { NodeProps, useEdges } from "@xyflow/react";
import { CONTROL_ICONS } from "@/consts/WorkflowIcons";
import { INodeContext } from "@/context/useFlowContext";
import ControlIconRoot from "./ControlIconRoot";
import { HandleSource, HandleTarget } from "../../handle";
import AddConnectionHandle from "../../add-connection-handle";
import { memo, useMemo } from "react";

const ConditionalIcon = ({ id, ...nodeProps }: NodeProps<INodeContext>) => {

  const Icon = CONTROL_ICONS["Conditional"]
  const edges = useEdges()

  // PERF: Set of connected sourceHandles for O(1) lookup.
  const connectedSources = useMemo(() => {
    const set = new Set<string>()
    for (const e of edges ?? []) {
      if (e.source === id && e.sourceHandle) set.add(e.sourceHandle)
    }
    return set
  }, [edges, id])

  // The input is single and has no id, so it is enough to know whether any edge
  // is arriving — that is what decides between a solid and a dashed socket.
  const freeInput = useMemo(
    () => !(edges ?? []).some(e => e.target === id),
    [edges, id],
  )

  return (
    <ControlIconRoot id={id} {...nodeProps}>

      <Icon className="text-xl" />

      <AddConnectionHandle nodeId={id}
        label="true"
        handleId="true"
        connectionVisible={!connectedSources.has("true")}
        className="!top-4" >

        <HandleSource id="true" className="!top-4" livre={!connectedSources.has("true")} />

      </AddConnectionHandle>

      <AddConnectionHandle nodeId={id}
        label="false"
        handleId="false"
        connectionVisible={!connectedSources.has("false")}
        className="!top-10" >

        <HandleSource id="false" className="!top-10" livre={!connectedSources.has("false")} />

      </AddConnectionHandle>

      <HandleTarget livre={freeInput} />

    </ControlIconRoot>
  )
}

export default memo(ConditionalIcon);