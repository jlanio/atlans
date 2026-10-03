"use client"
import { ReactFlow, useReactFlow, useNodesState, useEdgesState, Edge, Background, BackgroundVariant, Connection } from "@xyflow/react"
import React, { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useSession } from "next-auth/react"
import { INodeContext, useFlowContext } from "@/context/useFlowContext";
import { TbPlus } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { useConfigNodeParams } from "@/app/hooks/workflow/useConfigNodeParams";
import { useSubWorkflowContractSync } from "@/app/hooks/workflow/useSubWorkflowContractSync";
import { useDynamicPortsSync } from "@/app/hooks/workflow/useDynamicPortsSync";
import { useHandleRegistrySync } from "@/app/hooks/workflow/useHandleRegistrySync";
import { IWorkflow } from "@/service/types";
import { v4 as uuid } from 'uuid';
import WorkflowLocation from "./workflow-location";
import { useSidebar } from "../ui/sidebar";
import { useLinkNodeParams } from "@/app/hooks/workflow/useLinkNodeParams";
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast";
import ActionsButton from "./buttons";
import RunPanel from "./run-panel";
import AssistentePainel from "./assistente";
import type { ResultadoDaProposta } from "./utils/aplicar-proposta"
import {
  cabeNoEnquadrado, semMovimento, ZOOM_MAXIMO_DO_ENQUADRAMENTO, DURACAO_DO_ENQUADRAMENTO,
  type Caixa,
} from "./utils/enquadrar";
import WorkflowDrawer from "./drawer";
import { getTypeIcon } from "@/utils/getTypeIconsUtils";
import { nodeTypesFlow, customEdges } from "./canvas-types";
import { useTheme } from "@/context/ThemeContext"
import CanvasToolbar from "./canvas-toolbar";
import { CanvasInteractionProvider, useCanvasReadOnlyRoot } from "./canvas-interaction";
import { useCanvasHistory } from "@/app/hooks/workflow/useCanvasHistory";
import { fromBackend } from "@/lib/dayjs";
import { dadoOuAviso } from "@/lib/respostas";
import { viewportSalvoValido } from "./utils/viewport-salvo";
import { usePinExpirationTimer } from "@/app/hooks/workflow/usePinExpirationTimer";
import { useSaveWorkflow } from "@/app/hooks/workflow/useSaveWorkflow";
import UnsavedDialog from "./buttons/unsaved-dialog";
import GlobalSaveIndicator from "./global-save-indicator";
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore";
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore";
import { useKnownColumnsStore } from "@/app/stores/knownColumnsStore";
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore";
import { useRunPanelStore } from "@/app/stores/runPanelStore";
import { useCanvasViewStore } from "@/app/stores/canvasViewStore";
import { useSubflowDrilldownStore } from "@/app/stores/subflowDrilldownStore";
import { getCandidateKeys, resolveToKey } from "./utils/resolve-edge-keys";
import { MENSAGEM_DE_RECUSA, validarConexao } from "./utils/valida-conexao";
import { toast } from "sonner";
import { contratoDoNo } from "./utils/node-ports"
import { buildEdges, buildNodes } from "./utils/build-canvas";
import SubflowViewer from "./subflow-viewer";
import CanvasViewLayer from "./canvas-view-layer";
import CanvasLoading from "./canvas-loading";
import { useCanvasFocus } from "@/app/hooks/workflow/useCanvasFocus";
import { useZoomLod } from "@/app/hooks/workflow/useZoomLod";

// The configuration modal and everything it drags along (the json-edit-react
// JSON editor, input inspector, output preview, webhook helpers and the Jinja
// guide) is only used after a double-click on a node. Statically imported, that
// weight was downloaded and parsed before the first node appeared on screen.
// Same treatment already given to Monaco in code-field.
const NodeConfigModal = dynamic(() => import("./node-config-modal"), { ssr: false })

interface IReactFlowComponent {
  workflow?: IWorkflow
  reloadWorkflow?: () => Promise<void>
}

