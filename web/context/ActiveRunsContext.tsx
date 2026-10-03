"use client"

/**
 * Global visibility of runs in progress.
 *
 * Polls /observability/runs?status=running (lightweight — only live runs, and
 * the backend already scopes by user) and, crossing that with the workflows of
 * the current workspace, exposes which ones are "running now". A single
 * mechanism feeds three things:
 *   - the live pill on each workflow's card (runningHashes)
 *   - the "N runs" indicator in the sidebar (runningRuns / runningCount)
 *   - the notification when a run finishes in the background
 *
 * Completion is detected when a run drops out of the "running" set; the final
 * status (success/failure) comes from a one-off getRunDetail (only at that
 * moment, which is rare), avoiding downloading hundreds of records every tick
 * just to find terminal ones.
 *
 * workflow_name is admin-only in /observability/runs, so we cross with
 * getWorkflows to get the names (and to scope to the current workspace).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useNotifications } from "@/context/NotificationsContext"

export interface RunningRun {
  runId: string
  workflowHash: string
  name: string
  /** ISO `started_at`; null while the run is in the queue. */
  startedAt: string | null
  /** `trigger_source` do run (manual, schedule, webhook, retry). */
  triggerSource: string | null
  /** Friendly name of the executor; null without a host. */
  executorName: string | null
}

// What is kept of each live run between one poll and the next. Besides the
// name, the three fields the Projects list shows on the "running" row (projects
// spec §2.3) — `/observability/runs` already returns them, so they cost nothing.
type RunVivo = Pick<RunningRun, "name" | "startedAt" | "triggerSource" | "executorName"> & { hash: string }

interface ActiveRunsValue {
  /** Set of id_hash of the workflows with a live run in the workspace. */
  runningHashes: Set<string>
  /** Live runs of the current workspace, with the name resolved. */
  runningRuns: RunningRun[]
  /** Number of runs in progress. */
  runningCount: number
  /** Forces an immediate poll (e.g. right after a quick trigger from the list). */
  refresh: () => void
}

const ActiveRunsContext = createContext<ActiveRunsValue | undefined>(undefined)

// Cadence with the tab focused and some run alive — that is when the user is
// actually waiting for the result to show up.
const POLL_MS = 10_000
// Cadence when no run at all is running, which is the common case. This
// provider lives in the dashboard layout, so it runs on EVERY screen: without
// the step down, a forgotten idle tab generated ~8,600 requests/day on its own.
const IDLE_POLL_MS = 30_000
const LIMIT = 200
const TERMINAL = new Set(["success", "failed"])

