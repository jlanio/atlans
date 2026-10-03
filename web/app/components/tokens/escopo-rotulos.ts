import type { ApiTokenScope, ApiTokenStatus } from "@/service/types"

/**
 * Labels for the scopes and statuses of an access token.
 *
 * `ESCOPOS` is the canonical order — the dialog grid and the list chips follow
 * it, so the same set of scopes reads the same on any token. The short label
 * goes on the chip and the card; the description, only in the selection grid.
 * The raw value never appears on screen (contract §7).
 */

export const ESCOPOS = [
  "workflows:read",
  "workflows:write",
  "runs:execute",
  "triggers:manage",
  "drive:read",
  "drive:write",
] as const satisfies readonly ApiTokenScope[]

export const ESCOPO_ROTULOS: Record<ApiTokenScope, string> = {
  "workflows:read":  "Ler fluxos",
  "workflows:write": "Criar e editar fluxos",
  "runs:execute":    "Executar fluxos",
  "triggers:manage": "Gerenciar agendamentos e webhooks",
  "drive:read":      "Ler o Drive",
  "drive:write":     "Enviar arquivos ao Drive",
}

export const ESCOPO_DESCRICOES: Record<ApiTokenScope, string> = {
  "workflows:read":  "Listar fluxos e ver as definições e o histórico de execuções.",
  "workflows:write": "Criar fluxos novos e alterar os existentes.",
  "runs:execute":    "Disparar execuções e acompanhar o resultado.",
  "triggers:manage": "Ligar, desligar e configurar agendamentos e webhooks.",
  "drive:read":      "Listar e baixar arquivos do Drive.",
  "drive:write":     "Enviar e substituir arquivos no Drive.",
}

/** The dialog's "Somente leitura" (read-only) shortcut: the smallest useful set for an agent. */
export const ESCOPOS_SOMENTE_LEITURA: readonly ApiTokenScope[] = ["workflows:read", "drive:read"]

export function rotuloDeEscopo(escopo: ApiTokenScope | string): string {
  return ESCOPO_ROTULOS[escopo as ApiTokenScope] ?? escopo
}

/** Returns the scopes in canonical order, ignoring what isn't known. */
export function ordenarEscopos(escopos: readonly string[]): ApiTokenScope[] {
  return ESCOPOS.filter(e => escopos.includes(e))
}

const STATUS_ROTULOS: Record<ApiTokenStatus, string> = {
  active:  "Ativo",
  expired: "Expirado",
  revoked: "Revogado",
}

export function rotuloDeStatus(status: ApiTokenStatus | string | null | undefined): string {
  if (!status) return "—"
  return STATUS_ROTULOS[status as ApiTokenStatus] ?? status
}
