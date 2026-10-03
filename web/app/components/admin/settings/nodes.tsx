"use client"

// "Nodes da plataforma" (platform nodes) section of the admin Settings: enables/
// disables nodes (disabling requires a reason; workflows that use them fail until re-enabled).

import { memo, useCallback, useMemo, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { INodeAdminEntry } from "@/service/types"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { Switch } from "@/app/components/ui/switch"
import { Textarea } from "@/app/components/ui/textarea"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/app/components/ui/dialog"
import { createToast } from "@/utils/createToast"
import { formatarInteiro } from "@/lib/formatos"

// ── Admin: habilita/desabilita nodes ────────────────────────────────────────

const _NODE_TYPE_LABEL: Record<string, string> = {
  trigger:    "Triggers",
  action:     "Actions",
  datasource: "Datasources",
  control:    "Controls",
  spatial:    "Spatial",
  output:     "Outputs",
}
const _NODE_TYPE_ORDER = ["trigger", "action", "datasource", "control", "spatial", "output"]

/**
 * A node row, memoized: typing in "Filtrar nodes…" re-renders the whole section,
 * and without memo each of the ~50 rows (with a Radix Switch) repainted on every
 * keystroke. With stable `node`/`onToggle`/`saving`, only the row that actually
 * changed repaints.
 */
const NodeAdminRow = memo(function NodeAdminRow({
  node, onToggle, saving,
}: {
  node: INodeAdminEntry
  onToggle: (node: INodeAdminEntry) => void
  saving: boolean
}) {
  return (
    <li className="flex items-center justify-between gap-3 px-3 py-2 text-xs">
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium text-foreground">{node.alias}</div>
        <div className="truncate text-muted-foreground">{node.name}</div>
        {!node.enabled && node.reason && (
          <div className="mt-0.5 truncate text-amber-600 dark:text-amber-400">
            Motivo: {node.reason}
          </div>
        )}
      </div>
      <Switch
        checked={node.enabled}
        onCheckedChange={() => !saving && onToggle(node)}
        disabled={saving}
        aria-label={`${node.enabled ? "Desabilitar" : "Reabilitar"} ${node.alias}`}
      />
    </li>
  )
})

export function NodesAdminSection({
  nodes,
  onChanged,
}: {
  nodes: INodeAdminEntry[]
  onChanged: () => void
}) {
  const [search, setSearch] = useState("")
  const [pendingDisable, setPendingDisable] = useState<INodeAdminEntry | null>(null)
  const [reason, setReason] = useState("")
  const [saving, setSaving] = useState(false)

  const grouped = useMemo(() => {
    const lower = search.trim().toLowerCase()
    const match = (n: INodeAdminEntry) =>
      !lower || n.name.toLowerCase().includes(lower) || n.alias.toLowerCase().includes(lower)

    const out: Record<string, INodeAdminEntry[]> = {}
    for (const t of _NODE_TYPE_ORDER) out[t] = []
    for (const n of nodes) {
      if (!match(n)) continue
      const t = n.type || "other"
      ;(out[t] ?? (out[t] = [])).push(n)
    }
    return out
  }, [nodes, search])

  // useCallback: `toggleEnabled` goes down as a stable `onToggle` to the memoized
  // rows (NodeAdminRow) — recreating it on every keystroke in the filter would defeat the memo.
  const toggleEnabled = useCallback(async (node: INodeAdminEntry) => {
    // Desabilitar exige motivo — abre modal. Reabilitar e direto.
    if (node.enabled) {
      setPendingDisable(node)
      setReason("")
      return
    }
    setSaving(true)
    const res = await GisFlowService.patchAdminNode(node.name, { enabled: true })
    setSaving(false)
    if (res.error) {
      createToast.error("Erro ao reabilitar", res.error.message)
    } else {
      createToast.success(`'${node.alias}' reabilitado.`)
      onChanged()
    }
  }, [onChanged])

  async function confirmDisable() {
    if (!pendingDisable) return
    if (reason.trim().length < 5) {
      createToast.error("Motivo é obrigatório", "Pelo menos 5 caracteres.")
      return
    }
    setSaving(true)
    const res = await GisFlowService.patchAdminNode(pendingDisable.name, {
      enabled: false,
      reason: reason.trim(),
    })
    setSaving(false)
    if (res.error) {
      createToast.error("Erro ao desabilitar", res.error.message)
      return
    }
    createToast.success(`'${pendingDisable.alias}' desabilitado.`)
    setPendingDisable(null)
    onChanged()
  }

  const totals = useMemo(() => {
    const enabled = nodes.filter(n => n.enabled).length
    return { enabled, disabled: nodes.length - enabled, total: nodes.length }
  }, [nodes])

  const hasSearch = search.trim().length > 0

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-muted-foreground">
          <span className="font-semibold text-foreground tabular-nums">{formatarInteiro(totals.enabled)}</span> habilitados,{" "}
          <span className="font-semibold text-foreground tabular-nums">{formatarInteiro(totals.disabled)}</span> desabilitados (de {formatarInteiro(totals.total)}).
        </div>
        <Input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Filtrar nodes…"
          className="h-8 max-w-xs text-xs max-md:h-10"
          aria-label="Filtrar nodes"
        />
      </div>

      {_NODE_TYPE_ORDER.map(type => {
        const list = grouped[type] ?? []
        if (list.length === 0) return null
        const label = _NODE_TYPE_LABEL[type] ?? type
        const groupEnabled = list.filter(n => n.enabled).length

        // Groups start CLOSED: with 50+ nodes, opening everything pushed the rest
        // of the page far away. During a search they reopen — otherwise the filter
        // would find results without showing them.
        // The key alternates with hasSearch so the <details>, which keeps its own
        // state in the DOM, syncs on entering and leaving the search.
        return (
          <details
            key={`${type}-${hasSearch}`}
            open={hasSearch}
            className="rounded-md border border-border bg-muted/30"
          >
            <summary className="flex cursor-pointer select-none items-center justify-between px-3 py-2 text-xs font-medium hover:bg-muted/50">
              <span className="flex items-center gap-2">
                {label}
                <Badge variant="secondary" className="text-[11px] tabular-nums">{list.length}</Badge>
              </span>
              <span className="text-[11px] text-muted-foreground tabular-nums">
                {groupEnabled} habilitados, {list.length - groupEnabled} desabilitados
              </span>
            </summary>
            <ul className="divide-y divide-border">
              {list.map(node => (
                <NodeAdminRow key={node.name} node={node} onToggle={toggleEnabled} saving={saving} />
              ))}
            </ul>
          </details>
        )
      })}

      <Dialog open={pendingDisable !== null} onOpenChange={(open) => !open && setPendingDisable(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Desabilitar &quot;{pendingDisable?.alias}&quot;</DialogTitle>
            <DialogDescription>
              Operadores não conseguirão mais arrastar este node no canvas. Workflows existentes que o utilizam falharão ao executar até que o node seja reabilitado.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label className="text-xs">Motivo (mínimo 5 caracteres)</Label>
            <Textarea
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="ex: bug X em apuração, será removido na versão Y"
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingDisable(null)} disabled={saving} className="max-md:h-10">
              Cancelar
            </Button>
            <Button onClick={confirmDisable} disabled={saving || reason.trim().length < 5} className="max-md:h-10">
              {saving ? "Desabilitando…" : "Desabilitar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
