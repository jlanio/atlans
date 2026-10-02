/**
 * Rótulo em português de um status de execução.
 *
 * O backend usa `success/failed/running/pending/cancelled` (e, por nó,
 * `error`/`cached`). O `StatusBadge` mostrava o texto cru numa interface toda
 * em português; este é o único lugar que traduz, para todas as telas.
 */
const ROTULOS: Record<string, string> = {
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
  return ROTULOS[status] ?? status
}
