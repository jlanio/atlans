// Formats a duration in ms as a readable string (e.g. "123ms" or "1.23s")
export function formatDuration(ms?: number | null): string | null {
  if (ms == null) return null
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

/**
 * Formats bytes in the largest unit that fits.
 *
 * There were four copies of this, in two incompatible families: `/artifacts`
 * and `/drive` stopped at MB (a 3 GB file became "3072.0 MB"), while
 * `/dashboard` and `/admin/settings` scaled up to TB with adaptive precision.
 * This is the second one — the one that actually works for the sizes the
 * Drive receives.
 *
 * Adaptive precision: 2 decimals below 10, 1 decimal below 100, integer
 * above. Keeps the column width stable without losing resolution on small
 * values.
 */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return "—"
  if (bytes === 0) return "0 B"
  const units = ["B", "KB", "MB", "GB", "TB"]
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const val = bytes / Math.pow(1024, i)
  const texto = val < 10 ? val.toFixed(2) : val < 100 ? val.toFixed(1) : String(Math.round(val))
  return `${texto} ${units[i]}`
}

/**
 * Color class for a success rate (0..1).
 *
 * The rule was copied across four screens, and one of them diverged: three
 * used `>= 0.9 verde / >= 0.7 âmbar / resto vermelho`, and `/observability/[id]`
 * used `>= 0.9 verde / < 0.5 vermelho / resto âmbar`. The effect was a workflow
 * with 60% success showing up RED on three screens and AMBER on the fourth —
 * the same number, two opposite judgments, depending on where the user looked.
 *
 * Unified on the majority rule (the 0.7 threshold), which is also the more
 * conservative one: 60% is now red everywhere.
 *
 * `tom` covers the palette difference that already existed between the screens
 * (`text-amber-600` on the executor card, `text-yellow-500` in the tables).
 */
export function successRateColor(rate: number | null | undefined, tom: "amber" | "yellow" = "yellow"): string {
  if (rate == null) return "text-muted-foreground"
  if (rate >= 0.9) return tom === "amber" ? "text-green-600 dark:text-green-400" : "text-green-500"
  if (rate >= 0.7) return tom === "amber" ? "text-amber-600 dark:text-amber-400" : "text-yellow-500"
  return tom === "amber" ? "text-red-500 dark:text-red-400" : "text-red-500"
}
