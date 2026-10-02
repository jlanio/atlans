import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkflow } from "@/service/types"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { createToast } from "@/utils/createToast"

interface DeleteProjectProps {
  workflow: IWorkflow
  /** Chamado depois do DELETE dar certo: o pai tira o workflow da lista e fecha o diálogo. */
  onDeleted: (id: string) => void
}

// Recebe o workflow por prop, e não por um contexto de página: a lista vive
// no hook de dados de Projetos, e um segundo lugar guardando "os projetos"
// divergiria dela na primeira mutação otimista.
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
