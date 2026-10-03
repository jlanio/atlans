import { INodeContext } from "@/context/useFlowContext"
import { INodesDefinition, IEdgeDefinition } from "@/service/types"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { Edge, useReactFlow, useStoreApi, type Viewport } from "@xyflow/react"
import { useParams, useRouter } from "next/navigation"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { serializeEdge } from "@/app/components/workflow/utils/edge-persistence"
import { viewportsIguais } from "@/app/components/workflow/utils/viewport-salvo"

export interface OpcoesDeSave {
  /** Save triggered by another action (Executar saves before dispatching): no
   *  error toast — the caller answers with its own — and no "Salvo" (saved) flash
   *  when there is nothing to save. The chip keeps reflecting the state. */
  silent?: boolean
}

// Normalizes properties by sorting keys — JSON.stringify preserves insertion
// order, so two objects with the same entries but different orders produce
// different strings. ReactFlow may recreate the object internally with a
// different order after measuring dimensions, which would trigger a false
// positive in isDirty.
function normalizeProperties(properties: unknown): Record<string, string> {
  if (!properties || typeof properties !== 'object') return {}
  const source = properties as Record<string, string>
  const sorted: Record<string, string> = {}
  for (const key of Object.keys(source).sort()) {
    sorted[key] = source[key]
  }
  return sorted
}

/**
 * Persistable projection of the graph — what goes into `definition` in the backend.
 *
 * Pure and exported on purpose: the "unsaved" detector lives in another
 * component (global-save-indicator) and needs to build EXACTLY the same
 * payload the save writes. Any asymmetry between the two becomes a "Não salvo"
 * (unsaved) that never goes away.
 */
export function montarPayloadDoGrafo(nodes: INodeContext[], edges: Edge[]) {
  const nodesReq = nodes.map(node => {
    const { data: { name, alias, properties, type }, position } = node
    // Normalizes position to { x, y } — discards extra fields that ReactFlow
    // may have injected (positionAbsolute, etc).
    return {
      id: node.id,
      name,
      alias,
      type,
      properties: normalizeProperties(properties),
      position: { x: position.x, y: position.y }
    } satisfies INodesDefinition
  })

  // Serialization lives in utils/edge-persistence to stay symmetric with
  // loadEdges and testable — detect-dirty uses this same function.
  const edgesReq = edges.map(serializeEdge)

  return { nodesReq, edgesReq }
}

