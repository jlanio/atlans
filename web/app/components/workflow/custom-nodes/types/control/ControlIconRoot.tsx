import { NodeProps } from "@xyflow/react";
import { memo, ReactNode, useCallback } from "react";
import IconRoot from "../../icon-root";
import ToolsIcon from "../../tools";
import { useTools } from "@/app/hooks/workflow/useTools";

interface ControlIconRootProps extends NodeProps {
  children: ReactNode
}

// `selected` vem da prop do React Flow — ver o comentário em default-type.tsx.
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

// memo: evita re-render quando o pai (ex: ConditionalIcon) re-renderiza sem
// mudança real nos props do node.
export default memo(ControlIconRoot);
