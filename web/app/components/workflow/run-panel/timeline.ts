import { INodeStatusWorkFlow } from "@/context/useFlowContext"
import { RunEvent, RunOutcome } from "@/app/stores/workflowExecutionStore"

/** Synthetic node id the backend uses to signal the end of the run. */
export const WF_COMPLETE = "__workflow_complete__"

/** `unknown`: the run ended and this node's completion never arrived — see
 *  `StatusNodeStatusWorkFlow` in useFlowContext. Distinct from `pending`
 *  (not started) and from `running` (happening now). */
export type NodeRunStatus = "pending" | "running" | "completed" | "failed" | "unknown"

export interface NodePrint {
  offsetMs: number
  text: string
}

export interface NodeProblem {
  message: string
  traceback?: string | null
  category?: string | null
  retryable?: boolean | null
}

/** A workflow node seen as a SINGLE row that evolves in state.
 *
 * The old panel stacked two events per node (`started` and then
 * `completed`), so a 30-node workflow became 60 rows that merely
 * repeated the canvas animation and drowned prints and errors.
 */
export interface NodeRun {
  nodeId: string
  /** Canvas node this row represents. Equal to `nodeId` for the workflow's own
   *  nodes; for a node inside a sub-workflow it is the SubWorkflow node that
   *  called it — the only point on the canvas there is to focus, highlight or
   *  configure. */
  canvasNodeId: string
  /** Filled when the row came from inside a sub-workflow: name of the
   *  SubWorkflow node on the parent's canvas. */
  subFlow: string | null
  name: string
  type: string
  status: NodeRunStatus
  /** ms since the start of the run — answers "how long until we got here". */
  startOffsetMs: number | null
  startedAt: number | null
  durationMs: number | null
  outputKeys: string[]
  cacheHit: boolean
  branchResult?: boolean
  schemaDrift?: { missing: string[]; extra: string[] } | null
  debug: Record<string, string> | null
  prints: NodePrint[]
  problem: NodeProblem | null
  /** Start order; nodes not yet started go to the end. */
  order: number
}

export interface RunTimeline {
  startTs: number | null
  nodes: NodeRun[]
  problems: NodeRun[]
  totalPrints: number
  slowest: NodeRun | null
  counts: { total: number; done: number; failed: number; running: number; pending: number; unknown: number }
  workflow: {
    status: "idle" | "running" | "completed" | "failed" | "cancelled"
    durationMs: number | null
    error: string | null
    category: string | null
    retryable: boolean | null
  }
}

/** Readable name of a canvas node (the event carries `node_name`; the canvas, alias). */
function canvasNodeLabel(node: INodeStatusWorkFlow): string {
  const data = (node as { data?: { alias?: string; name?: string } }).data
  return data?.alias || data?.name || node.id
}

function canvasNodeType(node: INodeStatusWorkFlow): string {
  return (node as { data?: { name?: string } }).data?.name ?? ""
}

function emptyNodeRun(nodeId: string, name: string, type: string, order: number): NodeRun {
  return {
    nodeId, canvasNodeId: nodeId, subFlow: null, name, type,
    status: "pending",
    startOffsetMs: null,
    startedAt: null,
    durationMs: null,
    outputKeys: [],
    cacheHit: false,
    schemaDrift: null,
    debug: null,
    prints: [],
    problem: null,
    order,
  }
}

const CANVAS_STATUS: Record<string, NodeRunStatus> = {
  idle:      "pending",
  started:   "running",
  completed: "completed",
  failed:    "failed",
  unknown:   "unknown",
}

/** Seeds the timeline with the state the canvas already knows.
 *
 * The per-node state on the canvas is accumulated message by message and does
 * NOT go through rotation — whereas the event list has a ceiling (here and in
 * the Redis history, capped at 5000). In a run that prints a lot, the oldest
 * lifecycle events disappear, and deriving from them alone would make a
 * completed node reappear as "aguardando" (waiting), contradicting the canvas
 * itself. Starting from the canvas, the events only enrich (offset, outputs,
 * prints, traceback) what is already true.
 */
function seedFromCanvas(node: INodeStatusWorkFlow, order: number): NodeRun {
  const run = emptyNodeRun(node.id, canvasNodeLabel(node), canvasNodeType(node), order)
  run.status = CANVAS_STATUS[node.status] ?? "pending"
  if (node.duration != null) run.durationMs = node.duration
  if (node.output_keys) run.outputKeys = node.output_keys
  if (node.cache_hit !== undefined) run.cacheHit = !!node.cache_hit
  if (node.branch_result !== undefined) run.branchResult = node.branch_result
  if (node.schema_drift) run.schemaDrift = node.schema_drift
  if (node.status === "failed" && node.error) {
    run.problem = { message: node.error, traceback: null, category: null, retryable: null }
  }
  return run
}

