"use client"

import { memo, useEffect, useState } from "react"
import { TbActivity, TbChevronRight } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import { CartaoDeEstado, ErroDeCarga, SemResultado } from "@/app/components/shared/estados"
import { SeloAssistente } from "@/app/components/shared/selo-assistente"
import { StatusBadge } from "@/app/components/shared/StatusBadge"
import { CABECALHO_DE_COLUNAS, CELULA_COM_ROTULO, DESTAQUE_DA_FICHA, LINHA_EMPILHADA } from "@/app/components/shared/tabela-empilhada"
import { fromBackend, formatLocal } from "@/lib/dayjs"
import { cn } from "@/lib/utils"
import type { IRunSummary } from "@/service/types"
import { formatarDuracao, formatarInicio, formatarInteiro, rotuloDaCategoria, rotuloDaOrigem, rotuloDoNivel } from "@/lib/formatos"

interface Props {
  runs: IRunSummary[]
  total: number | null
  hasMore: boolean
  carregando: boolean
  carregandoMais: boolean
  falhou: boolean
  /** There is an active filter: changes the empty text and offers "Limpar filtros". */
  filtrado: boolean
  onCarregarMais: () => void
  onAbrir: (runId: string) => void
  onLimparFiltros?: () => void
  onRecarregar?: () => void
  /** run_id open in the panel — the row stays highlighted. */
  abertaId?: string | null
}

const EM_ANDAMENTO = new Set(["running", "pending"])

/**
 * Coarse-grained clock for the "elapsed" of in-progress runs. It only ticks
 * when there is one: a table of completed runs has no reason to re-render
 * every half minute.
 */
function useAgora(ativo: boolean): number {
  const [agora, setAgora] = useState(() => Date.now())
  useEffect(() => {
    if (!ativo) return
    setAgora(Date.now())
    // Like the other clocks/pollers in the codebase: it does not advance with the
    // tab hidden (nobody sees the "elapsed") and catches up at once when focus returns.
    const tick = () => { if (document.visibilityState === "visible") setAgora(Date.now()) }
    const t = setInterval(tick, 30_000)
    document.addEventListener("visibilitychange", tick)
    return () => {
      clearInterval(t)
      document.removeEventListener("visibilitychange", tick)
    }
  }, [ativo])
  return agora
}

/** Run duration; for in-progress ones, the time elapsed since the start. */
export function duracaoDaExecucao(run: IRunSummary, agoraMs: number): string {
  if (EM_ANDAMENTO.has(run.status)) {
    const inicio = fromBackend(run.started_at)?.valueOf()
    return inicio ? formatarDuracao((agoraMs - inicio) / 1000) : "—"
  }
  return formatarDuracao(run.duration_seconds)
}

/** "Cadastro · agendado · maria": workspace, origin and who triggered it, whatever there is. */
export function sublinhaDoWorkflow(run: IRunSummary): string {
  return [run.workspace_name, rotuloDaOrigem(run.trigger_source), run.triggered_by_username]
    .filter((p): p is string => !!p)
    .join(" · ")
}

/**
 * Runs table (spec §4.3). The whole row is the target — and it is a real
 * button for the keyboard, because a `<tr>` does not take focus or respond to
 * Enter on its own. No "Ativo" (active) switch: turning a workflow off is a
 * workflow action, and it lives in the "Por workflow" (by workflow) view.
 */
