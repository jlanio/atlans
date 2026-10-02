import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { FaArrowLeft } from "react-icons/fa"

const ReturnDrawerButton = () => {

  const setNodesDrawerState = useWorkflowCatalogStore(s => s.setNodesDrawerState)

  function handleClick() {
    setNodesDrawerState("opened")
  }

  return (
    <FaArrowLeft
      onClick={handleClick}
      className="text-foreground cursor-pointer" />
  )
}

export default ReturnDrawerButton
