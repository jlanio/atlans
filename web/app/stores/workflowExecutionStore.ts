import { create } from 'zustand'
import { Edge } from '@xyflow/react'
import { INodeStatusWorkFlow, IStatusWorkflow, StatusNodeStatusWorkFlow, StatusWorkflow } from '@/context/useFlowContext'

/** Origin of the line — separate from the lifecycle (`status`).
 *
 * Before, everything lived in `status` ("started"/"completed"/"failed" mixed with
 * "debug" and "log"), and the panel had to filter by negation ("everything that is
 * neither an error nor a print"). With `kind` each panel tab has a direct predicate.
 */
export type EventKind = 'lifecycle' | 'stdout' | 'debug'

/** Severity — independent of the lifecycle. */
export type EventLevel = 'info' | 'warn' | 'error'

/** Normalized execution event, as it arrives from the WebSocket or the HTTP replay. */
export interface RunEvent {
  /** Arrival order, assigned by the store. It is the `key` of the rows in the
   *  "Bruto" (raw) tab: keying by the array index made rotation (which removes
   *  stdout from the MIDDLE of the list) shift the index of every survivor, and
   *  React unmounted/remounted thousands of rows at once. */
  seq: number
  /** Epoch ms of the event in the BACKEND — not the arrival time in the browser.
   *  Using local time broke the timeline in the re-attach replay: the whole
   *  history got the timestamp of the moment of reconnection. */
  ts: number
  node?: string
  kind: EventKind
  level: EventLevel
  status?: string
  node_name?: string
  node_type?: string
  message?: string | null
  /** `print()` lines from an AGGREGATED stdout event (the executor gathers the
   *  output in ~200 ms windows instead of emitting one event per line).
   *
   *  It is the ONLY source of truth for the output: the executor stopped repeating
   *  the same text in `message`, because the duplication blew the frame's 64 KB
   *  ceiling and the event arrived reduced to the control fields — the panel lost
   *  the batch's 200 lines at once, silently. */
  lines?: string[] | null
  duration_ms?: number | null
  output_keys?: string[] | null
  debug_output?: Record<string, string> | null
  traceback?: string | null
  error_category?: string | null
  retryable?: boolean | null
  branch_result?: boolean
  cache_hit?: boolean
  schema_drift?: { missing: string[]; extra: string[] } | null
  /** Id of the canvas SubWorkflow node, when the event came from INSIDE a
   *  sub-workflow. The child's nodes do not exist on the parent's canvas; without
   *  this the line appeared in the panel without saying where it came from, and
   *  clicking it did nothing. */
  subworkflow_parent?: string | null
  raw: object
}

export type WsState = 'idle' | 'connecting' | 'open' | 'closed'

/** Ceiling on events kept in the panel's memory.
 *
 *  Exported because the producer (the per-frame buffer in `useExecuteWorkflow`)
 *  needs the SAME number: with the tab hidden `requestAnimationFrame` does not run
 *  and the raw buffer would grow without limit before the rotation here had a
 *  chance to act — a `for i in range(200000): print(i)` filled hundreds of MB. */
export const MAX_RUN_EVENTS = 2000

/** Raw payload from the events channel (WS or HTTP history). */
export interface RawEvent {
  node?: string
  kind?: string
  level?: string
  status?: string
  timestamp?: number
  duration_ms?: number | null
  error?: string | null
  message?: string | null
  extra?: {
    node_name?: string
    node_type?: string
    message?: string
    lines?: string[]
    output_keys?: string[]
    output_columns?: Record<string, string[]>
    debug_output?: Record<string, string>
    traceback?: string
    error_category?: string
    retryable?: boolean
    branch_result?: boolean
    cache_hit?: boolean
    schema_drift?: { missing: string[]; extra: string[] }
    subworkflow_parent_node?: string
  } | null
}

/** Normalizes the channel payload into `RunEvent`.
 *
 * `kind`/`level` are derived from `status` when absent: the history in Redis has
 * a 1h TTL, so right after a deploy there are still events published with the
 * old schema circulating in the replay.
 */
