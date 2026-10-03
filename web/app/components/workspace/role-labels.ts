/**
 * Labels for the roles within a workspace.
 *
 * There are two lists on purpose. `ROLE_LABELS` covers the five DISPLAYABLE
 * roles — including "owner", which the backend returns on the owner's synthetic
 * row. Without it, that row's `<Badge>` would render empty.
 *
 * `ROLE_OPTIONS` are the four ASSIGNABLE ones, and are what the selects can
 * offer: "owner" is not a role that is granted — it comes from
 * `Workspace.owner_id`, and the backend rejects any PUT that tries to assign
 * it (`_VALID_ROLES`).
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

/** Roles an admin can grant, from lowest to highest. */
export const ROLE_OPTIONS = ["viewer", "editor", "operator", "admin"] as const

/** What each role allows — the select offered four options without explaining any. */
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
