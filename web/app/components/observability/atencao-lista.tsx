"use client"

import type { IconType } from "react-icons"
import { TbAlertTriangle, TbBellOff, TbChevronRight, TbCircleCheck, TbClock, TbServer, TbX } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { SeloAssistente } from "../shared/selo-assistente"
import type { AcaoDeAtencao, ItemDeAtencao } from "./atencao"
import { useAtencaoDispensada } from "./atencao-dispensados"
import { plural } from "@/lib/formatos"

interface Props {
  itens: ItemDeAtencao[]
  carregando: boolean
  /** Sentence for the empty list (`textoDeVazio` from `atencao.ts`). */
  vazio: string
  onAcao: (acao: AcaoDeAtencao) => void
  /** Notice when one of the sources (metrics, executors) failed. */
  falha?: string
}

// Status colors, the ones from `StatusBadge`: stuck is "in progress for too
// long" (amber), failures are failures (red), ceiling is queue (blue).
const ESTILO: Record<ItemDeAtencao["tipo"], { icone: IconType; classe: string }> = {
  presa: { icone: TbClock, classe: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400" },
  falhas: { icone: TbAlertTriangle, classe: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400" },
  saturado: { icone: TbServer, classe: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400" },
}

/**
 * "Precisa de atenção" (Needs attention, spec §4.3). Each item is ONE button —
 * the whole item is the target, and the action (open the run, filter by
 * failures, open the executor) is decided by whoever composes the page; here
 * we only say what happened.
 *
 * The alerts are derived from live metrics, so they used to stay open with no
 * way to clear them. Now each item has a "dismiss" (×), with "Limpar tudo"
 * (clear all) and "Restaurar" (restore) at the top — a per-browser convenience
 * (`atencao-dispensados`). Dismissing does not blind: the item comes back if
 * the problem gets worse (the signature changes).
 */
export function AtencaoLista({ itens, carregando, vazio, onAcao, falha }: Props) {
  const { ocultar, contarOcultos, dispensar, dispensarTodos, restaurar } = useAtencaoDispensada()
  const visiveis = ocultar(itens)
  const ocultos = contarOcultos(itens)

  const mostrandoSkeleton = carregando && itens.length === 0 && !falha
  // Tells "nothing needs attention" (green) from "you dismissed everything"
  // (neutral): the second is NOT cause for celebration, and the way out is to
  // restore, not to relax.
  const tudoDispensado = visiveis.length === 0 && ocultos > 0

  return (
    <section
      aria-labelledby="atencao-titulo"
      aria-busy={mostrandoSkeleton}
      className="flex min-w-0 flex-col rounded-lg border bg-card shadow-xs"
    >
      <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1 px-4 pt-4 pb-1">
        <div className="min-w-0">
          <h2 id="atencao-titulo" className="text-sm font-semibold">Precisa de atenção</h2>
          <p className="text-xs text-muted-foreground">
            {mostrandoSkeleton
              ? "verificando…"
              : visiveis.length > 0
                ? `${plural(visiveis.length, "item", "itens")} · o que mudaria uma decisão hoje`
                : tudoDispensado
                  ? "tudo dispensado"
                  : "nada que mude uma decisão hoje"}
          </p>
        </div>
        {!mostrandoSkeleton && (visiveis.length > 0 || ocultos > 0) && (
          <div className="flex shrink-0 items-center gap-1">
            {ocultos > 0 && (
              <button
                type="button"
                onClick={restaurar}
                className="rounded-sm px-1 text-xs font-medium text-muted-foreground underline-offset-2 outline-none hover:text-foreground hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
              >
                Restaurar ({ocultos})
              </button>
            )}
            {visiveis.length > 0 && (
              <button
                type="button"
                onClick={() => dispensarTodos(itens)}
                className="rounded-sm px-1 text-xs font-medium text-muted-foreground underline-offset-2 outline-none hover:text-foreground hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
              >
                Limpar tudo
              </button>
            )}
          </div>
        )}
      </div>
      {falha && (
        <p role="alert" className="mx-4 mb-1 rounded-md bg-destructive/10 px-3 py-1.5 text-xs text-destructive">
          {falha}{itens.length > 0 && " Mostrando a última leitura."}
        </p>
      )}
      {mostrandoSkeleton ? (
        <div className="flex flex-col gap-2 px-4 pb-4 pt-2">
          {[0, 1, 2].map(i => (
            <div key={i} className="flex items-start gap-2.5">
              <Skeleton className="size-7 shrink-0 rounded-md" />
              <div className="flex flex-1 flex-col gap-1.5">
                <Skeleton className="h-3.5 w-4/5" />
                <Skeleton className="h-3 w-3/5" />
              </div>
            </div>
          ))}
        </div>
      ) : tudoDispensado ? (
        <div className="flex flex-1 items-center gap-3 px-4 pb-5 pt-3">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <TbBellOff size={16} aria-hidden="true" />
          </span>
          <p className="text-sm text-muted-foreground">
            {plural(ocultos, "alerta dispensado", "alertas dispensados")}.{" "}
            <button
              type="button"
              onClick={restaurar}
              className="rounded-sm font-medium text-primary underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              Restaurar
            </button>
          </p>
        </div>
      ) : visiveis.length === 0 ? (
        <div className="flex flex-1 items-center gap-3 px-4 pb-5 pt-3">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400">
            <TbCircleCheck size={16} aria-hidden="true" />
          </span>
          <p className="text-sm text-muted-foreground">{vazio}</p>
        </div>
      ) : (
        <ul className="flex flex-col gap-0.5 px-2 pb-2 pt-1">
          {visiveis.map(item => {
            const { icone: Icone, classe } = ESTILO[item.tipo]
            const resto = item.titulo.startsWith(item.nome) ? item.titulo.slice(item.nome.length) : ` ${item.titulo}`
            return (
              <li key={item.chave}>
                {/* Row = main action (the whole item) + a "dismiss" on the
                    right. Since a <button> cannot nest in a <button>, the two
                    are siblings inside a container that shares the hover. */}
                <div className="group/item flex items-stretch gap-0.5 rounded-md transition-colors hover:bg-accent/60">
                  <button
                    type="button"
                    onClick={() => onAcao(item.acao)}
                    aria-label={`${item.titulo}. ${item.detalhe}. ${item.rotuloDaAcao}`}
                    className={cn(
                      "grid min-w-0 flex-1 grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-2.5 rounded-md px-2 py-2 text-left",
                      "outline-none transition-colors focus-visible:bg-accent/60 focus-visible:ring-[3px] focus-visible:ring-ring/50",
                    )}
                  >
                    <span className={cn("mt-0.5 flex size-7 items-center justify-center rounded-md", classe)}>
                      <Icone size={14} aria-hidden="true" />
                    </span>
                    <span className="flex min-w-0 flex-col gap-0.5">
                      <span className="text-[13px] leading-snug">
                        <span className="font-semibold">{item.nome}</span>
                        <SeloAssistente origem={item.origem} className="mx-1 align-middle" />
                        {resto}
                      </span>
                      <span className="truncate text-xs text-muted-foreground" title={item.detalhe}>{item.detalhe}</span>
                    </span>
                    <span className="mt-0.5 inline-flex items-center gap-0.5 whitespace-nowrap text-xs font-medium text-primary">
                      {item.rotuloDaAcao}
                      <TbChevronRight size={13} aria-hidden="true" />
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => dispensar(item, itens)}
                    aria-label={`Dispensar o alerta de ${item.nome}`}
                    title="Dispensar"
                    className="flex shrink-0 items-center justify-center self-stretch rounded-md px-2 text-muted-foreground/50 outline-none transition-colors hover:bg-accent hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:w-10"
                  >
                    <TbX size={15} aria-hidden="true" />
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
