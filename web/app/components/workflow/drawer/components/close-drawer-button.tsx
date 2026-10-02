import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { useLinkNodeParams } from "@/app/hooks/workflow/useLinkNodeParams"
import { MdOutlineClose } from "react-icons/md"

const CloseDrawerButton = () => {

  const setNodesDrawerState = useWorkflowCatalogStore(s => s.setNodesDrawerState)
  const { removeLinkNodeParam } = useLinkNodeParams()

  function handleClick() {
    setNodesDrawerState("closed")
    removeLinkNodeParam()
  }

  return (
    <MdOutlineClose
      onClick={handleClick}
      className="text-foreground cursor-pointer font-semibold text-lg" />
  )
}

export default CloseDrawerButton
