// desktop/src/renderer/components/ui/skeleton.tsx
//
// Ported from web/app/components/ui/skeleton.tsx, with the `skeleton-shimmer`
// keyframe copied into index.css along with it.
//
// The app opens and sits at "Carregando…" (loading) — a centered sentence —
// while three IPC calls resolve. A sentence does not say where the content will
// appear or how much of it is coming; the skeleton says both, and it is what the
// web uses.
import * as React from 'react'

import { cn } from '../../lib/utils.js'

function Skeleton({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="skeleton"
      className={cn(
        'rounded-md bg-accent/60',
        'bg-[linear-gradient(90deg,transparent_0%,rgba(255,255,255,0.15)_50%,transparent_100%)]',
        'bg-[length:200%_100%] animate-skeleton-shimmer',
        className,
      )}
      {...props}
    />
  )
}

export { Skeleton }
