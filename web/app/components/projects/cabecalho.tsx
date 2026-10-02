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
  /** Com portal publicado e acessível (`temPortal`). */
  portal: number
}

interface Props {
  /** Da lista inteira; nulo na primeira carga (o subtítulo vira esqueleto). */
  contagens: ContagensDoCabecalho | null
  /** Recarga em curso: o botão gira e fica travado. */
  atualizando: boolean
  canEdit: boolean
  onAtualizar: () => void
  onNovoGrupo: () => void
  onCriarWorkflow: () => void
}

/**
 * "10 workflows em 3 grupos · 8 ativos · 4 agendados · 2 com portal". As
 * partes com zero somem — "0 agendados" não ajuda ninguém —, sem grupos o
 * "em N grupos" sai, e o singular vale para cada número.
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
 * Cabeçalho de Projetos (docs/specs/projetos.md §3.1): uma ação primária —
 * criar workflow —, "Novo grupo" em outline e "Atualizar" em ghost. Antes
 * eram três botões do mesmo peso, e criar grupo acontece uma vez por mês.
 *
 * No telefone o primário ocupa a linha, e o resto vai para um menu ⋯: dois
 * botões de texto ao lado de um terceiro não cabem em 390px sem cortar o
 * título.
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

        {/* Telefone: menu ⋯ com o que saiu da linha. */}
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
