"use client"

import { memo, useMemo, type ReactNode } from "react"
import type { IconType } from "react-icons"
import { TbActivity, TbAlertTriangle, TbCheck, TbClock, TbMinus, TbTrendingDown, TbTrendingUp } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import { Sparkline } from "@/app/components/shared/Sparkline"
import { cn } from "@/lib/utils"
import type { IObservabilityMetrics, IRunsByDay } from "@/service/types"
import { formatarDuracao, formatInteger, formatPercent, formatPoints, variation } from "@/lib/formatos"
import type { Period } from "./historico-url"

interface Props {
  metrics: IObservabilityMetrics | null
  dias: IRunsByDay[]
  carregando: boolean
  periodo: Period
}

/**
 * The period's four indicators (spec §4.3), each compared to the previous
 * period of the same size. No count-up animation or staggered entrance:
 * the old page re-animated the eight cards on every tab switch, and the number
 * that matters is the final one, not the count up to it.
 */
export function Indicadores({ metrics, dias, carregando, periodo }: Props) {
  const totalSeries = useMemo(() => dias.map(d => d.total), [dias])
  const failuresSeries = useMemo(() => dias.map(d => d.failed), [dias])
  // Rate per day = completed ÷ (completed + failed); days with neither of the
  // two have no rate and are left out instead of becoming 0 or 100%.
  const rateSeries = useMemo(
    () => dias.filter(d => d.success + d.failed > 0).map(d => d.success / (d.success + d.failed)),
    [dias],
  )

  // A previous period WITH NO runs is no basis for comparison: "+81" and
  // "+80,5 pt" over zero are just the number itself with a misleading arrow.
  // The trend is hidden and the description says why.
  const rawPrev = metrics?.prev_period ?? null
  const prev = rawPrev && rawPrev.total_runs > 0 ? rawPrev : null
  const noPrevious = !!rawPrev && rawPrev.total_runs === 0
  const dur = metrics?.duration ?? null

  // ── Runs ──
  const total = metrics?.total_runs ?? null
  // Memoized on the numeric values: the poll replaces `metrics` every 30 s and,
  // without this, the trend object changed identity and reconciled the Indicador.
  const tendTotal: Trend | null = useMemo(() => {
    const vTotal = variation(total, prev?.total_runs)
    return vTotal ? {
      direcao: vTotal.direcao,
      bom: vTotal.direcao === "sobe" ? "bom" : vTotal.direcao === "desce" ? "ruim" : "neutro",
      texto: vTotal.pct != null ? `${Math.abs(vTotal.pct).toFixed(0)}%` : withSign(vTotal.delta),
    } : null
  }, [total, prev?.total_runs])
  const descTotal = prev
    ? `${formatInteger(prev.total_runs)} no período anterior`
    : noPrevious ? "nenhuma no período anterior" : `nos últimos ${periodo} dias`

  // ── Success rate ──
  // With no run in the period, `success_rate` is 0/0 — the backend returns 0.0,
  // which would become a misleading "0%". `—` (null) is right, as in the sibling
  // per-row views (visao-workflows/visao-executores use the same `total_runs > 0`).
  const taxa = metrics && metrics.total_runs > 0 ? metrics.success_rate : null
  const rateDelta = taxa != null && prev ? taxa - prev.success_rate : null
  // Memoized on the numeric delta so the object is not recreated on every poll.
  const rateTrend: Trend | null = useMemo(() => rateDelta != null ? {
    direcao: Math.abs(rateDelta * 100) < 0.05 ? "igual" : rateDelta > 0 ? "sobe" : "desce",
    bom: Math.abs(rateDelta * 100) < 0.05 ? "neutro" : rateDelta > 0 ? "bom" : "ruim",
    texto: formatPoints(rateDelta),
  } : null, [rateDelta])
  const rateDesc = prev
    ? `${formatPercent(prev.success_rate)} no período anterior`
    : noPrevious ? "sem período anterior para comparar" : "concluídas ÷ (concluídas + falhas)"

  // ── Typical duration ──
  const p50 = dur?.p50_seconds ?? null
  const p95 = dur?.p95_seconds ?? null
  const durationDesc = prev?.p50_seconds != null
    ? `mediana; era ${formatarDuracao(prev.p50_seconds)} no período anterior`
    : "mediana das concluídas"

  // ── Falhas ──
  const falhas = metrics?.failed_runs ?? null
  const failuresDelta = falhas != null && prev ? falhas - prev.failed_runs : null
  // Fewer failures is green: the arrow follows what is good, not the sign. Memoized
  // on the delta so the object is not recreated on every poll.
  const failuresTrend: Trend | null = useMemo(() => failuresDelta != null ? {
    direcao: failuresDelta === 0 ? "igual" : failuresDelta > 0 ? "sobe" : "desce",
    bom: failuresDelta === 0 ? "neutro" : failuresDelta > 0 ? "ruim" : "bom",
    texto: withSign(failuresDelta),
  } : null, [failuresDelta])
  const pior = metrics?.top_failing_workflows?.[0]
  // ReactNode memoized on the primitive values: recreating the <>…</> on every
  // poll gave a new element and reconciled the Failures Indicador for nothing.
  // Deps on primitives on purpose (not the `pior`/`prev` object, which changes
  // identity on every poll): this way the memo holds between polls with equal data.
  const failuresDesc: ReactNode = useMemo(() => pior && pior.failure_count > 0
    ? <>{formatInteger(pior.failure_count)} delas em <span className="font-medium text-foreground">«{pior.workflow_name ?? pior.workflow_hash.slice(0, 8)}»</span></>
    : falhas === 0 ? "nenhuma no período"
    : prev ? `${formatInteger(prev.failed_runs)} no período anterior`
    : noPrevious ? "sem período anterior para comparar" : `nos últimos ${periodo} dias`,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pior?.failure_count, pior?.workflow_name, pior?.workflow_hash, falhas, prev?.failed_runs, noPrevious, periodo])
  const failuresDescText = pior && pior.failure_count > 0
    ? `${formatInteger(pior.failure_count)} delas em «${pior.workflow_name ?? pior.workflow_hash.slice(0, 8)}»`
    : typeof failuresDesc === "string" ? failuresDesc : ""

  // After ALL the hooks above (rules of hooks): the 1st load without metrics
  // shows the skeleton.
  if (!metrics && carregando) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-busy="true" aria-label="Indicadores carregando">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className="flex flex-col gap-2.5 rounded-lg border bg-card p-4 shadow-xs">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-7 w-20" />
            <Skeleton className="h-3 w-32" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-busy={carregando}>
      <Indicador
        titulo="Execuções"
        icone={TbActivity}
        valor={formatInteger(total)}
        tendencia={tendTotal}
        descricao={descTotal}
        serie={totalSeries}
        corDaSerie="text-primary"
        rotulo={`Execuções: ${formatInteger(total)}${tendTotal ? `, ${trendText(tendTotal)} que o período anterior` : ""}; ${descTotal}`}
      />
      <Indicador
        titulo="Taxa de sucesso"
        icone={TbCheck}
        valor={formatPercent(taxa)}
        tendencia={rateTrend}
        descricao={rateDesc}
        serie={rateSeries}
        corDaSerie="text-green-600 dark:text-green-400"
        rotulo={`Taxa de sucesso: ${formatPercent(taxa)}${rateTrend ? `, ${rateTrend.texto} em relação ao período anterior` : ""}; ${rateDesc}`}
      />
      <Indicador
        titulo="Duração típica"
        icone={TbClock}
        valor={formatarDuracao(p50)}
        complemento={p95 != null && p50 != null ? `5% mais lentas acima de ${formatarDuracao(p95)}` : undefined}
        descricao={durationDesc}
        rotulo={`Duração típica: ${formatarDuracao(p50)}${p95 != null ? `, 5% mais lentas acima de ${formatarDuracao(p95)}` : ""}; ${durationDesc}`}
      />
      <Indicador
        titulo="Falhas"
        icone={TbAlertTriangle}
        valor={formatInteger(falhas)}
        corDoValor={falhas != null && falhas > 0 ? "text-red-700 dark:text-red-400" : undefined}
        tendencia={failuresTrend}
        descricao={failuresDesc}
        serie={failuresSeries}
        corDaSerie="text-red-600 dark:text-red-400"
        rotulo={`Falhas: ${formatInteger(falhas)}${failuresTrend ? `, ${failuresTrend.texto} em relação ao período anterior` : ""}; ${failuresDescText}`}
      />
    </div>
  )
}