export function ActiveRunsProvider({ children }: { children: ReactNode }) {
  const { current } = useWorkspace()
  const { addNotification } = useNotifications()
  const workspaceId = current?.id_hash

  const [runningHashes, setRunningHashes] = useState<Set<string>>(new Set())
  const [runningRuns, setRunningRuns] = useState<RunningRun[]>([])

  // Manual poll without waiting for the interval (set inside the effect).
  const pollRef = useRef<() => void>(() => {})

  useEffect(() => {
    if (!workspaceId) {
      setRunningHashes(new Set())
      setRunningRuns([])
      return
    }

    let alive = true
    let timer: ReturnType<typeof setTimeout> | null = null
    let namesByHash = new Map<string, string>()
    // Hashes we have already tried to resolve and are still missing from
    // namesByHash. The poll brings runs from ALL of the user's workspaces (the
    // backend scopes by user), but namesByHash only has the workflows of the
    // ACTIVE workspace — so a live run from ANOTHER workspace never enters the
    // map and, without this memory, forced a full getWorkflows() on every tick
    // for as long as it lived.
    //
    // `hash -> time of the attempt`, with a TTL (not a permanent `Set`): a
    // freshly created workflow may not yet show up in getWorkflows (eventual
    // consistency). Without expiry, it would stay nameless for the rest of the
    // session; with the TTL, a later tick retries and the name appears as soon
    // as the backend lists it.
    const tentados = new Map<string, number>()
    const TENTADO_TTL_MS = 60_000
    // run_id -> {hash, name} of the live runs in the LAST poll. Rebuilt every
    // tick → size bounded by the number of live runs (does not grow forever).
    let prevLive = new Map<string, RunVivo>()
    // The first poll only seeds prevLive (it does not notify about runs that had
    // already finished before the app opened / before switching workspace).
    let seeded = false
    // Signature of the live set — avoids re-rendering consumers when nothing changes.
    let sig = ""

    async function loadNames(): Promise<boolean> {
      // Includes the assistant's workflows: a live run of an assistant workflow
      // (hidden from listings by default) needs the NAME for the pill, otherwise
      // it shows up unlabeled. This is name resolution, not the list the owner
      // sees.
      const res = await GisFlowService.getWorkflows(workspaceId, { incluirDoAssistente: true })
      if (!alive) return false
      // A transient error does NOT wipe the names already resolved: overwriting
      // with an empty map would make every pill lose its name until the next
      // successful load — which, with the hash already marked as "tried",
      // would never even happen.
      if (!res.data) return false
      namesByHash = new Map(res.data.map((w) => [w.id_hash, w.name]))
      return true
    }

    async function notifyIfCompleted(runId: string, name: string) {
      // Confirms the terminal state before notifying — avoids a false positive if
      // the run left the set for some reason other than completion.
      const detail = await GisFlowService.getRunDetail(runId)
      if (!alive || !detail.data) return
      const st = detail.data.status
      if (!TERMINAL.has(st)) return
      addNotification({
        type: st === "success" ? "success" : "error",
        title: st === "success" ? "Workflow concluído" : "Workflow falhou",
        message: name || undefined,
      })
    }

    async function poll() {
      const resp = await GisFlowService.getObservabilityRuns({ status: "running", limit: LIMIT })
      if (!alive || !resp.data) return   // transient error → keep state (no flicker)

      const raw = resp.data.runs ?? []
      // A freshly created workflow is not in the name map yet → reload once
      // per unseen hash. Runs from another workspace stay in `tentados` (with
      // a TTL) and do not trigger loadNames() again on the following ticks.
      const agora = Date.now()
      const inéditos = raw.filter((r) =>
        r.workflow_hash
        && !namesByHash.has(r.workflow_hash)
        && agora - (tentados.get(r.workflow_hash) ?? 0) > TENTADO_TTL_MS
      )
      if (inéditos.length > 0) {
        const ok = await loadNames()
        if (!alive) return
        // Only mark "already tried and didn't find it" when the load SUCCEEDED and
        // the hash still did not come (another workspace, or not replicated
        // yet). A network failure does not condemn the hash: the next tick
        // tries again.
        if (ok) {
          for (const r of inéditos) {
            if (!namesByHash.has(r.workflow_hash!)) tentados.set(r.workflow_hash!, agora)
          }
        }
      }

      // Scopes to the current workspace (only workflows it knows about).
      const nextLive = new Map<string, RunVivo>()
      for (const r of raw) {
        const hash = r.workflow_hash
        if (!hash || !namesByHash.has(hash)) continue
        nextLive.set(r.run_id, {
          hash,
          name: namesByHash.get(hash) ?? "Workflow",
          startedAt: r.started_at ?? null,
          triggerSource: r.trigger_source ?? null,
          executorName: r.executor_name ?? null,
        })
      }

      // Completions: a run that was alive before and is gone now.
      if (seeded) {
        for (const [runId, info] of prevLive) {
          if (!nextLive.has(runId)) void notifyIfCompleted(runId, info.name)
        }
      }
      prevLive = nextLive
      seeded = true

      // Updates state only when the live set changes (avoids a re-render every 10s).
      const nextSig = [...nextLive.keys()].sort().join(",")
      if (nextSig !== sig) {
        sig = nextSig
        setRunningRuns([...nextLive].map(([runId, i]) => ({
          runId, workflowHash: i.hash, name: i.name,
          startedAt: i.startedAt, triggerSource: i.triggerSource, executorName: i.executorName,
        })))
        setRunningHashes(new Set([...nextLive.values()].map((i) => i.hash)))
      }
    }

    // Serializes the calls: there are three triggers (scheduled tick, focus
    // return and manual refresh via pollRef) and nothing stopped them from
    // overlapping.
    let inFlight = false
    const pollOnce = async () => {
      if (inFlight) return
      inFlight = true
      try {
        await poll()
      } catch {
        // intermittent network — keep the previous state; the next tick tries again
      } finally {
        inFlight = false
      }
    }

    pollRef.current = () => { void pollOnce() }

    // Schedule the next tick instead of using a fixed-period setInterval: this
    // way the cadence follows the state (hidden tab = no queries; nothing
    // running = fewer queries). With setInterval the only option would be
    // "skip the tick", which keeps the timer waking up for nothing every 10s.
    const scheduleNext = () => {
      if (!alive) return
      const intervalo = prevLive.size > 0 ? POLL_MS : IDLE_POLL_MS
      timer = setTimeout(async () => {
        // A hidden tab does not need fresh data: nobody is looking, and the
        // `visibilitychange` below fires an immediate poll when focus returns.
        if (document.visibilityState === "visible") {
          await pollOnce()
        }
        scheduleNext()
      }, intervalo)
    }

    // When coming back to the tab, update right away — without this the user
    // would stare at stale data for up to IDLE_POLL_MS after regaining focus.
    //
    // The in-flight lock matters here: switching tabs in quick succession fires
    // one `visibilitychange` per switch, and without it every alt-tab would
    // become a request — working against the goal of reducing load. The
    // scheduled tick and the manual refresh (pollRef) go through the same lock.
    const onVisibility = () => {
      if (document.visibilityState === "visible") void pollOnce()
    }
    document.addEventListener("visibilitychange", onVisibility)

    ;(async () => {
      try {
        await loadNames()
      } catch {
        // without the names the poll still works (filters by what it knows); retry on the tick
      }
      if (!alive) return
      await pollOnce()
      if (!alive) return
      scheduleNext()
    })()

    return () => {
      alive = false
      if (timer) clearTimeout(timer)
      document.removeEventListener("visibilitychange", onVisibility)
      pollRef.current = () => {}
    }
  }, [workspaceId, addNotification])

  // The refresh goes through the ref, so it is stable on purpose: the context
  // value only changes when the set of live runs changes. Before, every render
  // of this provider (which sits at the dashboard root) created a new object
  // and propagated a re-render to every screen below, even when the poll had
  // nothing new.
  const refresh = useCallback(() => { pollRef.current() }, [])

  const value = useMemo<ActiveRunsValue>(
    () => ({ runningHashes, runningRuns, runningCount: runningRuns.length, refresh }),
    [runningHashes, runningRuns, refresh],
  )

  return (
    <ActiveRunsContext.Provider value={value}>
      {children}
    </ActiveRunsContext.Provider>
  )
}

export function useActiveRuns(): ActiveRunsValue {
  const ctx = useContext(ActiveRunsContext)
  if (!ctx) throw new Error("useActiveRuns precisa estar dentro de <ActiveRunsProvider>")
  return ctx
}