/**
 * Converts the chronological event stream into a per-node timeline.
 *
 * `canvasNodes` comes in so that nodes not yet executed show up as
 * "aguardando" (waiting) — the panel shows the whole graph, not only what has
 * already emitted an event.
 */
export function buildTimeline(
  events: RunEvent[],
  canvasNodes: INodeStatusWorkFlow[],
  runStartedTs: number | null = null,
): RunTimeline {
  const byId = new Map<string, NodeRun>()
  let order = 0

  for (const node of canvasNodes) {
    byId.set(node.id, seedFromCanvas(node, Number.MAX_SAFE_INTEGER))
  }

  // Run start: recorded in the store when the first event arrives, and not
  // read from `events[0]` — the list rotates, and once the beginning is dropped
  // ALL offsets would become relative to the oldest surviving event.
  // Timestamps come from the backend, so this also holds for the re-attach replay.
  const startTs = runStartedTs ?? (events.length > 0 ? events[0].ts : null)

  const workflow: RunTimeline["workflow"] = {
    status: events.length > 0 ? "running" : "idle",
    durationMs: null,
    error: null,
    category: null,
    retryable: null,
  }

  const offsetOf = (ts: number) => (startTs == null ? 0 : Math.max(0, ts - startTs))

  for (const ev of events) {
    const nodeId = ev.node
    if (!nodeId) continue

    if (nodeId === WF_COMPLETE) {
      workflow.status = ev.status === "failed" ? "failed"
        : ev.status === "cancelled" ? "cancelled"
        : "completed"
      workflow.durationMs = ev.duration_ms ?? null
      workflow.error = ev.message ?? null
      workflow.category = ev.error_category ?? null
      workflow.retryable = ev.retryable ?? null
      continue
    }

    let run = byId.get(nodeId)
    if (!run) {
      // A node that emitted an event but is not on the canvas: a node INSIDE a
      // sub-workflow, published with the prefixed id `pai::filho`. The row joins
      // the list tied to the parent's SubWorkflow node — without that it showed
      // the raw id, did not say it came from another workflow, and clicking it
      // was a silent no-op (`focusNode` does not find the id on the canvas).
      const pai = ev.subworkflow_parent ?? null
      run = emptyNodeRun(
        nodeId,
        ev.node_name ?? (pai ? nodeId.slice(pai.length + 2) : nodeId),
        ev.node_type ?? "",
        Number.MAX_SAFE_INTEGER,
      )
      if (pai) {
        run.canvasNodeId = pai
        run.subFlow = byId.get(pai)?.name ?? pai
      }
      byId.set(nodeId, run)
    }
    if (ev.node_name) run.name = ev.node_name
    if (ev.node_type) run.type = ev.node_type

    if (ev.kind === "stdout") {
      // The executor aggregates output in ~200 ms windows, so one event carries
      // SEVERAL lines in `lines` — one panel row per item. `lines` is the
      // only source: the executor stopped repeating the same text in `message`
      // because the duplication blew through the event's 64 KB ceiling and the
      // whole batch arrived here reduced to the control fields, with no output.
      const offset = offsetOf(ev.ts)
      if (ev.lines) {
        for (const linha of ev.lines) run.prints.push({ offsetMs: offset, text: linha })
      }
      continue
    }

    if (ev.kind === "debug") {
      if (ev.debug_output) run.debug = { ...(run.debug ?? {}), ...ev.debug_output }
      continue
    }

    // kind === "lifecycle"
    if (ev.status === "started") {
      run.status = "running"
      run.startedAt = ev.ts
      run.startOffsetMs = offsetOf(ev.ts)
      run.order = order++
      continue
    }

    if (ev.status === "completed" || ev.status === "failed") {
      run.status = ev.status === "failed" ? "failed" : "completed"
      // Does not wipe what the canvas already knew: an event without `duration_ms`
      // would erase the seeded duration.
      if (ev.duration_ms != null) run.durationMs = ev.duration_ms
      if (ev.output_keys) run.outputKeys = ev.output_keys
      if (ev.cache_hit !== undefined) run.cacheHit = !!ev.cache_hit
      if (ev.branch_result !== undefined) run.branchResult = ev.branch_result
      if (ev.schema_drift) run.schemaDrift = ev.schema_drift
      if (run.order === Number.MAX_SAFE_INTEGER) run.order = order++
      // A node that finished with no observed `started` (truncated replay):
      // rebuilds the start from the end minus the duration, to keep the offset.
      if (run.startOffsetMs == null) {
        run.startOffsetMs = Math.max(0, offsetOf(ev.ts) - (ev.duration_ms ?? 0))
      }
      if (ev.status === "failed") {
        run.problem = {
          message: ev.message ?? "Falha sem mensagem.",
          traceback: ev.traceback,
          category: ev.error_category,
          retryable: ev.retryable,
        }
      }
    }
  }

  const nodes = [...byId.values()].sort((a, b) => {
    if (a.order !== b.order) return a.order - b.order
    return a.name.localeCompare(b.name)
  })

  // Single pass: six separate sweeps over the node list were expensive
  // because this runs on every panel update during the run.
  const counts = { total: nodes.length, done: 0, failed: 0, running: 0, pending: 0, unknown: 0 }
  const problems: NodeRun[] = []
  let totalPrints = 0
  let slowest: NodeRun | null = null

  for (const node of nodes) {
    if (node.status === "completed") counts.done++
    else if (node.status === "failed") counts.failed++
    else if (node.status === "running") counts.running++
    // `unknown` has its own counter: added to `pending`, the panel's progress bar
    // would never close on an already finished run, and the number would
    // contradict the canvas, which shows the node as resolved-without-answer.
    else if (node.status === "unknown") counts.unknown++
    else counts.pending++

    if (node.problem != null) problems.push(node)
    totalPrints += node.prints.length
    if (node.durationMs != null && (slowest == null || node.durationMs > slowest.durationMs!)) {
      slowest = node
    }
  }

  return { startTs, nodes, problems, totalPrints, slowest, counts, workflow }
}