/** Origin of the line, with the old-schema derivation in a single place.
 *
 *  Whatever decides whether an event touches the canvas uses exactly this
 *  function — relying on raw `data.kind` would treat a `status:"debug"` without
 *  `kind` (Redis history, up to 1h after a deploy) as lifecycle. */
export function eventKind(data: RawEvent): EventKind {
  if (data.kind) return data.kind as EventKind
  if (data.status === 'log') return 'stdout'
  if (data.status === 'debug') return 'debug'
  return 'lifecycle'
}

export function toRunEvent(data: RawEvent): RunEvent {
  const status = data.status
  const kind = eventKind(data)
  const level: EventLevel =
    (data.level as EventLevel) ?? (status === 'failed' || status === 'error' ? 'error' : 'info')

  return {
    // Replaced by a monotonic value in `appendEvents`/`loadHistoricalEvents`
    // — the normalizer does not know the run's counter.
    seq: 0,
    ts: data.timestamp != null ? data.timestamp * 1000 : Date.now(),
    node: data.node,
    kind,
    level,
    status,
    node_name: data.extra?.node_name,
    node_type: data.extra?.node_type,
    message: data.extra?.message ?? data.error ?? data.message ?? null,
    lines: data.extra?.lines ?? null,
    duration_ms: data.duration_ms ?? null,
    output_keys: data.extra?.output_keys ?? null,
    debug_output: data.extra?.debug_output ?? null,
    traceback: data.extra?.traceback ?? null,
    error_category: data.extra?.error_category ?? null,
    retryable: data.extra?.retryable ?? null,
    branch_result: data.extra?.branch_result,
    cache_hit: data.extra?.cache_hit,
    schema_drift: data.extra?.schema_drift ?? null,
    subworkflow_parent: data.extra?.subworkflow_parent_node ?? null,
    raw: data as object,
  }
}

/** `source → edges` adjacency, memoized by array identity.
 *
 * Without an index the BFS below scanned ALL edges for each visited node —
 * O(branches × nodes × edges) on every WebSocket message. The edges array comes
 * from `useEdges()` and only changes when the topology changes, so the WeakMap
 * hits on practically every call and frees the entry by itself when the array dies.
 */
const adjacenciaPorArestas = new WeakMap<Edge[], Map<string, Edge[]>>()

function adjacencia(allEdges: Edge[]): Map<string, Edge[]> {
  let index = adjacenciaPorArestas.get(allEdges)
  if (index) return index
  index = new Map<string, Edge[]>()
  for (const edge of allEdges) {
    const lista = index.get(edge.source)
    if (lista) lista.push(edge)
    else index.set(edge.source, [edge])
  }
  adjacenciaPorArestas.set(allEdges, index)
  return index
}

function computeLosingBranches(statusNodes: INodeStatusWorkFlow[], allEdges: Edge[]) {
  const losingNodeIds = new Set<string>()
  const losingEdgeIds = new Set<string>()
  const porOrigem = adjacencia(allEdges)

  for (const node of statusNodes) {
    if (node.branch_result === undefined) continue
    const losingHandle = node.branch_result ? "false" : "true"
    // A read index instead of `queue.shift()`, which is O(n) on an array and
    // made the BFS quadratic on long branches.
    const queue: string[] = []
    let head = 0
    for (const edge of porOrigem.get(node.id) ?? []) {
      if (edge.sourceHandle === losingHandle) {
        losingEdgeIds.add(edge.id)
        queue.push(edge.target)
      }
    }
    const visited = new Set<string>()
    while (head < queue.length) {
      const nodeId = queue[head++]
      if (visited.has(nodeId)) continue
      visited.add(nodeId)
      losingNodeIds.add(nodeId)
      for (const edge of porOrigem.get(nodeId) ?? []) {
        losingEdgeIds.add(edge.id)
        if (!visited.has(edge.target)) queue.push(edge.target)
      }
    }
  }
  return { losingNodeIds, losingEdgeIds }
}

/** Signature of the already resolved branches — changes only when a Conditional decides. */
function assinaturaDeRamos(statusNodes: INodeStatusWorkFlow[]): string {
  let assinatura = ""
  for (const node of statusNodes) {
    if (node.branch_result === undefined) continue
    assinatura += node.id + (node.branch_result ? "1" : "0") + "|"
  }
  return assinatura
}