export const TabelaExecucoes = memo(function TabelaExecucoes({
  runs, total, hasMore, carregando, carregandoMais, falhou, filtrado,
  onCarregarMais, onAbrir, onLimparFiltros, onRecarregar, abertaId = null,
}: Props) {
  const agora = useAgora(runs.some(r => EM_ANDAMENTO.has(r.status)))

  if (carregando && runs.length === 0) {
    return (
      <div className="flex flex-col rounded-lg border bg-card shadow-xs" aria-busy="true" aria-label="Carregando execuções">
        {[0, 1, 2, 3, 4].map(i => (
          <div key={i} className="flex items-center gap-4 border-b px-4 py-3 last:border-0">
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-4 w-48" />
            <Skeleton className="ml-auto h-4 w-16" />
            <Skeleton className="h-4 w-12" />
          </div>
        ))}
      </div>
    )
  }

  if (falhou && runs.length === 0) {
    return (
      <ErroDeCarga
        titulo="Não foi possível carregar as execuções"
        mensagem="A lista não está vazia — só não pôde ser lida agora."
        onTentar={onRecarregar}
      />
    )
  }

  if (runs.length === 0) {
    return filtrado ? (
      <SemResultado
        texto="Nada com esses filtros"
        dica="Nenhuma execução no período combina com os filtros escolhidos."
        onLimpar={onLimparFiltros}
      />
    ) : (
      <CartaoDeEstado
        icone={TbActivity}
        titulo="Nenhuma execução no período"
        descricao="Quando um workflow rodar, ele aparece aqui com status, duração e executor."
      />
    )
  }

  return (
    <div className="flex flex-col rounded-lg border bg-card shadow-xs">
      <div className="overflow-x-auto rounded-t-lg">
        {/* `min-w` only from `md` up: below that the row becomes a card
            (tabela-empilhada.ts) and there are no columns to squeeze. */}
        <table className="w-full text-sm max-md:block md:min-w-[860px]">
          <thead className={CABECALHO_DE_COLUNAS}>
            <tr className="border-b bg-muted/40 text-[10.5px] font-semibold tracking-wider text-muted-foreground uppercase">
              <th scope="col" className="px-3 py-2 text-left">Status</th>
              <th scope="col" className="px-3 py-2 text-left">Workflow</th>
              <th scope="col" className="px-3 py-2 text-left">Início</th>
              <th scope="col" className="px-3 py-2 text-left">Duração</th>
              <th scope="col" className="px-3 py-2 text-left">Executor</th>
              <th scope="col" className="px-3 py-2 text-left">Erro</th>
              <th scope="col" className="w-8 px-2 py-2"><span className="sr-only">Abrir</span></th>
            </tr>
          </thead>
          <tbody className="max-md:block">
            {runs.map(run => (
              // Only in-progress runs use `agora` (the live elapsed time); the others
              // get a fixed 0, so the row's React.memo holds and does not
              // reconcile the whole table on every 30 s tick.
              <LinhaDaExecucao
                key={run.run_id}
                run={run}
                agora={EM_ANDAMENTO.has(run.status) ? agora : 0}
                aberta={run.run_id === abertaId}
                onAbrir={onAbrir}
              />
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t px-4 py-2.5 text-xs text-muted-foreground">
        <span aria-live="polite">
          {total != null
            ? `Mostrando ${formatarInteiro(runs.length)} de ${formatarInteiro(total)}`
            : `Mostrando ${formatarInteiro(runs.length)}`}
        </span>
        {hasMore && (
          <Button variant="outline" size="sm" onClick={onCarregarMais} disabled={carregandoMais} className="max-md:h-10">
            {carregandoMais ? "Carregando…" : "Ver mais"}
          </Button>
        )}
      </div>
    </div>
  )
})

const LinhaDaExecucao = memo(function LinhaDaExecucao({ run, agora, aberta, onAbrir }: {
  run: IRunSummary
  agora: number
  aberta: boolean
  onAbrir: (runId: string) => void
}) {
  const nome = run.workflow_name ?? "Workflow sem nome"
  const falhou = run.status === "failed" || run.status === "error"
  const categoria = rotuloDaCategoria(run.error_category)
  const erro = run.error_message?.trim() || null
  const erroTexto = erro ? (categoria ? `${categoria} · ${erro}` : erro) : null
  const nivel = rotuloDoNivel(run.dispatch_tier)
  const inicioCompleto = formatLocal(run.started_at, "DD/MM/YYYY HH:mm:ss")

  return (
    // The whole row responds to clicks (mouse and touch); the keyboard and
    // screen-reader target is the button on the workflow name. `role="button"`
    // on the <tr> itself would erase the cells (status, error) for those who
    // listen to the table.
    <tr
      onClick={() => onAbrir(run.run_id)}
      className={cn(
        "cursor-pointer border-b transition-colors last:border-0",
        "hover:bg-accent/50 focus-within:bg-accent/50",
        aberta && "bg-primary/5",
        // Touch target on the phone: the whole card, never less than 40px.
        "max-md:min-h-10",
        LINHA_EMPILHADA,
      )}
    >
      <td className="px-3 py-2.5 align-middle max-md:order-2"><StatusBadge status={run.status} /></td>
      <td className={cn("px-3 py-2.5 align-middle max-md:order-1", DESTAQUE_DA_FICHA)}>
        <div className="flex min-w-0 flex-col">
          <div className="flex min-w-0 items-center gap-1.5">
            <button
              type="button"
              onClick={e => { e.stopPropagation(); onAbrir(run.run_id) }}
              aria-label={`Abrir execução de ${nome}`}
              aria-current={aberta ? "true" : undefined}
              title={nome}
              className="truncate rounded-sm text-left font-medium outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              {nome}
            </button>
            <SeloAssistente origem={run.workflow_origem} />
          </div>
          <span className="truncate text-[11.5px] text-muted-foreground">{sublinhaDoWorkflow(run) || "—"}</span>
        </div>
      </td>
      <td className="px-3 py-2.5 align-middle whitespace-nowrap tabular-nums max-md:order-3 max-md:ml-auto max-md:text-xs max-md:text-muted-foreground" title={inicioCompleto}>
        {formatarInicio(run.started_at)}
      </td>
      <td data-rotulo="duração" className={cn("px-3 py-2.5 align-middle whitespace-nowrap tabular-nums max-md:order-4 max-md:text-xs", CELULA_COM_ROTULO)}>
        {duracaoDaExecucao(run, agora)}
      </td>
      <td data-rotulo="executor" className={cn("px-3 py-2.5 align-middle whitespace-nowrap max-md:order-5 max-md:text-xs", CELULA_COM_ROTULO)}>
        {run.executor_name || run.agent_host ? (
          <span className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" className="size-2 shrink-0 rounded-full bg-muted-foreground/50" />
            <span className="truncate" title={run.agent_host ?? undefined}>{run.executor_name ?? run.agent_host}</span>
            {nivel && (
              <span
                className={cn(
                  "rounded px-1 py-px text-[10px] font-semibold tracking-wider uppercase",
                  nivel === "reserva"
                    ? "bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400"
                    : "bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-400",
                )}
                title={nivel === "reserva" ? "Rodou num executor de reserva da política" : "Rodou no pool compartilhado"}
              >
                {nivel}
              </span>
            )}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      {/* The width limit lives on the text, not on the <td>: the specification does
          not define `max-width` on a table cell, and an error with a long URL
          could widen the column until the table scrolled sideways. On the
          <span> the rule of a regular block applies, the same in every browser. */}
      <td className="px-3 py-2.5 align-middle max-md:order-6 max-md:basis-full max-md:text-xs">
        {erroTexto ? (
          <span
            className={cn("block max-w-[220px] truncate text-[12.5px] max-md:max-w-full", falhou ? "text-red-600 dark:text-red-400" : "text-muted-foreground")}
            title={erroTexto}
          >
            {erroTexto}
          </span>
        ) : (
          <span className="sr-only">Sem erro</span>
        )}
      </td>
      <td className="w-8 px-2 py-2.5 text-right align-middle text-muted-foreground max-md:hidden">
        <TbChevronRight size={14} aria-hidden="true" className="inline" />
      </td>
    </tr>
  )
})
