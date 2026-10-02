"use client"

import { TbChevronRight, TbServer } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import { CartaoDeEstado } from "@/app/components/shared/estados"
import { CABECALHO_DE_COLUNAS, CELULA_COM_ROTULO, DESTAQUE_DA_FICHA, LINHA_EMPILHADA } from "@/app/components/shared/tabela-empilhada"
import { cn } from "@/lib/utils"
import type { IExecutorMetrics } from "@/service/types"
import { successRateColor } from "@/utils/formatters"
import { formatarDuracao, formatarInicio, formatarInteiro, formatarPercentual } from "@/lib/formatos"

interface Props {
  linhas: IExecutorMetrics[]
  carregando: boolean
  onVerExecucoes: (agentHost: string) => void
}

/** "2 de 4 em execução · 12 na fila" a partir da capacidade publicada; "—" sem ela. */
/** "geo-01@3f2a1" → nome "geo-01", sufixo "@3f2a1"; sem "@", tudo é nome. */
export function nomeDoExecutor(displayName: string): { nome: string; sufixo: string | null } {
  const i = displayName.indexOf("@")
  if (i <= 0) return { nome: displayName, sufixo: null }
  return { nome: displayName.slice(0, i), sufixo: displayName.slice(i) }
}

export function textoDeAgora(cap: IExecutorMetrics["capacity"]): string {
  if (!cap) return "—"
  const partes = [`${cap.running} de ${cap.max_concurrent} em execução`]
  if (cap.queued > 0) partes.push(`${formatarInteiro(cap.queued)} na fila`)
  return partes.join(" · ")
}

/** Executor no teto: tudo o que chegar agora vai para a fila. */
export function noTeto(cap: IExecutorMetrics["capacity"]): boolean {
  return !!cap && cap.max_concurrent > 0 && cap.running >= cap.max_concurrent
}

/**
 * Visão "Por executor" (spec §4.3): a frota inteira, com o que cada um está
 * fazendo agora e como foi no período. A linha "Sem executor" agrupa falhas
 * de despacho — não há host para filtrar, então ela não abre.
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
          <thead className={CABECALHO_DE_COLUNAS}>
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
                    LINHA_EMPILHADA,
                  )}
                >
                  <td className={cn("px-3 py-2.5 align-middle", DESTAQUE_DA_FICHA)}>
                    <span className="inline-flex min-w-0 items-center gap-2">
                      {!ex.unassigned && (
                        <span
                          className={cn("size-2 shrink-0 rounded-full", ex.online ? "bg-green-500" : "bg-muted-foreground/40")}
                          role="img"
                          aria-label={ex.online ? "online" : "offline"}
                        />
                      )}
                      {/* "geo-01@3f2a1": o sufixo é o que distingue dois executores
                          com o mesmo nome, não o que a pessoa reconhece — fica
                          menor e apagado, ao lado do nome. */}
                      <span className="truncate font-medium" title={ex.agent_host ?? undefined}>
                        {nomeDoExecutor(ex.display_name).nome}
                        {nomeDoExecutor(ex.display_name).sufixo && (
                          <span className="ml-1 text-[11px] font-normal text-muted-foreground">{nomeDoExecutor(ex.display_name).sufixo}</span>
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
                  <td data-rotulo="execuções" className={cn("px-3 py-2.5 text-right align-middle tabular-nums", CELULA_COM_ROTULO)}>
                    <span className="font-medium">{formatarInteiro(ex.total_runs)}</span>
                    <span className="ml-1.5 text-xs text-muted-foreground" aria-hidden="true">✓ {formatarInteiro(ex.success_runs)} · ✗ {formatarInteiro(ex.failed_runs)}</span>
                    <span className="sr-only">, {formatarInteiro(ex.success_runs)} concluídas, {formatarInteiro(ex.failed_runs)} falhas</span>
                  </td>
                  <td data-rotulo="sucesso" className={cn("px-3 py-2.5 text-right align-middle tabular-nums", CELULA_COM_ROTULO)}>
                    {ex.total_runs > 0
                      ? <span className={cn("font-medium", successRateColor(ex.success_rate, "amber"))}>{formatarPercentual(ex.success_rate, 0)}</span>
                      : <span className="text-muted-foreground">—</span>}
                  </td>
                  <td data-rotulo="típica" className={cn("px-3 py-2.5 text-right align-middle tabular-nums", CELULA_COM_ROTULO)}>
                    {/* Só a mediana: a média inclui falhas, zeros e órfãos — o número que o redesenho tirou da tela. */}
                    {formatarDuracao(ex.p50_seconds)}
                  </td>
                  <td data-rotulo="última" className={cn("px-3 py-2.5 align-middle text-xs tabular-nums whitespace-nowrap text-muted-foreground", CELULA_COM_ROTULO)} title={ex.last_run_at ?? undefined}>
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