/** Losing branches, short-circuited by (signature, edges identity).
 *
 * The recomputation is not just expensive: returning NEW Sets on every message
 * re-renders every node and every edge subscribed to them, even when no
 * Conditional decided anything. Preserving identity is half the gain.
 */
let ultimaAssinatura: string | null = null
let ultimasArestas: Edge[] | null = null
let ultimosRamos = { losingNodeIds: new Set<string>(), losingEdgeIds: new Set<string>() }

function ramosPerdedores(statusNodes: INodeStatusWorkFlow[], allEdges: Edge[]) {
  const assinatura = assinaturaDeRamos(statusNodes)
  if (assinatura === ultimaAssinatura && allEdges === ultimasArestas) return ultimosRamos
  ultimaAssinatura = assinatura
  ultimasArestas = allEdges
  ultimosRamos = computeLosingBranches(statusNodes, allEdges)
  return ultimosRamos
}

/** `id → state` index of the canvas.
 *
 * Each node and each edge built its OWN Map over the whole node list, on every
 * message — the O(1) cost promised by the comment multiplied by N+E.
 * Here it is built once, and the components subscribe only to their own entry.
 */
function indexarPorId(nodes: INodeStatusWorkFlow[]): Map<string, INodeStatusWorkFlow> {
  const index = new Map<string, INodeStatusWorkFlow>()
  for (const node of nodes) index.set(node.id, node)
  return index
}

/** Outcomes after which the run is history: nothing else writes to the canvas.
 *
 *  The client applies events in BATCHES, per `requestAnimationFrame` frame.
 *  With the tab in the background (or the desktop window unfocused) the frame
 *  does not run, but the WebSocket keeps delivering — so the batch stays pending
 *  for an indefinite time while the run finishes and is settled. When the user
 *  comes back, the delayed frame fires and reapplies OLD events over an already
 *  closed run: the node whose last event in the batch was `started` starts
 *  spinning again, and now there is no socket, no `isExecuting`, nothing to
 *  settle it again. That is why the outcome has to be final in here, and not only
 *  at the instant it is decided. */
export const RUN_ENCERRADO: ReadonlySet<string> = new Set(['completed', 'failed', 'cancelled'])

const SEM_STATUS: Map<string, INodeStatusWorkFlow> = new Map()

/** Applies the event ceiling by discarding the OLDEST `stdout` events.
 *
 * Lifecycle events are never the victims: they are the source of per-node state
 * in the "Nós" (nodes) tab, and throwing them away made an already completed node
 * show up again as "aguardando" (waiting) — contradicting the canvas itself — in
 * runs that print a lot. The cut is done in blocks to amortize the cost of this scan.
 */
function rotacionar(eventos: RunEvent[]): { events: RunEvent[]; dropped: number } {
  if (eventos.length <= MAX_RUN_EVENTS) return { events: eventos, dropped: 0 }

  const bloco = Math.floor(MAX_RUN_EVENTS * 0.2)
  const alvo = eventos.length - MAX_RUN_EVENTS + bloco
  const kept: RunEvent[] = []
  let dropped = 0
  for (const candidate of eventos) {
    if (dropped < alvo && candidate.kind === "stdout") {
      dropped++
      continue
    }
    kept.push(candidate)
  }
  // Not enough stdout to free space (a huge workflow, almost all of it
  // lifecycle): falls back to pure chronological discard.
  if (kept.length > MAX_RUN_EVENTS) {
    const corte = Math.min(kept.length, kept.length - MAX_RUN_EVENTS + bloco)
    kept.splice(0, corte)
    dropped += corte
  }
  return { events: kept, dropped }
}

