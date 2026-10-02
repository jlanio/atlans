// desktop/src/renderer/components/ui/skeleton.tsx
//
// Portado de web/app/components/ui/skeleton.tsx, com o keyframe
// `skeleton-shimmer` copiado para o index.css junto.
//
// O app abre e fica em "Carregando…" — uma frase centralizada — enquanto três
// chamadas de IPC resolvem. Uma frase não diz onde o conteúdo vai aparecer nem
// quanto dele vem; o esqueleto diz as duas coisas, e é o que o web usa.
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
