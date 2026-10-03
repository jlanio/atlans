"use client"

import { TbRefresh } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { cn } from "@/lib/utils"
import { PERIODS, type Period } from "./historico-url"

interface Props {
  periodo: Period
  onPeriodo: (p: Period) => void
  carregando: boolean
  onAtualizar: () => void
  /** Size of the previous window the indicators are compared with. */
  comparandoCom: number
}

/**
 * History header (spec §4.3): the period lives here, once, and the subtitle
 * says what the indicators are compared with — on the old screen the selector
 * lived inside the chart and governed eight cards without saying so.
 */
export function CabecalhoDoHistorico({
  periodo, onPeriodo, carregando, onAtualizar, comparandoCom,
}: Props) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold text-foreground">Histórico</h1>
        <p className="text-sm font-medium text-muted-foreground">
          Execuções dos seus workflows · comparado com os {comparandoCom} dias anteriores
        </p>
      </div>
      <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
        {/* Refresh on the left, as in /projetos: the reload action comes
            first; the period selector is a filter, it comes after. */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onAtualizar}
          disabled={carregando}
          aria-label="Atualizar os dados do Histórico"
          className="gap-1.5 max-md:h-10"
        >
          <TbRefresh size={14} className={carregando ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
          Atualizar
        </Button>
        <div
          role="group"
          aria-label="Período"
          className="inline-flex h-8 w-full overflow-hidden rounded-md border bg-card max-md:h-10 sm:w-auto"
        >
          {PERIODS.map(p => {
            const ativo = p === periodo
            return (
              <button
                key={p}
                type="button"
                aria-pressed={ativo}
                aria-label={`Últimos ${p} dias`}
                onClick={() => onPeriodo(p)}
                className={cn(
                  "flex-1 px-3 text-xs font-medium transition-colors outline-none sm:flex-none",
                  "border-l first:border-l-0 focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:z-10",
                  ativo ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )}
              >
                {p} dias
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/** Coarse grain on purpose: a seconds clock next to the button only distracts. */
export function textoDeFrescor(carimbo: number, agora: number): string {
  const s = Math.max(0, Math.round((agora - carimbo) / 1000))
  if (s < 10) return "atualizado agora"
  if (s < 60) return `atualizado há ${Math.floor(s / 10) * 10} s`
  const m = Math.floor(s / 60)
  if (m < 60) return `atualizado há ${m} min`
  const h = Math.floor(m / 60)
  return `atualizado há ${h} h`
}