interface WorkflowExecutionState {
  statusWorkflow: IStatusWorkflow | null
  /** Per-node state, indexed. The cards and the edges subscribe to ONE entry here
   *  instead of the whole `statusWorkflow` object — so only what actually changed
   *  re-renders. Always present (empty Map before the first run). */
  statusById: Map<string, INodeStatusWorkFlow>
  losingNodeIds: Set<string> | undefined
  losingEdgeIds: Set<string> | undefined
  debugMode: boolean
  isExecuting: boolean
  events: RunEvent[]
  /** The socket's real state — the panel's "live" indicator reads from here.
   *  Before, it read `isExecuting`, which is a proxy: a dead socket stayed green. */
  wsState: WsState
  /** Run whose events are loaded. It may be a historical (finished) run opened
   *  from the panel, not necessarily the run being executed. */
  viewingRunId: string | null
  /** true when the events came from the HTTP endpoint and not from a live run. */
  isHistorical: boolean
  /** How many output lines were discarded — by LOCAL rotation and by SERVER
   *  back-pressure (the `dropped` field of the events frame). Shown in the
   *  "Bruto" tab — truncating silently makes the panel look complete when it is
   *  not, and the server's discard is precisely what the user has no way of
   *  noticing on their own. */
  droppedEvents: number
  /** Epoch ms of the run's first event, fixed on arrival.
   *  Kept outside `events` because the list rotates: deriving the start from the
   *  first surviving item would shift all of the panel's `+Xs` offsets. */
  runStartedTs: number | null
  /** Canvas SubWorkflow nodes that have already executed something inside.
   *
   *  Kept here, and fed at O(1) per event, because the canvas needs the answer
   *  per node: scanning `events` in a selector would cost a pass over the whole
   *  list, per SubWorkflow node, on every WebSocket message. It survives the
   *  rotation of `events` on purpose — the node does not stop having been
   *  executed because the oldest event was discarded. */
  subflowRoots: Set<string>
  /** `seq` counter. Reset together with the events list. */
  eventSeq: number
  /** Outcome of the run (`__workflow_complete__`), stored at O(1) on arrival.
   *
   *  It exists so the panel bar can say "concluído em 3,2 s" (done in 3.2 s)
   *  WITHOUT anyone having to rebuild the timeline — with the panel closed that
   *  rebuild was pure CPU work that never reached the screen. */
  runOutcome: RunOutcome | null
}

export interface RunOutcome {
  status: "completed" | "failed" | "cancelled"
  durationMs: number | null
  error: string | null
  category: string | null
  retryable: boolean | null
}

/** Synthetic id the backend uses to signal the end of the run.
 *  Repeated here (and not imported from run-panel/timeline) so the store does
 *  not depend on a component. */
const WF_COMPLETE = "__workflow_complete__"

function desfechoDoEvento(event: RunEvent): RunOutcome | null {
  if (event.node !== WF_COMPLETE) return null
  return {
    status: event.status === "failed" ? "failed" : event.status === "cancelled" ? "cancelled" : "completed",
    durationMs: event.duration_ms ?? null,
    error: event.message ?? null,
    category: event.error_category ?? null,
    retryable: event.retryable ?? null,
  }
}

interface WorkflowExecutionActions {
  startExecution(nodes: INodeStatusWorkFlow[]): void
  setTaskId(taskId: string): void
  updateNodeStatuses(nodes: INodeStatusWorkFlow[], allEdges: Edge[]): void
  completeExecution(status: StatusWorkflow, nodes: INodeStatusWorkFlow[], allEdges: Edge[]): void
  failExecution(): void
  resetExecution(): void
  setDebugMode(v: boolean): void
  setWsState(v: WsState): void
  /** Appends a BATCH of events with a single copy of the array.
   *
   *  One event per `set()` did `[...events, event]` per message — O(H²)
   *  cumulatively, and in the re-attach replay (thousands of events) that alone
   *  froze the tab. The producer groups by frame and delivers everything at once. */
  appendEvents(events: RunEvent[]): void
  /** Adds to the discard counter the events the SERVER threw away due to
   *  back-pressure (the WebSocket's 500-slot buffer evicts the oldest stdout and
   *  reports how many in the frame's `dropped` field).
   *
   *  Without this the amber warning in the "Bruto" tab counted only the local
   *  rotation: the panel claimed to be complete while hundreds of `print()` lines
   *  had been discarded along the way. */
  registrarDescartados(quantidade: number): void
  clearEvents(): void
  loadHistoricalEvents(runId: string, events: RunEvent[]): void
}

