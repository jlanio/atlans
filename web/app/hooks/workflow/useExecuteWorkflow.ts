import { useParams } from "next/navigation"
import { useSaveWorkflow } from "./useSaveWorkflow"
import { useEffect, useRef } from "react"
import { useSession } from "next-auth/react"
import { INodeContext, INodeStatusWorkFlow, StatusWorkflow } from "@/context/useFlowContext"
import { createToast } from "@/utils/createToast"
import { dayjs } from "@/lib/dayjs"
import { useNodes, useEdges, useReactFlow, Edge } from "@xyflow/react"
import { GisFlowService } from "@/service/GisFlowService"
import { getWsUrl } from "@/utils/env"
import { useWorkflowExecutionStore, toRunEvent, eventKind, RawEvent, MAX_RUN_EVENTS, RUN_TERMINAL } from "@/app/stores/workflowExecutionStore"
import { useKnownColumnsStore } from "@/app/stores/knownColumnsStore"

/** Synthetic id the backend uses to signal the end of the run. */
const WF_COMPLETE = "__workflow_complete__"

/** Reconnection attempts before giving up on live tracking.
 *  With exponential backoff up to 15s, covers ~2 minutes of instability. */
const MAX_RECONEXOES = 8

/** Maximum silence tolerated on the socket before assuming it dead and recovering.
 *
 *  The server sends a heartbeat (empty batch) every ~20s during the run, so a
 *  healthy connection never gets anywhere near this. It only fires when the
 *  socket has actually died — the Safari case, which drops an idle WebSocket
 *  WITHOUT firing `onclose`: without this watchdog, reconnection (which lives in
 *  `onclose`) was never triggered and the panel spun forever. It is the
 *  transport's safety net; the server heartbeat is the prevention. */
const MAX_SILENCE_MS = 50_000
const WATCHDOG_INTERVAL_MS = 15_000

/** Run status in the backend → panel status. Only the terminal ones are listed:
 *  the others mean "still alive", and absence here is the test itself. */
const TERMINAL_OUTCOME: Record<string, StatusWorkflow> = {
  success:   "completed",
  failed:    "failed",
  cancelled: "cancelled",
}

/** Bridge to the socket OWNER.
 *
 *  This hook is mounted in more than one place at the same time — the canvas
 *  Executar (run) button and the Webhook node's "Testar" (test) tab, inside the
 *  config modal. All of them can TRIGGER a run, but only one can govern the
 *  socket: the execution store is global, so a second instance opened a
 *  competing WebSocket, wrote to the same `wsState` and, when mounting during a
 *  run, also called `startExecution`, wiping the canvas of whoever was already
 *  watching. Whoever triggers without being the owner hands the task_id to the
 *  owner to attach. */
let attachToOwner: ((taskId: string) => void) | null = null

/** Per-frame buffer item, stamped with its source run.
 *
 *  The stamp exists because a delayed flush is asynchronous by nature: the rAF
 *  scheduled while the user was on workflow A fires AFTER the switch to B.
 *  Without the stamp, A's events landed in B's freshly cleared store. */
interface BatchItem {
  runId: string
  data: RawEvent
}

