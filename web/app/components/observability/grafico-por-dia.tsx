"use client"

import { memo, useMemo } from "react"
import dynamic from "next/dynamic"
import { Skeleton } from "@/app/components/ui/skeleton"
import type { IRunsByDay } from "@/service/types"
import { formatShortDay, formatInteger } from "@/lib/formatos"
import type { Period } from "./historico-url"

/**
 * The four stacked series, in the status colors — the same as
 * `StatusBadge` (Tailwind's green/red/blue/amber-500), identical in both
 * themes, as in the approved design. Values, not classes, because SVG `fill`
 * does not accept a utility class. Defined HERE (and not in the Recharts
 * module) so the text legend does not pull the whole lib into the
 * first load.
 */
export const SERIES = [
  { chave: "success", rotulo: "Concluídas", cor: "#22c55e" },
  { chave: "failed", rotulo: "Falhas", cor: "#ef4444" },
  { chave: "running", rotulo: "Em andamento", cor: "#3b82f6" },
  { chave: "cancelled", rotulo: "Canceladas", cor: "#f59e0b" },
] as const

// Recharts weighs ~250 KB: it comes in only when the card mounts, like the old RunsChart.
const Barras = dynamic(() => import("./grafico-por-dia-barras"), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full rounded-md" />,
})

interface Props {
  dias: IRunsByDay[]
  periodo: Period
  carregando: boolean
  /** Notice when `/runs-by-day` failed and what is on screen is from the previous load. */
  falha?: string
}

/** "de 8 ago a 6 set · pico de 70 em 2 set" — what the axis does not say at once. */
export function chartSubtitle(dias: IRunsByDay[]): string | null {
  if (dias.length === 0) return null
  const primeiro = dias[0]
  const ultimo = dias[dias.length - 1]
  const pico = dias.reduce((m, d) => (d.total > m.total ? d : m), primeiro)
  const faixa = dias.length === 1
    ? formatShortDay(primeiro.day)
    : `de ${formatShortDay(primeiro.day)} a ${formatShortDay(ultimo.day)}`
  if (pico.total <= 0) return faixa
  return `${faixa} · pico de ${formatInteger(pico.total)} em ${formatShortDay(pico.day)}`
}

/**
 * Runs per day (spec §4.3): stacked bars Completed / Failed / In progress /
 * Canceled in the header's window. The period selector left here on
 * purpose — it governed the whole page and looked local.
 */
export const GraficoPorDia = memo(function GraficoPorDia({ dias, periodo, carregando, falha }: Props) {
  const subtitulo = useMemo(() => chartSubtitle(dias), [dias])
  const vazio = dias.length === 0 || dias.every(d => d.total === 0)

  return (
    <section
      aria-labelledby="grafico-por-dia-titulo"
      aria-busy={carregando && dias.length === 0}
      className="flex min-w-0 flex-col rounded-lg border bg-card shadow-xs"
    >
      <div className="flex flex-wrap items-start justify-between gap-2 px-4 pt-4 pb-1">
        <div className="min-w-0">
          <h2 id="grafico-por-dia-titulo" className="text-sm font-semibold">Execuções por dia</h2>
          <p className="text-xs text-muted-foreground">
            {subtitulo ?? `últimos ${periodo} dias`}
          </p>
        </div>
        {/* Text legend next to the title, so the reader does not depend on the
            SVG; the Recharts one stays hidden on narrow screens. */}
        <ul className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground" aria-label="Legenda">
          {SERIES.map(s => (
            <li key={s.chave} className="inline-flex items-center gap-1.5">
              <span aria-hidden="true" className="inline-block size-2 rounded-xs" style={{ backgroundColor: s.cor }} />
              {s.rotulo}
            </li>
          ))}
        </ul>
      </div>
      {falha && (
        <p role="alert" className="mx-4 mb-1 rounded-md bg-destructive/10 px-3 py-1.5 text-xs text-destructive">
          {falha}{dias.length > 0 && " Mostrando a última leitura."}
        </p>
      )}
      {/* Shorter on the phone: 160px is enough to read the shape of the week. */}
      <div className="h-40 px-2 pb-3 sm:h-[220px]">
        {dias.length === 0 ? (
          carregando
            ? <Skeleton className="h-full w-full rounded-md" />
            : <p className="flex h-full items-center justify-center text-sm text-muted-foreground">Sem execuções no período.</p>
        ) : vazio ? (
          <p className="flex h-full items-center justify-center text-sm text-muted-foreground">Sem execuções no período.</p>
        ) : (
          <Barras dias={dias} />
        )}
      </div>
    </section>
  )
})
