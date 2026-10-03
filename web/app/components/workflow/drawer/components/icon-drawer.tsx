import { NODE_TYPES, NodeTypes } from "@/consts/WorkflowIcons"
import { cn } from "@/lib/utils"
import { IconBaseProps } from "react-icons"
import { TbError404 } from "react-icons/tb"

interface CardIconDrawerProps extends IconBaseProps {
  type: NodeTypes | string
}

/**
 * Icon for the node CATEGORY.
 *
 * `fontSize` and `className` came AFTER the spread and silently overrode what
 * the caller passed: the node list asked for the type color in each group's
 * header and got `text-foreground`, and the category cards needed a
 * `!text-inherit` just to punch through it. With `cn()` and the default BEFORE
 * the spread, the caller is in charge again.
 */
const IconDrawer = ({ type, className, ...props }: CardIconDrawerProps) => {

  const Icon = NODE_TYPES[type] ?? TbError404

  return (
    <Icon fontSize={18} {...props} className={cn("text-foreground", className)} />
  )
}

export default IconDrawer