type Trend = { direcao: "sobe" | "desce" | "igual"; bom: "bom" | "ruim" | "neutro"; texto: string }

function withSign(n: number): string {
  if (n === 0) return "0"
  return `${n > 0 ? "+" : "−"}${formatInteger(Math.abs(n))}`
}

function trendText(t: Trend): string {
  if (t.direcao === "igual") return "igual ao"
  return `${t.texto} ${t.direcao === "sobe" ? "a mais" : "a menos"}`
}

const TREND_CLASS: Record<Trend["bom"], string> = {
  bom: "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400",
  ruim: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400",
  neutro: "bg-muted text-muted-foreground",
}

function TrendBadge({ t }: { t: Trend }) {
  const Icone = t.direcao === "sobe" ? TbTrendingUp : t.direcao === "desce" ? TbTrendingDown : TbMinus
  return (
    <span
      aria-hidden="true"
      className={cn("inline-flex items-center gap-0.5 rounded-full px-1.5 py-px text-[11px] font-semibold tabular-nums", TREND_CLASS[t.bom])}
    >
      <Icone size={11} />
      {t.direcao === "igual" ? "igual" : t.texto}
    </span>
  )
}

/**
 * Memoized: the Now strip's poll replaces `metrics` every 30 s and the four
 * cards should only reconcile when their number really changes. The series
 * arrive memoized from the parent for that reason.
 */
