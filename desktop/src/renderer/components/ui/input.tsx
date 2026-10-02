// desktop/src/renderer/components/ui/input.tsx
//
// Portado de web/app/components/ui/input.tsx, sem alteração de classes.
//
// Existe porque as telas montavam `<input>` cru com classes próprias, e cada
// uma divergia num detalhe: altura 40 em vez de 36, `focus:ring-1` em vez do
// anel de 3px do sistema, e nenhuma tratava `aria-invalid`. O system.md fixa
// h-9 / px-3 / rounded-md e o anel de foco — é aqui que isso passa a valer de
// uma vez.
//
// `md:text-sm` fica: no web ele evita o zoom automático do iOS em campos
// menores que 16px. Aqui a janela é sempre > 768px, então o efeito é só
// `text-sm` — mantê-lo custa nada e preserva a paridade literal com o web.
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
