import { useState } from "react"
import { createPortal } from "react-dom"
import { GisFlowService } from "@/service/GisFlowService"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { createToast } from "@/utils/createToast"
import { TbPinFilled, TbX } from "react-icons/tb"

interface PinDialogProps {
  nodeId: string
  workflowId: string
  onClose: () => void
}

const TTL_OPTIONS = [
  { label: "Sem expiração", value: null },
  { label: "1 hora", value: 1 },
  { label: "6 horas", value: 6 },
  { label: "12 horas", value: 12 },
  { label: "24 horas", value: 24 },
  { label: "48 horas", value: 48 },
  { label: "7 dias", value: 168 },
  { label: "30 dias", value: 720 },
]

export default function PinDialog({ nodeId, workflowId, onClose }: PinDialogProps) {
  const pinnedNodes = useWorkflowCatalogStore(s => s.pinnedNodes)
  const setPinnedNodes = useWorkflowCatalogStore(s => s.setPinnedNodes)
  const [ttlHours, setTtlHours] = useState<number | null>(null)
  const [customHours, setCustomHours] = useState("")
  const [useCustom, setUseCustom] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handlePin() {
    setLoading(true)
    const finalTtl = useCustom ? (Number(customHours) || null) : ttlHours

    try {
      const res = await GisFlowService.pinNodeOutput(workflowId, nodeId, {}, finalTtl)

      if (res?.error) {
        createToast.error("Erro ao fixar nó", res.error.message)
        return
      }

      setPinnedNodes([
        ...pinnedNodes.filter(p => p.node_id !== nodeId),
        {
          node_id: nodeId,
          pinned_at: res.data!.pinned_at,
          expires_at: res.data!.expires_at,
          ttl_hours: res.data!.ttl_hours,
          expired: false,
        },
      ])

      createToast.success("Output fixado!")
      onClose()
    } catch (err) {
      createToast.error("Erro ao fixar nó", String(err))
    } finally {
      setLoading(false)
    }
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-background border border-border rounded-lg shadow-lg p-5 w-[320px]" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TbPinFilled className="text-amber-500" size={18} />
            <h3 className="text-sm font-semibold">Fixar output do nó</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <TbX size={16} />
          </button>
        </div>

        <p className="text-xs text-muted-foreground mb-3">
          O output será fixado na próxima execução. Execuções futuras usarão o resultado salvo em vez de reprocessar o nó.
        </p>

        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 block">
          Validade do cache
        </label>

        <div className="flex flex-col gap-1.5 mb-3">
          {TTL_OPTIONS.map(opt => (
            <button
              key={opt.label}
              onClick={() => { setTtlHours(opt.value); setUseCustom(false) }}
              className={`text-left px-3 py-1.5 rounded-md border text-xs transition-colors ${
                !useCustom && ttlHours === opt.value
                  ? "border-amber-500 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                  : "border-border hover:bg-accent"
              }`}
            >
              {opt.label}
            </button>
          ))}

          <div className="flex items-center gap-2">
            <button
              onClick={() => setUseCustom(true)}
              className={`text-left px-3 py-1.5 rounded-md border text-xs transition-colors flex-1 ${
                useCustom
                  ? "border-amber-500 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                  : "border-border hover:bg-accent"
              }`}
            >
              Personalizado
            </button>
            {useCustom && (
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={1}
                  value={customHours}
                  onChange={e => setCustomHours(e.target.value)}
                  placeholder="N"
                  className="w-16 px-2 py-1 text-xs border border-border rounded-md bg-background"
                  autoFocus
                />
                <span className="text-xs text-muted-foreground">horas</span>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs rounded-md border border-border hover:bg-accent transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handlePin}
            disabled={loading}
            className="px-3 py-1.5 text-xs rounded-md bg-amber-500 text-white hover:bg-amber-600 transition-colors disabled:opacity-50"
          >
            {loading ? "Fixando..." : "Fixar"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
