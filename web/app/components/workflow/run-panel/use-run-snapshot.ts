import { useCallback, useSyncExternalStore } from "react"
import { RunEvent, useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { NodeRun, RunTimeline, buildHudTimeline, buildTimeline } from "./timeline"

/** Aggregation window for panel updates.
 *
 * A busy run emits dozens of events per second, and each of them changed
 * `events` AND `statusWorkflow.nodes`. Subscribed to the store via selector, the
 * panel re-rendered — and rebuilt the whole timeline — once per message, along
 * with every node row. Aggregating at ~8 frames per second is imperceptible to
 * the eye and cuts the work by an order of magnitude. The stopwatches
 * (`Elapsed`) have their own tick, so the "live" feel does not depend on this
 * rate.
 */
const REFRESH_MS = 120

export interface RunSnapshot {
  timeline: RunTimeline
  events: RunEvent[]
  droppedEvents: number
}

/**
 * A single snapshot per window, shared by all consumers.
 *
 * The run panel and the sub-workflow viewer ask for the same timeline. With one
 * timer and one rebuild per hook, opening the viewer during a run doubled the
 * cost: `buildTimeline` walks the whole event list (up to 2000) and sorts the
 * nodes, eight times per second, on the same thread that animates the canvas.
 * Here the rebuild happens once and both read the same object.
 */
const inscritos = new Set<() => void>()
/** Subset that needs the FULL timeline (panel open, sub-workflow viewer).
 *  Empty ⇒ only the bar summary is built. */
const querTimeline = new Set<() => void>()
let timer: ReturnType<typeof setTimeout> | null = null
let cancelarStore: (() => void) | null = null

function readSnapshot(anterior: RunSnapshot | null): RunSnapshot {
  const state = useWorkflowExecutionStore.getState()
  const nosDoCanvas = state.statusWorkflow?.nodes ?? []
  const timeline = querTimeline.size > 0
    ? buildTimeline(state.events, nosDoCanvas, state.runStartedTs)
    : buildHudTimeline(nosDoCanvas, state.runStartedTs, state.runOutcome, state.events.length > 0)
  return {
    timeline: anterior ? reaproveitar(anterior.timeline, timeline) : timeline,
    events: state.events,
    droppedEvents: state.droppedEvents,
  }
}

/** Is a `NodeRun` interchangeable with the previous one? Cheap shallow comparison.
 *
 * `startedAt` goes in together with `prints.length` on purpose: two different
 * runs never start at the same instant, so no prints array crosses over a run
 * change. Within the same run prints only grow, and equal length implies equal
 * content.
 */
function mesmoNo(a: NodeRun, b: NodeRun): boolean {
  return a.nodeId === b.nodeId
    && a.status === b.status
    && a.durationMs === b.durationMs
    && a.startOffsetMs === b.startOffsetMs
    && a.startedAt === b.startedAt
    && a.order === b.order
    && a.name === b.name
    && a.type === b.type
    && a.subFlow === b.subFlow
    && a.cacheHit === b.cacheHit
    && a.branchResult === b.branchResult
    && a.prints.length === b.prints.length
    && a.outputKeys.length === b.outputKeys.length
    && a.debug === b.debug
    && a.schemaDrift === b.schemaDrift
    && a.problem?.message === b.problem?.message
}

/**
 * Returns the new timeline reusing the previous one's objects where nothing changed.
 *
 * `buildTimeline` is pure and reallocates ALL `NodeRun`s on every call, so the
 * (memoized) panel rows re-rendered eight times per second even when a single
 * node had changed. Here identity is restored by value comparison — and, when
 * nothing changed in any node, the whole previous snapshot is returned, which
 * also holds the `useMemo`s of `visible`/`groups`.
 */
function reaproveitar(anterior: RunTimeline, nova: RunTimeline): RunTimeline {
  const antes = new Map<string, NodeRun>()
  for (const node of anterior.nodes) antes.set(node.nodeId, node)

  const reusados = new Map<string, NodeRun>()
  let todosIguais = anterior.nodes.length === nova.nodes.length
  const nodes = nova.nodes.map((node, i) => {
    const velho = antes.get(node.nodeId)
    if (velho && mesmoNo(velho, node)) {
      reusados.set(node.nodeId, velho)
      if (anterior.nodes[i] !== velho) todosIguais = false
      return velho
    }
    todosIguais = false
    return node
  })

  if (
    todosIguais
    && anterior.totalPrints === nova.totalPrints
    && anterior.startTs === nova.startTs
    && anterior.workflow.status === nova.workflow.status
    && anterior.workflow.durationMs === nova.workflow.durationMs
    && anterior.workflow.error === nova.workflow.error
  ) {
    return anterior
  }

  // `problems`/`slowest` point to the freshly created objects; without remapping,
  // the same row would exist as two different instances on the same screen.
  return {
    ...nova,
    nodes,
    problems: nova.problems.map(p => reusados.get(p.nodeId) ?? p),
    slowest: nova.slowest ? reusados.get(nova.slowest.nodeId) ?? nova.slowest : null,
  }
}

let snapshot: RunSnapshot = readSnapshot(null)

function agendarFlush() {
  if (timer) return // a flush is already scheduled in this window
  timer = setTimeout(() => {
    timer = null
    snapshot = readSnapshot(snapshot)
    for (const notificar of inscritos) notificar()
  }, REFRESH_MS)
}

function inscrever(notificar: () => void, precisaTimeline: boolean) {
  const primeiroCompleto = precisaTimeline && querTimeline.size === 0
  inscritos.add(notificar)
  if (precisaTimeline) querTimeline.add(notificar)
  // Subscribes to the store only once, while there is any consumer. The first
  // to arrive collects what already exists right away — waiting for the window
  // would leave the panel empty for an instant when opening an already loaded
  // run. React re-reads the snapshot right after subscribing, so this does not
  // need to notify anyone.
  if (!cancelarStore) {
    cancelarStore = useWorkflowExecutionStore.subscribe(agendarFlush)
    snapshot = readSnapshot(null)
  } else if (primeiroCompleto) {
    // The panel just opened and the current snapshot only has the bar summary.
    agendarFlush()
  }

  return () => {
    inscritos.delete(notificar)
    querTimeline.delete(notificar)
    if (inscritos.size > 0) return
    cancelarStore?.()
    cancelarStore = null
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }
}

/**
 * Aggregated snapshot of the run.
 *
 * The store is subscribed imperatively (and not via selector) precisely so that
 * a high write frequency does not turn into a high render frequency: the
 * components only update when the timer fires.
 *
 * `precisaTimeline` says whether this consumer shows the per-node timeline. The
 * panel passes `open`: when collapsed it only draws the summary bar, and the
 * full rebuild stops happening.
 */
export function useRunSnapshot(precisaTimeline = true): RunSnapshot {
  const subscribe = useCallback(
    (notificar: () => void) => inscrever(notificar, precisaTimeline),
    [precisaTimeline],
  )
  return useSyncExternalStore(subscribe, () => snapshot, () => snapshot)
}
