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
  /** Nº de nós de workflow que referenciam a credencial (0 = não exibe aviso). */
  usageCount?: number
}

const DeleteCredential = ({ deleteCredentialId, setDeleteCredentialId, usageCount = 0 }: DeleteCredentialProps) => {
  const { credentials, setCredentialsContext } = useCredentialsContext()
  const name = credentials.find(c => c.id === deleteCredentialId)?.name ?? ""

  async function handleConfirm() {
    if (!deleteCredentialId) return
    // O retorno era ignorado: em 403/409/rede o item desaparecia da lista e
    // reaparecia no próximo refresh, sem nenhuma mensagem.
    const res = await GisFlowService.deleteCredentialById(deleteCredentialId)
    if (res?.error) {
      createToast.error("Erro ao excluir credencial!", res.error.message)
      return
    }
    setCredentialsContext(prev => ({
      ...prev,
      credentials: prev.credentials.filter(c => c.id !== deleteCredentialId)
    }))
    // Sem invalidar, o canvas seguiria oferecendo por até 5 min uma credencial
    // que não existe mais — e o nó salvo com ela falharia só na execução.
    useWorkflowCatalogStore.getState().invalidarCredenciais()

    createToast.success("Credencial excluída", name || undefined)
    setDeleteCredentialId(undefined)
  }

  // Aviso discreto (uma linha muted, não um painel de alerta): informa que a
  // exclusão afeta nós que usam a credencial, sem transformar a confirmação
  // rotineira num susto.
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
