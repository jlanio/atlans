import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { dayjs, fromBackend, formatLocal } from "@/lib/dayjs"
import { TbPinFilled, TbPinnedOff, TbClock } from "react-icons/tb"
import { useState } from "react"
import PinDialog from "../custom-nodes/tools/pin-dialog"

interface PinSectionProps {
  nodeId: string
  workflowId: string
}

export default function PinSection({ nodeId, workflowId }: PinSectionProps) {
  const pinnedNodes = useWorkflowCatalogStore(s => s.pinnedNodes)
  const setPinnedNodes = useWorkflowCatalogStore(s => s.setPinnedNodes)
  const [pinDialogOpen, setPinDialogOpen] = useState(false)

  const pinMeta = pinnedNodes.find(p => p.node_id === nodeId)
  const isPinned = !!pinMeta && !pinMeta.expired

  async function handleUnpin() {
    try {
      const res = await GisFlowService.unpinNodeOutput(workflowId, nodeId)
      if (res?.error) {
        createToast.error("Erro ao remover pin", res.error.message)
        return
      }
      setPinnedNodes(pinnedNodes.filter(p => p.node_id !== nodeId))
      createToast.success("Pin removido")
    } catch (err) {
      createToast.error("Erro ao remover pin", String(err))
    }
  }

  function formatExpiry(expiresAt: string | null) {
    if (!expiresAt) return "Sem expiração"
    const d = fromBackend(expiresAt)
    if (!d) return "Sem expiração"
    const now = dayjs()
    if (d.isBefore(now)) return "Expirado"
    return `Expira ${d.from(now)}`
  }

  return (
    <div className="flex flex-col gap-2 px-3 py-3 border-t">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Pin Data
      </p>

      {isPinned ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 px-2.5 py-2 rounded-md border border-amber-500/30 bg-amber-500/5">
            <TbPinFilled className="text-amber-500 shrink-0" size={14} />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-amber-600 dark:text-amber-400">Output fixado</p>
              <div className="flex items-center gap-1 mt-0.5">
                <TbClock size={10} className="text-muted-foreground" />
                <span className="text-[10px] text-muted-foreground">
                  {formatExpiry(pinMeta.expires_at)}
                  {pinMeta.ttl_hours && ` (${pinMeta.ttl_hours}h)`}
                </span>
              </div>
              {pinMeta.pinned_at && (
                <span className="text-[10px] text-muted-foreground block mt-0.5">
                  Fixado em {formatLocal(pinMeta.pinned_at, "DD/MM HH:mm")}
                </span>
              )}
            </div>
            <button
              onClick={handleUnpin}
              title="Remover pin"
              className="p-1 rounded hover:bg-destructive/10 transition-colors"
            >
              <TbPinnedOff size={14} className="text-destructive" />
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setPinDialogOpen(true)}
          className="flex items-center gap-2 px-2.5 py-2 rounded-md border border-dashed border-border hover:border-amber-500/50 hover:bg-amber-500/5 transition-colors text-xs text-muted-foreground hover:text-amber-600 dark:hover:text-amber-400"
        >
          <TbPinFilled size={14} />
          <span>Fixar output deste nó</span>
        </button>
      )}

      {pinDialogOpen && (
        <PinDialog
          nodeId={nodeId}
          workflowId={workflowId}
          onClose={() => setPinDialogOpen(false)}
        />
      )}
    </div>
  )
}
