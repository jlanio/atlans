import { INodeContext } from "@/context/useFlowContext"
import { INodesDefinition, IEdgeDefinition, ISubworkflowNotice } from "@/service/types"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { Edge, useReactFlow, useStoreApi, type Viewport } from "@xyflow/react"
import { useParams, useRouter } from "next/navigation"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { serializeEdge } from "@/app/components/workflow/utils/edge-persistence"
import { viewportsIguais } from "@/app/components/workflow/utils/viewport-salvo"
import { levarConversaDaCriacao } from "@/app/components/workflow/assistente/conversa-da-criacao"

export interface SaveOptions {
  /** Save triggered by another action (Executar saves before dispatching): no
   *  error toast — the caller answers with its own — and no "Salvo" (saved) flash
   *  when there is nothing to save. The chip keeps reflecting the state. */
  silent?: boolean
  /** Save even if the definition changed elsewhere since it was loaded — what
   *  the conflict toast's "Salvar mesmo assim" asks for. */
  force?: boolean
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
 * Whether the last saved graph may have nodes — what the "never save an empty
 * graph" rail asks. With no snapshot the saved state is UNKNOWN, not empty: the
 * canvas has not been hydrated, which is exactly when an empty canvas means "not
 * loaded" rather than "cleared". Before, a missing snapshot switched the rail
 * off, and the snapshot only exists after the very load it was meant to cover.
 */
function savedGraphMayHaveNodes(snapshot: string | null): boolean {
  if (!snapshot) return true
  try {
    const prev = JSON.parse(snapshot) as { nodes?: unknown[] }
    return !!prev.nodes && prev.nodes.length > 0
  } catch {
    // corrupted snapshot — does not block
    return false
  }
}

/** "a, b, c e mais 2": a toast is read at a glance, not scrolled. */
function listaCurta(itens: string[], max = 3): string {
  return itens.length <= max
    ? itens.join(", ")
    : `${itens.slice(0, max).join(", ")} e mais ${itens.length - max}`
}

/**
 * ONE toast for every caller a save of a sub-workflow broke. The backend sends
 * one notice per caller node and side; a toast each would bury the editor when
 * a widely used sub-workflow loses a port, and what the person needs is which
 * workflows to reopen and which ports to fix there.
 */
function resumoDosAvisosDeSubfluxo(avisos: ISubworkflowNotice[]) {
  const nomes = [...new Map(avisos.map(a => [a.workflow_id, a.workflow_name])).values()]
  const portas = [...new Set(avisos.flatMap(a => a.ports))].sort()
  const n = nomes.length
  const uma = portas.length === 1
  return {
    titulo: `${n} ${n === 1 ? "workflow usa" : "workflows usam"} ${uma ? "uma porta removida" : "portas removidas"}`,
    descricao:
      `${uma ? "Porta" : "Portas"}: ${listaCurta(portas)}. ${n === 1 ? "Workflow" : "Workflows"}: ${listaCurta(nomes)}. `
      + `Até ajustar ${n === 1 ? "esse workflow" : "esses workflows"}, o que passava por `
      + `${uma ? "essa porta" : "essas portas"} não chega.`,
  }
}

/**
 * Persistable projection of the graph — what goes into `definition` in the backend.
 *
 * Pure and exported on purpose: the "unsaved" detector lives in another
 * component (global-save-indicator) and needs to build EXACTLY the same
 * payload the save writes. Any asymmetry between the two becomes a "Não salvo"
 * (unsaved) that never goes away.
 */
export function buildGraphPayload(nodes: INodeContext[], edges: Edge[]) {
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
    const { nodesReq, edgesReq } = buildGraphPayload(nodes as unknown as INodeContext[], edges)
    const viewportReq = reactFlowInstance.getViewport()
    return { nodesReq, edgesReq, viewportReq }
  }


