// desktop/src/renderer/components/Alerta.tsx
//
// Warning/error strip — the pattern that was solved inside App.tsx, without
// `export`, and therefore rebuilt by hand in GeoSync and Ajustes. The three
// copies had already diverged into three paddings, two radii and two text
// sizes: the same kind of event appeared with different visual weight
// depending on the tab, and any improvement (the icon, the `role`) would have
// to be made three times.
//
// Two things that exist only here:
//
//   - ICON. Before, the only trait separating error from warning was the hue
//     of the border — at 40% alpha, on a dark background. Anyone who cannot
//     tell red from yellow read both as "a strip". Shape before color.
//   - `role`. The alert mounts asynchronously (the state arrives over IPC
//     while the person may be on any tab) and it is the only surface that
//     announces "the executor is not running". Without `role`/`aria-live`,
//     nothing is announced: the app just changes color in a corner that may
//     not be in view.
import type { ReactNode } from 'react'
import { TbAlertTriangle, TbCircleX } from 'react-icons/tb'

import { Card, CardContent } from './ui/card.js'
import { cn } from '../lib/utils.js'

const TONS = {
  erro: {
    caixa: 'border-destructive/40 bg-destructive/5',
    marca: 'text-destructive',
    Icone: TbCircleX,
  },
  aviso: {
    caixa: 'border-warning/40 bg-warning/5',
    marca: 'text-warning',
    Icone: TbAlertTriangle,
  },
} as const

export function Alerta({
  tom, titulo, remedio, bruto, denso, children,
}: {
  tom: 'erro' | 'aviso'
  titulo: ReactNode
  /** Actionable sentence: what to do. Precedes the raw message. */
  remedio?: ReactNode
  /** System message. Accompanies the remedy — it is what support needs to read. */
  bruto?: string | null
  /** Variant embedded in a section, without the weight of a whole card. */
  denso?: boolean
  children?: ReactNode
}) {
  const { caixa, marca, Icone } = TONS[tom]

  const conteudo = (
    <>
      <Icone
        size={denso ? 15 : 17}
        className={cn('mt-0.5 shrink-0', marca)}
        aria-hidden="true"
      />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className={cn('font-medium', denso ? 'text-xs' : 'text-sm')}>{titulo}</p>
        {(remedio || bruto) && (
          <p className={cn('text-muted-foreground select-text', denso ? 'text-xs' : 'text-sm')}>
            {remedio ?? bruto}
          </p>
        )}
        {remedio && bruto && (
          <p className="font-mono text-xs break-words text-muted-foreground select-text">{bruto}</p>
        )}
      </div>
      {children && <div className="flex shrink-0 gap-2">{children}</div>}
    </>
  )

  // `role`/`aria-live` apply in both forms: an error embedded in a section is
  // still an error nobody asked to see.
  const semantica = {
    role: tom === 'erro' ? ('alert' as const) : ('status' as const),
    'aria-live': tom === 'erro' ? ('assertive' as const) : ('polite' as const),
  }

  if (denso) {
    return (
      <div
        {...semantica}
        className={cn(
          'flex items-start gap-2 rounded-md border px-3 py-2 leading-relaxed',
          // Fades in: the strip appears because of an external event, and a block
          // that materializes with a hard cut pushes the content below without
          // anything indicating where it came from.
          'animate-in fade-in-0 slide-in-from-top-1 duration-200',
          caixa,
        )}
      >
        {conteudo}
      </div>
    )
  }

  return (
    <Card {...semantica} className={cn('py-3 animate-in fade-in-0 slide-in-from-top-2 duration-300', caixa)}>
      <CardContent className="flex flex-wrap items-start justify-between gap-3 px-4">
        {conteudo}
      </CardContent>
    </Card>
  )
}
