"use client"

import { TbAlertTriangle, TbCircleCheck } from "react-icons/tb"

export interface TestResult {
  ok: boolean
  message: string
}

/**
 * Result of "Testar credencial" (test credential), shared by the create and
 * edit modals.
 *
 * Three fixes compared with the loose paragraph that used to be duplicated in both:
 *
 * - Icon alongside the color. Color alone carries no meaning for someone who
 *   cannot tell it apart.
 * - `dark:` variant. `text-green-600` on `bg-green-500/10` falls below 4.5:1
 *   in the dark theme — the same problem the listing already fixed.
 * - Live region. `role="status"` for success and `role="alert"` for failure,
 *   otherwise the result is not announced to screen readers.
 *
 * The `message` comes from the backend and is rendered literally on purpose: for
 * postgresql/mysql/s3 it reports a real connection, and for the other types the
 * backend answers "Campos validados com sucesso" (fields validated successfully)
 * — which is the truth, since in those cases it does not touch the network. We
 * don't rewrite the message here so as not to promise more than was done.
 */
export function TestResultBanner({ result }: { result: TestResult | null }) {
  if (!result) return null

  const Icon = result.ok ? TbCircleCheck : TbAlertTriangle

  return (
    <p
      role={result.ok ? "status" : "alert"}
      aria-live="polite"
      className={`flex items-start gap-1.5 rounded px-2 py-1.5 text-xs ${
        result.ok
          ? "bg-green-500/10 text-green-700 dark:text-green-400"
          : "bg-destructive/10 text-destructive"
      }`}
    >
      <Icon className="mt-px size-3.5 shrink-0" aria-hidden="true" />
      <span className="min-w-0">{result.message}</span>
    </p>
  )
}