  function handleSaveWorkflow(opcoes: SaveOptions = {}) {
    // Single guard — the decision to start lives in saveWorkflow. Before the
    // Zustand refactor, handleSaveWorkflow set isSaving=true here; but
    // Zustand is synchronous, so the next guard in saveWorkflow blocked
    // everything immediately and no PUT was ever fired.
    if (useWorkflowSaveStore.getState().isSaving) return
    return saveWorkflow(opcoes)
  }

  async function saveWorkflow({ silent = false, force = false }: SaveOptions = {}) {

    const store = useWorkflowSaveStore.getState()
    if (store.isSaving)
      return

    // An existing workflow whose graph has not reached the canvas yet (node
    // catalog still loading, or the previous workflow still on screen while this
    // one loads) has nothing of the user's to save — and the payload would be
    // built from an empty canvas, or from another workflow's graph. It lives here
    // and not in the callers because every one of them comes through: Ctrl+S has
    // no "loaded yet?" of its own (only the buttons fade out while loading) and
    // Executar saves silently before dispatching. Before the name check too: until
    // the workflow request returns the name is still empty, and a save there asked
    // for a name the workflow already has.
    //
    // An explicit save says why it did nothing: refused in silence, Ctrl+S on a
    // slow load looked like a broken shortcut — or like a save that happened.
    // The silent one stays silent, as everywhere here: its caller answers with
    // its own message.
    if (id && !store.canvasHidratado) {
      if (!silent) createToast.info("Aguarde o workflow carregar para salvar")
      return { data: null, error: null }
    }

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
    if (id && nodesReq.length === 0 && savedGraphMayHaveNodes(store.lastSavedSnapshot)) {
      // The workflow had nodes — or may have — and we refuse to overwrite it with an empty one.
      console.warn(
        "[useSaveWorkflow] Tentativa de salvar workflow existente com 0 nós bloqueada "
        + "(provável closure stale pré-hidratação).",
      )
      return { data: null, error: null }
    }

    if (id && !store.isDirty(nodesReq, edgesReq, currentName)) {
      // The graph is the saved one. Only the viewport may have changed — and it is
      // part of what gets saved ("reopen at the same zoom and position"), but it
      // is not an edit: it does not mark "unsaved" and Executar's silent save
      // does not chase it. It goes along when the USER asks for the save; the
      // backend does not open a version for it (`_has_substantial_changes`
      // ignores position and viewport).
      const viewportChanged = !viewportsIguais(viewportReq, store.lastSavedViewport)
      if (silent || !viewportChanged) {
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
    // The canvas this save belongs to. Switching workflows while the request is
    // in flight resets the store for the other one; the answer then says
    // nothing about the canvas on screen (see `geracao`).
    const geracao = useWorkflowSaveStore.getState().geracao
    const deOutroCanvas = () => useWorkflowSaveStore.getState().geracao !== geracao

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
        }, { expectedEtag: force ? null : store.definitionEtag })

        if (data.error?.code === "definition_conflict") {
          // Someone else saved this workflow after it was opened here — another
          // tab, another person, the assistant. Saving on would erase what they
          // did (their edges included) with nothing said, which is what the tag
          // exists to stop. Said even on a silent save: Executar stops here, and
          // the person has to know why.
          if (deOutroCanvas()) {
            // Already on another workflow: no chip to mark, and no "save
            // anyway" — it builds the payload from the canvas ON SCREEN and
            // would write the other workflow's graph over this one.
            createToast.error("Workflow não salvo", data.error.message)
            return data
          }
          store.failSave(data.error.message ?? "Workflow alterado em outro lugar.")
          createToast.error("Workflow alterado em outro lugar", data.error.message, {
            label: "Salvar mesmo assim",
            // Same guard when clicked later: the toast outlives a switch.
            onClick: () => { if (!deOutroCanvas()) void saveWorkflow({ force: true }) },
          })
          return data
        }

        if (data.error) {
          if (deOutroCanvas()) {
            // The person left believing it was saved: say so even if silent.
            createToast.error(`Workflow não salvo`, data.error.message)
            return data
          }
          store.failSave(data.error.message)
          // On a silent save (triggered by Execute before dispatch), the chip
          // already shows "Falha ao salvar" (save failed) — a toast here would
          // be the second warning.
          if (!silent) createToast.error(`Workflow não salvo`, data.error.message)
          return data
        }

        if (!deOutroCanvas()) {
          // The saved definition is the new base for the next save's check.
          useWorkflowSaveStore.setState({ definitionEtag: data.data?.definition_etag ?? null })
          const snapshot = JSON.stringify({ name: currentName, nodes: nodesReq, edges: edgesReq })
          // No success toast: the chip next to the workflow path says "Salvo"
          // and keeps saying "Salvo há N min" (saved N min ago). A toast on every
          // Ctrl+S was noise about the same information.
          store.completeSave(snapshot, viewportReq)
        }
        // Saved, but the schedule may not have been applied (inactive workflow,
        // invalid expression): the backend returns the reason in
        // `schedule_notices`. In that case the "Salvo" on the chip would hide an
        // important caveat — show an amber toast (even on a silent save: the user
        // needs to know the schedule did not take effect).
        for (const aviso of data.data?.schedule_notices ?? []) {
          createToast.warning("Agendamento não aplicado", aviso.message)
        }
        // Saved — but other workflows call this one as a sub-workflow and use
        // ports this save removed or renamed: their edges on those ports deliver
        // nothing from now on. Nothing on THIS canvas shows it, so the backend
        // lists them (`subworkflow_notices`) and one amber toast sums them up —
        // also on a silent save, for the same reason as the schedule notice.
        const avisosDeSubfluxo = data.data?.subworkflow_notices ?? []
        if (avisosDeSubfluxo.length > 0) {
          const { titulo, descricao } = resumoDosAvisosDeSubfluxo(avisosDeSubfluxo)
          createToast.warning(titulo, descricao)
        }
        return data
      }

