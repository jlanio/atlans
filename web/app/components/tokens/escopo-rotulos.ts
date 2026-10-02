import type { ApiTokenScope, ApiTokenStatus } from "@/service/types"

/**
 * Rótulos dos escopos e dos status de um token de acesso.
 *
 * `ESCOPOS` é a ordem canônica — a grade do diálogo e os chips da lista a
 * seguem, para o mesmo conjunto de escopos ler igual em qualquer token. O
 * rótulo curto vai no chip e no cartão; a descrição, só na grade de escolha.
 * O valor cru nunca aparece na tela (contrato §7).
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

/** Atalho «Somente leitura» do diálogo: o menor conjunto útil para um agente. */
export const ESCOPOS_SOMENTE_LEITURA: readonly ApiTokenScope[] = ["workflows:read", "drive:read"]

export function rotuloDeEscopo(escopo: ApiTokenScope | string): string {
  return ESCOPO_ROTULOS[escopo as ApiTokenScope] ?? escopo
}

/** Devolve os escopos na ordem canônica, ignorando o que não se conhece. */
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
