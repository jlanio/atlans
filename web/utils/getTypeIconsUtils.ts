import { TbError404 } from "react-icons/tb"
import { nodeTypesFlow } from "../app/components/workflow/canvas-types"
import { IconType } from "react-icons"

export  function getTypeIcon(item: {name: string, icon?: IconType, type: string}) {
    
    const hasNodeType = item.name in nodeTypesFlow
    const hasNotFoundIcon = item.icon === TbError404

    if (hasNodeType)
      return `${item.name}`

    if (hasNotFoundIcon)
      return "NotFound"

    if (item.type === "trigger")
      return "DefaultTriggerIcon"

    return "DefaultIcon"

  }