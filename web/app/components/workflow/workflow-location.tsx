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
   * Workspace a que o workflow ABERTO pertence (`IWorkflow.workspace_id`).
   * Ausente em /workflow/create, onde ainda não há workflow: lá o destino é o
   * workspace ativo, que é o que `useSaveWorkflow` envia ao criar.
   */
  workspaceId?: string | null
  /** O workflow ainda não chegou: a trilha mostra esqueletos no lugar do
   *  workspace e do nome, em vez de afirmar "Sem nome" e o workspace ativo
   *  (que pode nem ser o do workflow — ver `dono` abaixo). */
  carregando?: boolean
  /** O que fica na mesma fileira, à direita da trilha — o chip de salvamento.
   *  Filho direto do contêiner, para receber o `pointer-events` da camada. */
  children?: ReactNode
}

/**
 * Onde este workflow está: workspace › nome.
 *
 * Substitui o campo de nome que ficava aqui. Renomear é operação de catálogo,
 * não de edição de grafo — já existe em "Configurar projeto" (/projects), e um
 * input solto sobre o canvas oferecia a mesma coisa num lugar onde ninguém a
 * procura. Um workflow ainda sem nome continua sendo nomeado no primeiro save:
 * `useSaveWorkflow` marca `needs_name` e o UnsavedDialog pergunta.
 *
 * O que faltava aqui era o inverso — saber ONDE se está. O editor é a única
 * tela sem o cabeçalho do dashboard (`AppHeader` devolve null em /workflow/*,
 * porque a barra sticky cobria o botão de adicionar nó) e ainda recolhe a
 * sidebar sozinho ao abrir, de modo que nada na tela dizia o workspace — bem
 * onde se dispara a execução.
 *
 * Mesma trilha do visualizador de sub-fluxo: separador `TbChevronRight` em
 * `text-muted-foreground/40`, degrau final em `font-medium text-foreground`.
 */
export default function WorkflowLocation({ workspaceId, carregando = false, children }: Props) {
  const workflowName = useWorkflowSaveStore(s => s.workflowName)
  const { workspaces, current } = useWorkspace()

  const nome = workflowName?.trim() ?? ""

  // O workspace do WORKFLOW, não o selecionado na barra. Nada sincroniza um com
  // o outro: /workflow/[id] busca por id, sem filtro de workspace, e o ativo
  // pode ter mudado em outra aba (ele é reidratado do localStorage). Sem esta
  // resolução, a trilha afirmaria um workspace ao qual o workflow não pertence
  // — ao lado do botão de executar, que é justamente o que ela existe para
  // proteger. Enquanto a lista não chegou, não afirma nada.
  const dono = workspaceId
    ? workspaces.find(w => w.id_hash === workspaceId) ?? null
    : current

  return (
    <div
      // Largura limitada e camada própria: um contêiner em fluxo normal ocupava
      // a largura inteira do canvas e engolia clique e arrasto numa faixa
      // invisível — foi o defeito que o campo de nome já teve aqui. O teto
      // para antes do botão de adicionar nó, no canto direito. `flex-wrap`: o
      // chip de salvamento desce para a linha de baixo quando os dois não
      // cabem, em vez de espremer o nome do workflow.
      className={`${CAMADA_SOBRE_O_CANVAS} left-2 top-2 flex max-w-[calc(100%-1rem)] flex-wrap items-center gap-2 pl-safe sm:left-4 sm:top-3 sm:max-w-[min(44rem,calc(100%-6rem))]`}
    >
      {/* `min-h-8`: com os esqueletos (mais baixos que o texto) a caixa
          encolhia e a fileira saltava quando o nome chegava. */}
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
              {/* Sem teto fixo: quando os dois cabem, nada é cortado. Quando não
                  cabem, o workspace encolhe ~3x mais rápido — é o degrau menos
                  específico da trilha, e quem precisa continuar legível é o nome
                  do workflow. O `title` devolve o valor inteiro nos dois casos. */}
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
