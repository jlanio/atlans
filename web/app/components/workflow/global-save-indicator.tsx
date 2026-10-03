"use client"

import { useEffect, useReducer, type ReactNode } from "react"
import { useEdges, useNodes, useStoreApi } from "@xyflow/react"
import { TbAlertTriangle, TbCheck, TbCloudCheck, TbCloudOff, TbLoader, TbPencil } from "react-icons/tb"
import { INodeContext } from "@/context/useFlowContext"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { montarPayloadDoGrafo, useSaveWorkflow } from "@/app/hooks/workflow/useSaveWorkflow"
import { rotuloDeSalvo } from "./utils/rotulo-de-salvo"
import { cn } from "@/lib/utils"

/** Inactivity required before comparing the graph with the last snapshot. */
const ATRASO_DA_DETECCAO_MS = 300

/** How often "Salvo há N min" is recomputed while idle. */
const TIQUE_DO_RELOGIO_MS = 30_000

/**
 * Detects unsaved edits by comparing the graph with the last snapshot.
 *
 * It lives here, not in `useSaveWorkflow`, because that hook is mounted at
 * several points of the canvas tree (editor, Save button, Run button, this
 * chip) — detection ran once per mount on every drag frame, each pass mapping
 * every node and serializing the whole graph. This indicator is the only spot
 * mounted exactly once, and it is the one that shows the result.
 *
 * The comparison is deferred: during a drag `nodes` changes identity on every
 * pointermove, and comparing per frame turned workflows with large Python
 * Script or SQL nodes into a slideshow. The price is the label appearing up to
 * 300ms after the edit.
 */
function useDeteccaoDeAlteracoes() {
  // Subscriptions only as a TRIGGER: what reads the graph is the `getState()`
  // further down, after the delay. This component renders nothing that depends
  // on them, so the cost per drag frame is an empty render and a reschedule.
  const nodes = useNodes<INodeContext>()
  const edges = useEdges()
  const workflowName = useWorkflowSaveStore(s => s.workflowName)
  const lastSavedSnapshot = useWorkflowSaveStore(s => s.lastSavedSnapshot)
  const flowStore = useStoreApi()

  useEffect(() => {
    if (!lastSavedSnapshot) return

    const timer = setTimeout(() => {
      const { nodes: nosAtuais, edges: arestasAtuais } = flowStore.getState()
      const { nodesReq, edgesReq } = montarPayloadDoGrafo(
        nosAtuais as unknown as INodeContext[],
        arestasAtuais,
      )
      const store = useWorkflowSaveStore.getState()

      if (!store.isDirty(nodesReq, edgesReq, store.workflowName)) {
        // Back to the saved state (undid the edit, deleted what it had created): the
        // warning no longer has a reason to exist. Only 'unsaved' is dropped — the
        // other states are not deduced from the graph.
        if (store.saveStatus === 'unsaved') store.setStatus('idle')
        return
      }

      // Self-correction ONLY inside the hydration window (see
      // `autocorrigirSnapshot`): the initial snapshot, taken right after
      // setNodes/setEdges, may differ subtly from the current state because
      // ReactFlow was still measuring dimensions/positions.
      //
      // The rule is about TIME, not "the first difference that shows up". Since
      // this comparison is debounced, the first difference it sees is already
      // the FINAL result of the drag (or of Apply in the modal): a one-shot flag
      // swallowed the whole edit into the reference snapshot — no "Não salvo",
      // with Ctrl+S hitting isDirty's early return and Run telling the executor
      // to run the previous definition.
      if (store.autocorrigirSnapshot(nodesReq, edgesReq, store.workflowName)) return

      // An in-flight save, a failure and the name prompt are not states the graph
      // undoes. ReactFlow's re-measuring also changes the identity of `nodes`,
      // and downgraded "Falha ao salvar" to "Não salvo" right after the failure —
      // taking the retry button along with it.
      if (store.saveStatus === 'idle' || store.saveStatus === 'saved') store.setStatus('unsaved')
    }, ATRASO_DA_DETECCAO_MS)

    return () => clearTimeout(timer)
  }, [nodes, edges, workflowName, lastSavedSnapshot, flowStore])
}