export const useSaveWorkflow = () => {

  const router = useRouter()
  const { current: currentWorkspace } = useWorkspace()
  const reactFlowInstance = useReactFlow()
  // Imperative read of the React Flow store instead of useNodes()/useEdges().
  // This hook is mounted at several points of the canvas tree (editor, Save
  // button, Executar button, state chip): subscribing to both arrays
  // re-rendered all of them on every pointermove of a drag. And reading at call
  // time also does away with the refs that existed here to cover stale closures
  // — the store is never behind, so Execute's silent save has no way of
  // writing an empty graph.
  const flowStore = useStoreApi()
  const { id } = useParams<{ id: string }>()
  // Acessa a store Zustand — permite GlobalSaveIndicator ver o mesmo status
  const isSaving = useWorkflowSaveStore(s => s.isSaving)
  const saveStatus = useWorkflowSaveStore(s => s.saveStatus)

  function buildPayload() {
    const { nodes, edges } = flowStore.getState()
    const { nodesReq, edgesReq } = montarPayloadDoGrafo(nodes as unknown as INodeContext[], edges)
    const viewportReq = reactFlowInstance.getViewport()
    return { nodesReq, edgesReq, viewportReq }
  }


  function handleSaveWorkflow(opcoes: OpcoesDeSave = {}) {
    // Single guard — the decision to start lives in saveWorkflow. Before the
    // Zustand refactor, handleSaveWorkflow set isSaving=true here; but
    // Zustand is synchronous, so the next guard in saveWorkflow blocked
    // everything immediately and no PUT was ever fired.
    if (useWorkflowSaveStore.getState().isSaving) return
    return saveWorkflow(opcoes)
  }

  async function saveWorkflow({ silent = false }: OpcoesDeSave = {}) {

    const store = useWorkflowSaveStore.getState()
    if (store.isSaving)
      return

    // Captures the latest value from the store
    const currentName = store.workflowName
    if (!currentName || currentName.trim() === "") {
      // Missing name: marks the status but does NOT set isSaving (if it did, the
      // next click — after the user fills in the name in UnsavedDialog —
      // would be blocked by the `if (store.isSaving) return` guard above).
      store.setStatus('needs_name')
      return
    }

    const { nodesReq, edgesReq, viewportReq } = buildPayload()

    // Anti-data-loss guard rail: never overwrites an existing workflow with an
    // empty definition. If the user really wants to clear the workflow, they
    // need to delete the nodes on the canvas (which brings isDirty with an
    // explicit nodes=[] as the last rendered state). Protects against stale
    // closures that called saveWorkflow before the canvas hydrated.
    if (id && nodesReq.length === 0 && store.lastSavedSnapshot) {
      try {
        const prev = JSON.parse(store.lastSavedSnapshot) as { nodes?: unknown[] }
        if (prev.nodes && prev.nodes.length > 0) {
          // The workflow had nodes — we refuse to overwrite it with an empty one.
          console.warn(
            "[useSaveWorkflow] Tentativa de salvar workflow existente com 0 nós bloqueada "
            + "(provável closure stale pré-hidratação).",
          )
          return { data: null, error: null }
        }
      } catch {
        // corrupted snapshot — does not block
      }
    }

    if (id && !store.isDirty(nodesReq, edgesReq, currentName)) {
      // The graph is the saved one. Only the viewport may have changed — and it is
      // part of what gets saved ("reopen at the same zoom and position"), but it
      // is not an edit: it does not mark "unsaved" and Executar's silent save
      // does not chase it. It goes along when the USER asks for the save; the
      // backend does not open a version for it (`_has_substantial_changes`
      // ignores position and viewport).
      const viewportMudou = !viewportsIguais(viewportReq, store.lastSavedViewport)
      if (silent || !viewportMudou) {
        // Nothing to write — no PUT. But a Ctrl+S that answers nothing is
        // indistinguishable from a broken shortcut: flash "Salvo" to confirm that
        // everything is saved. No status reset is needed, since
        // startSaving() has not been called yet.
        if (!silent) store.flashSaved()
        return { data: null, error: null }
      }
    }

    // Only now mark as saving — there will be a PUT from here on.
    // Every path below exits via completeSave/failSave/catch, which clear
    // isSaving. (Before, the start was in handleSaveWorkflow and the early
    // returns above left isSaving=true stuck).
    store.startSaving()

    try {
      if (id) {
        // Minimal payload: only the fields the canvas edits. Sending
        // flag_ative/description/version/priority here WOULD OVERWRITE the
        // real values in the backend (e.g. a workflow deactivated via the switch
        // became active again on every edit).
        const data = await GisFlowService.updateWorkflowById(id, {
          name: currentName,
          definition: {
            nodes: nodesReq,
            edges: edgesReq,
            viewport: viewportReq,
          },
        })

        if (data.error) {
          store.failSave(data.error.message)
          // On a silent save (triggered by Execute before dispatch), the chip
          // already shows "Falha ao salvar" (save failed) — a toast here would
          // be the second warning.
          if (!silent) createToast.error(`Workflow não salvo`, data.error.message)
          return data
        }

        const snapshot = JSON.stringify({ name: currentName, nodes: nodesReq, edges: edgesReq })
        // No success toast: the chip next to the workflow path says "Salvo"
        // and keeps saying "Salvo há N min" (saved N min ago). A toast on every
        // Ctrl+S was noise about the same information.
        store.completeSave(snapshot, viewportReq)
        // Saved, but the schedule may not have been applied (inactive workflow,
        // invalid expression): the backend returns the reason in
        // `schedule_notices`. In that case the "Salvo" on the chip would hide an
        // important caveat — show an amber toast (even on a silent save: the user
        // needs to know the schedule did not take effect).
        for (const aviso of data.data?.schedule_notices ?? []) {
          createToast.warning("Agendamento não aplicado", aviso.message)
        }
        return data
      }

      // New workflow: reasonable defaults for the metadata fields.
      // created_by_id/updated_by_id are filled in by the backend from the
      // authenticated user — they are not sent by the frontend.
      const data = await GisFlowService.createWorkflow({
        flag_ative: true,
        name: currentName,
        description: "",
        version: "v1",
        priority: 0,
        workspace_id: currentWorkspace?.id_hash ?? undefined,
        definition: {
          nodes: nodesReq,
          edges: edgesReq,
          viewport: viewportReq,
        },
      })

      if (data.error) {
        store.failSave(data.error.message)
        createToast.error(`Workflow não criado`, data.error.message)
        return data
      }

      store.completeSave(JSON.stringify({ name: currentName, nodes: nodesReq, edges: edgesReq }), viewportReq)

      // The workflow now exists: the URL becomes its URL, and the editor stays
      // open. Before, the button sent you to the project list (abandoning what
      // you were editing) and Ctrl+S stayed on /workflow/create with no id —
      // the next Ctrl+S created a copy. `replace`, not `push`: going back to
      // /create in the history would mean going back to "create another".
      const novoId = data.data?.id_hash
      if (novoId) router.replace(`/workflow/${novoId}`)

      return data
    } catch (err) {
      store.failSave(String(err))
      createToast.error("Erro ao salvar workflow", String(err))
    }

  }

  /**
   * Initializes the reference snapshot with the state loaded from the backend.
   * Must be called ONCE after the canvas hydrates (loadNodes+loadEdges).
   * With the snapshot filled in, isDirty() returns false when the user has not
   * edited anything — avoiding an unnecessary PUT before POST /execute.
   *
   * `savedAt` is the server's `updated_at` (epoch ms): it is what the chip shows
   * at rest before this session's first save. `viewport` is what came in the
   * `definition`: a reference to know whether an explicit save has a new
   * viewport to write.
   *
   * IMPORTANT: the shape of nodesReq/edgesReq must be identical to what
   * buildPayload() produces (INodesDefinition[] / IEdgeDefinition[]).
   */
  function initSnapshot(nodesReq: INodesDefinition[], edgesReq: IEdgeDefinition[], name: string, savedAt?: number | null, viewport?: Viewport | null) {
    const store = useWorkflowSaveStore.getState()
    store.initSnapshot(nodesReq, edgesReq, name, savedAt, viewport)
  }

  return {
    isSaving,
    saveStatus,
    saveWorkflow: handleSaveWorkflow,
    initSnapshot,
    buildPayload,
  }
}
