"use client"

import { TbDotsVertical, TbFolderPlus, TbPlus, TbRefresh } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { Skeleton } from "@/app/components/ui/skeleton"
import { formatarInteiro, plural } from "@/lib/formatos"

export interface ContagensDoCabecalho {
  workflows: number
  grupos: number
  ativos: number
  agendados: number
  /** With a published and accessible portal (`temPortal`). */
  portal: number
}

interface Props {
  /** Of the whole list; null on the first load (the subtitle becomes a skeleton). */
  contagens: ContagensDoCabecalho | null
  /** Reload in progress: the button spins and is locked. */
  atualizando: boolean
  canEdit: boolean
  onAtualizar: () => void
  onNovoGrupo: () => void
  onCriarWorkflow: () => void
}

/**
 * "10 workflows em 3 grupos · 8 ativos · 4 agendados · 2 com portal". The
 * zero parts disappear — "0 agendados" helps nobody —, with no groups the
 * "em N grupos" goes away, and the singular applies to each number.
 */
export function textoDoSubtitulo(c: ContagensDoCabecalho): string {
  if (c.workflows === 0) {
    return c.grupos > 0 ? `Nenhum workflow · ${plural(c.grupos, "grupo")}` : "Nenhum workflow ainda"
  }
  const partes = [
    c.grupos > 0
      ? `${plural(c.workflows, "workflow")} em ${plural(c.grupos, "grupo")}`
      : plural(c.workflows, "workflow"),
  ]
  if (c.ativos > 0) partes.push(plural(c.ativos, "ativo"))
  if (c.agendados > 0) partes.push(plural(c.agendados, "agendado"))
  if (c.portal > 0) partes.push(`${formatarInteiro(c.portal)} com portal`)
  return partes.join(" · ")
}

/**
 * Projects header (docs/specs/projects.md §3.1): one primary action —
 * create workflow —, "Novo grupo" (new group) as outline and "Atualizar"
 * (refresh) as ghost. They used to be three buttons of the same weight, and
 * creating a group happens once a month.
 *
 * On the phone the primary takes the row, and the rest goes into a ⋯ menu: two
 * text buttons next to a third do not fit in 390px without cutting the
 * title.
 */
export function CabecalhoDeProjetos({
  contagens, atualizando, canEdit, onAtualizar, onNovoGrupo, onCriarWorkflow,
}: Props) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold text-foreground">Projetos</h1>
        {contagens ? (
          <p className="text-sm font-medium text-muted-foreground">{textoDoSubtitulo(contagens)}</p>
        ) : (
          <Skeleton className="mt-1 h-4 w-64" />
        )}
      </div>

      <div className="flex w-full items-center gap-2 select-none md:w-auto">
        {/* Desktop: Atualizar, Novo grupo, Criar workflow. */}
        <div className="hidden items-center gap-2 md:flex">
          <Button
            variant="ghost"
            size="sm"
            onClick={onAtualizar}
            disabled={atualizando}
            aria-label="Atualizar a lista de projetos"
            className="gap-1.5"
          >
            <TbRefresh size={14} className={atualizando ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
            Atualizar
          </Button>
          {canEdit && (
            <Button variant="outline" size="sm" onClick={onNovoGrupo}>
              <TbFolderPlus size={15} aria-hidden="true" /> Novo grupo
            </Button>
          )}
        </div>

        {/* Phone: ⋯ menu with what left the row. */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              aria-label="Mais ações"
              className="size-10 shrink-0 md:hidden"
            >
              <TbDotsVertical size={16} aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            {canEdit && (
              <DropdownMenuItem onClick={onNovoGrupo}>
                <TbFolderPlus /> Novo grupo
              </DropdownMenuItem>
            )}
            <DropdownMenuItem disabled={atualizando} onClick={onAtualizar}>
              <TbRefresh /> Atualizar
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {canEdit && (
          <Button onClick={onCriarWorkflow} size="sm" className="flex-1 max-md:h-10 md:flex-none">
            <TbPlus size={15} aria-hidden="true" /> Criar workflow
          </Button>
        )}
      </div>
    </div>
  )
}
