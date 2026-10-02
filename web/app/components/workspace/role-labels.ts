/**
 * Rótulos dos papéis dentro de um workspace.
 *
 * Há duas listas de propósito. `ROLE_LABELS` cobre os cinco papéis EXIBÍVEIS —
 * incluindo "owner", que o backend devolve na linha sintética do dono. Sem ele,
 * o `<Badge>` daquela linha renderizaria vazio.
 *
 * `ROLE_OPTIONS` são os quatro ATRIBUÍVEIS, e é o que os selects podem oferecer:
 * "owner" não é um papel que se concede — sai de `Workspace.owner_id`, e o
 * backend recusa qualquer PUT que tente atribuí-lo (`_VALID_ROLES`).
 */

export const ROLE_LABELS: Record<string, string> = {
  owner:    "Proprietário",
  admin:    "Admin",
  operator: "Operador",
  editor:   "Editor",
  viewer:   "Visualizador",
}

export const ROLE_COLORS: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  owner:    "default",
  admin:    "destructive",
  operator: "default",
  editor:   "outline",
  viewer:   "secondary",
}

/** Papéis que um admin pode conceder, do menor para o maior. */
export const ROLE_OPTIONS = ["viewer", "editor", "operator", "admin"] as const

/** O que cada papel permite — o select oferecia quatro opções sem explicar nenhuma. */
export const ROLE_DESCRIPTIONS: Record<string, string> = {
  owner:    "Criou o workspace. Edita as configurações gerais e pode excluí-lo.",
  admin:    "Gerencia membros, executor e notificações do workspace.",
  operator: "Executa workflows e reprocessa execuções.",
  editor:   "Cria e edita workflows, envia e apaga arquivos.",
  viewer:   "Apenas visualiza workflows, execuções e arquivos.",
}

export function roleLabel(role: string | null | undefined): string {
  if (!role) return "—"
  return ROLE_LABELS[role] ?? role
}
