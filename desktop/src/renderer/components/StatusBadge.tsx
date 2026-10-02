// desktop/src/renderer/components/StatusBadge.tsx
//
// Mesmas cores de status do StatusBadge do app web (.interface-design/system.md,
// secao "Status colors"). Sao a excecao aceita a regra de usar so tokens
// semanticos: verde/vermelho/azul/amarelo comunicam desfecho de execucao de
// forma que `--primary` nao comunica.
import { cn } from '../lib/utils.js'

const CORES: Record<string, string> = {
  ok: 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400',
  success: 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400',
  error: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400',
  failed: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400',
  running: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400',
  connected: 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400',
  connecting: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400',
  reconnecting: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-400',
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-400',
  cancelled: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-400',
  cached: 'bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400',
}

export function StatusBadge({
  status, rotulo, pulsando, className,
}: {
  status: string
  rotulo?: string
  pulsando?: boolean
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border border-transparent px-2.5 py-0.5 text-xs font-semibold',
        CORES[status] ?? 'bg-muted text-muted-foreground',
        className,
      )}
    >
      {pulsando && (
        <span className="relative flex size-1.5">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-60" />
          <span className="relative inline-flex size-1.5 rounded-full bg-current" />
        </span>
      )}
      {rotulo ?? status}
    </span>
  )
}
