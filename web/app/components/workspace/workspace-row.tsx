"use client"

import { TbLock, TbSettings } from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { Workspace } from "@/context/WorkspaceContext"
import { roleLabel } from "./role-labels"
import { WorkspaceAvatar } from "./workspace-avatar"
import {
  dotColor, inAlert, resumirExecutor, labelExecutor, type SummaryEntry,
} from "./executor-resumo"
import { modeClass, shortModeLabel } from "./politica"

const FLOOR_TITLE = "Isolamento obrigatório: definido pelo administrador da plataforma"

interface Props extends SummaryEntry {
  workspace: Workspace
  onUsar: () => void
  onConfigurar: () => void
}

/**
 * Compact row of a workspace that is NOT the active one: identity, role and the
 * executor as text, with "Usar" (Use) to promote it to the panel. Nothing here
 * is editable — whoever needs to touch the executor or the members opens the panel.
 */
export function WorkspaceRow({ workspace, onUsar, onConfigurar, ...entrada }: Props) {
  const resumo = resumirExecutor(entrada)
  const alerta = inAlert(resumo, entrada.politica)
  const ponto = dotColor(resumo, entrada.politica)
  const papel = workspace.my_role === "owner" ? "Proprietário" : roleLabel(workspace.my_role)
  // Only when there is a dedicated executor: "Compartilhado" (Shared) is the
  // default and a badge on every row would be noise — the "Pool" label already
  // says so.
  const politica = entrada.politica && entrada.politica.mode !== "pool" ? entrada.politica : null
  const emVigor = politica?.policy_routing_enabled === true

  return (
    <li className="flex items-center gap-3 rounded-lg border bg-card px-3 py-2.5 shadow-xs transition-colors hover:border-muted-foreground/30">
      <WorkspaceAvatar workspace={workspace} />

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <span className="font-medium leading-tight">{workspace.name}</span>
          {workspace.is_default && (
            <Badge variant="secondary" className="px-1.5 py-0 text-[11px]">padrão</Badge>
          )}
        </div>
        {/* `div`, not `p`: the executor skeleton is a block, and a block inside
            a paragraph is invalid HTML. */}
        <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
          <span>{papel}</span>
          <span aria-hidden="true">·</span>
          {resumo.estado === "carregando" ? (
            <Skeleton className="h-3 w-14 rounded" />
          ) : (
            <span className={cn(
              "inline-flex min-w-0 items-center gap-1.5",
              alerta && "font-medium text-amber-700 dark:text-amber-400",
            )}>
              {ponto && <span aria-hidden="true" className={cn("inline-block size-2 shrink-0 rounded-full", ponto)} />}
              <span className="truncate">{labelExecutor(resumo)}</span>
            </span>
          )}
          {politica && resumo.estado !== "carregando" && (
            <Badge
              variant="outline"
              className={cn(
                "shrink-0 gap-0.5 px-1 py-0 text-[10px] leading-tight",
                modeClass(politica.mode),
                !emVigor && "border-dashed",
              )}
              title={politica.isolation_floor === "no_pool" ? FLOOR_TITLE : !emVigor ? "Prévia: ainda não está em vigor" : undefined}
            >
              {politica.isolation_floor === "no_pool" && <TbLock size={9} aria-hidden="true" />}
              {shortModeLabel(politica.mode)}{!emVigor && " · prévia"}
            </Badge>
          )}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <Button variant="outline" size="sm" onClick={onUsar} aria-label={`Usar ${workspace.name}`}>
          Usar
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="size-8"
          onClick={onConfigurar}
          aria-label={`Configurar ${workspace.name}`}
          title="Configurar"
        >
          <TbSettings size={16} />
        </Button>
      </div>
    </li>
  )
}