      // The screen this save was asked from. Leaving it while the request is in
      // flight (Projetos, any other menu) mounts no other editor, so `geracao`
      // does not move: without this, the redirect below would pull the person
      // back into the editor from wherever they went.
      const caminho = window.location.pathname

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
        if (!deOutroCanvas()) store.failSave(data.error.message)
        createToast.error(`Workflow não criado`, data.error.message)
        return data
      }
      // Created, but the person already opened another workflow: neither its
      // state nor its URL are this one's to change.
      if (deOutroCanvas()) return data

      store.completeSave(JSON.stringify({ name: currentName, nodes: nodesReq, edges: edgesReq }), viewportReq)

      // The workflow now exists: the URL becomes its URL, and the editor reopens
      // on it (/workflow/[id] loads it back from the server). Before, the
      // button sent you to the project list (abandoning what
      // you were editing) and Ctrl+S stayed on /workflow/create with no id —
      // the next Ctrl+S created a copy. `replace`, not `push`: going back to
      // /create in the history would mean going back to "create another".
      //
      // The new id comes as `id` (see createWorkflow). Reading `id_hash` here
      // found nothing: the editor stayed on /workflow/create with no Executar,
      // and every later save tried to create again and hit the name already taken.
      const newId = data.data?.id
      if (!newId) {
        // Created, but with nowhere to open it. A plain "Salvo" here is how the
        // missing id went unnoticed: say where the workflow is instead.
        console.error("[useSaveWorkflow] POST /workflows answered without an id:", data.data)
        createToast.warning("Workflow criado", "Abra-o pela lista de Projetos para continuar e executar.")
        return data
      }
      if (window.location.pathname !== caminho) return data

      // The assistant's conversation that built it goes along: the drawer
      // mounts again over there.
      levarConversaDaCriacao(newId)
      // Until /workflow/<id> mounts, this canvas is that workflow but the route
      // still says "create": a save now would POST again and hit the name just
      // taken. Holding `isSaving` turns those saves away; the editor that mounts
      // there resets the store, which releases it.
      useWorkflowSaveStore.setState({ isSaving: true })
      router.replace(`/workflow/${newId}`)

      return data
    } catch (err) {
      if (!deOutroCanvas()) store.failSave(String(err))
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
