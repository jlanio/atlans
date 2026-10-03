import { TbHome } from "react-icons/tb"
import { getWorkspaceIdentity } from "@/lib/workspace-identity"
import { cn } from "@/lib/utils"
import type { Workspace } from "@/context/WorkspaceContext"

const TAMANHOS = {
  md: { caixa: "size-8 rounded-lg text-xs", selo: "size-3.5 -right-1 -bottom-1", icone: 8 },
  xl: { caixa: "size-12 rounded-xl text-sm", selo: "size-4.5 -right-1.5 -bottom-1.5", icone: 10 },
}

/**
 * Initials avatar with the identity color and, on the default workspace, the
 * home badge. The header's `WorkspaceBadge` does not carry the badge; here it
 * matters, because the workspaces screen is the only place that lists them all
 * side by side.
 */
export function WorkspaceAvatar({
  workspace,
  size = "md",
  className,
}: {
  workspace: Workspace
  size?: keyof typeof TAMANHOS
  className?: string
}) {
  const identity = getWorkspaceIdentity(workspace)
  const t = TAMANHOS[size]
  return (
    <span
      className={cn(
        "relative flex shrink-0 items-center justify-center font-semibold",
        identity.bg, identity.fg, t.caixa, className,
      )}
      aria-hidden="true"
    >
      {identity.initials}
      {workspace.is_default && (
        <span
          className={cn(
            "absolute flex items-center justify-center rounded-md border border-border bg-background text-muted-foreground",
            t.selo,
          )}
          title="Workspace padrão"
        >
          <TbHome size={t.icone} />
        </span>
      )}
    </span>
  )
}
