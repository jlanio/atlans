import { NodeProps, useNodeConnections } from "@xyflow/react";
import { memo, ReactNode, useCallback } from "react";
import IconRoot from "../../icon-root";
import { HandleSource, HandleTarget } from "../../handle";
import AddConnectionHandle from "../../add-connection-handle";
import { INodeContext } from "@/context/useFlowContext";
import ToolsIcon from "../../tools";
import { useTools } from "@/app/hooks/workflow/useTools";

interface ActionsIconRootProps extends NodeProps<INodeContext> {
  children: ReactNode
}

// `selected` comes from the React Flow prop — see the comment in default-type.tsx.
const ActionsIconRoot = ({ children, id, data, selected }: ActionsIconRootProps) => {

  const { toolState, handleToolState } = useTools()

  const onEnter = useCallback(() => handleToolState('onFocus'), [handleToolState])
  const onLeave = useCallback(() => handleToolState('leave'), [handleToolState])

  // `useNodeConnections` reads the connection index React Flow already keeps per
  // node. This used to be an effect that scanned ALL edges (O(N·E) across the
  // canvas) and called setState: besides the cost, it forced a second commit per
  // node, and that is why the handle's "+" flickered on every new connection.
  const saidas = useNodeConnections({ id, handleType: "source" })
  // Same source as the outputs: the input port also needs to know whether it is
  // connected to choose between a solid and a dashed stroke.
  const entradas = useNodeConnections({ id, handleType: "target" })

  const title = (data.properties?.["alias"] as string | undefined) || (data.alias as string)

  return (
    <IconRoot
      id={id}
      nodeType="action"
      title={title}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      data-selected={`${!!selected}`}
    >
      <ToolsIcon nodeId={id} open={toolState !== "disable"} />

      {children}

      <AddConnectionHandle nodeId={id} connectionVisible={saidas.length === 0}>
        <HandleSource livre={saidas.length === 0} />
      </AddConnectionHandle>

      <HandleTarget livre={entradas.length === 0} />
    </IconRoot>
  )
}

// memo: avoids re-rendering when the parent (e.g. HttpRequestIcon) re-renders
// without a real change in the node's props (shallow compare on
// id/data/selected/dragging already covers the real cases — data is
// referentially stable in ReactFlow).
export default memo(ActionsIconRoot);