/**
 * Projection of `nodes` that only changes identity when a node enters, leaves
 * or has its `data` replaced.
 *
 * Dragging a node recreates the array and every node object on each
 * pointermove, but `data` stays the SAME object. The three sync hooks below only
 * look at `id` and `data` — feeding them raw `nodes` made every drag frame
 * rebuild three string signatures over the whole graph just to conclude that
 * nothing changed.
 */
function useNosEstruturais(nodes: INodeContext[]): INodeContext[] {
  const anterior = useRef<INodeContext[]>([])
  const igual =
    anterior.current.length === nodes.length &&
    nodes.every((n, i) => anterior.current[i]?.id === n.id && anterior.current[i]?.data === n.data)
  if (!igual) anterior.current = nodes
  return anterior.current
}

const ReactFlowComponent = ({ workflow, reloadWorkflow }: IReactFlowComponent) => {

  const reactFlowInstance = useReactFlow();
  const domNode = React.useRef<HTMLDivElement>(null);

  const { setFlowContext } = useFlowContext()
  const nodesAPI = useWorkflowCatalogStore(s => s.nodesAPI)
  const setPinnedNodes = useWorkflowCatalogStore(s => s.setPinnedNodes)
  const setNewlyAddedNodeId = useWorkflowCatalogStore(s => s.setNewlyAddedNodeId)
  const setNodesDrawerState = useWorkflowCatalogStore(s => s.setNodesDrawerState)
  useConfigNodeParams()
  const { status } = useSession()
  const { theme } = useTheme()
  const [nodes, setNodes, onNodesChange] = useNodesState<INodeContext>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  // None of the three syncs reacts to position — they all read `id` and `data`.
  const nosEstruturais = useNosEstruturais(nodes);
  // Syncs the dynamic ports of SubWorkflow nodes with the target workflow's
  // contract (SubWorkflowInput/SubWorkflowOutput).
  useSubWorkflowContractSync(nosEstruturais);
  // Python Script ports: `data.inputs` follows the `ports` property.
  // Without this, defining the ports would only take effect on page reload.
  useDynamicPortsSync(nosEstruturais);
  // A connection point added to an already rendered node is drawn by React
  // but doesn't enter ReactFlow's registry: it shows on screen and doesn't accept
  // connections. Applies to Python Script ports and to sub-workflow ports.
  useHandleRegistrySync(nosEstruturais);
  const { saveSnapshot, captureBaseline, undo, redo, canUndo, canRedo } = useCanvasHistory()

  /** The last box the camera framed, in graph coordinates. */
  const enquadradoRef = useRef<Caixa | null>(null)

  /** What the assistant draws enters the canvas: animated, and in view.
   *
   * Two things that are not decoration:
   *
   * 1. **Framing.** `computeAutoLayout` puts the new nodes in graph
   *    coordinates, which may fall OUTSIDE the visible viewport. Without
   *    framing, the person is left staring at a still screen while the workflow
   *    grows outside it — the feature not working, not a detail.
   *
   *    But framing on EVERY step was the other extreme: `fitView` reframes the
   *    whole graph, so the zoom changed with every node and what you saw was
   *    the screen jumping in scale, not following along. Now it only moves when
   *    the drawing leaves what was already framed — the rest of the time the
   *    camera stays still, including if the person has dragged the canvas to
   *    look at something. When it moves, it goes slowly and with a zoom
   *    ceiling: without the ceiling, a two-node workflow is framed very close
   *    up and the next step jolts backward. It is the same care as in
   *    `run-panel/shared.tsx` and the sub-workflow viewer, which pass `maxZoom`
   *    for the same reason.
   *
   * 2. The class only on the NEW ids, cleared afterwards. Without clearing it
   *    would stay on the node object forever; without the selection, the whole
   *    workflow would blink on every added node.
   */
  const aplicarDoAssistente = useCallback((resultado: ResultadoDaProposta) => {
    saveSnapshot()
    setNodes(resultado.nodes.map(no => (
      resultado.idsNovos.has(no.id) ? { ...no, className: "assistente-entrando" } : no
    )))
    setEdges(resultado.edges.map(aresta => (
      resultado.idsArestasNovas.has(aresta.id)
        ? { ...aresta, className: "assistente-aresta-entrando" }
        : aresta
    )))

    // After React draws: measuring before that would measure the old canvas.
    requestAnimationFrame(() => {
      const caixa = reactFlowInstance.getNodesBounds(reactFlowInstance.getNodes())
      if (cabeNoEnquadrado(caixa, enquadradoRef.current)) return
      enquadradoRef.current = caixa
      reactFlowInstance.fitView({
        padding: 0.2,
        maxZoom: ZOOM_MAXIMO_DO_ENQUADRAMENTO,
        duration: semMovimento() ? 0 : DURACAO_DO_ENQUADRAMENTO,
      })
    })

    // The class comes off when the animation ends. It has done its job, and
    // leaving it pins a "just arrived" state on nodes that have been there for
    // minutes. 700ms covers the longer of the two (the edge: 120ms delay +
    // 400ms); cutting before the end would make the node jump to its final
    // state midway.
    const limpar = setTimeout(() => {
      setNodes(atuais => atuais.map(no => (no.className ? { ...no, className: undefined } : no)))
      setEdges(atuais => atuais.map(a => (a.className ? { ...a, className: undefined } : a)))
    }, 700)
    return () => clearTimeout(limpar)
  }, [reactFlowInstance, saveSnapshot, setEdges, setNodes])
  const snapshotTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { setOpen } = useSidebar()
  // On a phone the canvas becomes a viewer: you can navigate, run and read the
  // configuration, but not drag nodes or pull connections. It isn't laziness
  // about adapting — hitting an 8px handle with a finger, in a graph where pan
  // uses the same gesture as drag, produces more accidental edits than edits.
  // See canvas-interaction for why the gate is width and not pointer.
  const canvasSomenteLeitura = useCanvasReadOnlyRoot()
  const { saveWorkflow, saveStatus, initSnapshot, buildPayload } = useSaveWorkflow()
  // `workflow` (prop) is undefined both on /workflow/create and on
  // /workflow/[id] before the fetch responds; only the route tells which is which.
  const { id: idDaRota } = useParams<{ id?: string }>()
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false)
  // The graph has already been put on the canvas (loadNodes/loadEdges). It is
  // state, not the `hidratadoPara` ref, because it needs to re-render: it is what
  // removes the loading animation and enables the add-node button.
  const [hidratado, setHidratado] = useState(false)
  // Only the route with an id waits for anything; the creation screen is born ready.
  const carregando = Boolean(idDaRota) && !hidratado
  usePinExpirationTimer()

  // Opens the dialog when the save detects that the name is empty
  useEffect(() => {
    if (saveStatus === 'needs_name') setShowUnsavedDialog(true)
  }, [saveStatus])

  // See the comment on <UnsavedDialog>: without this exit from 'needs_name', a
  // second click on Save doesn't reopen the dialog. Closing without naming
  // saved nothing — if the canvas has something, the "unsaved" warning comes
  // back (the detector only runs when the graph changes, so here the decision
  // is immediate).
  const fecharSemNomear = useCallback(() => {
    const store = useWorkflowSaveStore.getState()
    if (store.saveStatus !== 'needs_name') return
    const { nodesReq, edgesReq } = buildPayload()
    store.setStatus(store.isDirty(nodesReq, edgesReq, store.workflowName) ? 'unsaved' : 'idle')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Saves the snapshot with a debounce so as not to create history on every drag keystroke
  const debouncedSave = useCallback(() => {
    if (snapshotTimerRef.current) clearTimeout(snapshotTimerRef.current)
    snapshotTimerRef.current = setTimeout(saveSnapshot, 300)
  }, [saveSnapshot])

  const handleNodesChange = useCallback((changes: Parameters<typeof onNodesChange>[0]) => {
    onNodesChange(changes)
    // Only saves a snapshot on structural changes (add/remove/reposition after drag)
    const hasStructural = changes.some(c => c.type === "add" || c.type === "remove" || (c.type === "position" && !c.dragging))
    if (hasStructural) debouncedSave()
  }, [onNodesChange, debouncedSave])

  const handleEdgesChange = useCallback((changes: Parameters<typeof onEdgesChange>[0]) => {
    onEdgesChange(changes)
    // `replace` is included because changing an edge's data key (the CustomEdge
    // badge) changes what the target node receives — it is an edit to the
    // workflow's content, as undoable as creating or removing the connection.
    const hasStructural = changes.some(
      c => c.type === "add" || c.type === "remove" || c.type === "replace",
    )
    if (hasStructural) debouncedSave()
  }, [onEdgesChange, debouncedSave])
  const { removeLinkNodeParam } = useLinkNodeParams()

  // Canvas → panel: clicking a node scrolls to its row in the run panel.
  // If the node failed and the panel is closed, it opens straight on "Problemas"
  // — the shortest path between "I saw the red node" and "I know why it broke".
  const revealNodeInPanel = useCallback((node: INodeContext) => {
    const panel = useRunPanelStore.getState()
    const execution = useWorkflowExecutionStore.getState()
    if (execution.events.length === 0) return

    const failed = execution.statusWorkflow?.nodes?.some(n => n.id === node.id && n.status === "failed")
    if (!panel.open && failed) panel.openAt("problems")
    if (panel.open || failed) panel.reveal(node.id)
  }, [])

  // Path highlight (hover/pin) and zoom-based level of detail.
  // Destructured on purpose: the handlers are individually stable, but the
  // returned object is new on every render — using it as a dependency would make
  // `handleNodeClick` unstable and re-render every node (NodeRenderer is
  // `memo` and receives `onNodeClick` as a prop).
  const {
    onNodeMouseEnter,
    onNodeMouseLeave,
    onNodeClick: onNodeFocusClick,
    onPaneClick,
  } = useCanvasFocus()
  useZoomLod()

  const handleNodeClick = useCallback((event: React.MouseEvent, node: INodeContext) => {
    revealNodeInPanel(node)
    onNodeFocusClick(event, node)
  }, [revealNodeInPanel, onNodeFocusClick])

  // Warns the user when trying to close/reload the page with edits in
  // progress — and ONLY in that case. Always warning, as it used to, made the
  // browser say "changes may not be saved" right after a save, and that was
  // exactly the doubt the user had ("did it save or not?").
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      const { saveStatus } = useWorkflowSaveStore.getState()
      if (saveStatus === 'idle' || saveStatus === 'saved') return
      event.preventDefault();
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Atalho Ctrl+S / Cmd+S para salvar o workflow
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        saveWorkflow()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [saveWorkflow])

  // Listens for the Command Palette event to add a node to the canvas
  useEffect(() => {
    function handleCommandAddNode(e: Event) {
      const node = (e as CustomEvent).detail
      if (!node?.name) return

      const apiNode = nodesAPI.find(n => n.name === node.name)
      if (!apiNode) return

      const viewPort = reactFlowInstance.getViewport()
      const clientWidth = domNode.current?.clientWidth ?? 0
      const clientHeight = domNode.current?.clientHeight ?? 0

      const properties: Record<string, string> = {}
      apiNode.properties.forEach(field => {
        const isObject = typeof field.default === "object"
        properties[field.name] = isObject ? field.default as string : field.default as string ?? ""
      })

      const newNode: INodeContext = {
        id: uuid(),
        type: getTypeIcon(node),
        data: {
          ...node,
          fields: apiNode.properties,
          properties,
          // A single place: `data` is built here and in `loadNodes`, and a field
          // forgotten in one of them works on the new node and vanishes on reload.
          ...contratoDoNo(apiNode, properties),
        },
        position: {
          x: (clientWidth / 2) - viewPort.x - 80,
          y: (clientHeight / 2) - viewPort.y - 30,
        },
      }

      setNodes(prev => [...prev, newNode])
      setNewlyAddedNodeId(newNode.id)
    }

    window.addEventListener("command-add-node", handleCommandAddNode)
    return () => window.removeEventListener("command-add-node", handleCommandAddNode)
  }, [nodesAPI, reactFlowInstance, setNodes, setNewlyAddedNodeId])

  // Initializes static references — on mount only.
  // setFlowContext here only updates the context's 3 immutable fields
  // (reactFlowInstance, flowRef, reloadWorkflow). Dynamic fields
  // (nodesAPI, credentials, pinnedNodes, drawerState) moved to the
  // workflowCatalogStore (Zustand).
  useEffect(() => {
    setFlowContext({
      flowRef: domNode,
      reactFlowInstance,
      reloadWorkflow,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Syncs workflowName and flagActive into the dedicated store when the
  // workflow changes. These fields used to live in FlowContext, but the Zustand
  // refactor (3089cba) moved them to useWorkflowSaveStore. The setFlowContext
  // here was writing to nonexistent fields → workflowName stayed "" and every
  // save fell into 'needs_name'; flagActive always true left Run enabled on
  // deactivated workflows.
  useEffect(() => {
    const saveStore = useWorkflowSaveStore.getState()
    saveStore.setWorkflowName(workflow?.name ?? "")
    saveStore.setFlagActive(workflow?.flag_ative ?? true)
  }, [workflow?.name, workflow?.flag_ative])

  // Resets stores when switching workflows — the Zustand stores are global,
  // so navigating /workflow/A → /workflow/B, A's run/save state would
  // contaminate B (phantom "completed" nodes, invalid lastSavedSnapshot,
  // false-positive isDirty, etc.). Clears before the new canvas is hydrated.
  useEffect(() => {
    useWorkflowExecutionStore.getState().resetExecution()
    // The column memory does NOT follow the execution reset: it belongs to the
    // workflow, not to the run — only switching workflows clears it (and
    // reopening the same one doesn't). Node ids of a duplicated workflow repeat
    // the original's, so without this cut A's columns would show up as
    // suggestions in B.
    useKnownColumnsStore.getState().prepararParaWorkflow(idDaRota ?? null)
    // Clears the catalog's per-workflow fields (pins, newly-added, drawer). nodesAPI
    // and credentials belong to the user (global) and stay intact.
    useWorkflowCatalogStore.getState().resetWorkflowScoped()
    // A highlight pinned in A would point to ids that don't exist in B.
    useCanvasViewStore.getState().resetView()
    // The sub-workflow viewer covers the canvas: left open, A's sub-workflow
    // would sit on top of B's editor, with a trail of nonexistent nodes.
    useSubflowDrilldownStore.getState().close()
    // Clears snapshot and status — workflowName/flagActive are repopulated by
    // the other useEffect when the `workflow` prop arrives.
    //
    // In an existing workflow the true baseline is the post-hydration one (the
    // first real initSnapshot); until then, with no snapshot, the detector
    // stays quiet. On the creation screen there will be no hydration at all —
    // and without a baseline the detector never ran, so a new workflow never
    // said "não salvo". There the baseline is the empty canvas: the first node
    // is already an edit. snapshotIniciadoEm is reset in both cases: the
    // self-correction window belongs to the new workflow's hydration, and what
    // opens it is that initSnapshot.
    useWorkflowSaveStore.setState({
      lastSavedSnapshot: idDaRota ? null : JSON.stringify({ name: "", nodes: [], edges: [] }),
      lastSavedAt: null,
      lastError: null,
      isSaving: false,
      saveStatus: 'idle',
      snapshotIniciadoEm: null,
    })
    // Lets the snapshot hydration effect run again for the new workflow.
    snapshotInitializedFor.current = null
    // And the viewport one: B's is B's, not the framing done for A.
    initialFitDone.current = false
    // The canvas goes back to waiting until B's graph comes in.
    setHidratado(false)
  }, [workflow?.id_hash, idDaRota])

  // Loads the workflow's pins
  useEffect(() => {
    if (workflow?.id_hash) loadPinnedNodes()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow?.id_hash])

  async function loadPinnedNodes() {
    if (!workflow?.id_hash) return
    const dados = dadoOuAviso(await GisFlowService.listPinnedNodes(workflow.id_hash), "Erro ao carregar nós fixados")
    if (dados?.pinned_nodes) setPinnedNodes(dados.pinned_nodes)
  }

  useEffect(() => {
    setOpen(false)
    removeLinkNodeParam()
    if (status === "authenticated") {
      // Fires in parallel — cuts ~N×latency to ~max(latencies).
      // Both lists are global to the user and survive switching workflows
      // (resetWorkflowScoped preserves them): what decides whether there is a
      // download is the store's TTL. Before, going to /projects and opening
      // another workflow re-downloaded ~100 KB of catalog and the canvas only
      // drew after it arrived.
      Promise.all([getNodesAPI(), getCredentialsAPI()]).catch(() => { /* each fetch logs its own error */ })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  const initialFitDone = useRef(false)

  // Loads the workflow's nodes and edges (doesn't handle the snapshot — that
  // lives in another effect that fires once ReactFlow has processed the data).
  //
  // Hydration is IDEMPOTENT per workflow object, and doesn't react to the
  // identity of `nodesAPI`. Before, any catalog writer (Ctrl+K became one, by
  // calling ensureNodesAPI with an expired TTL) swapped the list reference and
  // this effect redrew the graph from `workflow.definition` — the object
  // fetched ONCE when the page opened. The canvas went back to its initial
  // state and the next save wrote that reversal to the backend. Only what truly
  // needs to re-hydrate (restoring a version via reloadWorkflow) swaps the
  // `workflow` OBJECT, and that is what the guard lets through.
  const hidratadoPara = useRef<IWorkflow | null>(null)
  const catalogoDeNosPronto = nodesAPI.length > 0
  useEffect(() => {
    if (!workflow || !catalogoDeNosPronto) return
    if (hidratadoPara.current === workflow) return
    hidratadoPara.current = workflow
    // loadEdges needs the ports declared by each node to resolve the source
    // handle — which is why it consumes loadNodes' return value.
    const loadedNodes = loadNodes()
    loadEdges(loadedNodes)
    setHidratado(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow, catalogoDeNosPronto])

  // Initializes the reference snapshot AFTER ReactFlow processes nodes/edges.
  // Uses buildPayload() — the same function isDirty uses — to guarantee full
  // symmetry between the initial snapshot and the later comparison. Without
  // it, detect-dirty flagged "Não salvo" even with no edits, because the
  // initial snapshot (loadedNodes directly) differed subtly from the current
  // snapshot (nodes via useNodes(), already processed by ReactFlow).
  const snapshotInitializedFor = useRef<string | null>(null)
  useEffect(() => {
    if (!workflow?.id_hash) return
    if (snapshotInitializedFor.current === workflow.id_hash) return
    if (!nodesAPI?.length || nodes.length === 0) return

    snapshotInitializedFor.current = workflow.id_hash
    const { nodesReq, edgesReq } = buildPayload()
    // The server's `updated_at` is the "saved at" the chip shows before the
    // first save of this session. `fromBackend` because the date has no offset.
    initSnapshot(
      nodesReq, edgesReq, workflow.name ?? "",
      fromBackend(workflow.updated_at)?.valueOf() ?? null,
      viewportSalvoValido(workflow.definition?.viewport) ? workflow.definition.viewport : null,
    )
    // F10: undo/redo history baseline with the freshly hydrated state. Without
    // this the history starts empty and the FIRST edge edit was not undoable
    // (undo guards pointer <= 0). Mirrors the save's initSnapshot.
    captureBaseline()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, workflow?.id_hash, workflow?.name, nodesAPI?.length])

  // Restores the saved viewport, or frames the nodes, after loading.
  //
  // The saved viewport used to be handed to <ReactFlow> via `defaultViewport`.
  // But that prop applies ONCE, on mount — and the canvas mounts before the
  // workflow arrives (the page renders with `workflow` undefined while
  // fetching). The real value arrived late and was ignored; this effect saw a
  // saved viewport, skipped fitView, and the workflow opened at (0,0) with zoom
  // 1, as if it had never been saved. `setViewport` actually applies it. No rAF:
  // framing needs the measured nodes, restoring a viewport doesn't — and
  // waiting a frame means flashing in the wrong position.
  useEffect(() => {
    if (nodes.length > 0 && !initialFitDone.current) {
      initialFitDone.current = true
      const savedViewport = workflow?.definition?.viewport
      if (viewportSalvoValido(savedViewport)) {
        reactFlowInstance.setViewport(savedViewport)
      } else {
        // No saved viewport — frames all nodes
        requestAnimationFrame(() => reactFlowInstance.fitView({ padding: 0.15 }))
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes])

  async function getNodesAPI() {
    try {
      await useWorkflowCatalogStore.getState().ensureNodesAPI()
    } catch (err) {
      createToast.error("Erro ao carregar nós", String(err))
    }
  }

  async function getCredentialsAPI() {
    try {
      await useWorkflowCatalogStore.getState().ensureCredentials()
    } catch (err) {
      createToast.error("Erro ao carregar credenciais", String(err))
    }
  }

  // The assembly itself lives in utils/build-canvas, pure: the sub-workflow
  // viewer draws ANOTHER workflow's graph with the same rules, and duplicating them
  // would make `data` diverge between the two canvases.
  function loadEdges(loadedNodes: INodeContext[] = []) {
    const edges = buildEdges(workflow?.definition, loadedNodes)
    setEdges(edges)
    return edges
  }

  function loadNodes() {
    const nodes = buildNodes(workflow?.definition, nodesAPI)
    setNodes(nodes)
    return nodes
  }

  function addEdgeWithKey(connection: Connection, from_key?: string, to_key?: string) {
    setEdges(prev => [
      ...prev,
      {
        ...connection,
        id: uuid(),
        type: 'custom',
        data: {
          ...(from_key ? { from_key } : {}),
          ...(to_key   ? { to_key   } : {}),
        },
      }
    ])
  }

  function handleConnectNodes(connections: Connection) {
    // Validation lives in `validarConexao` (a single home, derived from the
    // catalog): self-connection, duplicate, funnel without ports and
    // incompatible type. `isValidConnection` already holds back the gesture in
    // most cases; this is the second line (and the one that talks) — the toast
    // explains what the refused line doesn't say.
    const recusa = validarConexao(connections, nodes as never[], edges)
    if (recusa) {
      toast.warning(MENSAGEM_DE_RECUSA[recusa])
      return
    }

    const sourceNode = nodes.find(n => n.id === connections.source)
    const targetNode = nodes.find(n => n.id === connections.target)

    // from_key candidates: the node's output fields (see getCandidateKeys).
    // Same rule used by the handle's "+" button (drawer) — see resolve-edge-keys.
    const candidateKeys = getCandidateKeys(sourceNode?.data)

    // Only filled when the target declares multiple named inputs — the rule
    // lives in resolve-edge-keys because the "+" button (drawer) creates edges too.
    const to_key = resolveToKey(connections.targetHandle, targetNode?.data?.inputs)

    if (connections.sourceHandle) {
      const handleIsDataKey = candidateKeys.some(f => f.name === connections.sourceHandle)

      if (handleIsDataKey) {
        // Port handle (DefaultTypeIcon, triggers): the handle already is the data key
        addEdgeWithKey(connections, connections.sourceHandle, to_key)
        return
      }

      // Routing handle (e.g. "true"/"false"): the DATA key still needs to be
      // chosen, but it isn't worth interrupting — it is born with the first
      // candidate and the edge badge lets you change it.
      addEdgeWithKey(connections, candidateKeys[0]?.name, to_key)
      return
    }

    // No sourceHandle: same rule. Zero candidates leaves the edge without a
    // from_key (the executor spreads everything via inputs.update — legacy
    // behavior kept for nodes with no declared schema).
    addEdgeWithKey(connections, candidateKeys[0]?.name, to_key)
  }

  return (
    <>

      {/* Closing without naming must GIVE BACK the status. `saveWorkflow` answers
          an empty name with `setStatus('needs_name')`; if the status already is
          that, the store selector compares equal, nothing re-renders, the effect
          that opens this dialog doesn't fire — and the Save button stops doing
          anything. While the name was editable on the canvas there was a way
          out; now there isn't. */}
      <UnsavedDialog
        open={showUnsavedDialog}
        onOpenChange={aberto => {
          setShowUnsavedDialog(aberto)
          if (!aberto) fecharSemNomear()
        }}
        onSave={() => { setShowUnsavedDialog(false); saveWorkflow() }}
        onDiscard={() => { setShowUnsavedDialog(false); fecharSemNomear() }}
      />

      <WorkflowDrawer />

      <NodeConfigModal />

      <div className="flex w-full h-full relative">

        {/* The canvas area is a wrapper of its own so that it SHRINKS when the
            assistant drawer opens — and with it the add-node button, which
            used to be anchored to the page and ended up under the drawer. With
            the drawer closed the wrapper is exactly the box from before. */}
        <div className="relative flex h-full min-w-0 flex-1">

        {/* Hidden on a phone along with the rest of editing: a button that opens a
            catalog to insert nodes makes no sense on a canvas where they can be
            neither positioned nor connected. */}
        {/* While the workflow loads the button is hidden (and doesn't pulse): the
            canvas is empty because the graph hasn't arrived yet, not because the
            workflow is new. */}
        {!canvasSomenteLeitura && (
          <Button
            size="icon"
            onClick={() => setNodesDrawerState('opened')}
            className={`absolute z-10 top-5 right-5 h-11 w-11 rounded-lg shadow-lg
              bg-primary hover:bg-primary/90 text-primary-foreground border-0
              transition-all hover:scale-105 active:scale-95
              ${carregando ? "opacity-0 pointer-events-none" : ""}
              ${nodes.length === 0 && !carregando ? "add-node-pulse" : ""}`}
            title="Adicionar nó"
          >
            <TbPlus size={22} strokeWidth={2.5} />
          </Button>
        )}

        <ReactFlow nodes={nodes}
          colorMode={theme}
          ref={domNode}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          nodeTypes={nodeTypesFlow}
          edgeTypes={customEdges}
          onConnect={handleConnectNodes}
          // A16: the forbidden line doesn't even stick — same rule as onConnect,
          // derived from the catalog (see utils/valida-conexao).
          isValidConnection={(c) => validarConexao(c as Connection, nodes as never[], edges) === null}
          onNodeClick={handleNodeClick}
          onNodeMouseEnter={onNodeMouseEnter}
          onNodeMouseLeave={onNodeMouseLeave}
          onPaneClick={onPaneClick}
          onlyRenderVisibleElements
          // Viewer on a phone. `elementsSelectable` stays on on purpose: tapping a
          // node is how the configuration opens and how the path highlight
          // anchors — turning it off would take navigation away along with
          // editing. `deleteKeyCode` goes away because an external keyboard (or
          // the system's own) can still reach the canvas.
          nodesDraggable={!canvasSomenteLeitura}
          nodesConnectable={!canvasSomenteLeitura}
          edgesReconnectable={!canvasSomenteLeitura}
          deleteKeyCode={canvasSomenteLeitura ? null : undefined}
        >

          <CanvasInteractionProvider>
          <CanvasViewLayer />
          <CanvasLoading carregando={carregando} />

          {/* The save chip goes on the same row as the breadcrumb — it is next to the
              workflow name that people look for "is this saved?". */}
          <WorkflowLocation workspaceId={workflow?.workspace_id} carregando={carregando}>
            <GlobalSaveIndicator />
          </WorkflowLocation>

          <ActionsButton workflow={workflow} />

          <RunPanel />

          <Background
            variant={theme === "dark" ? BackgroundVariant.Cross : BackgroundVariant.Dots} gap={12} size={1} />

          <CanvasToolbar
            onUndo={undo}
            onRedo={redo}
            canUndo={canUndo}
            canRedo={canRedo}
            onSaveSnapshot={saveSnapshot}
          />

          </CanvasInteractionProvider>
        </ReactFlow>

        </div>

        {/* A flex sibling of the canvas, not an overlay: the canvas shrinks and both
            stay visible — you can watch the workflow appear while reading the
            explanation. The assistant does NOT save; applying is what brings the
            definition here, and saving is still the Save button.

            The snapshot comes BEFORE `setNodes`: it is what lets Ctrl+Z undo
            an apply, which is the safety net of a destructive button. */}
        <AssistentePainel
          workflowId={workflow?.id_hash}
          abrirPorPadrao={!idDaRota}
          onAplicar={aplicarDoAssistente}
        />

        {/* Overlaid on the canvas, not inside it: it is a second React Flow, with
            its own provider, drawing the graph of the executed sub-workflow. */}
        <SubflowViewer rootLabel={workflow?.name ?? ""} />
      </div>

    </>
  )
}

export default ReactFlowComponent
