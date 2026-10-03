// desktop/src/renderer/components/MetricCard.tsx
//
// Card variant for KPIs, following .interface-design/system.md:
// header `flex-row items-center justify-between pb-2`, value `text-2xl font-bold`
// (the only accepted exception to "do not use font-bold").
//
// The icon goes in a faintly tinted square, on the right. It is not decoration:
// four cards with the same typography and no visual mark force you to READ each
// title to find what you are looking for, and the Painel is precisely the screen
// people check at a glance.
// PATTERN NOTE — `CardHeader` is a GRID, not flex.
//
// The primitive (ported from the web) declares `grid auto-rows-min grid-rows-[auto_auto]`.
// A `flex-row` added via className does nothing there: `flex-direction` does
// not apply to a grid container, and `justify-between` ends up aligning within
// the cell, not between siblings. The effect was silent yet visible — each
// child dropped onto a ROW of its own, stretched across the full width.
//
// The right way is the one the primitive itself offers: whatever goes on the
// right goes into `CardAction` (the header has `has-data-[slot=card-action]:grid-cols-[1fr_auto]`),
// and whatever accompanies the title on the left goes INSIDE `CardTitle`.
import type { ComponentType } from 'react'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from './ui/card.js'
import { cn } from '../lib/utils.js'

/** Value color. Only where the number carries a judgment — the rest stays neutral. */
const TONS = {
  atencao: 'text-warning',
  erro: 'text-destructive',
  ativo: 'text-primary',
} as const

export function MetricCard({
  titulo, valor, rodape, icone: Icone, tom,
}: {
  titulo: string
  valor: string
  rodape?: string
  /**
   * The icon COMPONENT, not a ready-made element — the size is decided here,
   * and a `size` baked into the call would take that freedom away from the card.
   */
  icone?: ComponentType<{ size?: number; className?: string }>
  tom?: keyof typeof TONS
}) {
  return (
    <Card className="gap-0 py-4 transition-colors hover:border-primary/30">
      {/* See the PATTERN NOTE at the top: the icon goes in `CardAction`, which
          is the slot the header reserves on the right. With `flex-row` it
          dropped onto a row of its own, BELOW the title and left-aligned —
          the opposite of what this file's comment describes. */}
      <CardHeader className="items-center gap-2 px-4 pb-2">
        <CardTitle className="truncate text-xs font-medium text-muted-foreground">
          {titulo}
        </CardTitle>
        {Icone && (
          <CardAction className={cn(
            'flex size-7 shrink-0 items-center justify-center rounded-md transition-colors',
            tom ? 'bg-current/10' : 'bg-muted',
            tom ? TONS[tom] : 'text-muted-foreground',
          )}>
            <Icone size={15} />
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="px-4">
        {/* `tabular-nums` keeps the value from "dancing" on every 1s tick when
            the digits change width. */}
        <div className={cn('text-2xl font-bold tabular-nums', tom && TONS[tom])}>{valor}</div>
        {rodape && <p className="mt-0.5 truncate text-xs text-muted-foreground">{rodape}</p>}
      </CardContent>
    </Card>
  )
}
