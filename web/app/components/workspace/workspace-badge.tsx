"use client"

import { TbBuildingFactory2, TbCrown, TbUserCheck } from "react-icons/tb"
import { cn } from "@/lib/utils"
import { getWorkspaceIdentity } from "@/lib/workspace-identity"
import { roleLabel } from "./role-labels"
import type { Workspace } from "@/context/WorkspaceContext"

interface Props {
  workspace: Workspace | null
  /** sm: 24px | md: 32px | lg: 40px */
  size?: "sm" | "md" | "lg"
  /** Mostra nome do workspace ao lado do avatar */
  showName?: boolean
  /** Mostra badge Proprietário/Convidado (requer currentUserId) */
  showRole?: boolean
  /**
   * Mostra o avatar de iniciais. Ligado no gatilho do seletor do cabeçalho: a
   * cor determinística do workspace é o sinal de escopo ativo mais rápido de
   * ler num relance. Fica desligado só onde repetiria uma marca já visível.
   */
  showAvatar?: boolean
  /** id_hash do usuário logado — usado pra decidir Proprietário/Convidado */
  currentUserId?: string | null
  className?: string
}

const SIZE_CLASSES = {
  sm: { avatar: "size-6 text-[10px]", name: "text-xs", roleIcon: "size-2.5" },
  md: { avatar: "size-8 text-xs",     name: "text-sm", roleIcon: "size-3"   },
  lg: { avatar: "size-10 text-sm",    name: "text-base", roleIcon: "size-3.5" },
}

export function WorkspaceBadge({
  workspace,
  size = "md",
  showName = false,
  showRole = false,
  showAvatar = true,
  currentUserId = null,
  className,
}: Props) {
  const s = SIZE_CLASSES[size]

  // Sem workspace: avatar neutro genérico
  if (!workspace) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        {showAvatar && (
          <div
            className={cn(
              "flex aspect-square items-center justify-center rounded-lg",
              "bg-muted text-muted-foreground",
              s.avatar,
            )}
          >
            <TbBuildingFactory2 className="size-4" />
          </div>
        )}
        {showName && (
          <span className={cn("truncate text-muted-foreground", s.name)}>
            Sem workspace
          </span>
        )}
      </div>
    )
  }

  const identity = getWorkspaceIdentity(workspace)
  // `my_role` é a resposta do backend e distingue os cinco papéis; comparar
  // `owner_id` só sabe responder "dono ou não", e todo o resto — admin,
  // operador, editor — era rotulado "Convidado". No cabeçalho, onde o papel
  // ficou sendo uma das duas únicas coisas exibidas, isso era simplesmente
  // errado. A comparação por id fica como reserva para quando `my_role` falta.
  const isOwner =
    workspace.my_role === "owner" ||
    !!(currentUserId && workspace.owner_id && workspace.owner_id === currentUserId)
  const papel = isOwner
    ? "Proprietário"
    : workspace.my_role
      ? roleLabel(workspace.my_role)
      : "Convidado"

  return (
    <div className={cn("flex items-center gap-2 min-w-0", className)}>
      {showAvatar && (
        <div
          className={cn(
            "flex aspect-square items-center justify-center rounded-lg font-semibold shrink-0",
            identity.bg,
            identity.fg,
            s.avatar,
          )}
          aria-label={`Workspace ${workspace.name}`}
        >
          {identity.initials}
        </div>
      )}

      {showName && (
        <div className="grid min-w-0 flex-1 leading-tight">
          <span className={cn("truncate font-semibold", s.name)}>
            {workspace.name}
          </span>
          {showRole && (
            <span className="flex items-center gap-1 truncate text-xs text-muted-foreground">
              {isOwner ? (
                <TbCrown className={cn("shrink-0 text-amber-700 dark:text-amber-400", s.roleIcon)} />
              ) : (
                <TbUserCheck className={cn("shrink-0", s.roleIcon)} />
              )}
              {papel}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
