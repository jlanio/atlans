import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'
import relative from 'dayjs/plugin/relativeTime'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(duration)
dayjs.extend(relative)

/**
 * Converts an ISO string coming from the backend into a dayjs in the LOCAL timezone.
 *
 * Context: the backend serializes dates with `datetime.utcnow().isoformat()` —
 * which returns a naive string (no `Z` and no offset). Per the ECMAScript spec,
 * `new Date(...)` and `dayjs(...)` interpret strings without an offset as the
 * LOCAL timezone, which produces shifted times (e.g. shows +3h in UTC-3).
 *
 * This helper forces parsing as UTC when there is no offset, then converts
 * to the browser's timezone. If the backend ever starts serializing
 * with `Z` or an explicit offset, the code stays correct.
 *
 * Returns `null` if the input is `null`/`undefined`/`""` — ideal for
 * use with `?? "—"` in the UI.
 */
export function fromBackend(iso: string | null | undefined) {
  if (!iso) return null
  const hasOffset = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(iso)
  return hasOffset ? dayjs(iso).local() : dayjs.utc(iso).local()
}

/** Atalho para formato brasileiro curto (DD/MM/YYYY HH:mm). Null-safe. */
export function formatLocal(iso: string | null | undefined, pattern = "DD/MM/YYYY HH:mm") {
  return fromBackend(iso)?.format(pattern) ?? "—"
}

/** Shortcut for "X min/h ago" relative to local now. Null-safe. */
export function fromNowLocal(iso: string | null | undefined) {
  return fromBackend(iso)?.fromNow() ?? "—"
}

export { dayjs }