export const useWorkflowExecutionStore = create<WorkflowExecutionState & WorkflowExecutionActions>((set) => ({
  statusWorkflow: null,
  statusById: SEM_STATUS,
  losingNodeIds: undefined,
  losingEdgeIds: undefined,
  debugMode: false,
  isExecuting: false,
  events: [],
  wsState: 'idle',
  viewingRunId: null,
  isHistorical: false,
  droppedEvents: 0,
  runStartedTs: null,
  subflowRoots: new Set(),
  eventSeq: 0,
  runOutcome: null,

  startExecution: (nodes) => {
    const iniciais = nodes.map(n => ({ ...n, status: 'idle' as const }))
    set({
      isExecuting: true,
      wsState: 'connecting',
      statusWorkflow: {
        status: 'queued',
        nodes: iniciais,
      },
      statusById: indexarPorId(iniciais),
      losingNodeIds: undefined,
      losingEdgeIds: undefined,
      // Clears the previous execution's events — the panel must start clean.
      events: [],
      droppedEvents: 0,
      runStartedTs: null,
      viewingRunId: null,
      isHistorical: false,
      subflowRoots: new Set(),
      eventSeq: 0,
      runOutcome: null,
    })
  },

  setTaskId: (taskId) => {
    set(state => ({
      viewingRunId: taskId,
      statusWorkflow: state.statusWorkflow ? {
        ...state.statusWorkflow,
        task_id: taskId,
        status: 'running' as const,
      } : null,
    }))
  },

  updateNodeStatuses: (nodes, allEdges) => {
    set(state => {
      // A closed run does not go back. See `RUN_ENCERRADO`: without this guard,
      // a late batch returned the node to `started` AND the workflow to `running`,
      // leaving the blue ring spinning forever on an already finished run.
      if (state.statusWorkflow && RUN_ENCERRADO.has(state.statusWorkflow.status)) {
        return {}
      }
      const { losingNodeIds, losingEdgeIds } = ramosPerdedores(nodes, allEdges)
      return {
        statusWorkflow: state.statusWorkflow ? {
          ...state.statusWorkflow,
          status: 'running' as const,
          nodes,
        } : null,
        statusById: indexarPorId(nodes),
        losingNodeIds,
        losingEdgeIds,
      }
    })
  },

  completeExecution: (status, nodes, allEdges) => {
    // The run ended: no node may stay in `started`. Before, only cancellation
    // settled them, and so a node `completed` lost along the way (the socket
    // drops without warning, the server evicts under pressure, the executor
    // discards with a full queue) left that node spinning FOREVER — with the
    // run already marked as finished in the panel and in the dashboard.
    //
    // The two outcomes are different and must not be confused:
    //   cancelled → the work was actually interrupted; goes back to `idle`.
    //   others    → the node probably finished and it is the news that got lost;
    //               becomes `unknown`, which the UI shows as "resultado não
    //               recebido" (result not received). Painting it green would be
    //               inventing a result.
    const paradoComo: StatusNodeStatusWorkFlow = status === 'cancelled' ? 'idle' : 'unknown'
    const settled = nodes.some(n => n.status === 'started')
      ? nodes.map(n => (n.status === 'started' ? { ...n, status: paradoComo } : n))
      : nodes
    const { losingNodeIds, losingEdgeIds } = ramosPerdedores(settled, allEdges)
    set(state => ({
      statusWorkflow: {
        status,
        // Preserves the task_id: the panel uses it to offer "ver na observabilidade"
        // (view in observability) and to reload this run's events after it finishes.
        task_id: state.statusWorkflow?.task_id,
        nodes: settled,
      },
      statusById: indexarPorId(settled),
      losingNodeIds,
      losingEdgeIds,
      isExecuting: false,
      wsState: 'closed',
    }))
  },

  failExecution: () => {
    set(state => {
      // Same invariant as `completeExecution`: the run closed, so no node
      // survives in `started`. Without this, exhausting the reconnections closed
      // the panel but left the nodes spinning — the symptom we wanted to
      // eliminate, reintroduced through the give-up path.
      const nodes = state.statusWorkflow?.nodes ?? []
      const settled = nodes.some(n => n.status === 'started')
        ? nodes.map(n => (n.status === 'started' ? { ...n, status: 'unknown' as const } : n))
        : nodes
      return {
        statusWorkflow: state.statusWorkflow ? {
          ...state.statusWorkflow,
          status: 'failed' as const,
          nodes: settled,
        } : null,
        statusById: state.statusWorkflow ? indexarPorId(settled) : state.statusById,
        isExecuting: false,
        wsState: 'closed',
        losingNodeIds: undefined,
        losingEdgeIds: undefined,
      }
    })
  },

  resetExecution: () => {
    set({
      statusWorkflow: null,
      statusById: SEM_STATUS,
      losingNodeIds: undefined,
      losingEdgeIds: undefined,
      // `debugMode` is NOT included here: it is a user preference, not run state.
      // Since the Executar button clears the previous run before firing the new one,
      // resetting it here erased the yellow toggle on the very click in which debug
      // should apply — the request went out in debug, but the UI said otherwise.
      isExecuting: false,
      wsState: 'idle',
      // Clears events too — without this, when switching workflows the previous
      // one's logs stayed visible in the panel until the next execution.
      events: [],
      droppedEvents: 0,
      runStartedTs: null,
      viewingRunId: null,
      isHistorical: false,
      subflowRoots: new Set(),
      eventSeq: 0,
      runOutcome: null,
    })
  },

  setDebugMode: (v) => {
    set({ debugMode: v })
  },

  setWsState: (v) => {
    set({ wsState: v })
  },

  appendEvents: (lote) => {
    if (lote.length === 0) return
    set(state => {
      let eventSeq = state.eventSeq
      let runStartedTs = state.runStartedTs
      let runOutcome = state.runOutcome
      // A new Set only when someone gets in: recreating it on every batch would make
      // every node that queries this set re-render on every frame.
      let subflowRoots = state.subflowRoots
      for (const event of lote) {
        // The batch's events just came out of `toRunEvent`, in this same turn of
        // the event loop — nobody else has seen them, numbering them here is the
        // only way for the counter to be the store's.
        event.seq = eventSeq++
        runStartedTs ??= event.ts
        const pai = event.subworkflow_parent
        if (pai && !subflowRoots.has(pai)) {
          if (subflowRoots === state.subflowRoots) subflowRoots = new Set(state.subflowRoots)
          subflowRoots.add(pai)
        }
        runOutcome = desfechoDoEvento(event) ?? runOutcome
      }

      // One copy per batch — not one per event.
      const { events, dropped } = rotacionar(state.events.concat(lote))
      return {
        events,
        droppedEvents: dropped > 0 ? state.droppedEvents + dropped : state.droppedEvents,
        runStartedTs,
        subflowRoots,
        eventSeq,
        runOutcome,
      }
    })
  },

  registrarDescartados: (quantidade) => {
    if (!(quantidade > 0)) return
    set(state => ({ droppedEvents: state.droppedEvents + quantidade }))
  },

  clearEvents: () => {
    set({ events: [], droppedEvents: 0, runStartedTs: null, subflowRoots: new Set(), eventSeq: 0, runOutcome: null })
  },

  loadHistoricalEvents: (runId, events) => {
    const subflowRoots = new Set<string>()
    let runOutcome: RunOutcome | null = null
    for (const event of events) {
      if (event.subworkflow_parent) subflowRoots.add(event.subworkflow_parent)
      runOutcome = desfechoDoEvento(event) ?? runOutcome
    }
    // The same ceiling as the live path: the endpoint returns up to 5000 events and
    // rendering them all at once locked up the tab for seconds — the historical
    // path cannot be worse than the live one.
    const { events: mantidos, dropped } = rotacionar(events)
    let seq = 0
    for (const event of mantidos) event.seq = seq++
    set({
      events: mantidos,
      droppedEvents: dropped,
      runStartedTs: events.length > 0 ? events[0].ts : null,
      viewingRunId: runId,
      isHistorical: true,
      wsState: 'idle',
      subflowRoots,
      eventSeq: seq,
      runOutcome,
    })
  },
}))
