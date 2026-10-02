"use client"

import React from "react"
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts"
import type { IRunsByDay } from "@/service/types"
import { formatarDiaCurto, formatarInteiro, plural } from "@/lib/formatos"
import { SERIES } from "./grafico-por-dia"

/**
 * O corpo Recharts do gráfico por dia. Vive num módulo próprio para entrar
 * pelo `dynamic()` de `grafico-por-dia.tsx`: importado estaticamente, os
 * ~250 KB da lib iriam para o first-load da rota.
 */

type ChaveDaSerie = typeof SERIES[number]["chave"]
const ROTULO: Record<string, string> = Object.fromEntries(SERIES.map(s => [s.chave, s.rotulo]))

type Ponto = { day: string; total: number } & Record<ChaveDaSerie, number>

/** Quantos rótulos pular no eixo X para caber ~7 por gráfico. */
export function intervaloDosTicks(n: number): number {
  return Math.max(0, Math.ceil(n / 7) - 1)
}

function DicaDoDia({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ dataKey?: string | number; value?: number | string; fill?: string; payload?: Ponto }>
  label?: string | number
}) {
  if (!active || !payload?.length) return null
  const total = payload[0]?.payload?.total ?? payload.reduce((s, p) => s + Number(p.value ?? 0), 0)
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <p className="mb-1 font-semibold">{formatarDiaCurto(String(label ?? ""))} · {plural(total, "execução", "execuções")}</p>
      {payload.filter(p => Number(p.value ?? 0) > 0).map(p => (
        <div key={String(p.dataKey)} className="flex items-center gap-2">
          <span aria-hidden="true" className="size-2 rounded-full" style={{ backgroundColor: p.fill }} />
          <span className="text-muted-foreground">{ROTULO[String(p.dataKey)] ?? String(p.dataKey)}</span>
          <span className="ml-auto font-medium tabular-nums">{formatarInteiro(Number(p.value))}</span>
        </div>
      ))}
    </div>
  )
}

function GraficoPorDiaBarrasImpl({ dias }: { dias: IRunsByDay[] }) {
  const pontos: Ponto[] = dias.map(d => ({
    day: d.day,
    total: d.total,
    success: d.success,
    failed: d.failed,
    running: d.running,
    cancelled: d.cancelled ?? 0,
  }))
  // `initialDimension`: na primeira pintura o contêiner ainda não foi medido
  // e o Recharts avisava "width(-1) and height(-1)" no console.
  return (
    <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 640, height: 220 }}>
      <BarChart data={pontos} margin={{ top: 4, right: 4, left: -16, bottom: 0 }} barCategoryGap="25%">
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
        <XAxis
          dataKey="day"
          tickFormatter={formatarDiaCurto}
          interval={intervaloDosTicks(pontos.length)}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<DicaDoDia />} cursor={{ fill: "var(--accent)", opacity: 0.5 }} />
        {/* A legenda é a do cabeçalho do card (texto, em `grafico-por-dia.tsx`);
            duplicá-la aqui só roubava altura do gráfico no telefone. */}
        {/* Sem animação: trocar de período redesenha com os dados novos, sem
            as barras "crescerem" de novo — e o poll da faixa Agora não passa
            por aqui, então nada reanima sozinho. */}
        {SERIES.map(s => (
          <Bar key={s.chave} dataKey={s.chave} stackId="dia" fill={s.cor} isAnimationActive={false} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

export const GraficoPorDiaBarras = React.memo(GraficoPorDiaBarrasImpl)
export default GraficoPorDiaBarras
