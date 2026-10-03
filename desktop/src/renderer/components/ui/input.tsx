// desktop/src/renderer/components/ui/input.tsx
//
// Ported from web/app/components/ui/input.tsx, with no class changes.
//
// Exists because the screens built a raw `<input>` with their own classes, and
// each one diverged in a detail: height 40 instead of 36, `focus:ring-1`
// instead of the system's 3px ring, and none handled `aria-invalid`. system.md
// fixes h-9 / px-3 / rounded-md and the focus ring — this is where that takes
// effect once and for all.
//
// `md:text-sm` stays: on the web it prevents iOS auto-zoom on fields smaller
// than 16px. Here the window is always > 768px, so the effect is just
// `text-sm` — keeping it costs nothing and preserves literal parity with the web.
import * as React from 'react'

import { cn } from '../../lib/utils.js'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'text-foreground file:text-foreground placeholder:text-muted-foreground dark:bg-input/20 border-input flex h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-base transition-[color,box-shadow] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm',
        'focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]',
        'aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
