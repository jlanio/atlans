// desktop/src/renderer/components/Copiavel.tsx
//
// A technical value the user may eventually need to send to someone — executor
// ID, path, error message.
//
// Exists because the ID appeared truncated (`7f26ceba…`) with no way to get the
// whole value: whoever asked for support would have to open `.env` in Explorer.
import { useEffect, useState } from 'react'
import { cn } from '../lib/utils.js'

export function Copiavel({
  valor, rotulo, exibir, className,
}: {
  valor: string
  /** `title` text. Without it, the value itself. */
  rotulo?: string
  /** What to show, if different from the value (e.g. truncated). */
  exibir?: string
  className?: string
}) {
  const [copiado, setCopiado] = useState(false)

  // Disappears on its own: a permanent "copiado!" (copied!) becomes noise.
  useEffect(() => {
    if (!copiado) return
    const t = setTimeout(() => setCopiado(false), 1600)
    return () => clearTimeout(t)
  }, [copiado])

  return (
    <button
      type="button"
      title={copiado ? 'Copiado' : `${rotulo ?? valor} — clique para copiar`}
      onClick={() => {
        void navigator.clipboard.writeText(valor).then(() => setCopiado(true))
      }}
      className={cn(
        'group inline-flex items-center gap-1.5 rounded font-mono text-xs text-muted-foreground',
        'transition-colors hover:text-foreground',
        className,
      )}
    >
      <span>{exibir ?? valor}</span>
      <span className={cn(
        'text-[10px] transition-opacity',
        copiado ? 'text-green-600 opacity-100 dark:text-green-400' : 'opacity-0 group-hover:opacity-60',
      )}>
        {copiado ? 'copiado' : 'copiar'}
      </span>
    </button>
  )
}
