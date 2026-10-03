// desktop/src/renderer/lib/formato.ts
//
// Number formatting for the screens — in a single place.
//
// The duration lived copied in the Painel (App.tsx) and in the Execuções list,
// and the copies diverged: the Painel fixed the rounding and the list kept
// showing "60.0s" and "59m 60s".

/** Duration in seconds, as read on a clock: `12.3s`, `4m 5s`, `2h 10m`. */
export function duracao(s: number | null | undefined): string {
  if (s == null) return '—'
  // Rounds BEFORE deciding the range. Doing it after, 59.97s fell into `< 60`
  // and toFixed(1) printed "60.0s"; and 3599.7s became "59m 60s" — two values
  // that do not exist on a clock, in a dashboard people check at a glance.
  const tenths = Math.round(s * 10) / 10
  if (tenths < 60) return `${tenths.toFixed(1)}s`
  const totalSeg = Math.round(s)
  const m = Math.floor(totalSeg / 60)
  return m < 60
    ? `${m}m ${totalSeg % 60}s`
    : `${Math.floor(m / 60)}h ${m % 60}m`
}
