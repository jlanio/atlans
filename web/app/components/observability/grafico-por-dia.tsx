"use client"

import { memo, useMemo } from "react"
import dynamic from "next/dynamic"
import { Skeleton } from "@/app/components/ui/skeleton"
import type { IRunsByDay } from "@/service/types"
import { formatarDiaCurto, formatarInteiro } from "@/lib/formatos"
import type { Periodo } from "./historico-url"

/**
 * As quatro séries empilhadas, nas cores dos status — as mesmas do
 * `StatusBadge` (green/red/blue/amber-500 do Tailwind), iguais nos dois
 * temas, como no desenho aprovado. Valores, e não classes, porque `fill` de
 * SVG não aceita classe utilitária. Definidas AQUI (e não no módulo do
 * Recharts) para a legenda em texto não puxar a lib inteira para o
 * first-load.
 */
export const SERIES = [
  { chave: "success", rotulo: "Concluídas", cor: "#22c55e" },
  { chave: "failed", rotulo: "Falhas", cor: "#ef4444" },
  { chave: "running", rotulo: "Em andamento", cor: "#3b82f6" },
  { chave: "cancelled", rotulo: "Canceladas", cor: "#f59e0b" },
] as const

// Recharts pesa ~250 KB: entra só quando o card monta, como o RunsChart antigo.
const Barras = dynamic(() => import("./grafico-por-dia-barras"), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full rounded-md" />,
})

interface Props {
  dias: IRunsByDay[]
  periodo: Periodo
  carregando: boolean
  /** Aviso quando `/runs-by-day` falhou e o que está na tela é da carga anterior. */
  falha?: string
}

/** "de 8 ago a 6 set · pico de 70 em 2 set" — o que o eixo não diz de uma vez. */
export function subtituloDoGrafico(dias: IRunsByDay[]): string | null {
  if (dias.length === 0) return null
  const primeiro = dias[0]
  const ultimo = dias[dias.length - 1]
  const pico = dias.reduce((m, d) => (d.total > m.total ? d : m), primeiro)
  const faixa = dias.length === 1
    ? formatarDiaCurto(primeiro.day)
    : `de ${formatarDiaCurto(primeiro.day)} a ${formatarDiaCurto(ultimo.day)}`
  if (pico.total <= 0) return faixa
  return `${faixa} · pico de ${formatarInteiro(pico.total)} em ${formatarDiaCurto(pico.day)}`
}

/**
 * Execuções por dia (spec §4.3): barras empilhadas Concluídas / Falhas /
 * Em andamento / Canceladas na janela do cabeçalho. O seletor de período
 * saiu daqui de propósito — governava a página inteira e parecia local.
 */
export const GraficoPorDia = memo(function GraficoPorDia({ dias, periodo, carregando, falha }: Props) {
  const subtitulo = useMemo(() => subtituloDoGrafico(dias), [dias])
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
        {/* Legenda em texto ao lado do título, para o leitor não depender do
            SVG; a do Recharts fica escondida em telas estreitas. */}
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
      {/* Mais baixo no telefone: 160px basta para ler a forma da semana. */}
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