/** Re-renders on every tick while `ativo`, so "há N min" doesn't go stale. */
function useRelogio(ativo: boolean) {
  const [, tique] = useReducer((n: number) => n + 1, 0)
  useEffect(() => {
    if (!ativo) return
    const intervalo = setInterval(tique, TIQUE_DO_RELOGIO_MS)
    return () => clearInterval(intervalo)
  }, [ativo])
}

interface Rotulo {
  texto: string
  icone: ReactNode
  classe: string
}

/**
 * Save state, next to the workflow path.
 *
 * Visible WHENEVER there is something to say — including while idle ("Salvo há
 * 5 min"). The previous version was a centered pill that disappeared 3s after
 * the save and showed nothing in the normal state: between a "Salvo" that went
 * by fast and a "Salvando…" that lasted as long as the PUT, the impression was
 * that there was no feedback at all. The error got its own state, with the
 * retry where the failure is read; before, it fell into "Não salvo" and the
 * message went away with the toast.
 *
 * Render as a child of `<WorkflowLocation>`: it is what positions the row over
 * the canvas and gives its direct children `pointer-events` (the retry needs it).
 */
const GlobalSaveIndicator = () => {
  const status = useWorkflowSaveStore(s => s.saveStatus)
  const lastSavedAt = useWorkflowSaveStore(s => s.lastSavedAt)
  const lastError = useWorkflowSaveStore(s => s.lastError)
  const { saveWorkflow } = useSaveWorkflow()
  useDeteccaoDeAlteracoes()

  const emRepouso = status === 'idle' && lastSavedAt !== null
  useRelogio(emRepouso)

  const rotulo: Rotulo | null = (() => {
    switch (status) {
      case 'idle':
        // With no known save (new workflow) there is nothing to state.
        return emRepouso
          ? { texto: rotuloDeSalvo(lastSavedAt), icone: <TbCloudCheck size={13} />, classe: "text-muted-foreground" }
          : null
      case 'unsaved':
        return { texto: "Alterações não salvas", icone: <TbPencil size={13} />, classe: "text-amber-500 border-amber-500/40" }
      case 'saving':
        return { texto: "Salvando…", icone: <TbLoader className="animate-spin" size={13} />, classe: "text-muted-foreground" }
      case 'saved':
        return { texto: "Salvo", icone: <TbCheck size={13} />, classe: "text-green-500 border-green-500/40" }
      case 'error':
        return { texto: "Falha ao salvar", icone: <TbAlertTriangle size={13} />, classe: "text-destructive border-destructive/40" }
      case 'needs_name':
        return { texto: "Sem nome", icone: <TbCloudOff size={13} />, classe: "text-amber-500 border-amber-500/40" }
    }
  })()

  if (!rotulo) return null

  return (
    <div
      role="status"
      // While idle the text changes by itself every minute; announcing that on a
      // screen reader would be a talking clock. The other states are responses
      // to a user action, and there the announcement is the feedback.
      aria-live={emRepouso ? "off" : "polite"}
      title={status === 'error' ? lastError ?? undefined : undefined}
      data-save-status={status}
      className={cn(
        "flex h-8 shrink-0 items-center gap-1.5 rounded-lg border border-border bg-background/85 px-2.5 text-xs font-medium shadow-xs backdrop-blur-sm transition-colors duration-200",
        rotulo.classe,
      )}
    >
      {rotulo.icone}
      <span>{rotulo.texto}</span>
      {status === 'error' && (
        <button
          type="button"
          onClick={() => { saveWorkflow() }}
          className="ml-1 rounded px-1.5 py-0.5 text-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          Tentar novamente
        </button>
      )}
    </div>
  )
}

export default GlobalSaveIndicator
