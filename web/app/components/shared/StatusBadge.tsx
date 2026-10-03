import { TbCheck, TbPlayerStop, TbX } from "react-icons/tb"
import { rotuloDoStatus } from "./status-rotulos"

const STATUS_COLORS: Record<string, string> = {
  success: "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400",
  failed:  "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400",
  error:   "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400",
  running: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400",
  pending: "bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-400",
  cached:  "bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400",
  // Cancelled is not a failure — its own color so it isn't confused with an error
  // in the run lists.
  cancelled: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400",
}

export function StatusBadge({ status }: { status: string }) {
  const isRunning = status === "running"
  return (
    <span
      data-status={status}
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[status] ?? "bg-muted text-muted-foreground"}`}
    >
      {isRunning && (
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full motion-safe:animate-ping rounded-full bg-blue-500 opacity-60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
        </span>
      )}
      {status === "success" ? <TbCheck className="h-3 w-3" aria-hidden="true" />
        : (status === "failed" || status === "error") ? <TbX className="h-3 w-3" aria-hidden="true" />
        : status === "cancelled" ? <TbPlayerStop className="h-3 w-3" aria-hidden="true" />
        : null}
      {/* Portuguese label on every screen (spec §4.2); `data-status` keeps the raw
          value for whoever needs to cross-check with the backend, without turning
          into an English tooltip. */}
      {rotuloDoStatus(status)}
    </span>
  )
}