const Indicador = memo(function Indicador({
  titulo, icone: Icone, valor, complemento, corDoValor, tendencia, descricao, serie, corDaSerie, rotulo,
}: {
  titulo: string
  icone: IconType
  valor: string
  complemento?: string
  corDoValor?: string
  tendencia?: Trend | null
  descricao: ReactNode
  serie?: number[]
  /** Text class: the sparkline paints with `currentColor`, so the color comes from the theme. */
  corDaSerie?: string
  rotulo: string
}) {
  const hasSeries = !!serie && serie.length > 1
  return (
    <div
      role="group"
      aria-label={rotulo}
      className="relative flex min-w-0 flex-col gap-1.5 overflow-hidden rounded-lg border bg-card p-3 shadow-xs sm:p-4"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{titulo}</span>
        <Icone size={15} className="shrink-0 text-muted-foreground" aria-hidden="true" />
      </div>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className={cn("text-2xl font-semibold leading-none tabular-nums tracking-tight", corDoValor)}>{valor}</span>
        {tendencia && <TrendBadge t={tendencia} />}
        {complemento && <span className="text-xs font-medium text-muted-foreground">{complemento}</span>}
      </div>
      {/* Space on the right so the sparkline does not run over the text. */}
      <p className={cn("min-w-0 text-xs text-muted-foreground", hasSeries && "sm:pr-24")}>{descricao}</p>
      {hasSeries && (
        <div className={cn("pointer-events-none absolute right-3 bottom-3 hidden w-[84px] sm:block", corDaSerie)}>
          <Sparkline data={serie} color="currentColor" height={26} />
        </div>
      )}
    </div>
  )
})
