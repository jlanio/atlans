"use client"

import {
  Suspense, useCallback, useDeferredValue, useEffect, useMemo, useRef, useState, type DragEvent, type ReactNode,
} from "react"
import { TbFolderOpen, TbFolderPlus, TbGripVertical } from "react-icons/tb"
import type { IParamSchema, IWorkflow, IWorkflowGroup } from "@/service/types"
import { GisFlowService } from "@/service/GisFlowService"
import { useViewTransitionRouter } from "@/app/hooks/useViewTransition"
import { moveTargets, useWorkspace } from "@/context/WorkspaceContext"
import { useActiveRuns, type RunningRun } from "@/context/ActiveRunsContext"
import { createToast } from "@/utils/createToast"
import { cn } from "@/lib/utils"
import PageRoot from "../page-root"
import { Button } from "../ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../ui/dialog"
import ExecuteParamsDialog from "@/app/components/workflow/execute-params-dialog"
import PortalSettingsDialog from "@/app/components/workflow/PortalSettingsDialog"
import ConfigureProject from "./dialog-content/configure-project"
import CreateGroup from "./dialog-content/create-group"
import DeleteProject from "./dialog-content/delete-project"
import MoveWorkflowDialog from "./dialog-content/move-workflow"
import RenameGroup from "./dialog-content/rename-group"
import { CabecalhoDeProjetos, type HeaderCounts } from "./cabecalho"
import { derivarComoAnda, type HowItsGoing } from "./como-anda"
import { ConfirmarDesativar } from "./confirmar-desativar"
import { ErroDeCarga, MetricasIndisponiveis, SemResultado, SkeletonDeProjetos, VazioPrimeiroUso } from "./estados"
import { BarraDeFiltros } from "./filtros-barra"
import { matchesSearch, contarPorFiltro, ordenar, predicadoDoFiltro, type FilterContext } from "./filtros"
import { derivarGatilho, resumirAgendamento, type Gatilho, type ScheduleSummary } from "./gatilho"
import { GrupoSecao, textoDaContagemDoGrupo } from "./grupo-secao"
import { chaveDosColapsados, saveCollapsed, readCollapsed } from "./grupos-colapsados"
import { LinhaWorkflow } from "./linha-workflow"
import { moverGrupo } from "./ordem-dos-grupos"
import { filtrosAtivos } from "./projetos-url"
import { useProjetosDados } from "./use-projetos-dados"
import { useProjetosUrl } from "./use-projetos-url"

/**
 * Projects (docs/specs/projects.md §3.1). This file only orchestrates: the
 * search/chip/order state lives in the URL, the data in the hook, the live runs
 * in `ActiveRunsContext`, the permissions in `WorkspaceContext`; the pure logic
 * lives in the neighboring modules and each block decides its own text.
 *
 * The `Suspense` is required by `useSearchParams` in the static build — same
 * reason as the History page.
 */
export default function ProjectActions() {
  return (
    <Suspense fallback={<PageRoot><SkeletonDeProjetos /></PageRoot>}>
      <Projetos />
    </Suspense>
  )
}

/** What each row needs and that only changes when the data changes (not on every search keystroke). */
interface Derived {
  gatilho: Gatilho
  resumo: ScheduleSummary | null
  comoAnda: HowItsGoing
}

