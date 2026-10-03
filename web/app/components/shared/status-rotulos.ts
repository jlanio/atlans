/**
 * Portuguese label for a run status.
 *
 * The backend uses `success/failed/running/pending/cancelled` (and, per node,
 * `error`/`cached`). The `StatusBadge` showed the raw text in an interface
 * entirely in Portuguese; this is the only place that translates, for every screen.
 */
const LABELS: Record<string, string> = {
  success: "Concluída",
  failed: "Falhou",
  error: "Falhou",
  running: "Em andamento",
  pending: "Na fila",
  cancelled: "Cancelada",
  cached: "Cache",
}

export function rotuloDoStatus(status: string | null | undefined): string {
  if (!status) return "—"
  return LABELS[status] ?? status
}
