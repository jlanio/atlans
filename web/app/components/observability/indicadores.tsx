"use client"

import { memo, useMemo, type ReactNode } from "react"
import type { IconType } from "react-icons"
import { TbActivity, TbAlertTriangle, TbCheck, TbClock, TbMinus, TbTrendingDown, TbTrendingUp } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import { Sparkline } from "@/app/components/shared/Sparkline"
import { cn } from "@/lib/utils"
import type { IObservabilityMetrics, IRunsByDay } from "@/service/types"
import { formatarDuracao, formatarInteiro, formatarPercentual, formatarPontos, variacao } from "@/lib/formatos"
import type { Periodo } from "./historico-url"

interface Props {
  metrics: IObservabilityMetrics | null
  dias: IRunsByDay[]
  carregando: boolean
  periodo: Periodo
}

/**
 * Os quatro indicadores do período (spec §4.3), cada um comparado ao período
 * anterior de mesmo tamanho. Sem animação de contagem nem entrada escalonada:
 * a página antiga reanimava os oito cards a cada troca de aba, e o número que
 * importa é o final, não a contagem até ele.
 */
export function Indicadores({ metrics, dias, carregando, periodo }: Props) {
  const serieTotal = useMemo(() => dias.map(d => d.total), [dias])
  const serieFalhas = useMemo(() => dias.map(d => d.failed), [dias])
  // Taxa por dia = concluídas ÷ (concluídas + falhas); dias sem nenhuma das
  // duas não têm taxa e ficam de fora em vez de virarem 0 ou 100%.
  const serieTaxa = useMemo(
    () => dias.filter(d => d.success + d.failed > 0).map(d => d.success / (d.success + d.failed)),
    [dias],
  )

  // Um período anterior SEM execuções não é base de comparação: "+81" e
  // "+80,5 pt" sobre zero são só o próprio número com uma seta enganosa. A
  // tendência some e a descrição diz por quê.
  const prevBruto = metrics?.prev_period ?? null
  const prev = prevBruto && prevBruto.total_runs > 0 ? prevBruto : null
  const semAnterior = !!prevBruto && prevBruto.total_runs === 0
  const dur = metrics?.duration ?? null

  // ── Execuções ──
  const total = metrics?.total_runs ?? null
  // Memoizado nos valores numéricos: o poll troca `metrics` a cada 30 s e, sem
  // isto, o objeto da tendência mudava de identidade e reconciliava o Indicador.
  const tendTotal: Tendencia | null = useMemo(() => {
    const vTotal = variacao(total, prev?.total_runs)
    return vTotal ? {
      direcao: vTotal.direcao,
      bom: vTotal.direcao === "sobe" ? "bom" : vTotal.direcao === "desce" ? "ruim" : "neutro",
      texto: vTotal.pct != null ? `${Math.abs(vTotal.pct).toFixed(0)}%` : comSinal(vTotal.delta),
    } : null
  }, [total, prev?.total_runs])
  const descTotal = prev
    ? `${formatarInteiro(prev.total_runs)} no período anterior`
    : semAnterior ? "nenhuma no período anterior" : `nos últimos ${periodo} dias`

  // ── Taxa de sucesso ──
  // Sem execução no período, `success_rate` é 0/0 — o backend devolve 0.0, que
  // viraria um "0%" enganoso. `—` (null) é o certo, como nas visões irmãs por
  // linha (visao-workflows/visao-executores usam o mesmo `total_runs > 0`).
  const taxa = metrics && metrics.total_runs > 0 ? metrics.success_rate : null
  const deltaTaxa = taxa != null && prev ? taxa - prev.success_rate : null
  // Memoizado no delta numérico para não recriar o objeto a cada poll.
  const tendTaxa: Tendencia | null = useMemo(() => deltaTaxa != null ? {
    direcao: Math.abs(deltaTaxa * 100) < 0.05 ? "igual" : deltaTaxa > 0 ? "sobe" : "desce",
    bom: Math.abs(deltaTaxa * 100) < 0.05 ? "neutro" : deltaTaxa > 0 ? "bom" : "ruim",
    texto: formatarPontos(deltaTaxa),
  } : null, [deltaTaxa])
  const descTaxa = prev
    ? `${formatarPercentual(prev.success_rate)} no período anterior`
    : semAnterior ? "sem período anterior para comparar" : "concluídas ÷ (concluídas + falhas)"

  // ── Duração típica ──
  const p50 = dur?.p50_seconds ?? null
  const p95 = dur?.p95_seconds ?? null
  const descDuracao = prev?.p50_seconds != null
    ? `mediana; era ${formatarDuracao(prev.p50_seconds)} no período anterior`
    : "mediana das concluídas"

  // ── Falhas ──
  const falhas = metrics?.failed_runs ?? null
  const deltaFalhas = falhas != null && prev ? falhas - prev.failed_runs : null
  // Menos falhas é verde: a seta segue o que é bom, não o sinal. Memoizado no
  // delta para não recriar o objeto a cada poll.
  const tendFalhas: Tendencia | null = useMemo(() => deltaFalhas != null ? {
    direcao: deltaFalhas === 0 ? "igual" : deltaFalhas > 0 ? "sobe" : "desce",
    bom: deltaFalhas === 0 ? "neutro" : deltaFalhas > 0 ? "ruim" : "bom",
    texto: comSinal(deltaFalhas),
  } : null, [deltaFalhas])
  const pior = metrics?.top_failing_workflows?.[0]
  // ReactNode memoizado nos valores primitivos: recriar o <>…</> a cada poll
  // dava um elemento novo e reconciliava o Indicador das Falhas à toa.
  // Deps por primitivos de propósito (não o objeto `pior`/`prev`, que troca de
  // identidade a cada poll): assim o memo segura entre polls com dados iguais.
  const descFalhas: ReactNode = useMemo(() => pior && pior.failure_count > 0
    ? <>{formatarInteiro(pior.failure_count)} delas em <span className="font-medium text-foreground">«{pior.workflow_name ?? pior.workflow_hash.slice(0, 8)}»</span></>
    : falhas === 0 ? "nenhuma no período"
    : prev ? `${formatarInteiro(prev.failed_runs)} no período anterior`
    : semAnterior ? "sem período anterior para comparar" : `nos últimos ${periodo} dias`,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pior?.failure_count, pior?.workflow_name, pior?.workflow_hash, falhas, prev?.failed_runs, semAnterior, periodo])
  const descFalhasTexto = pior && pior.failure_count > 0
    ? `${formatarInteiro(pior.failure_count)} delas em «${pior.workflow_name ?? pior.workflow_hash.slice(0, 8)}»`
    : typeof descFalhas === "string" ? descFalhas : ""

  // Depois de TODOS os hooks acima (regras dos hooks): a 1ª carga sem métricas
  // mostra o esqueleto.
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
        valor={formatarInteiro(total)}
        tendencia={tendTotal}
        descricao={descTotal}
        serie={serieTotal}
        corDaSerie="text-primary"
        rotulo={`Execuções: ${formatarInteiro(total)}${tendTotal ? `, ${textoDaTendencia(tendTotal)} que o período anterior` : ""}; ${descTotal}`}
      />
      <Indicador
        titulo="Taxa de sucesso"
        icone={TbCheck}
        valor={formatarPercentual(taxa)}
        tendencia={tendTaxa}
        descricao={descTaxa}
        serie={serieTaxa}
        corDaSerie="text-green-600 dark:text-green-400"
        rotulo={`Taxa de sucesso: ${formatarPercentual(taxa)}${tendTaxa ? `, ${tendTaxa.texto} em relação ao período anterior` : ""}; ${descTaxa}`}
      />
      <Indicador
        titulo="Duração típica"
        icone={TbClock}
        valor={formatarDuracao(p50)}
        complemento={p95 != null && p50 != null ? `5% mais lentas acima de ${formatarDuracao(p95)}` : undefined}
        descricao={descDuracao}
        rotulo={`Duração típica: ${formatarDuracao(p50)}${p95 != null ? `, 5% mais lentas acima de ${formatarDuracao(p95)}` : ""}; ${descDuracao}`}
      />
      <Indicador
        titulo="Falhas"
        icone={TbAlertTriangle}
        valor={formatarInteiro(falhas)}
        corDoValor={falhas != null && falhas > 0 ? "text-red-700 dark:text-red-400" : undefined}
        tendencia={tendFalhas}
        descricao={descFalhas}
        serie={serieFalhas}
        corDaSerie="text-red-600 dark:text-red-400"
        rotulo={`Falhas: ${formatarInteiro(falhas)}${tendFalhas ? `, ${tendFalhas.texto} em relação ao período anterior` : ""}; ${descFalhasTexto}`}
      />
    </div>
  )
}

