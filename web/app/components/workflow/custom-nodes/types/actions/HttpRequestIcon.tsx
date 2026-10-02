import { NodeProps } from "@xyflow/react";
import { ACTION_ICONS } from "@/consts/WorkflowIcons";
import { INodeContext } from "@/context/useFlowContext";
import ActionsIconRoot from "./ActionsIconRoot";
import { TbHttpDelete, TbHttpGet, TbHttpPatch, TbHttpPost, TbHttpPut } from "react-icons/tb";
import { memo } from "react";

const HttpRequestIcon = ({ id, ...nodeProps }: NodeProps<INodeContext>) => {
  const method = nodeProps.data.properties.method
  const Icon = method === "GET" ? TbHttpGet :
    method === "POST" ? TbHttpPost :
      method === "PUT" ? TbHttpPut :
        method === "DELETE" ? TbHttpDelete :
          method === "PATCH" ? TbHttpPatch :
            ACTION_ICONS["HttpRequest"]

  return (
    <ActionsIconRoot id={id} {...nodeProps}>
      <Icon className="text-3xl text-foreground" /> {/* Ícone centralizado */}
    </ActionsIconRoot>
  )
}

export default memo(HttpRequestIcon);