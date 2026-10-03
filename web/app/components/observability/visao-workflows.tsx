"use client"

import { useEffect, useState } from "react"
import { TbChevronRight, TbHierarchy3 } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { Skeleton } from "@/app/components/ui/skeleton"
import { Switch } from "@/app/components/ui/switch"
import { CartaoDeEstado } from "@/app/components/shared/estados"
import { SeloAssistente } from "@/app/components/shared/selo-assistente"
import { StatusBadge } from "@/app/components/shared/StatusBadge"
import { COLUMN_HEADER, LABELED_CELL, CARD_HIGHLIGHT, STACKED_ROW } from "@/app/components/shared/tabela-empilhada"
import { cn } from "@/lib/utils"
import type { IWorkflowMetricsRow } from "@/service/types"
import { successRateColor } from "@/utils/formatters"
import { formatarDuracao, formatarInicio, formatInteger, formatPercent, categoryLabel } from "@/lib/formatos"

interface Props {
  linhas: IWorkflowMetricsRow[]
  carregando: boolean
  /** Only admins see the switch: `PUT /admin/workflows/{id}/status` is admin-only. */
  isAdmin: boolean
  onVerExecucoes: (workflowHash: string) => void
  /**
   * Called after the confirmation (when turning off) or directly (when turning
   * on). Returning `false` — or rejecting — reverts the switch; the toast belongs
   * to the caller, which has the API's message.
   */
  onAlternarAtivo: (workflowHash: string, ativo: boolean) => void | boolean | Promise<void | boolean>
}

/**
 * "Por workflow" (by workflow) view (spec §4.3): the list the old Workflows tab
 * was not. The order comes from the backend (`total_runs` desc, name asc), and
 * the switch asks for confirmation only when TURNING OFF — that is what stops
 * scheduled runs.
 */
