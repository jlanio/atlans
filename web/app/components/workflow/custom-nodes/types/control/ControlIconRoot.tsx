import { NodeProps } from "@xyflow/react";
import { memo, ReactNode, useCallback } from "react";
import IconRoot from "../../icon-root";
import ToolsIcon from "../../tools";
import { useTools } from "@/app/hooks/workflow/useTools";

interface ControlIconRootProps extends NodeProps {
  children: ReactNode
}

// `selected` comes from the React Flow prop — see the comment in default-type.tsx.
const ControlIconRoot = ({ children, id, data, selected }: ControlIconRootProps) => {

  const { toolState, handleToolState } = useTools()

  const onEnter = useCallback(() => handleToolState('onFocus'), [handleToolState])
  const onLeave = useCallback(() => handleToolState('leave'), [handleToolState])

  return (
    <IconRoot
      id={id}
      nodeType="control"
      title={data.alias as string}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      data-selected={`${!!selected}`}
    >
      <ToolsIcon nodeId={id} open={toolState !== "disable"} />

      {children}
    </IconRoot>
  )
}

// memo: avoids re-rendering when the parent (e.g. ConditionalIcon) re-renders
// without a real change in the node's props.
export default memo(ControlIconRoot);
