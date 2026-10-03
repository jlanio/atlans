"use client"

import { TbCrown, TbLoader2, TbX } from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/app/components/ui/select"
import {
  Tooltip, TooltipContent, TooltipTrigger,
} from "@/app/components/ui/tooltip"
import type { IWorkspaceMember } from "@/service/types"
import { ROLE_COLORS, ROLE_DESCRIPTIONS, ROLE_LABELS, ROLE_OPTIONS, roleLabel } from "../role-labels"

interface Props {
  member: IWorkspaceMember
  canManage: boolean
  /** id of the logged-in user — their own row does not offer removal (that is "Sair", Leave). */
  currentUserId: string | null
  /** id being mutated, or null. Locks ALL rows, not just the one saving. */
  savingUserId: string | null
  onRoleChange: (userId: string, role: string) => void
  onRemove: (member: IWorkspaceMember) => void
}

export function MemberRow({
  member, canManage, currentUserId, savingUserId, onRoleChange, onRemove,
}: Props) {
  const isOwner = member.role === "owner"
  const isSelf = currentUserId != null && member.user_id === currentUserId
  const isSaving = savingUserId === member.user_id
  // Any in-flight mutation locks the whole row: with the selects free, two
  // quick clicks fired concurrent PUTs and the last to respond set the
  // role — even across different rows.
  const locked = savingUserId !== null

  // The owner has no row in `workspace_members`; the backend rejects PUT and
  // DELETE on them. Offering the controls here would only produce a 400.
  const editable = canManage && !isOwner
  const removable = canManage && !isOwner && !isSelf

  return (
    <div className="flex items-center gap-2 rounded-md border px-3 py-2">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          {isOwner && <TbCrown className="size-3.5 shrink-0 text-amber-500" aria-hidden="true" />}
          <span className="truncate text-sm font-medium">{member.username}</span>
          {isSelf && <span className="shrink-0 text-xs text-muted-foreground">(você)</span>}
        </div>
        <p className="truncate text-xs text-muted-foreground">{member.email}</p>
      </div>

      {isSaving && (
        <TbLoader2 className="size-4 shrink-0 animate-spin text-muted-foreground" aria-hidden="true" />
      )}

      {editable ? (
        <Select
          value={member.role}
          disabled={locked}
          onValueChange={role => onRoleChange(member.user_id, role)}
        >
          <SelectTrigger size="sm" className="w-32 shrink-0 text-xs" aria-label={`Papel de ${member.username}`}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ROLE_OPTIONS.map(role => (
              <SelectItem key={role} value={role} className="text-xs">
                <span className="flex flex-col items-start">
                  <span>{ROLE_LABELS[role]}</span>
                  <span className="text-[10px] text-muted-foreground">
                    {ROLE_DESCRIPTIONS[role]}
                  </span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : (
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant={ROLE_COLORS[member.role] ?? "secondary"} className="shrink-0 text-[10px]">
              {roleLabel(member.role)}
            </Badge>
          </TooltipTrigger>
          <TooltipContent side="left" className="max-w-56 text-xs">
            {ROLE_DESCRIPTIONS[member.role] ?? "Papel neste workspace."}
          </TooltipContent>
        </Tooltip>
      )}

      {removable && (
        <button
          type="button"
          className="shrink-0 text-muted-foreground transition-colors hover:text-destructive disabled:opacity-40"
          onClick={() => onRemove(member)}
          disabled={locked}
          aria-label={`Remover ${member.username}`}
          title="Remover membro"
        >
          <TbX className="size-4" />
        </button>
      )}
    </div>
  )
}
