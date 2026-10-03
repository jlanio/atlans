import { TbCheck, TbDeviceFloppy, TbLoader } from "react-icons/tb"
import { useSaveWorkflow } from "../../../hooks/workflow/useSaveWorkflow"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { Button } from "@/app/components/ui/button"
import { cn } from "@/lib/utils"

// The state text (Salvando…/Salvo/Alterações não salvas) lives in the chip next
// to the workflow path. This button only ECHOES the state — an amber dot
// when there's something to save, red when the last save failed, a check right
// after saving — because it sits in the bottom column, far from the chip, and
// it's where the eye looks for "do I need to save?".
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
