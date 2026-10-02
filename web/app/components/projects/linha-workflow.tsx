"use client"

import React, { type ReactNode } from "react"
import type { IconType } from "react-icons"
import {
  TbArrowsExchange, TbBolt, TbClock, TbCopy, TbDotsVertical, TbFile, TbFolderOpen, TbFolders, TbGripVertical,
  TbHistory, TbLock, TbMapPin, TbPencil, TbPlayerPlay, TbSettings, TbSubtask, TbToggleLeft, TbToggleRight,
  TbTrash, TbWorld,
} from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuSub,
  DropdownMenuSubContent, DropdownMenuSubTrigger, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import type { IWorkflow, IWorkflowGroup } from "@/service/types"
import { fromBackend, dayjs } from "@/lib/dayjs"
import { cn } from "@/lib/utils"
import { formatarInicio } from "@/lib/formatos"
import { SeloAssistente } from "../shared/selo-assistente"
import { ComoAndaCelula } from "./como-anda-celula"
import type { ComoAnda } from "./como-anda"
import { temPortal } from "./filtros"
import type { Gatilho, ResumoDoAgendamento, TipoDeGatilho } from "./gatilho"
import { SeloSubFluxo } from "./selo-subfluxo"

export interface LinhaWorkflowProps {
  workflow: IWorkflow
  gatilho: Gatilho
  resumoDoAgendamento: ResumoDoAgendamento | null
  comoAnda: ComoAnda
  grupos: IWorkflowGroup[]
  canEdit: boolean
  canExecute: boolean
  canManage: boolean
  /** Há algum workspace de destino elegível para "Mover para workspace". */
  podeMover: boolean
  /** Arrastar só existe a partir do primeiro grupo criado. */
  hasDnd: boolean
  isDragging: boolean
  /** Disparando ou resolvendo os parâmetros deste workflow. */
  executando: boolean
  duplicando: boolean
  /** `run_id` do run vivo (`ActiveRunsContext`): o Executar vira "Ver execução". */
  runIdVivo: string | null
  onOpen: (id: string) => void
  /** Aquece a rota do editor antes do clique (ver `onPointerEnter` abaixo). */
  onPrefetch: (id: string) => void
  onRun: (workflow: IWorkflow) => void
  onVerExecucao: (runId: string) => void
  onAtivar: (workflow: IWorkflow) => void
  onDesativar: (workflow: IWorkflow) => void
  onConfigure: (id: string) => void
  onPortal: (workflow: IWorkflow) => void
  onMove: (workflow: IWorkflow) => void
  onDuplicate: (workflow: IWorkflow) => void
  onDelete: (id: string) => void
  onViewRuns: (id: string) => void
  onAddToGroup: (workflowId: string, groupId: string) => void
  onRemoveFromGroup: (workflowId: string, groupId: string) => void
  onDragStart: (id: string) => void
  onDragEnd: () => void
}

const ICONE_DO_GATILHO: Record<TipoDeGatilho, IconType> = {
  agendado: TbClock,
  webhook: TbBolt,
  arquivo: TbFile,
  geofence: TbMapPin,
  manual: TbPlayerPlay,
  subfluxo: TbSubtask,
}

const TITULO_DO_SUBFLUXO = "Sub-fluxo: executar sozinho normalmente não faz o esperado"
const VINTE_E_QUATRO_HORAS = 24

/** Criado há menos de 24 h: ganha o selo "Novo". Sem `created_at` não há como afirmar. */
export function ehNovo(wf: Pick<IWorkflow, "created_at">, agora: Date = new Date()): boolean {
  const criado = fromBackend(wf.created_at)
  return criado != null && dayjs(agora).diff(criado, "hour") < VINTE_E_QUATRO_HORAS
}

/**
 * "há 2 d" para a lista: `formatarInicio` foi feito para o início de uma
 * execução e passa a data por extenso depois de ontem — "alterado 4 set,
 * 03:00 por maria" lê pior que "alterado há 3 d por maria". A data volta
 * depois de um mês, quando "há 47 d" já não diz nada.
 */
