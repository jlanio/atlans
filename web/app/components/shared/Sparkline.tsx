"use client"

import React, { useId, useMemo } from "react"

interface SparklineProps {
  data: number[]
  color?: string
  height?: number
}

/**
 * SVG escrito à mão de propósito. Hoje o consumidor é `observability/indicadores`
 * (reusado por Histórico e Dashboard); a razão original de existir era manter os
 * indicadores sem recharts, cuja lib de ~250 KB entraria no first-load dessas
 * rotas por um mero gráfico de 7 pontos. São 7 pontos e uma polilinha: nada aqui
 * justificava um ResponsiveContainer com ResizeObserver por card.
 *
 * Sem animação de entrada também por decisão: o poll de ACKs de 10 s
 * re-renderizava a página e os 5 sparklines reanimavam sozinhos, "piscando" sem
 * que nenhum dado tivesse mudado.
 */
function SparklineImpl({ data, color = "var(--chart-1)", height = 28 }: SparklineProps) {
  // `useId()` devolve delimitadores (`:`/`«»`) que quebram o `url(#id)` do
  // atributo fill — daí o saneamento em vez do id cru.
  const gradientId = `spark-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`

  const geometry = useMemo(() => {
    if (data.length < 2) return null
    // O viewBox usa largura fixa de 100 e `preserveAspectRatio="none"`: o SVG
    // estica para a largura do card sem precisar medir o DOM.
    const W = 100
    const TOP = 2 // respiro para o traço não ser cortado no pico
    const min = Math.min(...data)
    const max = Math.max(...data)
    const span = max - min
    const stepX = W / (data.length - 1)

    const points = data.map((v, i) => {
      const x = i * stepX
      // Série constante (inclusive toda zerada) vira uma reta no meio: sem isto
      // a divisão por zero levaria o traço para fora do viewBox.
      const ratio = span === 0 ? 0.5 : (v - min) / span
      const y = TOP + (1 - ratio) * (height - TOP)
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })

    const line = `M${points.join("L")}`
    // A área fecha no rodapé para receber o gradiente 0.3 → 0.
    const area = `${line}L${W},${height}L0,${height}Z`
    return { line, area }
  }, [data, height])

  if (!geometry) return null

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 100 ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
      style={{ display: "block", overflow: "visible" }}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.3} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={geometry.area} fill={`url(#${gradientId})`} stroke="none" />
      <path
        d={geometry.line}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        // `preserveAspectRatio="none"` distorceria a espessura junto com o eixo X.
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}

export const Sparkline = React.memo(SparklineImpl)
