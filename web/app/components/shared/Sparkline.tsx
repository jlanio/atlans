"use client"

import React, { useId, useMemo } from "react"

interface SparklineProps {
  data: number[]
  color?: string
  height?: number
}

/**
 * Hand-written SVG on purpose. Today the consumer is `observability/indicadores`
 * (reused by History and Dashboard); the original reason for it to exist was to keep
 * the indicators free of recharts, whose ~250 KB lib would enter those routes'
 * first-load for a mere 7-point chart. It's 7 points and a polyline: nothing here
 * justified a ResponsiveContainer with a ResizeObserver per card.
 *
 * No entrance animation, also by decision: the 10 s ACK poll re-rendered the page
 * and the 5 sparklines re-animated on their own, "blinking" without any data
 * having changed.
 */
function SparklineImpl({ data, color = "var(--chart-1)", height = 28 }: SparklineProps) {
  // `useId()` returns delimiters (`:`/`«»`) that break the fill attribute's
  // `url(#id)` — hence the sanitizing instead of the raw id.
  const gradientId = `spark-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`

  const geometry = useMemo(() => {
    if (data.length < 2) return null
    // The viewBox uses a fixed width of 100 and `preserveAspectRatio="none"`: the SVG
    // stretches to the card width without having to measure the DOM.
    const W = 100
    const TOP = 2 // headroom so the stroke isn't clipped at the peak
    const min = Math.min(...data)
    const max = Math.max(...data)
    const span = max - min
    const stepX = W / (data.length - 1)

    const points = data.map((v, i) => {
      const x = i * stepX
      // A constant series (including all zeros) becomes a line in the middle: without
      // this the division by zero would send the stroke outside the viewBox.
      const ratio = span === 0 ? 0.5 : (v - min) / span
      const y = TOP + (1 - ratio) * (height - TOP)
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })

    const line = `M${points.join("L")}`
    // The area closes at the bottom to receive the 0.3 → 0 gradient.
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