export function formatarHa(iso: string | null | undefined, agora: Date = new Date()): string {
  const d = fromBackend(iso)
  if (!d) return "—"
  const ref = dayjs(agora)
  const minutos = ref.diff(d, "minute")
  if (minutos < 1) return "agora"
  if (minutos < 60) return `há ${minutos} min`
  const horas = ref.diff(d, "hour")
  if (horas < 24) return `há ${horas} h`
  const dias = ref.diff(d, "day")
  if (dias < 30) return `há ${dias} d`
  return `em ${formatarInicio(iso, agora)}`
}

type CamposDeAutoria = Pick<IWorkflow, "created_at" | "updated_at" | "created_by_username" | "updated_by_username">

/**
 * "alterado há 2 d por maria" — ou "criado há 3 h por joão" quando nunca foi
 * alterado depois de criado; sem nome (usuário apagado) fica só o quando.
 * Nulo quando a listagem não trouxe data nenhuma.
 */
export function textoDeAutoria(wf: CamposDeAutoria, agora: Date = new Date()): string | null {
  const criado = fromBackend(wf.created_at)
  const alterado = fromBackend(wf.updated_at)
  const referencia = alterado ?? criado
  if (!referencia) return null
  // Comparado por instante, não por string: o backend pode serializar as
  // duas datas com precisões diferentes.
  const ehCriacao = !alterado || !criado || alterado.valueOf() === criado.valueOf()
  const verbo = ehCriacao ? "criado" : "alterado"
  const quem = ehCriacao ? wf.created_by_username : wf.updated_by_username
  const quando = formatarHa(ehCriacao ? wf.created_at ?? wf.updated_at : wf.updated_at, agora)
  return quem ? `${verbo} ${quando} por ${quem}` : `${verbo} ${quando}`
}

/**
 * A linha de um workflow na tela de Projetos (docs/specs/projetos.md §3.9).
 *
 * Memoizada de propósito, como o card que ela substitui: as linhas nascem
 * dentro de um `.map`, e QUALQUER render da página (uma tecla na busca, o
 * poll de execuções ativas, o relógio das métricas) recriaria a lista inteira
 * — cada linha com um DropdownMenu do Radix dentro. Com props primitivas e
 * callbacks de identidade estável, só a linha que mudou re-renderiza. Quem
 * compõe a página é responsável por memoizar `gatilho`, `resumoDoAgendamento`
 * e `comoAnda` por workflow.
 */
