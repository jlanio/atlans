"use client"

import type { DragEvent, ReactNode } from "react"
import { TbChevronDown, TbChevronRight, TbDotsVertical, TbGripVertical, TbPencil, TbTrash } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import type { IWorkflow, IWorkflowGroup } from "@/service/types"
import { cn } from "@/lib/utils"
import { plural } from "@/lib/formatos"

export interface GroupSectionProps {
  grupo: IWorkflowGroup
  /** The rows to show — already filtered and sorted by the page composer. */
  workflows: IWorkflow[]
  /** Counts of the group's WHOLE list, not the filtered one. */
  totalNoGrupo: number
  ativosNoGrupo: number
  recolhido: boolean
  onToggle: (groupId: string) => void
  canEdit: boolean
  /** Reorder handle: only `canEdit` and more than one group. */
  podeArrastar: boolean
  /** This group is being dragged (it goes to 40%). */
  arrastandoEste: boolean
  /** Another group is being dragged over this one (dashed). */
  alvoDeReordenacao: boolean
  /** A workflow is being dragged over this group (primary border). */
  recebendoWorkflow: boolean
  nomeDoArrastado: string | null
  onDragOver: (e: DragEvent<HTMLElement>) => void
  onDragLeave: (e: DragEvent<HTMLElement>) => void
  onDrop: () => void
  onDragStartGrupo: (groupId: string) => void
  onDragEndGrupo: () => void
  onRenomear: (grupo: IWorkflowGroup) => void
  onExcluir: (grupo: IWorkflowGroup) => void
  /** One row per workflow; alternative to `children`. */
  renderLinha?: (workflow: IWorkflow) => ReactNode
  /** Ready-made body (the index may prefer to build the rows itself). */
  children?: ReactNode
}

/**
 * "3 workflows · 2 ativos" (singular "1 workflow · 1 ativo"; "vazio" with
 * none). With an active filter and fewer rows than the total, appends "· N com
 * este filtro" — the header count is always the whole group's.
 */
export function textoDaContagemDoGrupo(total: number, ativos: number, comFiltro: number | null = null): string {
  if (total === 0) return "vazio"
  const base = `${plural(total, "workflow")} · ${plural(ativos, "ativo")}`
  return comFiltro != null && comFiltro < total ? `${base} · ${comFiltro} com este filtro` : base
}

/**
 * A group as a section (docs/specs/projects.md §3.8): header with handle,
 * collapse, name, count, description and menu; body with the rows; the same
 * drag targets and states as before — "receive a workflow" and "change
 * position" happen over the same rectangle, which is why each has its own look.
 */
export function GrupoSecao({
  grupo, workflows, totalNoGrupo, ativosNoGrupo, recolhido, onToggle, canEdit, podeArrastar,
  arrastandoEste, alvoDeReordenacao, recebendoWorkflow, nomeDoArrastado,
  onDragOver, onDragLeave, onDrop, onDragStartGrupo, onDragEndGrupo, onRenomear, onExcluir,
  renderLinha, children,
}: GroupSectionProps) {
  const id = grupo.id_hash
  const tituloId = `grupo-${id}-titulo`
  const bodyId = `grupo-${id}-corpo`
  // Fewer rows than the total only happens with an active search or chip: with
  // no filter the group's list is the whole group.
  const comFiltro = workflows.length < totalNoGrupo ? workflows.length : null
  const contagem = textoDaContagemDoGrupo(totalNoGrupo, ativosNoGrupo, comFiltro)
  const vazio = workflows.length === 0

  return (
    <section
      aria-labelledby={tituloId}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      data-grupo={id}
      className={cn(
        "flex flex-col gap-1.5 rounded-lg border bg-muted/30 p-2.5 transition-[border-color,background-color,opacity]",
        recebendoWorkflow && "border-primary bg-primary/5 ring-1 ring-primary/30",
        alvoDeReordenacao && "border-dashed border-primary ring-1 ring-primary/20",
        arrastandoEste && "opacity-40",
      )}
    >
      <div className="flex min-w-0 items-center gap-1.5">
        {/* Only the handle drags the group: a fully draggable header would steal
            the collapse click and the rename click. */}
        {podeArrastar && (
          <span
            draggable
            onDragStart={e => { e.stopPropagation(); e.dataTransfer?.setData("text/plain", id); onDragStartGrupo(id) }}
            onDragEnd={onDragEndGrupo}
            title="Arraste para reordenar os grupos"
            className="cursor-grab text-muted-foreground/30 transition-colors hover:text-muted-foreground/70 active:cursor-grabbing"
          >
            <TbGripVertical size={15} aria-hidden="true" />
          </span>
        )}
        <button
          type="button"
          aria-expanded={!recolhido}
          aria-controls={bodyId}
          onClick={() => onToggle(id)}
          className={cn(
            "flex min-w-0 items-center gap-2 rounded-sm text-sm font-semibold text-foreground outline-none transition-colors",
            "hover:text-primary focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10",
          )}
        >
          {recolhido
            ? <TbChevronRight size={16} className="shrink-0" aria-hidden="true" />
            : <TbChevronDown size={16} className="shrink-0" aria-hidden="true" />}
          <span id={tituloId} className="truncate">{grupo.name}</span>
          <span className="shrink-0 text-xs font-normal text-muted-foreground">{contagem}</span>
        </button>
        {/* The description has always existed in the model and was never shown —
            it was asked for at creation and disappeared. */}
        {grupo.description && (
          <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground max-md:hidden" title={grupo.description}>
            {grupo.description}
          </span>
        )}
        {canEdit && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Ações do grupo ${grupo.name}`}
                title="Ações do grupo"
                className="ml-auto size-8 text-muted-foreground max-md:size-10"
              >
                <TbDotsVertical size={16} aria-hidden="true" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onRenomear(grupo)}>
                <TbPencil aria-hidden="true" /> Renomear grupo
              </DropdownMenuItem>
              <DropdownMenuItem variant="destructive" onClick={() => onExcluir(grupo)}>
                <TbTrash aria-hidden="true" /> Excluir grupo
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {alvoDeReordenacao && (
        <p className="pl-6 text-xs text-primary/70">Soltar aqui move o grupo para esta posição</p>
      )}
      {recebendoWorkflow && (
        <p className="pl-6 text-xs text-primary/70 motion-safe:animate-pulse">
          Solte para mover «{nomeDoArrastado ?? "o workflow"}» para {grupo.name}
        </p>
      )}

      {/* The body always exists (just hidden when collapsed): the button's
          `aria-controls` must point to an element that is present. The rows,
          however, are only mounted when open — rendering dozens of invisible
          cards is not worth it. */}
      <div id={bodyId} hidden={recolhido}>
        {!recolhido && (
          vazio ? (
            // When receiving a workflow the message above already says what to do;
            // repeating the invitation here would be noise.
            !recebendoWorkflow && (
              <p className="py-1.5 pl-6 text-xs text-muted-foreground">
                {canEdit
                  ? "Nenhum workflow aqui. Arraste um para cá ou use «Mover para grupo» no menu do workflow."
                  : "Nenhum workflow neste grupo."}
              </p>
            )
          ) : (
            children ?? (
              <ul className="flex flex-col gap-1.5">
                {workflows.map(wf => <li key={wf.id_hash}>{renderLinha?.(wf)}</li>)}
              </ul>
            )
          )
        )}
      </div>
    </section>
  )
}
