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
  corDoPonto, emAlerta, resumirExecutor, rotularExecutor, type EntradaDoResumo,
} from "./executor-resumo"
import { classeDoModo, rotuloCurtoDoModo } from "./politica"

const TITULO_PISO = "Isolamento obrigatório: definido pelo administrador da plataforma"

interface Props extends EntradaDoResumo {
  workspace: Workspace
  onUsar: () => void
  onConfigurar: () => void
}

/**
 * Linha compacta de um workspace que NÃO é o ativo: identidade, papel e o
 * executor por texto, com "Usar" para promovê-lo ao painel. Nada aqui é
 * editável — quem precisa mexer no executor ou nos membros abre o painel.
 */
export function WorkspaceRow({ workspace, onUsar, onConfigurar, ...entrada }: Props) {
  const resumo = resumirExecutor(entrada)
  const alerta = emAlerta(resumo, entrada.politica)
  const ponto = corDoPonto(resumo, entrada.politica)
  const papel = workspace.my_role === "owner" ? "Proprietário" : roleLabel(workspace.my_role)
  // Só quando há dedicado: "Compartilhado" é o padrão e um selo em toda linha
  // seria ruído — o rótulo "Pool" já diz isso.
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
        {/* `div`, não `p`: o esqueleto do executor é um bloco, e bloco dentro
            de parágrafo é HTML inválido. */}
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
              <span className="truncate">{rotularExecutor(resumo)}</span>
            </span>
          )}
          {politica && resumo.estado !== "carregando" && (
            <Badge
              variant="outline"
              className={cn(
                "shrink-0 gap-0.5 px-1 py-0 text-[10px] leading-tight",
                classeDoModo(politica.mode),
                !emVigor && "border-dashed",
              )}
              title={politica.isolation_floor === "no_pool" ? TITULO_PISO : !emVigor ? "Prévia: ainda não está em vigor" : undefined}
            >
              {politica.isolation_floor === "no_pool" && <TbLock size={9} aria-hidden="true" />}
              {rotuloCurtoDoModo(politica.mode)}{!emVigor && " · prévia"}
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
