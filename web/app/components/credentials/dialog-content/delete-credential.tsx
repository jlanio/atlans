import { GisFlowService } from "@/service/GisFlowService"
import { Dispatch, SetStateAction } from "react"
import { useCredentialsContext } from "@/context/useCredentialsContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { createToast } from "@/utils/createToast"
import { plural } from "@/lib/formatos"

interface DeleteCredentialProps {
  deleteCredentialId: string | undefined
  setDeleteCredentialId: Dispatch<SetStateAction<string | undefined>>
  /** Number of workflow nodes that reference the credential (0 = no warning shown). */
  usageCount?: number
}

const DeleteCredential = ({ deleteCredentialId, setDeleteCredentialId, usageCount = 0 }: DeleteCredentialProps) => {
  const { credentials, setCredentialsContext } = useCredentialsContext()
  const name = credentials.find(c => c.id === deleteCredentialId)?.name ?? ""

  async function handleConfirm() {
    if (!deleteCredentialId) return
    // The return value was ignored: on 403/409/network the item disappeared from the
    // list and reappeared on the next refresh, without any message.
    const res = await GisFlowService.deleteCredentialById(deleteCredentialId)
    if (res?.error) {
      createToast.error("Erro ao excluir credencial!", res.error.message)
      return
    }
    setCredentialsContext(prev => ({
      ...prev,
      credentials: prev.credentials.filter(c => c.id !== deleteCredentialId)
    }))
    // Without invalidating, the canvas would keep offering for up to 5 min a
    // credential that no longer exists — and the node saved with it would only
    // fail at execution.
    useWorkflowCatalogStore.getState().invalidarCredenciais()

    createToast.success("Credencial excluída", name || undefined)
    setDeleteCredentialId(undefined)
  }

  // Discreet warning (a muted line, not an alert panel): it says that the
  // deletion affects nodes using the credential, without turning the routine
  // confirmation into a scare.
  const note = usageCount > 0
    ? `Em uso em ${plural(usageCount, "nó", "nós")} de workflow — deixarão de resolver esta credencial.`
    : undefined

  return (
    <DeleteDialog
      title={`Excluir credencial «${name}»`}
      description="Ao excluir a credencial, não será possível recuperá-la."
      note={note}
      onConfirm={handleConfirm}
    />
  )
}

export default DeleteCredential
