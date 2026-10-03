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
  /** Shows the workspace name next to the avatar */
  showName?: boolean
  /** Shows the Proprietário/Convidado (Owner/Guest) badge (requires currentUserId) */
  showRole?: boolean
  /**
   * Shows the initials avatar. On in the header picker's trigger: the
   * workspace's deterministic color is the active-scope signal that is fastest
   * to read at a glance. It is off only where it would repeat a mark already
   * visible.
   */
  showAvatar?: boolean
  /** id_hash of the logged-in user — used to decide Proprietário/Convidado */
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

  // No workspace: generic neutral avatar
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
  // `my_role` is the backend's answer and distinguishes the five roles; comparing
  // `owner_id` can only answer "owner or not", and everything else — admin,
  // operator, editor — was labeled "Convidado" (Guest). In the header, where the
  // role became one of only two things displayed, that was simply wrong. The
  // id comparison remains as a fallback for when `my_role` is missing.
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
