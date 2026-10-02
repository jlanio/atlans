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

export interface GrupoSecaoProps {
  grupo: IWorkflowGroup
  /** As linhas a mostrar — já filtradas e ordenadas por quem compõe a página. */
  workflows: IWorkflow[]
  /** Contagens da lista INTEIRA do grupo, não da filtrada. */
  totalNoGrupo: number
  ativosNoGrupo: number
  recolhido: boolean
  onToggle: (groupId: string) => void
  canEdit: boolean
  /** Alça de reordenar: só `canEdit` e mais de um grupo. */
  podeArrastar: boolean
  /** Este grupo está sendo arrastado (fica a 40%). */
  arrastandoEste: boolean
  /** Outro grupo está sendo arrastado por cima deste (tracejado). */
  alvoDeReordenacao: boolean
  /** Um workflow está sendo arrastado por cima deste grupo (borda primária). */
  recebendoWorkflow: boolean
  nomeDoArrastado: string | null
  onDragOver: (e: DragEvent<HTMLElement>) => void
  onDragLeave: (e: DragEvent<HTMLElement>) => void
  onDrop: () => void
  onDragStartGrupo: (groupId: string) => void
  onDragEndGrupo: () => void
  onRenomear: (grupo: IWorkflowGroup) => void
  onExcluir: (grupo: IWorkflowGroup) => void
  /** Uma linha por workflow; alternativa a `children`. */
  renderLinha?: (workflow: IWorkflow) => ReactNode
  /** Corpo pronto (o index pode preferir montar as linhas ele mesmo). */
  children?: ReactNode
}

/**
 * "3 workflows · 2 ativos" (singular "1 workflow · 1 ativo"; "vazio" sem
 * nenhum). Com filtro ativo e menos linhas que o total, acrescenta "· N com
 * este filtro" — a contagem do cabeçalho é sempre a do grupo inteiro.
 */
export function textoDaContagemDoGrupo(total: number, ativos: number, comFiltro: number | null = null): string {
  if (total === 0) return "vazio"
  const base = `${plural(total, "workflow")} · ${plural(ativos, "ativo")}`
  return comFiltro != null && comFiltro < total ? `${base} · ${comFiltro} com este filtro` : base
}

/**
 * Um grupo como seção (docs/specs/projetos.md §3.8): cabeçalho com alça,
 * recolher, nome, contagem, descrição e menu; corpo com as linhas; os mesmos
 * alvos e estados de arrasto de antes — "receber um workflow" e "trocar de
 * posição" acontecem sobre o mesmo retângulo, por isso cada um tem a sua cara.
 */
export function GrupoSecao({
  grupo, workflows, totalNoGrupo, ativosNoGrupo, recolhido, onToggle, canEdit, podeArrastar,
  arrastandoEste, alvoDeReordenacao, recebendoWorkflow, nomeDoArrastado,
  onDragOver, onDragLeave, onDrop, onDragStartGrupo, onDragEndGrupo, onRenomear, onExcluir,
  renderLinha, children,
}: GrupoSecaoProps) {
  const id = grupo.id_hash
  const tituloId = `grupo-${id}-titulo`
  const corpoId = `grupo-${id}-corpo`
  // Menos linhas que o total só acontece com busca ou chip ativo: sem filtro
  // a lista do grupo é o grupo inteiro.
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
        {/* Só a alça arrasta o grupo: o cabeçalho inteiro arrastável roubaria
            o clique de recolher e o de renomear. */}
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
          aria-controls={corpoId}
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
        {/* A descrição existe no modelo desde sempre e nunca foi exibida —
            era pedida na criação e desaparecia. */}
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

      {/* O corpo existe sempre (só escondido quando recolhido): `aria-controls`
          do botão precisa apontar para um elemento presente. As linhas, porém,
          só são montadas quando aberto — não vale renderizar dezenas de cards
          invisíveis. */}
      <div id={corpoId} hidden={recolhido}>
        {!recolhido && (
          vazio ? (
            // Ao receber um workflow a mensagem de cima já diz o que fazer;
            // repetir o convite aqui seria ruído.
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