export function VisaoWorkflows({ linhas, carregando, isAdmin, onVerExecucoes, onAlternarAtivo }: Props) {
  // Immediate reflection of the switch until the next refetch; it goes away when
  // the new list arrives, because that list already carries the saved value.
  const [overrides, setOverrides] = useState<Record<string, boolean>>({})
  useEffect(() => { setOverrides({}) }, [linhas])
  const [confirming, setConfirming] = useState<IWorkflowMetricsRow | null>(null)
  const [salvando, setSaving] = useState(false)

  async function aplicar(wf: IWorkflowMetricsRow, ativo: boolean) {
    setOverrides(prev => ({ ...prev, [wf.workflow_hash]: ativo }))
    setSaving(true)
    let ok = true
    try {
      ok = (await onAlternarAtivo(wf.workflow_hash, ativo)) !== false
    } catch {
      ok = false
    }
    setSaving(false)
    if (!ok) {
      setOverrides(prev => {
        const clone = { ...prev }
        delete clone[wf.workflow_hash]
        return clone
      })
    }
    setConfirming(null)
  }

  function aoAlternar(wf: IWorkflowMetricsRow, proximo: boolean) {
    if (proximo) void aplicar(wf, true)
    else setConfirming(wf)
  }

  if (carregando && linhas.length === 0) {
    return (
      <div className="flex flex-col rounded-lg border bg-card shadow-xs" aria-busy="true" aria-label="Carregando workflows">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className="flex items-center gap-4 border-b px-4 py-3 last:border-0">
            <div className="flex flex-1 flex-col gap-1.5"><Skeleton className="h-4 w-44" /><Skeleton className="h-3 w-24" /></div>
            <Skeleton className="h-4 w-12" /><Skeleton className="h-4 w-12" /><Skeleton className="h-4 w-20" />
          </div>
        ))}
      </div>
    )
  }

  if (linhas.length === 0) {
    return (
      <CartaoDeEstado
        icone={TbHierarchy3}
        titulo="Nenhum workflow no escopo"
        descricao="Crie um workflow, ou troque o workspace do filtro."
      />
    )
  }

  return (
    <div className="flex flex-col rounded-lg border bg-card shadow-xs">
      <div className="overflow-x-auto rounded-t-lg">
        <table className="w-full text-sm max-md:block md:min-w-[860px]">
          <thead className={COLUMN_HEADER}>
            <tr className="border-b bg-muted/40 text-[10.5px] font-semibold tracking-wider text-muted-foreground uppercase">
              <th scope="col" className="px-3 py-2 text-left">Workflow</th>
              <th scope="col" className="px-3 py-2 text-right">Execuções</th>
              <th scope="col" className="px-3 py-2 text-right">Sucesso</th>
              <th scope="col" className="px-3 py-2 text-right">Duração típica</th>
              <th scope="col" className="px-3 py-2 text-left">Última</th>
              <th scope="col" className="px-3 py-2 text-left">Falhas</th>
              {isAdmin && <th scope="col" className="px-3 py-2 text-center">Ativo</th>}
              <th scope="col" className="w-8 px-2 py-2"><span className="sr-only">Abrir</span></th>
            </tr>
          </thead>
          <tbody className="max-md:block">
            {linhas.map(wf => {
              const ativo = overrides[wf.workflow_hash] ?? wf.active
              const lastError = wf.last_error?.trim() || null
              const categoria = categoryLabel(wf.last_error_category)
              const errorText = lastError ? (categoria ? `${categoria} · ${lastError}` : lastError) : null
              return (
                <tr
                  key={wf.workflow_hash}
                  onClick={() => onVerExecucoes(wf.workflow_hash)}
                  className={cn(
                    "cursor-pointer border-b transition-colors last:border-0 hover:bg-accent/50",
                    !ativo && "text-muted-foreground",
                    STACKED_ROW,
                  )}
                >
                  <td className={cn("px-3 py-2.5 align-middle", CARD_HIGHLIGHT)}>
                    <div className="flex min-w-0 flex-col">
                      <div className="flex min-w-0 items-center gap-1.5">
                        {/* The button is the keyboard target; the whole row is the mouse's. */}
                        <button
                          type="button"
                          onClick={e => { e.stopPropagation(); onVerExecucoes(wf.workflow_hash) }}
                          aria-label={`Ver execuções de ${wf.workflow_name}`}
                          className="truncate text-left font-medium text-foreground outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 rounded-sm max-md:min-h-10"
                          title={wf.workflow_name}
                        >
                          {wf.workflow_name}
                        </button>
                        <SeloAssistente origem={wf.origem} />
                      </div>
                      <span className="truncate text-[11.5px] text-muted-foreground">
                        {wf.workspace_name ?? "—"}{!ativo && " · desativado"}
                      </span>
                    </div>
                  </td>
                  <td data-rotulo="execuções" className={cn("px-3 py-2.5 text-right align-middle tabular-nums", LABELED_CELL)}>
                    {formatInteger(wf.total_runs)}
                    {wf.running_runs > 0 && <span className="ml-1 text-xs text-blue-600 dark:text-blue-400">· {wf.running_runs} agora</span>}
                  </td>
                  <td data-rotulo="sucesso" className={cn("px-3 py-2.5 text-right align-middle tabular-nums", LABELED_CELL)}>
                    {wf.total_runs > 0
                      ? <span className={cn("font-medium", successRateColor(wf.success_rate, "amber"))}>{formatPercent(wf.success_rate, 0)}</span>
                      : <span className="text-muted-foreground">—</span>}
                  </td>
                  <td data-rotulo="típica" className={cn("px-3 py-2.5 text-right align-middle tabular-nums", LABELED_CELL)}>
                    {formatarDuracao(wf.p50_seconds)}
                  </td>
                  <td data-rotulo="última" className={cn("px-3 py-2.5 align-middle whitespace-nowrap", LABELED_CELL)}>
                    {wf.last_run_at ? (
                      <span className="inline-flex items-center gap-2">
                        <span className="tabular-nums text-xs" title={wf.last_run_at}>{formatarInicio(wf.last_run_at)}</span>
                        {wf.last_status && <span className="scale-90 origin-left"><StatusBadge status={wf.last_status} /></span>}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  {/* Limit on the inner block, not on the <td>: `max-width` on a table
                      cell is not defined by the specification (see the Erro
                      column of tabela-execucoes.tsx). */}
                  <td data-rotulo="falhas" className={cn("px-3 py-2.5 align-middle max-md:basis-full", LABELED_CELL)}>
                    <div className="flex min-w-0 max-w-[240px] items-baseline gap-2 max-md:max-w-full">
                      <span className={cn("tabular-nums font-medium", wf.failed_runs > 0 ? "text-red-600 dark:text-red-400" : "text-muted-foreground")}>
                        {formatInteger(wf.failed_runs)}
                      </span>
                      {errorText && (
                        <span className="truncate text-[12px] text-muted-foreground" title={errorText}>{errorText}</span>
                      )}
                    </div>
                  </td>
                  {isAdmin && (
                    <td className="px-3 py-2.5 text-center align-middle" onClick={e => e.stopPropagation()}>
                      {/* 40px touch target on the phone: it is the page's destructive action. */}
                      {/* <label>: the Switch is a <button>, a labelable element — a tap anywhere
                          in the 40px box toggles the switch. */}
                      <label className="inline-flex items-center justify-center max-md:min-h-10 max-md:min-w-10">
                        <Switch
                          checked={ativo}
                          disabled={salvando && confirming?.workflow_hash === wf.workflow_hash}
                          onCheckedChange={proximo => aoAlternar(wf, proximo)}
                          aria-label={`${ativo ? "Desativar" : "Ativar"} ${wf.workflow_name}`}
                        />
                      </label>
                    </td>
                  )}
                  <td className="w-8 px-2 py-2.5 text-right align-middle text-muted-foreground max-md:hidden">
                    <TbChevronRight size={14} aria-hidden="true" className="inline" />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <Dialog open={!!confirming} onOpenChange={aberto => { if (!aberto && !salvando) setConfirming(null) }}>
        <DialogContent closeDisabled={salvando}>
          <DialogHeader>
            <DialogTitle>Desativar «{confirming?.workflow_name}»?</DialogTitle>
            <DialogDescription>Novas execuções, inclusive agendadas, não vão rodar.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirming(null)} disabled={salvando}>Cancelar</Button>
            <Button variant="destructive" onClick={() => confirming && aplicar(confirming, false)} disabled={salvando}>
              {salvando ? "Desativando…" : "Desativar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
