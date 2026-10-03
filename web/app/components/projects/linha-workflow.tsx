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
import type { HowItsGoing } from "./como-anda"
import { hasPortal } from "./filtros"
import type { Gatilho, ScheduleSummary, TriggerKind } from "./gatilho"
import { SeloSubFluxo } from "./selo-subfluxo"

export interface WorkflowRowProps {
  workflow: IWorkflow
  gatilho: Gatilho
  resumoDoAgendamento: ScheduleSummary | null
  comoAnda: HowItsGoing
  grupos: IWorkflowGroup[]
  canEdit: boolean
  canExecute: boolean
  canManage: boolean
  /** There is some eligible destination workspace for "Mover para workspace". */
  podeMover: boolean
  /** Dragging only exists from the first group created on. */
  hasDnd: boolean
  isDragging: boolean
  /** Firing or resolving this workflow's parameters. */
  executando: boolean
  duplicando: boolean
  /** `run_id` of the live run (`ActiveRunsContext`): Executar becomes "Ver execução". */
  runIdVivo: string | null
  onOpen: (id: string) => void
  /** Warms up the editor route before the click (see `onPointerEnter` below). */
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

const TRIGGER_ICON: Record<TriggerKind, IconType> = {
  agendado: TbClock,
  webhook: TbBolt,
  arquivo: TbFile,
  geofence: TbMapPin,
  manual: TbPlayerPlay,
  subfluxo: TbSubtask,
}

const SUBFLOW_TITLE = "Sub-fluxo: executar sozinho normalmente não faz o esperado"
const TWENTY_FOUR_HOURS = 24

/** Created less than 24 h ago: gets the "Novo" badge. Without `created_at` there is no way to tell. */
export function ehNovo(wf: Pick<IWorkflow, "created_at">, agora: Date = new Date()): boolean {
  const criado = fromBackend(wf.created_at)
  return criado != null && dayjs(agora).diff(criado, "hour") < TWENTY_FOUR_HOURS
}

/**
 * "há 2 d" for the list: `formatarInicio` was made for the start of a run and
 * switches to the spelled-out date after yesterday — "alterado 4 set, 03:00
 * por maria" reads worse than "alterado há 3 d por maria". The date comes back
 * after a month, when "há 47 d" no longer says anything.
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

type AuthorshipFields = Pick<IWorkflow, "created_at" | "updated_at" | "created_by_username" | "updated_by_username">

/**
 * "alterado há 2 d por maria" — or "criado há 3 h por joão" when it was never
 * changed after creation; with no name (deleted user) only the when remains.
 * Null when the listing brought no date at all.
 */
export function textoDeAutoria(wf: AuthorshipFields, agora: Date = new Date()): string | null {
  const criado = fromBackend(wf.created_at)
  const alterado = fromBackend(wf.updated_at)
  const referencia = alterado ?? criado
  if (!referencia) return null
  // Compared by instant, not by string: the backend may serialize the two
  // dates with different precisions.
  const isCreation = !alterado || !criado || alterado.valueOf() === criado.valueOf()
  const verbo = isCreation ? "criado" : "alterado"
  const quem = isCreation ? wf.created_by_username : wf.updated_by_username
  const quando = formatarHa(isCreation ? wf.created_at ?? wf.updated_at : wf.updated_at, agora)
  return quem ? `${verbo} ${quando} por ${quem}` : `${verbo} ${quando}`
}

/**
 * A workflow's row on the Projects screen (docs/specs/projects.md §3.9).
 *
 * Memoized on purpose, like the card it replaces: the rows are born inside a
 * `.map`, and ANY render of the page (a search keystroke, the active-runs
 * poll, the metrics clock) would recreate the whole list — each row with a
 * Radix DropdownMenu inside. With primitive props and stable-identity
 * callbacks, only the row that changed re-renders. The page composer is
 * responsible for memoizing `gatilho`, `resumoDoAgendamento` and `comoAnda`
 * per workflow.
 */
export const LinhaWorkflow = React.memo(function LinhaWorkflow({
  workflow, gatilho, resumoDoAgendamento, comoAnda, grupos,
  canEdit, canExecute, canManage, podeMover, hasDnd, isDragging, executando, duplicando, runIdVivo,
  onOpen, onPrefetch, onRun, onVerExecucao, onAtivar, onDesativar, onConfigure, onPortal, onMove,
  onDuplicate, onDelete, onViewRuns, onAddToGroup, onRemoveFromGroup, onDragStart, onDragEnd,
}: WorkflowRowProps) {
  const id = workflow.id_hash
  const nome = workflow.name
  const inativo = !workflow.flag_ative
  const emExecucao = comoAnda.tipo === "executando"
  // A viewer sees everything without a handle (spec §3.10): `hasDnd` says there
  // are groups, `canEdit` says the person can move.
  const arrastavel = hasDnd && canEdit
  const Icone = TRIGGER_ICON[gatilho.tipo]
  const subfluxo = gatilho.tipo === "subfluxo"
  const portal = hasPortal(workflow)
  const novo = ehNovo(workflow)
  const autoria = textoDeAutoria(workflow)
  // A single path for "Mover para grupo": all groups except the current one.
  const destinos = grupos.filter(g => g.id_hash !== workflow.group_id)

  const metadados: ReactNode[] = [
    <span key="gatilho" className="font-medium text-foreground">{gatilho.rotulo}</span>,
  ]
  if (resumoDoAgendamento) metadados.push(...scheduleParts(resumoDoAgendamento))
  if (autoria) metadados.push(autoria)

  const hasMoveActions = (canEdit && destinos.length > 0) || (canEdit && !!workflow.group_id)
    || (canManage && podeMover && !!workflow.workspace_id)

  return (
    // The whole row responds to clicks (mouse and touch); the keyboard and
    // screen-reader target is the button on the name. No `role`: a
    // `role="button"` here would erase the trigger, the schedule and the "como
    // anda" for those who listen to the list.
    <div
      draggable={arrastavel}
      // `setData` is required for Firefox to start the drag; the value is not
      // used (the target reads the id from state), but without it `dragstart` is ignored.
      onDragStart={arrastavel ? e => { e.dataTransfer?.setData("text/plain", id); onDragStart(id) } : undefined}
      onDragEnd={arrastavel ? onDragEnd : undefined}
      onClick={() => onOpen(id)}
      // The editor is the heaviest route in the application and the list navigates
      // via `onClick`, not via <Link> — the App Router would never prefetch it
      // on its own. The pointer over the row is the earliest hint of the click.
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

      {/* Trigger tile, with the state dot in the corner: green active, gray
          inactive, pulsing blue while running. */}
      <span
        title={gatilho.rotulo}
        className={cn(
          "relative flex size-[34px] shrink-0 items-center justify-center rounded-lg",
          subfluxo ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400" : "bg-muted text-muted-foreground",
          // Inactive is dimmed (the "Inativo" badge and the gray dot reinforce it);
          // "como anda" and the actions stay legible — an inactive workflow's
          // failure still needs to be read.
          inativo && "opacity-60",
        )}
      >
        <Icone size={17} aria-hidden="true" />
        <span className="sr-only">{gatilho.rotulo}</span>
        <StateDot inativo={inativo} emExecucao={emExecucao} />
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
            <Badge className="bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-400">
              {workflow.portal_access === "public"
                ? <><TbWorld size={11} aria-hidden="true" /> Portal público</>
                : <><TbLock size={11} aria-hidden="true" /> Portal privado</>}
            </Badge>
          )}
          {inativo && <Badge className="bg-muted text-muted-foreground">Inativo</Badge>}
          {novo && <Badge className="bg-primary/10 text-primary">Novo</Badge>}
        </div>
        {workflow.description && (
          <p className="truncate text-xs text-muted-foreground max-md:hidden" title={workflow.description}>
            {workflow.description}
          </p>
        )}
        {/* Each part carries its own separator, tied to it by a non-breaking
            space: in a line that wraps (phone), the "·" is never left alone
            at the start of the next line. The normal space before it is what
            the copied text needs to come out as "Agendado · todo dia". */}
        <p className="flex min-w-0 flex-wrap items-center gap-x-1 text-xs text-muted-foreground">
          {metadados.map((parte, i) => (
            <span key={i} className="min-w-0">
              {i > 0 && <span aria-hidden="true">{" ·\u00A0"}</span>}
              {parte}
            </span>
          ))}
        </p>
      </div>

      {/* On the phone, "como anda" moves down below the main block, aligned
          with it (the tile column stays empty). */}
      <ComoAndaCelula comoAnda={comoAnda} className="max-md:col-span-2 max-md:col-start-2 max-md:row-start-2" />

      <div
        className="flex shrink-0 items-center gap-1 self-center max-md:col-start-3 max-md:row-start-1"
        onClick={e => e.stopPropagation()}
      >
        <PrimaryAction
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
          {/* The content lives in a portal, but React events bubble up through
              the component tree: without this, picking an item would open the
              editor via the row's `onClick`. */}
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
            {/* `has_publish_map` comes from the listing itself; the condition must not
                read `definition.nodes`, which the light schema does not carry. */}
            {canEdit && workflow.has_publish_map && (
              <DropdownMenuItem onClick={() => onPortal(workflow)}>
                <TbWorld aria-hidden="true" /> Configurar portal
              </DropdownMenuItem>
            )}
            {hasMoveActions && <DropdownMenuSeparator />}
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
            {/* Moving crosses the tenant boundary and requires admin/owner in
                BOTH workspaces — hence outside the `canEdit` gate. `workspace_id`
                is required because the listing also brings legacy workflows with
                no workspace: for them the route would answer 403. */}
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

/** Schedule description and what comes after it: the next run, the pause (amber) or "calculando…". */
function scheduleParts(resumo: ScheduleSummary): ReactNode[] {
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
 * The button of the moment, in the same place on every row: "Ver execução"
 * when there is a live run (it is what the person is waiting for), "Ativar" on
 * the inactive one (the switch left the card and the safe action stays one
 * click away), "Executar" on the rest.
 */
function PrimaryAction({
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
        // The sub-workflow stays clickable (some people test it on its own), but
        // dimmed and with the warning: the run it fires does not do what is expected.
        title={subfluxo ? SUBFLOW_TITLE : "Executar agora"}
        onClick={onRun}
        disabled={executando}
        className={cn(classe, subfluxo && "opacity-45")}
      >
        <TbPlayerPlay size={16} aria-hidden="true" />
      </Button>
    )
  }
  // No action (viewer, or inactive without edit permission): the space stays,
  // so the ⋯ menu lines up from row to row.
  return <span aria-hidden="true" className={classe} />
}

function StateDot({ inativo, emExecucao }: { inativo: boolean; emExecucao: boolean }) {
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

function Badge({ className, children }: { className: string; children: ReactNode }) {
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1 rounded px-1.5 py-px text-[10px] font-medium", className)}>
      {children}
    </span>
  )
}
