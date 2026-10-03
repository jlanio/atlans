// desktop/src/shared/disco.ts
//
// Disk space thresholds, shared between the screen and the notification.
//
// In `shared/` because BOTH sides need them: the renderer to paint the bar, the
// main process to decide on the notification. The renderer cannot import a
// value from `main/ui/notificacoes.ts` (it pulls in `electron`, and the import
// would bring the page down — the vite.config.ts plugin blocks this at build
// time), and the main process importing from `renderer/` would be the inverted
// dependency.
//
// Having the two numbers diverge would be worse than duplicating them: the bar
// would be green while the notification had already warned, or the reverse.

/** Below this, a reasonable workflow may already be unable to write its output. */
export const DISCO_BAIXO_GB = 5

/** Below this, it is a matter of time until it fails. */
export const DISCO_CRITICO_GB = 1

export type DiskLevel = 'ok' | 'baixo' | 'critico'

export function diskLevel(freeGb: number | null | undefined): DiskLevel | null {
  if (typeof freeGb !== 'number') return null
  if (freeGb < DISCO_CRITICO_GB) return 'critico'
  if (freeGb < DISCO_BAIXO_GB) return 'baixo'
  return 'ok'
}

export function gb(n: number | null | undefined): string {
  if (typeof n !== 'number') return '—'
  // Below 10 GB the decimal place is the difference between "enough for today"
  // and "not enough"; above that it is just clutter.
  return n < 10 ? `${n.toFixed(1)} GB` : `${Math.round(n)} GB`
}