function Projetos() {
  const router = useViewTransitionRouter()
  const { current: currentWorkspace, canEdit, canExecute, canManage, workspaces } = useWorkspace()
  // Runs in progress (global polling): they beat the metrics for being
  // fresher, and they are what turns Executar into "Ver execução".
  const { runningRuns, refresh: refreshActiveRuns } = useActiveRuns()
  const { estado, atualizar, limparFiltros } = useProjetosUrl()
  const dados = useProjetosDados()
  const { workflows, grupos, metricas, metricasIndisponiveis, definirWorkflows, definirGrupos, recarregar } = dados

  // ── Collapsed groups ───────────────────────────────────────────────────────
  // The collapsed state survives a reload — without it, whoever collapses the
  // groups they do not use collapses everything again on every visit. The read
  // happens in an effect (and not in the initial `useState`) because
  // `localStorage` does not exist in the server render.
  const [recolhidos, setCollapsed] = useState<Set<string>>(new Set())
  const collapseKey = chaveDosColapsados(currentWorkspace?.id_hash)
  useEffect(() => {
    setCollapsed(readCollapsed(collapseKey))
  }, [collapseKey])

  const toggleGroup = useCallback((groupId: string) => {
    setCollapsed(prev => {
      const next = new Set(prev)
      if (next.has(groupId)) next.delete(groupId)
      else next.add(groupId)
      saveCollapsed(collapseKey, next)
      return next
    })
  }, [collapseKey])

  function collapseAll() {
    const next = new Set(grupos.map(g => g.id_hash))
    saveCollapsed(collapseKey, next)
    setCollapsed(next)
  }

  function expandAll() {
    const next = new Set<string>()
    saveCollapsed(collapseKey, next)
    setCollapsed(next)
  }

  const todosRecolhidos = grupos.length > 0 && grupos.every(g => recolhidos.has(g.id_hash))
  // ──────────────────────────────────────────────────────────────────────────

  // ── Per-workflow derivations ───────────────────────────────────────────────
  const runByHash = useMemo(
    () => new Map<string, RunningRun>(runningRuns.map(r => [r.workflowHash, r])),
    [runningRuns],
  )
  const groupsById = useMemo(() => new Map(grupos.map(g => [g.id_hash, g])), [grupos])

  // Minute clock for the relative texts ("há 4 min"). Without it, freshness
  // depended on a SIDE EFFECT of the metrics poll changing the identity of
  // `metricas` — if the poll changed nothing, the times froze. It only advances
  // with the tab visible (nobody reads a hidden tab) and a return to focus
  // recomputes right away, so "há N min" does not come back stale.
  const [minuto, setMinute] = useState(0)
  useEffect(() => {
    const bump = () => { if (document.visibilityState === "visible") setMinute(m => m + 1) }
    const timer = setInterval(bump, 60_000)
    document.addEventListener("visibilitychange", bump)
    return () => { clearInterval(timer); document.removeEventListener("visibilitychange", bump) }
  }, [])

  // Trigger, schedule and "como anda" of each row, recomputed on every change
  // of DATA or of the minute clock — and not on every render: the rows are
  // memoized and receive these objects by identity, so a keystroke in the
  // search must not recreate them. `minuto` keeps the relative times fresh on
  // its own, independent of the metrics poll cadence.
  const derivados = useMemo(() => {
    const agora = new Date()
    const mapa = new Map<string, Derived>()
    for (const wf of workflows) {
      mapa.set(wf.id_hash, {
        gatilho: derivarGatilho(wf),
        resumo: resumirAgendamento(wf.schedule, wf.flag_ative, agora),
        comoAnda: derivarComoAnda(wf, metricas?.get(wf.id_hash), runByHash.get(wf.id_hash), metricasIndisponiveis, agora),
      })
    }
    return mapa
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflows, metricas, runByHash, metricasIndisponiveis, minuto])

  const contexto = useMemo<FilterContext>(() => {
    const comoAndaPorHash = new Map<string, HowItsGoing>()
    const resumoDoAgendamentoPorHash = new Map<string, ScheduleSummary | null>()
    for (const [hash, d] of derivados) {
      comoAndaPorHash.set(hash, d.comoAnda)
      resumoDoAgendamentoPorHash.set(hash, d.resumo)
    }
    return { comoAndaPorHash, resumoDoAgendamentoPorHash }
  }, [derivados])

  // Chips and subtitle: always over the whole list.
  const contagens = useMemo(() => contarPorFiltro(workflows, contexto), [workflows, contexto])
  // ──────────────────────────────────────────────────────────────────────────

  // ── Search, chip, order ────────────────────────────────────────────────────
  // PERF: useDeferredValue — the field responds immediately while the
  // filtering is deferred to a low-priority transition. Avoids the caret
  // stalling while typing in large lists.
  const deferredQuery = useDeferredValue(estado.q)
  const sliceActive = filtrosAtivos({ ...estado, q: deferredQuery }) > 0

  const visiveis = useMemo(() => {
    const matchesFilter = predicadoDoFiltro(estado.filtro, contexto)
    return workflows.filter(wf => matchesSearch(wf, groupsById, deferredQuery) && matchesFilter(wf))
  }, [workflows, estado.filtro, contexto, groupsById, deferredQuery])

  // How many would match the search alone: the empty state's "Há N com «q» sem o filtro".
  const searchOnly = useMemo(
    () => workflows.filter(wf => matchesSearch(wf, groupsById, deferredQuery)).length,
    [workflows, groupsById, deferredQuery],
  )

  const byGroup = useMemo(() => {
    const mapa = new Map<string, IWorkflow[]>()
    for (const wf of visiveis) {
      if (!wf.group_id) continue
      const lista = mapa.get(wf.group_id) ?? []
      lista.push(wf)
      mapa.set(wf.group_id, lista)
    }
    for (const [id, lista] of mapa) mapa.set(id, ordenar(lista, estado.ordem, contexto))
    return mapa
  }, [visiveis, estado.ordem, contexto])

  const ungrouped = useMemo(
    () => ordenar(visiveis.filter(wf => !wf.group_id), estado.ordem, contexto),
    [visiveis, estado.ordem, contexto],
  )

  // Count in each section's header: of the WHOLE group, not the slice —
  // counted here, and not via `workflow_count`, because the local list already
  // reflects the optimistic moves before the server responds.
  const totais = useMemo(() => {
    const mapa = new Map<string | null, { total: number; ativos: number }>()
    for (const wf of workflows) {
      const chave = wf.group_id ?? null
      const t = mapa.get(chave) ?? { total: 0, ativos: 0 }
      t.total++
      if (wf.flag_ative) t.ativos++
      mapa.set(chave, t)
    }
    return mapa
  }, [workflows])
  const ungroupedTotal = totais.get(null) ?? { total: 0, ativos: 0 }

  // With an active search or chip, groups with no matching row disappear;
  // with no slice, all appear (including empty ones). Memoized so it does not
  // re-filter on every render (e.g. every search keystroke).
  const visibleGroups = useMemo(
    () => sliceActive
      ? grupos.filter(g => (byGroup.get(g.id_hash)?.length ?? 0) > 0)
      : grupos,
    [sliceActive, grupos, byGroup],
  )
  // ──────────────────────────────────────────────────────────────────────────

  // ── Quick run ──────────────────────────────────────────────────────────────
  const [runningId, setRunningId] = useState<string | null>(null)
  const [preparingId, setPreparingId] = useState<string | null>(null)
  // Target of the parameters dialog: the schema comes along because the LISTING
  // does not carry it (see handleRunClick).
  const [executeTarget, setExecuteTarget] =
    useState<{ project: IWorkflow; schema: Record<string, IParamSchema> } | null>(null)

  const handleRunWorkflow = useCallback(async (project: IWorkflow, inputs: Record<string, unknown> = {}) => {
    setExecuteTarget(null)
    setRunningId(project.id_hash)
    const res = await GisFlowService.executeWorkflow(project.id_hash, inputs, false)
    setRunningId(null)
    if (res?.error) {
      createToast.error("Erro ao executar workflow", res.error.message)
    } else {
      createToast.success(`Workflow "${project.name}" iniciado!`)
      // Updates the global runs indicator without waiting for the next poll.
      refreshActiveRuns()
    }
  }, [refreshActiveRuns])

  /**
   * `GET /workflows/` answers with the light schema (WorkflowListItem), which
   * does not carry `params_schema` — reading `project.params_schema` here was
   * ALWAYS undefined, and workflows with required inputs were fired with `{}`
   * and failed on the executor. The schema is fetched on click, a single
   * request, instead of fattening the whole listing with a field almost no row uses.
   */
  const handleRunClick = useCallback(async (project: IWorkflow) => {
    // Its own state, not `runningId`: while the schema is being fetched the
    // workflow is NOT running yet, and the row's "em execução" dot would read
    // that wait as a run in progress.
    setPreparingId(project.id_hash)
    const res = await GisFlowService.getWorkflowById(project.id_hash)
    setPreparingId(null)
    // "Has no schema" and "could not find out whether it has one" are different
    // things: without this branch, a 500/timeout here fell into the else and
    // FIRED the workflow with empty inputs — exactly the failure that fetching
    // the schema came to fix, back through the error path and now worse,
    // because the user came to trust that the parameters dialog shows up when needed.
    if (res.error || !res.data) {
      createToast.error(
        "Não foi possível preparar a execução.",
        res.error?.message ?? "Falha ao ler os parâmetros do workflow. Tente de novo.",
      )
      return
    }
    const schema = res.data.params_schema
    if (schema && Object.keys(schema).length > 0) {
      setExecuteTarget({ project, schema })
    } else {
      handleRunWorkflow(project)
    }
  }, [handleRunWorkflow])
  // ──────────────────────────────────────────────────────────────────────────

  // ── Ativar / Desativar ─────────────────────────────────────────────────────
  const [deactivating, setDeactivating] = useState<IWorkflow | null>(null)

  // Reads the value from the row ITSELF instead of looking it up in the list,
  // and updates the state through a function: without this the callback closed
  // over `workflows` and changed identity on every server response — and the
  // rows' memo was worthless.
  const changeStatus = useCallback(async (workflow: IWorkflow, novo: boolean) => {
    const aplicar = (valor: boolean) => definirWorkflows(prev =>
      prev.map(p => p.id_hash === workflow.id_hash ? { ...p, flag_ative: valor } : p),
    )
    // Optimistic, with rollback: a status switch is the kind of change where
    // waiting for the server makes the row "snap back" under the cursor.
    aplicar(novo)
    const res = await GisFlowService.updateStatusWorkflow(workflow.id_hash, { flag_ative: novo })
    if (res.error) {
      aplicar(!novo)
      createToast.error("Erro ao atualizar status do workflow.", res.error.message)
      return
    }
    createToast.success(`«${workflow.name}» ${novo ? "ativado" : "desativado"}`)
  }, [definirWorkflows])

  // Activating is safe and stays one click away; Deactivating goes through the
  // confirmation that says what it pauses (`ConfirmarDesativar`).
  const ativar = useCallback((workflow: IWorkflow) => { void changeStatus(workflow, true) }, [changeStatus])
  const requestDeactivate = useCallback((workflow: IWorkflow) => setDeactivating(workflow), [])
  const confirmDeactivate = useCallback((workflow: IWorkflow) => {
    setDeactivating(null)
    void changeStatus(workflow, false)
  }, [changeStatus])
  // ──────────────────────────────────────────────────────────────────────────

  // ── Duplication ────────────────────────────────────────────────────────────
  const [duplicatingId, setDuplicatingId] = useState<string | null>(null)

  const handleDuplicate = useCallback(async (project: IWorkflow) => {
    setDuplicatingId(project.id_hash)
    const res = await GisFlowService.duplicateWorkflowById(project.id_hash)
    setDuplicatingId(null)

    if (res?.error) {
      createToast.error("Erro ao duplicar workflow", res.error.message)
      return
    }
    // Reloads instead of inserting the copy by hand: the backend picks the name
    // (it disambiguates when "Cópia de X" already exists) and the listing
    // carries fields the duplication response does not have.
    //
    // The notice is unconditional: the listing does not carry `definition`, so
    // there is no way to know from here whether this workflow has a schedule —
    // and the endpoint's rule applies to all (the copy is born with the
    // schedule turned off).
    createToast.success(
      `Cópia criada: "${res.data?.name}"`,
      "Se o original tinha agendamento, a cópia nasce com ele desligado.",
    )
    recarregar()
  }, [recarregar])
  // ──────────────────────────────────────────────────────────────────────────

  // ── Grupos: criar, renomear, excluir, mover para dentro/fora ───────────────
  const [newGroupModal, setNewGroupModal] = useState(false)
  const [editGroup, setEditGroup] = useState<IWorkflowGroup | null>(null)
  const [deleteGroupConfirm, setDeleteGroupConfirm] = useState<IWorkflowGroup | null>(null)

  function handleGroupCreated(group: IWorkflowGroup) {
    setNewGroupModal(false)
    definirGrupos(prev => [...prev, group])
  }

  // Deleting a group with workflows inside used to be BLOCKED, and the operator
  // had to empty the group by hand first. The FK is `ondelete='SET NULL'`: the
  // workflows just go back to having no group, none is deleted. The confirmation
  // says how many will be ungrouped — that is what justifies not blocking.
  async function handleDeleteGroup(groupId: string) {
    const result = await GisFlowService.deleteWorkflowGroup(groupId)
    if (result?.error) { createToast.error("Erro ao excluir grupo"); return }
    createToast.success("Grupo excluído.")
    definirGrupos(prev => prev.filter(g => g.id_hash !== groupId))
    // Mirrors the database's SET NULL: without this the rows would vanish from the
    // screen until the next load, because the group that held them no longer exists.
    definirWorkflows(prev => prev.map(p => p.group_id === groupId ? { ...p, group_id: null } : p))
  }

  async function handleRenameGroup(groupId: string, name: string, description: string | null) {
    const result = await GisFlowService.updateWorkflowGroup(groupId, { name, description })
    if (result?.error) { createToast.error("Erro ao renomear grupo"); return }
    definirGrupos(prev => prev.map(g => g.id_hash === groupId ? { ...g, name, description } : g))
  }

  // The handlers that go to the rows are `useCallback` with stable deps and
  // functional state updates: constant identity is what makes LinhaWorkflow's
  // React.memo worth anything.
  const handleAddToGroup = useCallback(async (workflowId: string, groupId: string) => {
    const result = await GisFlowService.addWorkflowToGroup(groupId, workflowId)
    if (result?.error) { createToast.error("Erro ao mover workflow para o grupo"); return }
    definirWorkflows(prev => prev.map(p => p.id_hash === workflowId ? { ...p, group_id: groupId } : p))
  }, [definirWorkflows])

  /** Changes group in one step: the backend overwrites `group_id`, so
   *  calling just "add" already removes it from the previous one. */
  const handleMoveToGroup = useCallback(async (project: IWorkflow, groupId: string) => {
    if (project.group_id === groupId) return
    await handleAddToGroup(project.id_hash, groupId)
  }, [handleAddToGroup])

  const handleRemoveFromGroup = useCallback(async (workflowId: string, groupId: string) => {
    const result = await GisFlowService.removeWorkflowFromGroup(groupId, workflowId)
    if (result?.error) { createToast.error("Erro ao remover workflow do grupo"); return }
    definirWorkflows(prev => prev.map(p => p.id_hash === workflowId ? { ...p, group_id: null } : p))
  }, [definirWorkflows])
  // ──────────────────────────────────────────────────────────────────────────

  // ── Drag and Drop ──────────────────────────────────────────────────────────
  // Two things drag — the row and the whole group — and the drop target is the
  // SAME rectangle. Without knowing what is in hand, dropping a group on another
  // would be interpreted as "move workflow to this group".
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [draggingGroupId, setDraggingGroupId] = useState<string | null>(null)
  const [dragOverGroupId, setDragOverGroupId] = useState<string | null>(null)
  const [dragOverUngrouped, setDragOverUngrouped] = useState(false)

  // `useCallback` because they go down as props to each memoized row.
  const handleDragStart = useCallback((workflowId: string) => {
    setDraggingId(workflowId)
  }, [])

  const handleDragEnd = useCallback(() => {
    setDraggingId(null)
    setDraggingGroupId(null)
    setDragOverGroupId(null)
    setDragOverUngrouped(false)
  }, [])

  /** Drops a group on another: the dragged one takes the target's position. */
  async function handleReorderGroups(targetId: string) {
    const sourceId = draggingGroupId
    handleDragEnd()
    if (!sourceId || sourceId === targetId) return

    const atual = grupos.map(g => g.id_hash)
    const ordem = moverGrupo(atual, sourceId, targetId)
    // Identity preserved when nothing moved — not worth a POST.
    if (ordem === atual) return

    // Optimistic, with rollback — same pattern as `changeStatus`. Order is the kind
    // of change where waiting for the server makes the item "snap back" under
    // the cursor, and that reads as a failure even when it worked.
    const anterior = grupos
    const byId = new Map(grupos.map(g => [g.id_hash, g]))
    definirGrupos(ordem.map(id => byId.get(id)!).filter(Boolean))

    const result = await GisFlowService.reorderWorkflowGroups(ordem)
    if (result?.error) {
      definirGrupos(anterior)
      createToast.error("Erro ao reordenar grupos")
    }
  }

  async function handleDropOnGroup(groupId: string) {
    if (draggingGroupId) return handleReorderGroups(groupId)
    if (!draggingId) return
    const workflow = workflows.find(p => p.id_hash === draggingId)
    handleDragEnd()
    if (!workflow) return
    // One call, not two: `add_workflow_to_group` overwrites the `group_id`.
    // Removing from the group first opened a window in which the workflow was
    // left with no group at all if the second call failed.
    await handleMoveToGroup(workflow, groupId)
  }

  async function handleDropOnUngrouped() {
    if (!draggingId) return
    const workflow = workflows.find(p => p.id_hash === draggingId)
    handleDragEnd()
    if (!workflow || !workflow.group_id) return
    await handleRemoveFromGroup(workflow.id_hash, workflow.group_id)
  }

  const arrastando = draggingId ? workflows.find(p => p.id_hash === draggingId) ?? null : null
  const removeZone = {
    onDragOver: (e: DragEvent<HTMLElement>) => { e.preventDefault(); setDragOverUngrouped(true) },
    onDragLeave: (e: DragEvent<HTMLElement>) => {
      if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOverUngrouped(false)
    },
    onDrop: () => { void handleDropOnUngrouped() },
  }
  // ──────────────────────────────────────────────────────────────────────────

  // ── Per-workflow dialogs ───────────────────────────────────────────────────
  const [deleteProjectId, setDeleteProjectId] = useState<string | null>(null)
  const [configureProjectId, setConfigureProjectId] = useState<string | null>(null)
  const [portalDialogProject, setPortalDialogProject] = useState<IWorkflow | null>(null)
  const [moveDialogProject, setMoveDialogProject] = useState<IWorkflow | null>(null)
  // By id, not by object: the workflow may change in the list (renamed,
  // activated) while the dialog is open, and the dialog must read the current version.
  const workflowToDelete = deleteProjectId ? workflows.find(p => p.id_hash === deleteProjectId) ?? null : null
  const workflowToConfigure = configureProjectId ? workflows.find(p => p.id_hash === configureProjectId) ?? null : null
  // ──────────────────────────────────────────────────────────────────────────

  // Same list the dialog offers in the select — the menu only decides whether there is any.
  const podeMover = useMemo(
    () => moveTargets(workspaces, currentWorkspace?.id_hash).length > 0,
    [workspaces, currentWorkspace?.id_hash],
  )

  // ── Stable callbacks handed to the rows ────────────────────────────────────
  // Everything that goes down to LinhaWorkflow has constant identity —
  // otherwise React.memo never hits and the whole list re-renders again on
  // every search keystroke.
  const openWorkflow = useCallback(
    (id: string) => router.push(`./workflow/${id}`),
    [router],
  )
  /**
   * Warms up the editor route on the first hover over the row.
   *
   * `/workflow/[id]` is the heaviest route in the application (React Flow +
   * Monaco) and the rows navigate via `onClick`, not via <Link>: the App Router
   * had no way to prefetch it, so each opening paid for the RSC payload + chunks
   * from scratch and the listing sat frozen for seconds, with no visual feedback
   * at all. With the route warm the commit fits within the wait ceiling of
   * `useViewTransitionRouter`, and the route transition actually happens.
   *
   * The `Set` avoids repeating the call on every pointer entry into the same
   * row — Next's cache already deduplicates, but not for free.
   */
  const prefetched = useRef<Set<string>>(new Set())
  const prefetchWorkflow = useCallback((id: string) => {
    if (prefetched.current.has(id)) return
    prefetched.current.add(id)
    router.prefetch(`./workflow/${id}`)
  }, [router])
  // History already sliced to the workflow (spec §3.9); the live run opens
  // straight in its panel.
  const viewRuns = useCallback(
    (id: string) => router.push(`/observability?workflow=${encodeURIComponent(id)}`),
    [router],
  )
  const viewRun = useCallback(
    (runId: string) => router.push(`/observability?execucao=${encodeURIComponent(runId)}`),
    [router],
  )
  const openPortal = useCallback((project: IWorkflow) => setPortalDialogProject(project), [])
  const openMove = useCallback((project: IWorkflow) => setMoveDialogProject(project), [])
  const openConfigure = useCallback((id: string) => setConfigureProjectId(id), [])
  const openDelete = useCallback((id: string) => setDeleteProjectId(id), [])
  const createWorkflow = useCallback(() => router.push("./workflow/create"), [router])
  const refreshList = useCallback(() => recarregar({ force: true }), [recarregar])
  const tentarDeNovo = useCallback(() => recarregar(), [recarregar])
  // ──────────────────────────────────────────────────────────────────────────

  const hasDnd = grupos.length > 0

  /** A workflow's row, with what has already been derived for it. */
  function linha(wf: IWorkflow): ReactNode {
    const d = derivados.get(wf.id_hash)
    if (!d) return null
    return (
      <LinhaWorkflow
        workflow={wf}
        gatilho={d.gatilho}
        resumoDoAgendamento={d.resumo}
        comoAnda={d.comoAnda}
        grupos={grupos}
        canEdit={canEdit}
        canExecute={canExecute}
        canManage={canManage}
        podeMover={podeMover}
        hasDnd={hasDnd}
        isDragging={draggingId === wf.id_hash}
        executando={runningId === wf.id_hash || preparingId === wf.id_hash}
        duplicando={duplicatingId === wf.id_hash}
        runIdVivo={runByHash.get(wf.id_hash)?.runId ?? null}
        onOpen={openWorkflow}
        onPrefetch={prefetchWorkflow}
        onRun={handleRunClick}
        onVerExecucao={viewRun}
        onAtivar={ativar}
        onDesativar={requestDeactivate}
        onConfigure={openConfigure}
        onPortal={openPortal}
        onMove={openMove}
        onDuplicate={handleDuplicate}
        onDelete={openDelete}
        onViewRuns={viewRuns}
        onAddToGroup={handleAddToGroup}
        onRemoveFromGroup={handleRemoveFromGroup}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      />
    )
  }

  // ── Screen states ──────────────────────────────────────────────────────────
  const carregando = dados.carregando
  // The error block takes over the screen only when there has NEVER been an
  // accepted load (`atualizadoEm == null`): whoever switched workspaces must not
  // see the previous shelf as if it were the new one. A reload that fails
  // (Atualizar, Duplicar) over a list already in place does not erase it — the
  // hook keeps what was there and the toast warns; blocking the whole screen
  // over a transient error would be worse than the problem.
  const hasError = !carregando && dados.erro != null && dados.atualizadoEm == null
  const firstUse = !carregando && !hasError && workflows.length === 0 && grupos.length === 0
  const noResults = !carregando && !hasError && !firstUse && sliceActive && visiveis.length === 0
  const listReady = !carregando && !hasError && !firstUse
  // The subtitle only disappears while there is nothing to count (first load, or
  // an error before any response).
  const headerCounts: HeaderCounts | null =
    carregando || (hasError && dados.atualizadoEm == null)
      ? null
      : { workflows: workflows.length, grupos: grupos.length, ativos: contagens.ativos, agendados: contagens.agendados, portal: contagens.portal }
  // ──────────────────────────────────────────────────────────────────────────

  return (
    <PageRoot>
      <CabecalhoDeProjetos
        contagens={headerCounts}
        atualizando={dados.atualizando}
        canEdit={canEdit}
        onAtualizar={refreshList}
        onNovoGrupo={() => setNewGroupModal(true)}
        onCriarWorkflow={createWorkflow}
      />

      {carregando && <SkeletonDeProjetos />}

      {hasError && <ErroDeCarga mensagem={dados.erro!} onTentar={tentarDeNovo} />}

      {firstUse && <VazioPrimeiroUso canEdit={canEdit} onCriar={createWorkflow} />}

      {listReady && (
        <>
          {metricasIndisponiveis && <MetricasIndisponiveis onTentar={refreshList} />}

          <BarraDeFiltros
            estado={estado}
            onEstado={atualizar}
            onLimpar={limparFiltros}
            contagens={contagens}
            temGrupos={grupos.length > 0}
            todosRecolhidos={todosRecolhidos}
            onRecolherTodos={collapseAll}
            onExpandirTodos={expandAll}
          />

          {noResults && (
            <SemResultado q={estado.q} filtro={estado.filtro} semFiltro={searchOnly} onLimpar={limparFiltros} />
          )}

          {/* Ungrouped comes BEFORE the groups. A titled section only when there
              are groups; without them, the list comes out untitled — there is
              nothing to tell it apart from. */}
          {!noResults && ungrouped.length > 0 && (
            grupos.length > 0 ? (
              <section aria-labelledby="sem-grupo-titulo" {...removeZone} className="flex flex-col gap-1.5">
                <h2 className="flex flex-wrap items-baseline gap-x-2 px-1">
                  <span id="sem-grupo-titulo" className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
                    Sem grupo
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {textoDaContagemDoGrupo(
                      ungroupedTotal.total,
                      ungroupedTotal.ativos,
                      ungrouped.length < ungroupedTotal.total ? ungrouped.length : null,
                    )}
                  </span>
                </h2>
                <ul className="flex flex-col gap-1.5">
                  {ungrouped.map(wf => <li key={wf.id_hash}>{linha(wf)}</li>)}
                </ul>
              </section>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {ungrouped.map(wf => <li key={wf.id_hash}>{linha(wf)}</li>)}
              </ul>
            )
          )}

          {!noResults && visibleGroups.map(grupo => {
            const id = grupo.id_hash
            const total = totais.get(id) ?? { total: 0, ativos: 0 }
            // Dragging a GROUP had no visual feedback at all: the person held
            // the handle and nothing on screen said where the group would land.
            // The two states are distinct on purpose — "receive a workflow" and
            // "change position" happen over the same rectangle.
            const arrastandoEste = draggingGroupId === id
            return (
              <GrupoSecao
                key={id}
                grupo={grupo}
                workflows={byGroup.get(id) ?? []}
                totalNoGrupo={total.total}
                ativosNoGrupo={total.ativos}
                recolhido={recolhidos.has(id)}
                onToggle={toggleGroup}
                canEdit={canEdit}
                podeArrastar={canEdit && grupos.length > 1}
                arrastandoEste={arrastandoEste}
                alvoDeReordenacao={dragOverGroupId === id && !!draggingGroupId && !arrastandoEste}
                recebendoWorkflow={dragOverGroupId === id && !!draggingId}
                nomeDoArrastado={arrastando?.name ?? null}
                onDragOver={e => { e.preventDefault(); setDragOverGroupId(id) }}
                onDragLeave={e => {
                  if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOverGroupId(null)
                }}
                onDrop={() => { void handleDropOnGroup(id) }}
                onDragStartGrupo={setDraggingGroupId}
                onDragEndGrupo={handleDragEnd}
                onRenomear={setEditGroup}
                onExcluir={setDeleteGroupConfirm}
                renderLinha={linha}
              />
            )
          })}

          {/* Zona fixa — aparece ao arrastar um workflow grouped. */}
          {arrastando?.group_id && (
            <div
              {...removeZone}
              className={cn(
                "flex items-center justify-center gap-2 rounded-lg border-2 border-dashed py-4 text-sm transition-colors select-none",
                dragOverUngrouped
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border text-muted-foreground/50",
              )}
            >
              <TbFolderOpen size={16} aria-hidden="true" />
              Solte aqui para remover do grupo
            </div>
          )}

          {/* The groups feature had nowhere to introduce itself: with no group
              created, nothing in the list suggested grouping was possible — not
              even the drag handle, which only appears from the first group on.
              This invitation is the only place where it can show itself. */}
          {canEdit && !sliceActive && grupos.length === 0 && workflows.length > 2 && (
            <button
              type="button"
              onClick={() => setNewGroupModal(true)}
              className="flex items-center gap-3 rounded-lg border border-dashed border-border px-4 py-3 text-left transition-colors outline-none hover:border-primary/50 hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <TbFolderPlus className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block text-sm font-medium">Agrupar workflows</span>
                <span className="block text-xs text-muted-foreground">
                  Crie um grupo e arraste as linhas para dentro. Grupos podem ser
                  recolhidos e reordenados.
                </span>
              </span>
            </button>
          )}

          {/* Drag hint, on the first group created: the handle only exists from
              then on, and nothing would explain that it appeared. */}
          {canEdit && grupos.length === 1 && ungroupedTotal.total > 0 && (
            <p className="flex items-center gap-2 px-1 text-xs text-muted-foreground">
              <TbGripVertical size={14} className="shrink-0" aria-hidden="true" />
              Arraste um workflow pela alça para colocá-lo no grupo — ou use
              &quot;Mover para grupo&quot; no menu do workflow.
            </p>
          )}
        </>
      )}

      {/* ── Dialogs ───────────────────────────────────────────────────────── */}
      <Dialog open={newGroupModal} onOpenChange={setNewGroupModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Novo grupo</DialogTitle>
            <DialogDescription>Organize workflows dentro de um grupo.</DialogDescription>
          </DialogHeader>
          <CreateGroup onSuccess={handleGroupCreated} />
        </DialogContent>
      </Dialog>

      <Dialog open={!!editGroup} onOpenChange={open => { if (!open) setEditGroup(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Renomear grupo</DialogTitle>
            <DialogDescription>O nome e a descrição aparecem no cabeçalho do grupo.</DialogDescription>
          </DialogHeader>
          {editGroup && (
            <RenameGroup
              key={editGroup.id_hash}
              group={editGroup}
              onSubmit={(nome, descricao) => handleRenameGroup(editGroup.id_hash, nome, descricao)}
              onDone={() => setEditGroup(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!deleteGroupConfirm} onOpenChange={open => { if (!open) setDeleteGroupConfirm(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Excluir grupo{deleteGroupConfirm ? ` «${deleteGroupConfirm.name}»` : ""}?</DialogTitle>
            <DialogDescription>
              {(() => {
                const dentro = totais.get(deleteGroupConfirm?.id_hash ?? "")?.total ?? 0
                if (dentro === 0) return "Tem certeza que deseja excluir este grupo?"
                return dentro === 1
                  ? "1 workflow volta para «Sem grupo». Nenhum é excluído."
                  : `${dentro} workflows voltam para «Sem grupo». Nenhum é excluído.`
              })()}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setDeleteGroupConfirm(null)}>Cancelar</Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deleteGroupConfirm) void handleDeleteGroup(deleteGroupConfirm.id_hash)
                setDeleteGroupConfirm(null)
              }}
            >
              Excluir
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!workflowToDelete} onOpenChange={open => { if (!open) setDeleteProjectId(null) }}>
        {workflowToDelete && (
          <DeleteProject
            workflow={workflowToDelete}
            onDeleted={id => {
              definirWorkflows(prev => prev.filter(p => p.id_hash !== id))
              setDeleteProjectId(null)
            }}
          />
        )}
      </Dialog>

      <Dialog open={!!workflowToConfigure} onOpenChange={open => { if (!open) setConfigureProjectId(null) }}>
        {workflowToConfigure && (
          <ConfigureProject
            key={workflowToConfigure.id_hash}
            workflow={workflowToConfigure}
            onSaved={atualizado => definirWorkflows(prev => prev.map(p => p.id_hash === atualizado.id_hash ? atualizado : p))}
            onDone={() => setConfigureProjectId(null)}
          />
        )}
      </Dialog>

      {/* Parameters dialog for a quick run — the schema comes from the
          `getWorkflowById` fired on click, because the listing does not carry it. */}
      {executeTarget && (
        <ExecuteParamsDialog
          open
          paramsSchema={executeTarget.schema}
          onConfirm={inputs => handleRunWorkflow(executeTarget.project, inputs)}
          onCancel={() => setExecuteTarget(null)}
        />
      )}

      <ConfirmarDesativar workflow={deactivating} onConfirm={confirmDeactivate} onCancel={() => setDeactivating(null)} />

      {portalDialogProject && (
        <PortalSettingsDialog
          open={!!portalDialogProject}
          onOpenChange={open => { if (!open) setPortalDialogProject(null) }}
          workflowId={portalDialogProject.id_hash}
          workflowName={portalDialogProject.name}
          initialAccess={portalDialogProject.portal_access ?? "disabled"}
          initialSharedWith={portalDialogProject.portal_shared_with ?? null}
          onSaved={(access, shared) => {
            definirWorkflows(prev => prev.map(p =>
              p.id_hash === portalDialogProject.id_hash
                ? { ...p, portal_access: access, portal_shared_with: shared }
                : p,
            ))
            setPortalDialogProject(null)
          }}
        />
      )}

      {moveDialogProject && (
        <MoveWorkflowDialog
          open={!!moveDialogProject}
          onOpenChange={open => { if (!open) setMoveDialogProject(null) }}
          workflowId={moveDialogProject.id_hash}
          workflowName={moveDialogProject.name}
          portalAccess={moveDialogProject.portal_access}
          onMoved={() => {
            // The workflow left the active workspace, so it leaves the listing. Optimistic
            // update instead of a refetch: the whole list would flicker for nothing.
            definirWorkflows(prev => prev.filter(p => p.id_hash !== moveDialogProject.id_hash))
          }}
        />
      )}
    </PageRoot>
  )
}