export const LinhaWorkflow = React.memo(function LinhaWorkflow({
  workflow, gatilho, resumoDoAgendamento, comoAnda, grupos,
  canEdit, canExecute, canManage, podeMover, hasDnd, isDragging, executando, duplicando, runIdVivo,
  onOpen, onPrefetch, onRun, onVerExecucao, onAtivar, onDesativar, onConfigure, onPortal, onMove,
  onDuplicate, onDelete, onViewRuns, onAddToGroup, onRemoveFromGroup, onDragStart, onDragEnd,
}: LinhaWorkflowProps) {
  const id = workflow.id_hash
  const nome = workflow.name
  const inativo = !workflow.flag_ative
  const emExecucao = comoAnda.tipo === "executando"
  // Viewer vê tudo sem alça (spec §3.10): o `hasDnd` diz que há grupos, o
  // `canEdit` diz que a pessoa pode mover.
  const arrastavel = hasDnd && canEdit
  const Icone = ICONE_DO_GATILHO[gatilho.tipo]
  const subfluxo = gatilho.tipo === "subfluxo"
  const portal = temPortal(workflow)
  const novo = ehNovo(workflow)
  const autoria = textoDeAutoria(workflow)
  // Um único caminho para "Mover para grupo": todos os grupos menos o atual.
  const destinos = grupos.filter(g => g.id_hash !== workflow.group_id)

  const metadados: ReactNode[] = [
    <span key="gatilho" className="font-medium text-foreground">{gatilho.rotulo}</span>,
  ]
  if (resumoDoAgendamento) metadados.push(...partesDoAgendamento(resumoDoAgendamento))
  if (autoria) metadados.push(autoria)

  const temMovimentacao = (canEdit && destinos.length > 0) || (canEdit && !!workflow.group_id)
    || (canManage && podeMover && !!workflow.workspace_id)

  return (
    // A linha inteira responde ao clique (mouse e toque); o alvo de teclado e
    // de leitor de tela é o botão no nome. Sem `role`: um `role="button"` aqui
    // apagaria o gatilho, o agendamento e o "como anda" para quem ouve a lista.
    <div
      draggable={arrastavel}
      // `setData` é obrigatório para o Firefox iniciar o arrasto; o valor não
      // é usado (o alvo lê o id do estado), mas sem ele o `dragstart` é ignorado.
      onDragStart={arrastavel ? e => { e.dataTransfer?.setData("text/plain", id); onDragStart(id) } : undefined}
      onDragEnd={arrastavel ? onDragEnd : undefined}
      onClick={() => onOpen(id)}
      // O editor é a rota mais pesada da aplicação e a lista navega por
      // `onClick`, não por <Link> — o App Router nunca a pré-carregaria
      // sozinho. O ponteiro sobre a linha é o aviso mais antecipado do clique.
      onPointerEnter={() => onPrefetch(id)}
      data-workflow={id}
      className={cn(
        "grid min-h-14 cursor-pointer items-start gap-x-3 gap-y-1.5 rounded-lg border bg-card px-3 py-2 shadow-xs",
        "transition-[background-color,opacity] hover:bg-accent/40 focus-within:bg-accent/40",
        "max-md:grid-cols-[34px_minmax(0,1fr)_auto]",
        arrastavel
          ? "md:grid-cols-[14px_34px_minmax(0,1fr)_260px_auto]"
          : "md:grid-cols-[34px_minmax(0,1fr)_260px_auto]",
        "md:items-center",
        isDragging && "opacity-40",
      )}
    >
      {arrastavel && (
        <span
          aria-hidden="true"
          title="Arraste para mover para um grupo"
          className="hidden cursor-grab self-center text-muted-foreground/30 transition-colors hover:text-muted-foreground/70 active:cursor-grabbing md:flex"
        >
          <TbGripVertical size={14} />
        </span>
      )}

      {/* Tile do gatilho, com o ponto de estado no canto: verde ativo, cinza
          inativo, azul pulsando em execução. */}
      <span
        title={gatilho.rotulo}
        className={cn(
          "relative flex size-[34px] shrink-0 items-center justify-center rounded-lg",
          subfluxo ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400" : "bg-muted text-muted-foreground",
          // Inativo fica esmaecido (o selo "Inativo" e o ponto cinza reforçam);
          // "como anda" e as ações ficam legíveis — a falha de um inativo ainda
          // precisa ser lida.
          inativo && "opacity-60",
        )}
      >
        <Icone size={17} aria-hidden="true" />
        <span className="sr-only">{gatilho.rotulo}</span>
        <PontoDeEstado inativo={inativo} emExecucao={emExecucao} />
      </span>

      <div className={cn("flex min-w-0 flex-col gap-0.5", inativo && "opacity-60")}>
        <div className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5">
          <button
            type="button"
            onClick={e => { e.stopPropagation(); onOpen(id) }}
            aria-label={`Abrir ${nome} no editor`}
            title={nome}
            className="min-w-0 max-w-full truncate rounded-sm text-left text-sm font-medium outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            {nome}
          </button>
          <SeloSubFluxo workflow={workflow} />
          <SeloAssistente origem={workflow.origem} />
          {portal && (
            <Selo className="bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-400">
              {workflow.portal_access === "public"
                ? <><TbWorld size={11} aria-hidden="true" /> Portal público</>
                : <><TbLock size={11} aria-hidden="true" /> Portal privado</>}
            </Selo>
          )}
          {inativo && <Selo className="bg-muted text-muted-foreground">Inativo</Selo>}
          {novo && <Selo className="bg-primary/10 text-primary">Novo</Selo>}
        </div>
        {workflow.description && (
          <p className="truncate text-xs text-muted-foreground max-md:hidden" title={workflow.description}>
            {workflow.description}
          </p>
        )}
        {/* Cada parte leva o próprio separador, preso a ela por um espaço
            inquebrável: numa linha que quebra (telefone), o "·" nunca fica
            sozinho no começo da linha seguinte. O espaço normal antes dele
            é o que o texto copiado precisa para sair "Agendado · todo dia". */}
        <p className="flex min-w-0 flex-wrap items-center gap-x-1 text-xs text-muted-foreground">
          {metadados.map((parte, i) => (
            <span key={i} className="min-w-0">
              {i > 0 && <span aria-hidden="true">{" ·\u00A0"}</span>}
              {parte}
            </span>
          ))}
        </p>
      </div>

      {/* No telefone, "como anda" desce para baixo do principal, alinhado
          com ele (a coluna do tile fica vazia). */}
      <ComoAndaCelula comoAnda={comoAnda} className="max-md:col-span-2 max-md:col-start-2 max-md:row-start-2" />

      <div
        className="flex shrink-0 items-center gap-1 self-center max-md:col-start-3 max-md:row-start-1"
        onClick={e => e.stopPropagation()}
      >
        <AcaoPrincipal
          nome={nome}
          inativo={inativo}
          subfluxo={subfluxo}
          canEdit={canEdit}
          canExecute={canExecute}
          executando={executando}
          runIdVivo={runIdVivo}
          onRun={() => onRun(workflow)}
          onVerExecucao={onVerExecucao}
          onAtivar={() => onAtivar(workflow)}
        />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Mais ações de ${nome}`}
              title="Mais ações"
              className="size-8 text-muted-foreground max-md:size-10"
            >
              <TbDotsVertical size={16} aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          {/* O conteúdo vive num portal, mas os eventos do React sobem pela
              árvore de componentes: sem isto, escolher um item abriria o
              editor pelo `onClick` da linha. */}
          <DropdownMenuContent align="end" onClick={e => e.stopPropagation()}>
            <DropdownMenuItem onClick={() => onOpen(id)}>
              <TbPencil aria-hidden="true" /> Abrir no editor
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onViewRuns(id)}>
              <TbHistory aria-hidden="true" /> Ver execuções
            </DropdownMenuItem>
            {canEdit && (
              <DropdownMenuItem disabled={duplicando} onClick={() => onDuplicate(workflow)}>
                <TbCopy aria-hidden="true" /> {duplicando ? "Duplicando…" : "Duplicar"}
              </DropdownMenuItem>
            )}
            {canEdit && (
              <DropdownMenuItem onClick={() => onConfigure(id)}>
                <TbSettings aria-hidden="true" /> Configurar
              </DropdownMenuItem>
            )}
            {/* `has_publish_map` vem da própria listagem; a condição não pode
                ler `definition.nodes`, que o schema leve não traz. */}
            {canEdit && workflow.has_publish_map && (
              <DropdownMenuItem onClick={() => onPortal(workflow)}>
                <TbWorld aria-hidden="true" /> Configurar portal
              </DropdownMenuItem>
            )}
            {temMovimentacao && <DropdownMenuSeparator />}
            {canEdit && destinos.length > 0 && (
              <DropdownMenuSub>
                <DropdownMenuSubTrigger className="gap-2 [&_svg]:size-4 [&_svg]:text-muted-foreground">
                  <TbFolders aria-hidden="true" /> Mover para grupo
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  {destinos.map(g => (
                    <DropdownMenuItem key={g.id_hash} onClick={() => onAddToGroup(id, g.id_hash)}>
                      {g.name}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuSubContent>
              </DropdownMenuSub>
            )}
            {canEdit && workflow.group_id && (
              <DropdownMenuItem onClick={() => onRemoveFromGroup(id, workflow.group_id!)}>
                <TbFolderOpen aria-hidden="true" /> Remover do grupo
              </DropdownMenuItem>
            )}
            {/* Mover atravessa a fronteira de tenant e exige admin/owner nos
                DOIS workspaces — por isso fora do gate `canEdit`. `workspace_id`
                é exigido porque a listagem também traz workflows legados sem
                workspace: para eles a rota responderia 403. */}
            {canManage && podeMover && workflow.workspace_id && (
              <DropdownMenuItem onClick={() => onMove(workflow)}>
                <TbArrowsExchange aria-hidden="true" /> Mover para workspace
              </DropdownMenuItem>
            )}
            {canEdit && <DropdownMenuSeparator />}
            {canEdit && (inativo ? (
              <DropdownMenuItem onClick={() => onAtivar(workflow)}>
                <TbToggleRight aria-hidden="true" /> Ativar
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem onClick={() => onDesativar(workflow)}>
                <TbToggleLeft aria-hidden="true" /> Desativar…
              </DropdownMenuItem>
            ))}
            {canEdit && (
              <DropdownMenuItem variant="destructive" onClick={() => onDelete(id)}>
                <TbTrash aria-hidden="true" /> Excluir…
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
})

/** Descrição do agendamento e o que vem depois dela: a próxima, a pausa (âmbar) ou "calculando…". */
function partesDoAgendamento(resumo: ResumoDoAgendamento): ReactNode[] {
  const partes: ReactNode[] = [
    resumo.descricaoCrua
      ? <code key="descricao" className="rounded bg-muted px-1 font-mono text-[11px]">{resumo.descricao}</code>
      : <span key="descricao">{resumo.descricao}</span>,
  ]
  if (resumo.estado === "ativo") {
    partes.push(<span key="proxima">próxima {resumo.proxima}</span>)
  } else if (resumo.estado === "pausado") {
    partes.push(
      <span key="pausado" className="font-medium text-amber-700 dark:text-amber-400">
        Agendamento pausado{resumo.motivoPausa ? ` (${resumo.motivoPausa})` : ""}
      </span>,
    )
  } else {
    partes.push(<span key="calculando">próxima: calculando…</span>)
  }
  return partes
}

/**
 * O botão da vez, no mesmo lugar em toda linha: "Ver execução" quando há run
 * vivo (é o que a pessoa está esperando), "Ativar" na inativa (o interruptor
 * saiu do card e a ação segura fica a um clique), "Executar" no resto.
 */
function AcaoPrincipal({
  nome, inativo, subfluxo, canEdit, canExecute, executando, runIdVivo, onRun, onVerExecucao, onAtivar,
}: {
  nome: string
  inativo: boolean
  subfluxo: boolean
  canEdit: boolean
  canExecute: boolean
  executando: boolean
  runIdVivo: string | null
  onRun: () => void
  onVerExecucao: (runId: string) => void
  onAtivar: () => void
}) {
  const classe = "size-8 max-md:size-10"
  if (runIdVivo) {
    return (
      <Button
        variant="outline"
        size="icon"
        aria-label={`Ver execução de ${nome}`}
        title="Ver execução"
        onClick={() => onVerExecucao(runIdVivo)}
        className={cn(classe, "text-blue-700 dark:text-blue-400")}
      >
        <TbHistory size={16} aria-hidden="true" />
      </Button>
    )
  }
  if (inativo && canEdit) {
    return (
      <Button
        variant="outline"
        size="icon"
        aria-label={`Ativar ${nome}`}
        title="Ativar"
        onClick={onAtivar}
        className={classe}
      >
        <TbToggleRight size={16} aria-hidden="true" />
      </Button>
    )
  }
  if (!inativo && canExecute) {
    return (
      <Button
        variant="outline"
        size="icon"
        aria-label={`Executar ${nome} agora`}
        // O sub-fluxo continua clicável (há quem o teste sozinho), mas
        // apagado e com o aviso: o run que ele dispara não faz o esperado.
        title={subfluxo ? TITULO_DO_SUBFLUXO : "Executar agora"}
        onClick={onRun}
        disabled={executando}
        className={cn(classe, subfluxo && "opacity-45")}
      >
        <TbPlayerPlay size={16} aria-hidden="true" />
      </Button>
    )
  }
  // Sem ação (viewer, ou inativo sem permissão de editar): o espaço fica,
  // para o menu ⋯ alinhar de linha em linha.
  return <span aria-hidden="true" className={classe} />
}

function PontoDeEstado({ inativo, emExecucao }: { inativo: boolean; emExecucao: boolean }) {
  const posicao = "absolute -right-0.5 -bottom-0.5 size-2.5 rounded-full border-2 border-card"
  if (emExecucao) {
    return (
      <span aria-hidden="true" className={cn(posicao, "bg-blue-500")}>
        <span className="absolute inset-0 rounded-full bg-blue-500 opacity-60 motion-safe:animate-ping" />
      </span>
    )
  }
  return (
    <span
      aria-hidden="true"
      className={cn(posicao, inativo ? "bg-muted-foreground/40" : "bg-green-500")}
    />
  )
}

function Selo({ className, children }: { className: string; children: ReactNode }) {
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1 rounded px-1.5 py-px text-[10px] font-medium", className)}>
      {children}
    </span>
  )
}
