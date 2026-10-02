import { TbCheck, TbDeviceFloppy, TbLoader } from "react-icons/tb"
import { useSaveWorkflow } from "../../../hooks/workflow/useSaveWorkflow"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { Button } from "@/app/components/ui/button"
import { cn } from "@/lib/utils"

// O texto do estado (Salvando…/Salvo/Alterações não salvas) mora no chip ao
// lado do caminho do workflow. Este botão só ECOA o estado — um ponto âmbar
// quando há o que salvar, vermelho quando o último save falhou, um check logo
// depois de salvar — porque ele fica na coluna de baixo, longe do chip, e é
// nele que o olho procura "preciso salvar?".
const SaveWorkflow = () => {

  const { isSaving, saveWorkflow } = useSaveWorkflow()
  const status = useWorkflowSaveStore(s => s.saveStatus)

  async function handleSave() {
    if (isSaving) return
    await saveWorkflow()
  }

  const titulo =
    status === 'unsaved' || status === 'needs_name' ? "Salvar alterações (Ctrl+S)"
    : status === 'error' ? "Falha ao salvar. Tentar novamente (Ctrl+S)"
    : status === 'saving' ? "Salvando…"
    : "Salvar workflow (Ctrl+S)"

  const pendente = status === 'unsaved' || status === 'needs_name' || status === 'error'

  return (
    <Button
      onClick={handleSave}
      variant="outline"
      size="icon"
      title={titulo}
      aria-label={titulo}
      data-save-status={status}
      className="relative"
    >
      {status === 'saving'
        ? <TbLoader className="animate-spin" />
        : status === 'saved'
          ? <TbCheck className="text-green-500" />
          : <TbDeviceFloppy />
      }
      {pendente && (
        <span
          aria-hidden="true"
          data-role="save-pending-dot"
          className={cn(
            "absolute -top-1 -right-1 size-2.5 rounded-full ring-2 ring-background",
            status === 'error' ? "bg-destructive" : "bg-amber-500",
          )}
        />
      )}
    </Button>
  )
}

export default SaveWorkflow
