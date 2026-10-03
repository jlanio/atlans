"use client"

import { TbChevronRight, TbServer } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import { CartaoDeEstado } from "@/app/components/shared/estados"
import { COLUMN_HEADER, LABELED_CELL, CARD_HIGHLIGHT, STACKED_ROW } from "@/app/components/shared/tabela-empilhada"
import { cn } from "@/lib/utils"
import type { IExecutorMetrics } from "@/service/types"
import { successRateColor } from "@/utils/formatters"
import { formatarDuracao, formatarInicio, formatInteger, formatPercent } from "@/lib/formatos"

interface Props {
  linhas: IExecutorMetrics[]
  carregando: boolean
  onVerExecucoes: (agentHost: string) => void
}

/** "2 de 4 em execução · 12 na fila" from the published capacity; "—" without it. */
/** "geo-01@3f2a1" → name "geo-01", suffix "@3f2a1"; without "@", it is all name. */
export function executorName(displayName: string): { nome: string; sufixo: string | null } {
  const i = displayName.indexOf("@")
  if (i <= 0) return { nome: displayName, sufixo: null }
  return { nome: displayName.slice(0, i), sufixo: displayName.slice(i) }
}

export function textoDeAgora(cap: IExecutorMetrics["capacity"]): string {
  if (!cap) return "—"
  const partes = [`${cap.running} de ${cap.max_concurrent} em execução`]
  if (cap.queued > 0) partes.push(`${formatInteger(cap.queued)} na fila`)
  return partes.join(" · ")
}

/** Executor at the ceiling: everything that arrives now goes to the queue. */
export function noTeto(cap: IExecutorMetrics["capacity"]): boolean {
  return !!cap && cap.max_concurrent > 0 && cap.running >= cap.max_concurrent
}

/**
 * "Por executor" (by executor) view (spec §4.3): the whole fleet, with what each
 * one is doing now and how it went in the period. The "Sem executor" row groups
 * dispatch failures — there is no host to filter by, so it does not open.
 */