type Tendencia = { direcao: "sobe" | "desce" | "igual"; bom: "bom" | "ruim" | "neutro"; texto: string }

function comSinal(n: number): string {
  if (n === 0) return "0"
  return `${n > 0 ? "+" : "−"}${formatarInteiro(Math.abs(n))}`
}

function textoDaTendencia(t: Tendencia): string {
  if (t.direcao === "igual") return "igual ao"
  return `${t.texto} ${t.direcao === "sobe" ? "a mais" : "a menos"}`
}

const CLASSE_DA_TENDENCIA: Record<Tendencia["bom"], string> = {
  bom: "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400",
  ruim: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400",
  neutro: "bg-muted text-muted-foreground",
}

function SeloDeTendencia({ t }: { t: Tendencia }) {
  const Icone = t.direcao === "sobe" ? TbTrendingUp : t.direcao === "desce" ? TbTrendingDown : TbMinus
  return (
    <span
      aria-hidden="true"
      className={cn("inline-flex items-center gap-0.5 rounded-full px-1.5 py-px text-[11px] font-semibold tabular-nums", CLASSE_DA_TENDENCIA[t.bom])}
    >
      <Icone size={11} />
      {t.direcao === "igual" ? "igual" : t.texto}
    </span>
  )
}

/**
 * Memoizado: o poll da faixa Agora troca `metrics` a cada 30 s e os quatro
 * cards só devem reconciliar quando o número deles muda de verdade. As séries
 * chegam memoizadas do pai por isso.
 */
const Indicador = memo(function Indicador({
  titulo, icone: Icone, valor, complemento, corDoValor, tendencia, descricao, serie, corDaSerie, rotulo,
}: {
  titulo: string
  icone: IconType
  valor: string
  complemento?: string
  corDoValor?: string
  tendencia?: Tendencia | null
  descricao: ReactNode
  serie?: number[]
  /** Classe de texto: o sparkline pinta com `currentColor`, então a cor vem do tema. */
  corDaSerie?: string
  rotulo: string
}) {
  const temSerie = !!serie && serie.length > 1
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
        {tendencia && <SeloDeTendencia t={tendencia} />}
        {complemento && <span className="text-xs font-medium text-muted-foreground">{complemento}</span>}
      </div>
      {/* Espaço à direita para o sparkline não passar por cima do texto. */}
      <p className={cn("min-w-0 text-xs text-muted-foreground", temSerie && "sm:pr-24")}>{descricao}</p>
      {temSerie && (
        <div className={cn("pointer-events-none absolute right-3 bottom-3 hidden w-[84px] sm:block", corDaSerie)}>
          <Sparkline data={serie} color="currentColor" height={26} />
        </div>
      )}
    </div>
  )
})
