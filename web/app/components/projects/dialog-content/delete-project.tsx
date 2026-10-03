import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkflow } from "@/service/types"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { createToast } from "@/utils/createToast"

interface DeleteProjectProps {
  workflow: IWorkflow
  /** Called after the DELETE succeeds: the parent removes the workflow from the list and closes the dialog. */
  onDeleted: (id: string) => void
}

// Takes the workflow by prop, not through a page context: the list lives
// in the Projects data hook, and a second place holding "the projects"
// would diverge from it on the first optimistic mutation.
const DeleteProject = ({ workflow, onDeleted }: DeleteProjectProps) => {
  async function handleConfirm() {
    const res = await GisFlowService.deleteWorkflowById(workflow.id_hash)
    if (res?.error) {
      createToast.error("Erro ao excluir workflow.")
      return
    }
    onDeleted(workflow.id_hash)
  }

  return (
    <DeleteDialog
      title={`Deletar projeto "${workflow.name}"`}
      description="Ao deletar o projeto, não será possível recuperá-lo."
      onConfirm={handleConfirm}
    />
  )
}

export default DeleteProject