export function VisaoExecutores({ linhas, carregando, onVerExecucoes }: Props) {
  if (carregando && linhas.length === 0) {
    return (
      <div className="flex flex-col rounded-lg border bg-card shadow-xs" aria-busy="true" aria-label="Carregando executores">
        {[0, 1, 2].map(i => (
          <div key={i} className="flex items-center gap-4 border-b px-4 py-3 last:border-0">
            <Skeleton className="h-4 w-36" /><Skeleton className="h-4 w-40" /><Skeleton className="ml-auto h-4 w-16" />
          </div>
        ))}
      </div>
    )
  }

  if (linhas.length === 0) {
    return (
      <CartaoDeEstado
        icone={TbServer}
        titulo="Nenhum executor no escopo"
        descricao="Registre um executor, ou espere um deles processar uma execução."
      />
    )
  }

  return (
    <div className="flex flex-col rounded-lg border bg-card shadow-xs">
      <div className="overflow-x-auto rounded-t-lg">
        <table className="w-full text-sm max-md:block md:min-w-[820px]">
          <thead className={COLUMN_HEADER}>
            <tr className="border-b bg-muted/40 text-[10.5px] font-semibold tracking-wider text-muted-foreground uppercase">
              <th scope="col" className="px-3 py-2 text-left">Executor</th>
              <th scope="col" className="px-3 py-2 text-left">Agora</th>
              <th scope="col" className="px-3 py-2 text-right">Execuções</th>
              <th scope="col" className="px-3 py-2 text-right">Sucesso</th>
              <th scope="col" className="px-3 py-2 text-right">Duração típica</th>
              <th scope="col" className="px-3 py-2 text-left">Última</th>
              <th scope="col" className="w-8 px-2 py-2"><span className="sr-only">Abrir</span></th>
            </tr>
          </thead>
          <tbody className="max-md:block">
            {linhas.map(ex => {
              const abrivel = !ex.unassigned && !!ex.agent_host
              const saturado = noTeto(ex.capacity)
              const abrir = () => { if (abrivel && ex.agent_host) onVerExecucoes(ex.agent_host) }
              return (
                <tr
                  key={ex.agent_host ?? "__sem_executor__"}
                  role={abrivel ? "button" : undefined}
                  tabIndex={abrivel ? 0 : undefined}
                  aria-label={abrivel ? `Ver execuções de ${ex.display_name}` : undefined}
                  title={abrivel ? undefined : "Execuções que falharam antes de chegar a um executor (falhas de despacho); não há executor para abrir"}
                  onClick={abrivel ? abrir : undefined}
                  onKeyDown={abrivel ? e => {
                    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); abrir() }
                  } : undefined}
                  className={cn(
                    "border-b transition-colors last:border-0 outline-none",
                    abrivel
                      ? "cursor-pointer hover:bg-accent/50 focus-visible:bg-accent/50 focus-visible:ring-[3px] focus-visible:ring-inset focus-visible:ring-ring/50"
                      : "text-muted-foreground/80",
                    "max-md:min-h-10",
                    STACKED_ROW,
                  )}
                >
                  <td className={cn("px-3 py-2.5 align-middle", CARD_HIGHLIGHT)}>
                    <span className="inline-flex min-w-0 items-center gap-2">
                      {!ex.unassigned && (
                        <span
                          className={cn("size-2 shrink-0 rounded-full", ex.online ? "bg-green-500" : "bg-muted-foreground/40")}
                          role="img"
                          aria-label={ex.online ? "online" : "offline"}
                        />
                      )}
                      {/* "geo-01@3f2a1": the suffix is what tells apart two executors
                          with the same name, not what the person recognizes — it
                          stays smaller and dimmed, next to the name. */}
                      <span className="truncate font-medium" title={ex.agent_host ?? undefined}>
                        {executorName(ex.display_name).nome}
                        {executorName(ex.display_name).sufixo && (
                          <span className="ml-1 text-[11px] font-normal text-muted-foreground">{executorName(ex.display_name).sufixo}</span>
                        )}
                      </span>
                      {ex.is_default && (
                        <span className="rounded bg-teal-100 px-1 py-px text-[10px] font-semibold tracking-wider text-teal-700 uppercase dark:bg-teal-500/15 dark:text-teal-400" title="Executor do pool compartilhado">
                          pool
                        </span>
                      )}
                    </span>
                  </td>
                  <td className={cn("px-3 py-2.5 align-middle text-xs whitespace-nowrap max-md:basis-full", saturado ? "font-medium text-amber-700 dark:text-amber-400" : "text-muted-foreground")}>
                    {ex.unassigned ? "—" : textoDeAgora(ex.capacity)}
                    {saturado && <span className="sr-only"> (no teto)</span>}
                  </td>
                  <td data-rotulo="execuções" className={cn("px-3 py-2.5 text-right align-middle tabular-nums", LABELED_CELL)}>
                    <span className="font-medium">{formatInteger(ex.total_runs)}</span>
                    <span className="ml-1.5 text-xs text-muted-foreground" aria-hidden="true">✓ {formatInteger(ex.success_runs)} · ✗ {formatInteger(ex.failed_runs)}</span>
                    <span className="sr-only">, {formatInteger(ex.success_runs)} concluídas, {formatInteger(ex.failed_runs)} falhas</span>
                  </td>
                  <td data-rotulo="sucesso" className={cn("px-3 py-2.5 text-right align-middle tabular-nums", LABELED_CELL)}>
                    {ex.total_runs > 0
                      ? <span className={cn("font-medium", successRateColor(ex.success_rate, "amber"))}>{formatPercent(ex.success_rate, 0)}</span>
                      : <span className="text-muted-foreground">—</span>}
                  </td>
                  <td data-rotulo="típica" className={cn("px-3 py-2.5 text-right align-middle tabular-nums", LABELED_CELL)}>
                    {/* Only the median: the mean includes failures, zeros and orphans — the number the redesign took off the screen. */}
                    {formatarDuracao(ex.p50_seconds)}
                  </td>
                  <td data-rotulo="última" className={cn("px-3 py-2.5 align-middle text-xs tabular-nums whitespace-nowrap text-muted-foreground", LABELED_CELL)} title={ex.last_run_at ?? undefined}>
                    {formatarInicio(ex.last_run_at)}
                  </td>
                  <td className="w-8 px-2 py-2.5 text-right align-middle text-muted-foreground max-md:hidden">
                    {abrivel && <TbChevronRight size={14} aria-hidden="true" className="inline" />}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