/**
 * Summary for the panel BAR, without touching the event list.
 *
 * With the panel collapsed the only consumer of the timeline is the 34px bar,
 * which needs counts, status, slowest node and running node — none of that
 * requires walking up to 2000 events, allocating prints or sorting.
 * Rebuilding everything eight times per second was CPU that never reached the
 * screen.
 *
 * The run's outcome (total duration, error) comes from the store, which records
 * it in O(1) when the `__workflow_complete__` event arrives.
 */
export function buildHudTimeline(
  canvasNodes: INodeStatusWorkFlow[],
  runStartedTs: number | null,
  outcome: RunOutcome | null,
  hasEvents: boolean,
): RunTimeline {
  const nodes: NodeRun[] = []
  const problems: NodeRun[] = []
  const counts = { total: 0, done: 0, failed: 0, running: 0, pending: 0, unknown: 0 }
  let slowest: NodeRun | null = null

  for (const node of canvasNodes) {
    const run = seedFromCanvas(node, Number.MAX_SAFE_INTEGER)
    nodes.push(run)
    if (run.status === "completed") counts.done++
    else if (run.status === "failed") counts.failed++
    else if (run.status === "running") counts.running++
    else if (run.status === "unknown") counts.unknown++
    else counts.pending++
    if (run.problem != null) problems.push(run)
    if (run.durationMs != null && (slowest == null || run.durationMs > slowest.durationMs!)) {
      slowest = run
    }
  }
  counts.total = nodes.length

  return {
    startTs: runStartedTs,
    nodes,
    problems,
    totalPrints: 0,
    slowest,
    counts,
    workflow: {
      status: outcome?.status ?? (hasEvents ? "running" : "idle"),
      durationMs: outcome?.durationMs ?? null,
      error: outcome?.error ?? null,
      category: outcome?.category ?? null,
      retryable: outcome?.retryable ?? null,
    },
  }
}

/** Renders the timeline as plain text — used by "copy all" and "download". */
export function timelineToText(timeline: RunTimeline, runId: string | null): string {
  const lines: string[] = []
  lines.push(`# Execução ${runId ?? "(sem id)"}`)
  lines.push(`# status: ${timeline.workflow.status}`)
  if (timeline.workflow.durationMs != null) lines.push(`# duração: ${timeline.workflow.durationMs.toFixed(0)}ms`)
  lines.push("")

  for (const node of timeline.nodes) {
    const offset = node.startOffsetMs != null ? `+${(node.startOffsetMs / 1000).toFixed(2)}s` : "—"
    const duration = node.durationMs != null ? `${node.durationMs.toFixed(0)}ms` : "—"
    // The indentation keeps the pasted text reading like the screen: you can see
    // what happened inside the sub-workflow without mixing it up with the parent's nodes.
    const dentro = node.subFlow ? `  ↳ [${node.subFlow}] ` : "  "
    lines.push(`${offset.padStart(8)}${dentro}${node.status.padEnd(9)} ${node.name}  (${node.type}) ${duration}`)
    for (const print of node.prints) {
      lines.push(`            | ${print.text}`)
    }
    if (node.problem) {
      lines.push(`            ! ${node.problem.message}`)
      if (node.problem.category) lines.push(`            ! categoria: ${node.problem.category}`)
      if (node.problem.traceback) {
        for (const tl of node.problem.traceback.split("\n")) lines.push(`            ! ${tl}`)
      }
    }
  }

  if (timeline.workflow.error) {
    lines.push("")
    lines.push(`# erro do workflow: ${timeline.workflow.error}`)
  }
  return lines.join("\n")
}
