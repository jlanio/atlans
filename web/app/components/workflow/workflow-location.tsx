"use client"

import type { ReactNode } from "react"
import { TbChevronRight, TbSitemap } from "react-icons/tb"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { WorkspaceBadge } from "@/app/components/workspace/workspace-badge"
import { Skeleton } from "@/app/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { CAMADA_SOBRE_O_CANVAS } from "./canvas-layers"

interface Props {
  /**
   * Workspace the OPEN workflow belongs to (`IWorkflow.workspace_id`).
   * Absent on /workflow/create, where there is no workflow yet: there the
   * destination is the active workspace, which is what `useSaveWorkflow` sends
   * on create.
   */
  workspaceId?: string | null
  /** The workflow has not arrived yet: the breadcrumb shows skeletons in place
   *  of the workspace and the name, instead of claiming "Sem nome" (untitled)
   *  and the active workspace (which may not even be the workflow's — see
   *  `dono` below). */
  carregando?: boolean
  /** What sits in the same row, to the right of the breadcrumb — the save chip.
   *  A direct child of the container, to receive the layer's `pointer-events`. */
  children?: ReactNode
}

/**
 * Where this workflow is: workspace › name.
 *
 * Replaces the name field that used to be here. Renaming is a catalog
 * operation, not a graph-editing one — it already exists in "Configurar
 * projeto" (/projects), and a loose input over the canvas offered the same
 * thing in a place where nobody looks for it. A workflow still without a name
 * keeps being named on the first save: `useSaveWorkflow` sets `needs_name` and
 * the UnsavedDialog asks.
 *
 * What was missing here was the opposite — knowing WHERE you are. The editor is
 * the only screen without the dashboard header (`AppHeader` returns null on
 * /workflow/*, because the sticky bar covered the add-node button) and it also
 * collapses the sidebar on its own when opening, so nothing on screen said the
 * workspace — right where the run is triggered.
 *
 * Same breadcrumb as the sub-workflow viewer: `TbChevronRight` separator in
 * `text-muted-foreground/40`, final step in `font-medium text-foreground`.
 */
export default function WorkflowLocation({ workspaceId, carregando = false, children }: Props) {
  const workflowName = useWorkflowSaveStore(s => s.workflowName)
  const { workspaces, current } = useWorkspace()

  const nome = workflowName?.trim() ?? ""

  // The WORKFLOW's workspace, not the one selected in the bar. Nothing syncs
  // one with the other: /workflow/[id] fetches by id, with no workspace filter,
  // and the active one may have changed in another tab (it is rehydrated from
  // localStorage). Without this resolution, the breadcrumb would claim a
  // workspace the workflow does not belong to — next to the run button, which
  // is precisely what it exists to protect. Until the list arrives, it claims
  // nothing.
  const dono = workspaceId
    ? workspaces.find(w => w.id_hash === workspaceId) ?? null
    : current

  return (
    <div
      // Limited width and its own layer: a container in normal flow took the
      // canvas's full width and swallowed clicks and drags in an invisible
      // strip — the defect the name field once had here. The ceiling stops
      // before the add-node button, in the right corner. `flex-wrap`: the
      // save chip drops to the line below when the two do not fit, instead of
      // squeezing the workflow name.
      className={`${CAMADA_SOBRE_O_CANVAS} left-2 top-2 flex max-w-[calc(100%-1rem)] flex-wrap items-center gap-2 pl-safe sm:left-4 sm:top-3 sm:max-w-[min(44rem,calc(100%-6rem))]`}
    >
      {/* `min-h-8`: with the skeletons (shorter than the text) the box
          shrank and the row jumped when the name arrived. */}
      <div className="flex min-h-8 min-w-0 items-center gap-1.5 rounded-lg border border-border bg-background/85 py-1.5 pr-3 pl-1.5 shadow-xs backdrop-blur-sm">
        {carregando ? (
          <>
            <span className="sr-only">Carregando workflow.</span>
            <Skeleton className="ml-1 h-3 w-24" aria-hidden="true" />
            <TbChevronRight size={12} className="shrink-0 text-muted-foreground/40" aria-hidden="true" />
            <Skeleton className="h-3.5 w-36" aria-hidden="true" />
          </>
        ) : (
          <>
          <span className="sr-only">
            {nome ? `Workflow ${nome}` : "Workflow sem nome"}
            {dono ? ` no workspace ${dono.name}.` : "."}
          </span>

          {dono ? (
            <>
              <WorkspaceBadge workspace={dono} size="sm" className="shrink-0" />
              {/* No fixed ceiling: when both fit, nothing is cut. When they do not
                  fit, the workspace shrinks ~3x faster — it is the least
                  specific step of the breadcrumb, and what must stay readable
                  is the workflow name. `title` gives back the full value in both cases. */}
              <span
                aria-hidden="true"
                title={dono.name}
                className="min-w-0 shrink-[3] truncate text-xs text-muted-foreground"
              >
                {dono.name}
              </span>
              <TbChevronRight size={12} className="shrink-0 text-muted-foreground/40" aria-hidden="true" />
            </>
          ) : (
            <TbSitemap size={15} className="ml-1 shrink-0 text-muted-foreground" aria-hidden="true" />
          )}

          <span
            aria-hidden="true"
            title={nome || undefined}
            className={cn(
              "min-w-0 truncate text-sm font-medium",
              nome ? "text-foreground" : "text-muted-foreground italic",
            )}
          >
            {nome || "Sem nome"}
          </span>
          </>
        )}
      </div>

      {children}
    </div>
  )
}
