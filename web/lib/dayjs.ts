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
 * Converte uma string ISO vinda do backend em dayjs no timezone LOCAL.
 *
 * Contexto: o backend serializa datas com `datetime.utcnow().isoformat()` —
 * que retorna uma string naive (sem `Z` nem offset). Por spec do ECMAScript,
 * `new Date(...)` e `dayjs(...)` interpretam strings sem offset como timezone
 * LOCAL, o que gera horários deslocados (ex.: mostra +3h em UTC-3).
 *
 * Este helper força parse como UTC quando não há offset, depois converte
 * para o fuso do navegador. Se o backend algum dia passar a serializar
 * com `Z` ou offset explícito, o código continua correto.
 *
 * Retorna `null` se a entrada é `null`/`undefined`/`""` — ideal para
 * usar com `?? "—"` em UI.
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

/** Atalho para "há X min/h" relativo ao agora local. Null-safe. */
export function fromNowLocal(iso: string | null | undefined) {
  return fromBackend(iso)?.fromNow() ?? "—"
}

export { dayjs }