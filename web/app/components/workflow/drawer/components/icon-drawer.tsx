import { NODE_TYPES, NodeTypes } from "@/consts/WorkflowIcons"
import { cn } from "@/lib/utils"
import { IconBaseProps } from "react-icons"
import { TbError404 } from "react-icons/tb"

interface CardIconDrawerProps extends IconBaseProps {
  type: NodeTypes | string
}

/**
 * Ícone da CATEGORIA de nó.
 *
 * `fontSize` e `className` vinham DEPOIS do spread e sobrescreviam em silêncio o
 * que o chamador passava: a lista de nós pedia a cor do tipo no cabeçalho de
 * cada grupo e recebia `text-foreground`, e os cartões de categoria precisaram
 * de um `!text-inherit` só para furar isso. Com `cn()` e o padrão ANTES do
 * spread, o chamador volta a mandar.
 */
const IconDrawer = ({ type, className, ...props }: CardIconDrawerProps) => {

  const Icon = NODE_TYPES[type] ?? TbError404

  return (
    <Icon fontSize={18} {...props} className={cn("text-foreground", className)} />
  )
}

export default IconDrawer