export const useExecuteWorkflow = () => {

  const { saveWorkflow } = useSaveWorkflow()
  const { id } = useParams<{ id: string }>()
  const nodes = useNodes<INodeContext>()
  const edges = useEdges<Edge>()
  const reactFlowInstance = useReactFlow<INodeContext, Edge>()
  // Refs always in sync — the workflow's first execution happened with stale
  // closures captured BEFORE the canvas hydrated (nodes=[]).
  // Result: initialNodes came out empty and the visual feedback on the canvas
  // did not appear on the 1st execution. Reading via ref, any closure consumes
  // the latest value at click time.
  const nodesRef = useRef(nodes)
  useEffect(() => { nodesRef.current = nodes }, [nodes])
  const edgesRef = useRef(edges)
  useEffect(() => { edgesRef.current = edges }, [edges])
  // The run's active WS (trigger OR re-attach). Kept in a ref to (a) close the
  // previous connection before opening another and (b) close it when switching
  // workflows — avoids duplicate/orphan connections feeding the store at once.
  const wsRef = useRef<WebSocket | null>(null)
  // Whether THIS mount triggered a run via the button. Re-attach uses this (and
  // NOT the global isExecuting, which is volatile and lingers between visits) to
  // decide whether to re-attach — avoids clobbering a freshly triggered run.
  const sessionTriggeredRef = useRef(false)
  const { data: session } = useSession()

  // Acessa store para isExecuting e debugMode
  const isExecuting = useWorkflowExecutionStore(s => s.isExecuting)
  const debugMode = useWorkflowExecutionStore(s => s.debugMode)
  const setDebugMode = useWorkflowExecutionStore(s => s.setDebugMode)

  // Batch for the current frame. Each WS message is its own macrotask, so
  // without this React could not batch anything: a replay of 5000 events
  // became 5000 render cycles of the whole canvas, in sequence, on the same
  // thread — the tab froze for seconds when reopening a run in progress.
  const bufferRef = useRef<BatchItem[]>([])
  const frameRef = useRef<number | null>(null)
  // Run whose socket is active NOW. It is the flush gate: a pending rAF from
  // workflow A that fires after the switch to B finds a different id here (or
  // null) and dumps nothing into B's store. That way correctness no longer
  // depends on every cleanup path being right.
  const activeRunRef = useRef<string | null>(null)
  // Synchronous drain of the active attach. It lives in a ref because the code
  // that needs it (the visibility listener, registered once on mount) does not
  // know the `attachToRun` closure.
  const drainNowRef = useRef<() => void>(() => {})

  // ── Stream recovery ──────────────────────────────────────────────────────
  // None of this existed before, and its absence was the bug: the client treated
  // the channel as lossless, when every layer along the path can drop an event
  // and the socket can die without warning.
  const reconexaoRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const attemptsRef = useRef(0)
  // Sockets that WE closed (end of run, workflow switch, new attach).
  // The close code cannot tell them apart: the server closes with 1000 on every
  // normal path — including when the Redis subscription ends without the run
  // having finished, which is exactly the case that needs to reconnect.
  const closedOnPurposeRef = useRef(new WeakSet<WebSocket>())
  // Inactivity watchdog: time of the last message received and the timer that
  // watches the silence. It exists because in Safari a dead socket does not fire
  // `onclose` — without this, the drop went unnoticed and the panel spun
  // forever. See `SILENCIO_MAX_MS`.
  const lastMsgRef = useRef(0)
  const watchdogRef = useRef<ReturnType<typeof setInterval> | null>(null)

  function closeOnPurpose(sock: WebSocket | null | undefined) {
    if (!sock) return
    closedOnPurposeRef.current.add(sock)
    sock.close(1000)
  }

  function cancelReconnect() {
    if (reconexaoRef.current != null) {
      clearTimeout(reconexaoRef.current)
      reconexaoRef.current = null
    }
  }

  function stopWatchdog() {
    if (watchdogRef.current != null) {
      clearInterval(watchdogRef.current)
      watchdogRef.current = null
    }
  }

  /** Watches the socket's silence. In Safari a dead connection does not fire
   *  `onclose`; here we detect it by the absence of traffic and treat it as a drop:
   *  close it (so a late `onclose` does not duplicate) and fall into recovery,
   *  which reconciles through the API or reconnects and rebuilds via the Redis
   *  replay. */
  function startWatchdog(sock: WebSocket, taskId: string) {
    stopWatchdog()
    watchdogRef.current = setInterval(() => {
      if (wsRef.current !== sock) return          // socket already replaced
      if (activeRunRef.current !== taskId) return
      if (!useWorkflowExecutionStore.getState().isExecuting) return
      if (Date.now() - lastMsgRef.current <= MAX_SILENCE_MS) return
      console.warn(
        `[ws/workflow] ${taskId} sem tráfego há >${MAX_SILENCE_MS}ms — ` +
        "socket presumido morto (Safari não dispara onclose) — recuperando",
      )
      stopWatchdog()
      closeOnPurpose(sock)
      if (wsRef.current === sock) wsRef.current = null
      recoverStream(taskId).catch(err =>
        console.error("[ws/workflow] falha ao recuperar o stream", err),
      )
    }, WATCHDOG_INTERVAL_MS)
  }

  /** Closes the panel with the run's REAL outcome, by asking the API.
   *
   *  Returns true when the run has already finished (and the panel was closed).
   *  It is the safety net for a `__workflow_complete__` that did not arrive: the
   *  database knows the outcome even when the live channel failed. */
  async function reconcileRun(taskId: string): Promise<boolean> {
    try {
      const detail = await GisFlowService.getRunDetail(taskId)
      const desfecho = TERMINAL_OUTCOME[detail?.data?.status ?? ""]
      if (!desfecho) return false
      const store = useWorkflowExecutionStore.getState()
      if (!store.isExecuting) return true
      // `completeExecution` settles the stuck nodes: they started, the run ended,
      // and their completion did not arrive — they become `unknown`, not green.
      store.completeExecution(desfecho, store.statusWorkflow?.nodes ?? [], edgesRef.current)
      return true
    } catch {
      // Bad network: nothing can be asserted about the run. Let reconnection
      // try — asserting "failed" here would be inventing an outcome.
      return false
    }
  }

  /** The stream dropped with the run still open: finds out whether it has already
   *  ended and, if not, reconnects with backoff. On reconnecting, the history
   *  replay rebuilds what was lost in the gap — which is why reconnecting is cheap
   *  and correct. */
  async function recoverStream(taskId: string) {
    // Applies NOW what has already arrived. The `requestAnimationFrame` frame may
    // have been pending for a long time (a background tab does not run it) and
    // those events are legitimate information: they need to reach the canvas
    // BEFORE settlement, so that `completeExecution` decides on the most recent
    // state. After it the batch is garbage — and it is discarded right below.
    drainNowRef.current()
    if (await reconcileRun(taskId)) {
      // The run was settled. Anything still in the buffer (or an already
      // scheduled frame) would rewrite the canvas over the outcome, resurrecting
      // as `started` a node that was just resolved.
      discardBatch()
      return
    }
    // `reconcileRun` has an await in the middle: during it the user may have
    // switched workflows, or an `attachToRun` may have already reopened the
    // socket (the Executar button, the re-attach). Reconnecting on top would
    // open a second connection for the same run.
    if (activeRunRef.current !== taskId) return
    if (wsRef.current) return

    if (attemptsRef.current >= MAX_RECONEXOES) {
      // Giving up on LIVE tracking is not giving up on the run: it keeps going on
      // the server. Saying so is what separates "I lost the connection" from
      // "your workflow failed".
      useWorkflowExecutionStore.getState().failExecution()
      createToast.error(
        "Acompanhamento ao vivo interrompido",
        "A execução continua no servidor. Recarregue a página ou acompanhe pela observabilidade.",
      )
      return
    }

    const base = Math.min(1000 * 2 ** attemptsRef.current, 15_000)
    attemptsRef.current += 1
    cancelReconnect()
    // 50-100% jitter, as in the executor's backoff: several tabs that dropped
    // together don't come back in a burst against the same server.
    reconexaoRef.current = setTimeout(() => {
      reconexaoRef.current = null
      // The user may have switched workflows — or reconnected by another route —
      // during the wait.
      if (activeRunRef.current !== taskId || wsRef.current) return
      attachToRun(taskId)
    }, base * (0.5 + Math.random() * 0.5))
  }

  // Discards the pending batch. Called at the THREE exit points (new attach,
  // workflow switch, unmount): closing the WebSocket does not stop an already
  // scheduled flush from running on the next frame with the previous run's events.
  function discardBatch() {
    bufferRef.current = []
    activeRunRef.current = null
    cancelReconnect()
    stopWatchdog()
    if (frameRef.current != null) {
      cancelAnimationFrame(frameRef.current)
      frameRef.current = null
    }
  }

  // Whoever arrived first governs the socket; the others only trigger. The ref is
  // always fresh because `attachToRun` is recreated on every render.
  const isOwnerRef = useRef(false)
  const attachRef = useRef<(taskId: string) => void>(() => {})
  attachRef.current = (taskId: string) => { attachToRun(taskId) }

  useEffect(() => {
    if (attachToOwner === null) {
      isOwnerRef.current = true
      attachToOwner = (taskId) => attachRef.current(taskId)
    }
    return () => {
      if (isOwnerRef.current) {
        attachToOwner = null
        isOwnerRef.current = false
      }
    }
  }, [])

  useEffect(() => {
    // With the tab in the background the browser does NOT run
    // `requestAnimationFrame` callbacks (same in Electron, with
    // backgroundThrottling on): the batch would sit in the buffer, growing with no
    // ceiling, until the user came back. Draining when the tab is hidden delivers
    // what has already arrived and empties everything.
    const onVisibilityChange = () => {
      if (document.visibilityState === "hidden") drainNowRef.current()
    }
    document.addEventListener("visibilitychange", onVisibilityChange)
    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange)
      discardBatch()
    }
    // Only on mount/unmount. `discardBatch` is recreated on every render, but
    // operates exclusively on refs — declaring it as a dependency would
    // re-register the listener on every render without changing anything.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleExecuteWorkflow(inputs: Record<string, unknown> = {}) {

    const store = useWorkflowExecutionStore.getState()
    if (store.isExecuting)
      return
    // Marks that this mount triggered a run — re-attach uses this so as not to
    // clobber the freshly triggered run in case its discovery is in flight.
    sessionTriggeredRef.current = true

    // Immediate visual feedback — the canvas reacts in <16ms, before the save/POST.
    // Source of the nodes in order of priority:
    //   1. nodesRef.current — useNodes hook via ref (avoids a stale closure)
    //   2. reactFlowInstance.getNodes() — fallback if the ref is still empty on the 1st click
    //      (hydrates straight from React Flow's internal store, always up to date)
    // Without this fallback the store stayed with nodes=[] and no WS event
    // found a match (see [ws/workflow] evento sem match de node_id).
    const liveNodes = nodesRef.current.length > 0
      ? nodesRef.current
      : reactFlowInstance.getNodes()
    const initialNodes = liveNodes.map((node) => ({
      ...node,
      id: node.id,
      status: "idle" as const,
    }))
    if (initialNodes.length === 0) {
      createToast.error("Canvas vazio", "Carregue o workflow antes de executar.")
      return
    }
    store.startExecution(initialNodes)

    const respSave = await saveWorkflow({ silent: true })

    if (respSave?.error) {
      store.resetExecution()
      return
    }

    const respExec = await executeWorkflow(inputs)

    if (respExec?.error) {
      createToast.error("Ocorreu um erro no workflow!", respExec?.error.message)
      store.resetExecution()
      return
    }

    // Extra defense: if the backend did not return a task_id, never open a WS with
    // "undefined" in the URL (a guaranteed 4404). Treat it as an error and stop.
    const taskId = respExec?.data?.task_id
    if (!taskId) {
      console.error("[useExecuteWorkflow] POST /execute retornou sem task_id", respExec)
      createToast.error("Falha ao iniciar workflow", "Servidor não retornou task_id.")
      store.resetExecution()
      return
    }

    // If this instance is not the socket owner (the trigger came from the webhook's
    // "Testar" tab, for example), it hands the run to whoever governs — instead
    // of opening a second socket over the same store.
    ;(attachToOwner ?? attachToRun)(taskId)
  }

  // Opens a run's WebSocket and installs the handlers that feed the store
  // (node animation + execution console). Used both on trigger and on
  // re-attaching to a run already in progress — on connecting, the backend
  // replays the run's whole history (Redis) and then streams live. Returns the
  // socket so the caller can close it (e.g. when switching workflows).
  function attachToRun(taskId: string): WebSocket {
    // Closes any previous connection (intentionally) before opening the new one, so
    // there are never two WSs writing to the store at the same time.
    closeOnPurpose(wsRef.current)
    // Discards what is left of the previous run: a pending flush would apply
    // another run's events (and close the wrong socket) on the next frame.
    discardBatch()
    const ws = new WebSocket(`${getWsUrl()}/ws/workflow/${taskId}`)
    wsRef.current = ws
    activeRunRef.current = taskId
    drainNowRef.current = drainNow

    useWorkflowExecutionStore.getState().setWsState("connecting")

    ws.onopen = () => {
      const token = session?.user?.access_token ?? ""
      if (token) ws.send(token)
      // The socket's REAL state — the panel's "live" indicator reads from here instead
      // of inferring from isExecuting, which stayed green with the socket dead.
      useWorkflowExecutionStore.getState().setWsState("open")
      // Connection is up: the next stumble restarts the backoff from zero.
      attemptsRef.current = 0
      // Arms the inactivity watchdog. `onopen` already counts as traffic; from here on
      // the server sends a heartbeat every ~20s, so silence only grows if the
      // socket died (Safari) — and then the watchdog recovers.
      lastMsgRef.current = Date.now()
      startWatchdog(ws, taskId)
    }

    // queued → running transition with the real task_id
    useWorkflowExecutionStore.getState().setTaskId(taskId)

    // Applies the batch accumulated in the frame: one pass over the nodes, one
    // `updateNodeStatuses`, one `appendEvents`. Before, each message paid on its
    // own for the map of ALL nodes, the recomputation of the losing branches over
    // ALL edges and a copy of the events array.
    function drainBatch() {
      const bruto = bufferRef.current
      bufferRef.current = []
      if (bruto.length === 0) return
      // Only what belongs to the active run gets in. Without this filter, the pending
      // rAF from workflow A ran after the switch to B and dumped A's log into B's
      // store — including A's `__workflow_complete__`, which closed B's panel
      // with "Concluído · 0 nós" (done · 0 nodes) for a workflow that never ran.
      const ativo = activeRunRef.current
      const lote = bruto.filter(item => item.runId === ativo).map(item => item.data)
      if (lote.length === 0) return

      // Feeds the execution panel via the store — a single WS connection (before there
      // was a second WS inside the log component, for the same run_id).
      // `toRunEvent` normalizes kind/level and converts the BACKEND timestamp:
      // stamping with local time broke the timeline in the re-attach replay,
      // which redelivers the whole history at once.
      // It goes in BEFORE the `kind` filter below, so that stdout and debug
      // (which don't touch the canvas) also show up in the panel.
      const store = useWorkflowExecutionStore.getState()
      store.appendEvents(lote.map(toRunEvent))

      // Reads the state AFTER the append — and only once per frame.
      const current = useWorkflowExecutionStore.getState()
      let currentNodes = current.statusWorkflow?.nodes ?? []
      let byId = current.statusById
      // Defensive recovery: if the store is still empty (initialNodes did not
      // hydrate in time on the click), repopulates it from React Flow.
      if (currentNodes.length === 0 && lote.some(d => d.node && !d.node.startsWith("__"))) {
        const live = reactFlowInstance.getNodes().map((n) => ({
          ...n,
          id: n.id,
          status: "idle" as const,
        }))
        if (live.length > 0) {
          currentNodes = live
          byId = new Map(live.map(n => [n.id, n as INodeStatusWorkFlow]))
        }
      }

      // Only the LIFECYCLE touches node state. `print()` lines arrive with
      // kind="stdout" and status="log": applying them as a status erased the
      // node's `started` (the blue ring vanished on the first print) and also
      // dragged in the whole re-render cascade over nodes and edges.
      const alterados = new Map<string, INodeStatusWorkFlow>()
      // Columns for the suggestions store — which lives OUTSIDE the run lifecycle.
      // `null` = the node completed WITHOUT publishing columns (non-tabular
      // output, or the key cut off in transport): its entry is erased there,
      // because keeping the old value would assert columns this run did not produce.
      const batchColumns = new Map<string, Record<string, string[]> | null>()
      let fim: RawEvent | null = null
      for (const data of lote) {
        if (data.node === WF_COMPLETE) {
          fim = data
          continue
        }
        if (eventKind(data) !== "lifecycle") continue
        const base = alterados.get(data.node ?? "") ?? byId.get(data.node ?? "")
        if (!base) continue
        if (data.status === "completed") {
          batchColumns.set(base.id, data.extra?.output_columns ?? null)
        }
        const updated: INodeStatusWorkFlow = {
          ...base,
          status: data.status as INodeStatusWorkFlow["status"],
          duration: data.duration_ms ?? undefined,
          error: data.error ?? undefined,
        }
        if (data.extra?.branch_result !== undefined) {
          updated.branch_result = data.extra.branch_result
        }
        if (data.extra?.cache_hit !== undefined) {
          updated.cache_hit = data.extra.cache_hit
        }
        // Columns of each output — they feed the column-name suggestion in the
        // Join and filter fields. They only come from executor 2.4.0 or
        // newer; earlier versions do not publish the key.
        if (data.extra?.output_columns !== undefined) {
          updated.output_columns = data.extra.output_columns
        }
        // Without this, the InputInspector's "Saídas" (outputs) panel never saw the
        // output's real keys — only the "output" fallback, even after running.
        if (data.extra?.output_keys !== undefined) {
          updated.output_keys = data.extra.output_keys
        }
        if (data.extra?.schema_drift !== undefined) {
          updated.schema_drift = data.extra.schema_drift
        }
        alterados.set(base.id, updated)
      }

      // Nothing changed on the canvas: no new nodes array, no new branch Sets —
      // that is what keeps a noisy run from re-rendering the graph for nothing.
      if (alterados.size > 0) {
        current.updateNodeStatuses(
          currentNodes.map(node => alterados.get(node.id) ?? node),
          edgesRef.current,
        )
      }

      // Per-workflow column memory — survives an execution reset/F5 and is
      // what the config modal reads to suggest names.
      if (batchColumns.size > 0) {
        useKnownColumnsStore.getState().aplicarDeExecucao(id, taskId, batchColumns)
      }

      if (fim) {
        const duration = dayjs.duration(Math.round(fim.duration_ms ?? 0)).format("mm[min ]ss[s ] SSS[ms ]")

        // Immediate (ephemeral) toast. The persistent entry in the notification bell
        // is left to ActiveRunsProvider (single source), so as not to duplicate the
        // notification of a run that is also detected by the global polling.
        if (fim.status === "failed") {
          createToast.error("Ocorreu um erro no workflow!", fim.error ?? undefined)
        } else if (fim.status === "cancelled") {
          createToast.info("Execução cancelada", `Interrompida após ${duration}`)
        } else {
          createToast.success(`Workflow concluído em ${duration}`)
        }

        // Reads again — the status block above just updated the store.
        const finalState = useWorkflowExecutionStore.getState()
        finalState.completeExecution(
          fim.status as StatusWorkflow,
          finalState.statusWorkflow?.nodes ?? [],
          edgesRef.current,
        )

        closeOnPurpose(ws)
        // The run ended within THIS batch. What is left in the buffer predates the
        // marker and has nowhere to go; a scheduled frame that ran later would
        // reapply `started` over freshly settled nodes.
        discardBatch()
      }
    }

    function scheduleFlush() {
      if (frameRef.current != null) return
      frameRef.current = requestAnimationFrame(() => {
        frameRef.current = null
        drainBatch()
      })
    }

    // Drains NOW, canceling the pending frame so it does not drain twice.
    function drainNow() {
      if (frameRef.current != null) {
        cancelAnimationFrame(frameRef.current)
        frameRef.current = null
      }
      drainBatch()
    }

    ws.onmessage = (event) => {
      // ANY frame counts as a sign of life — including the heartbeat (empty batch)
      // and even an unreadable frame: what the watchdog watches is the transport's
      // silence, not the content. That is why it is the FIRST line, before parsing.
      lastMsgRef.current = Date.now()

      // The server builds the frame by concatenating raw strings from Redis, so a
      // single corrupted item invalidates the JSON of the ENTIRE batch — including
      // `__workflow_complete__`, if it is in that block. Without this guard the
      // exception bubbled up from onmessage, the socket stayed open and the panel
      // sat at "Executando" (running) with nothing on screen saying a batch was lost.
      let frame: { events?: unknown; dropped?: number } | null = null
      try {
        frame = JSON.parse(event.data)
      } catch (err) {
        console.error("[ws/workflow] frame ilegível — lote descartado", err)
        // Counts it as a visible loss: the "Bruto" (raw) tab shows the warning instead
        // of the log looking complete.
        useWorkflowExecutionStore.getState().registrarDescartados(1)
        return
      }

      // A SINGLE envelope: history replay and live stream arrive in the SAME
      // format — {"type":"events","events":[...],"dropped":N}, with the raw
      // events concatenated by the server. Before, it was one frame (and one
      // render cycle of the whole canvas) per event — up to 5000 of them on re-attach.
      //
      // What decides whether the run ended is the batch's CONTENT, never the
      // envelope: while the client relied on the envelope, the day the server
      // started sending the live stream in batches left the immediate-completion
      // path dead.
      const eventos: RawEvent[] = Array.isArray(frame?.events) ? frame.events : []

      // SERVER back-pressure (the 500-slot buffer evicts old stdout).
      // Without adding this up, the "Bruto" tab drops the warning and the user
      // concludes the script simply did not print those lines.
      if (frame?.dropped) {
        useWorkflowExecutionStore.getState().registrarDescartados(frame.dropped)
      }

      if (eventos.length === 0) return
      for (const evento of eventos) bufferRef.current.push({ runId: taskId, data: evento })

      // The end of the run cannot wait for the next frame: `completeExecution` and
      // `ws.close()` happen inside the flush. With the tab in the background the rAF
      // does not run — the run got stuck at "Executando", with the button at
      // "Cancelar" and the completion toast only showing up minutes later, when
      // returning to the tab.
      if (eventos.some(e => e.node === WF_COMPLETE)) {
        drainNow()
        return
      }

      // Memory ceiling for the hidden tab, where the rAF never comes: the
      // MAX_RUN_EVENTS rotation only acts AFTER the drain, inside the store, so
      // without this a `for i in range(200000): print(i)` piled up hundreds of MB
      // in the buffer.
      if (bufferRef.current.length >= MAX_RUN_EVENTS) {
        drainNow()
        return
      }

      scheduleFlush()
    }

    ws.onerror = (err) => {
      // Decides nothing: `onclose` comes right after, and that is where recovery
      // lives. Failing here killed the run at the first instability, before
      // even trying to reconnect.
      console.error("[ws/workflow] erro no socket", err)
    }

    ws.onclose = (event) => {
      // Clears the ref and stops the watchdog if this is still the active WS (it may
      // already have been replaced — in that case the running watchdog belongs to
      // ANOTHER socket).
      if (wsRef.current === ws) {
        wsRef.current = null
        stopWatchdog()
      }
      const storeState = useWorkflowExecutionStore.getState()
      storeState.setWsState("closed")

      // We closed it on purpose (end of run, workflow switch, new attach), or this
      // socket has already been replaced, or the run has already closed: nothing
      // to recover.
      if (closedOnPurposeRef.current.has(ws)) return
      if (activeRunRef.current !== taskId) return
      if (!storeState.isExecuting) return

      // From here down the stream dropped with the run still open. THE CODE DOES NOT
      // TELL THEM APART: the server also closes with 1000 when the Redis
      // subscription ends without `__workflow_complete__` — and treating that as a
      // normal close was what left nodes spinning and the panel at
      // "Executando" forever, with no toast, no log, no output.
      console.warn(
        `[ws/workflow] stream de ${taskId} caiu com o run aberto (code=${event.code}) — recuperando`,
      )
      // `.catch` is mandatory: `void` on an async that rejects becomes an unhandled
      // rejection, which in some browsers brings down the whole page.
      recoverStream(taskId).catch(err =>
        console.error("[ws/workflow] falha ao recuperar o stream", err),
      )
    }

    return ws
  }

  async function executeWorkflow(inputs: Record<string, unknown> = {}) {
    // Note: do NOT check isExecuting here — handleExecuteWorkflow already did so
    // at the start and then called store.startExecution(), which sets
    // isExecuting=true. A guard here (which existed before the Zustand refactor)
    // blocks the POST and leaves respExec=undefined → task_id "undefined" in the
    // WebSocket URL → 4404. That was the real bug observed on the canvas.
    const data = await GisFlowService.executeWorkflow(id, inputs, debugMode)
    return data
  }

  // Waits for the canvas to hydrate (React Flow populating the nodes) before
  // seeding/attaching, up to `timeoutMs`. Without this, the run's history replay
  // could arrive before any node existed to paint — hence re-attach animated only
  // sometimes, depending on who won the race (network vs. canvas hydration).
  function waitForCanvasNodes(shouldAbort: () => boolean, timeoutMs = 8000): Promise<boolean> {
    return new Promise((resolve) => {
      const start = Date.now()
      const tick = () => {
        if (shouldAbort()) return resolve(false)
        if (reactFlowInstance.getNodes().length > 0) return resolve(true)
        if (Date.now() - start > timeoutMs) return resolve(false)
        setTimeout(tick, 100)
      }
      tick()
    })
  }

  // Re-attaches to the animations of a run still in progress when (re)opening the
  // workflow. The canvas animates 100% from the store, which is volatile and is
  // wiped on mount (workflow/index.tsx). Without this, reopening a "running"
  // workflow showed a static canvas — it looked like nothing was happening. Here
  // we discover the most recent live run and reopen the SAME WebSocket as the
  // trigger: the backend replays the run's whole history and continues live,
  // repainting the nodes. It only re-attaches to live runs (running/pending); if
  // the last run has already finished, the canvas stays clean.
  useEffect(() => {
    if (!id) return
    // Only the socket owner re-attaches. Without this guard, opening the config
    // modal of a Webhook node during a run mounted a second instance that called
    // `startExecution` (wiping the canvas in progress) and opened a competing
    // socket for the SAME run.
    if (!isOwnerRef.current) return
    // Do NOT use the global isExecuting as a gate: it is volatile and, when
    // returning to a workflow, it may be TRUE as a leftover from the previous visit
    // (the reset lives in another effect, in workflow/index.tsx, which runs AFTER
    // this one). That was what made re-attach alternate between visits
    // (works/stops/works). Here we reset the per-mount control; a manual trigger
    // turns it on in handleExecuteWorkflow.
    sessionTriggeredRef.current = false

    let cancelled = false
    const openedFor = id
    const aborted = () => cancelled || openedFor !== id

    ;(async () => {
      const resp = await GisFlowService.getObservabilityRuns({ workflow_id: id, limit: 1 })
      const latest = resp?.data?.runs?.[0]
      // Aborts if the workflow changed during the await, if there is no run, or if it
      // is not alive. If a manual trigger started in this mount, it does not clobber.
      if (aborted() || !latest) return
      if (latest.status !== "running" && latest.status !== "pending") {
        // The most recent run has already finished: nothing to re-attach — but its
        // `node_stats` holds `output_columns`, and seeding the suggestions store
        // from here is what makes the columns appear when OPENING the
        // workflow, without running anything. Before, they only existed while
        // the run's session lived: F5 and the hint was gone ("sometimes it works").
        //
        // Deliberately best-effort: a suggestion is a hint, not state — with no
        // run whose details can be fetched (403 for a restricted role, 404, stats
        // without the key due to an old executor or the 8KB cut), the editor
        // carries on as today, with no toast when the workflow opens.
        //
        // A LIVE run does not pass through here on purpose: the WebSocket replay
        // redelivers the history and writes the columns through the live path (`fresh`).
        const detalhe = await GisFlowService.getRunDetail(latest.run_id)
        if (aborted()) return
        const stats = detalhe?.data?.node_stats ?? {}
        const columnsByNode: Record<string, { porPorta: Record<string, string[]>; parciais?: boolean }> = {}
        for (const [nodeId, stat] of Object.entries(stats)) {
          if (stat?.output_columns) {
            // `__truncated__` = the executor's 8KB cut reduced each list to the
            // first 50 — the suggestion label warns "lista parcial" (partial list).
            columnsByNode[nodeId] = { porPorta: stat.output_columns, parciais: !!stat.__truncated__ }
          }
        }
        if (Object.keys(columnsByNode).length > 0) {
          useKnownColumnsStore.getState().semearDoHistorico(id, latest.run_id, columnsByNode)
        }
        return
      }
      if (sessionTriggeredRef.current) return

      // Waits for the canvas to hydrate BEFORE seeding — without this the replay
      // arrived with no nodes to paint (the cause of the intermittent animation on reopen).
      await waitForCanvasNodes(aborted)
      if (aborted() || sessionTriggeredRef.current) return

      // Seeds the store with the canvas's current nodes (idle) — but ONLY when there
      // is no state for this run yet. `startExecution` wipes nodes and events, and
      // doing that over a run we are already tracking (a second mount of the
      // hook, a re-run effect) erases the progress already painted and bets
      // everything on the replay arriving. If the socket drops right after, the
      // canvas ends up worse than it was before the "recovery".
      const store = useWorkflowExecutionStore.getState()
      // ...or when the state we have for this run is an OUTCOME. The server has
      // just said it is still alive, so our closing was premature (a racing
      // reconciliation, or giving up after exhausting the reconnections).
      // Without re-seeding, the replay would arrive at a run the store considers
      // closed and the `updateNodeStatuses` guard would discard it, leaving the
      // canvas frozen on the wrong outcome.
      const encerrado = !!store.statusWorkflow && RUN_TERMINAL.has(store.statusWorkflow.status)
      if (store.viewingRunId !== latest.run_id || !store.statusWorkflow || encerrado) {
        const source = nodesRef.current.length > 0 ? nodesRef.current : reactFlowInstance.getNodes()
        const liveNodes = source.map((node) => ({ ...node, id: node.id, status: "idle" as const }))
        store.startExecution(liveNodes)
        createToast.info("Reconectado à execução em andamento")
      }
      attachToRun(latest.run_id)
    })()

    return () => {
      cancelled = true
      // Closes the active WS when leaving/switching workflows. Marked as
      // intentional, otherwise `onclose` would treat the screen change as a drop
      // and try to reconnect to a run the user left behind.
      closeOnPurpose(wsRef.current)
      // Navigating /workflow/A → /workflow/B does NOT remount the component: the
      // buffer and the pending frame survive the switch. Closing the socket is not
      // enough — messages already queued in the event loop would still be delivered.
      discardBatch()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  return {
    executeWorkflow: handleExecuteWorkflow,
    isExecuting,
    debugMode,
    setDebugMode,
  }
}
