import { NodeProps } from "@xyflow/react";
import { TbError404 } from "react-icons/tb";
import ActionsIconRoot from "./types/actions/ActionsIconRoot";
import { INodeContext } from "@/context/useFlowContext";
import { memo } from "react";

const NotFoundIcon = (nodeProps: NodeProps<INodeContext> ) => {

  return (
    <ActionsIconRoot {...nodeProps}>
      <TbError404 className="text-3xl" /> {/* Centered icon */}
    </ActionsIconRoot>
  )
}

export default memo(NotFoundIcon);