// Zustand store for "dynamic" editor data that used to live in FlowContext.
// Separates UI state (drawer, newly-added) and the server-state catalog (nodesAPI,
// credentials, pinnedNodes) from FlowContext — which now only holds immutable refs
// (reactFlowInstance, flowRef, reloadWorkflow).
//
// Motivation: each `setFlowContext(prev => ...)` recreated the whole context
// value, causing a re-render in all ~40 consumers of the hook even when the
// change affected only 1 field. Granular subscriptions via Zustand eliminate
// that cascade.
import { create } from 'zustand'

import { fromBackend } from '@/lib/dayjs'
import { GisFlowService } from '@/service/GisFlowService'
import type { INodesAPI } from '@/service/types'
import type { ICredentials } from '@/service/types'
import type { IPinNodeMeta } from '@/service/types'

export type NodesDrawerState = 'opened' | 'closed' | (string & {})

/** Validity of the in-memory catalog. Nodes and credentials only change when an
 *  admin disables a node or the user registers a credential — not every time a
 *  canvas opens. */
const CATALOG_TTL_MS = 5 * 60 * 1000

// Requests in flight, so that two simultaneous mounts (canvas + Ctrl+K)
// share the same download instead of firing two.
let nodesInFlight: Promise<INodesAPI[]> | null = null
let credentialsInFlight: Promise<ICredentials[]> | null = null

const isFresh = (carimbo: number | null) =>
  carimbo !== null && Date.now() - carimbo < CATALOG_TTL_MS

/** Compares content, not reference.
 *
 *  The canvas subscribes to `nodesAPI` and re-hydrates the graph when that list
 *  changes IDENTITY. A refetch after the TTL expires returns a new array from the
 *  JSON even when the catalog is byte-for-byte the same — and that was enough to
 *  redraw the graph over everything the user had already edited. */
const sameContent = (a: unknown[], b: unknown[]) =>
  a.length === b.length && JSON.stringify(a) === JSON.stringify(b)

interface WorkflowCatalogState {
  /** Catalog of node types — response from GET /nodes */
  nodesAPI: INodesAPI[]
  /** Credentials available to the user — response from GET /credentials */
  credentials: ICredentials[]
  /** When `nodesAPI` was downloaded (epoch ms). null = never. */
  nodesFetchedAt: number | null
  /** When `credentials` was downloaded (epoch ms). null = never. */
  credentialsFetchedAt: number | null
  /** Nodes with pinned output (pin data) in the current workflow */
  pinnedNodes: IPinNodeMeta[]
  /** ID of the newly added node — used for the highlight animation */
  newlyAddedNodeId: string | undefined
  /** State of the side drawer for adding nodes */
  nodesDrawerState: NodesDrawerState
}

interface WorkflowCatalogActions {
  setCredentials(v: ICredentials[]): void
  /** Ensures the catalog is in memory: downloads only if it is empty or expired.
   *  A fetch that fails PRESERVES what was already in memory and does not stamp
   *  the TTL — the next call tries again. */
  ensureNodesAPI(): Promise<INodesAPI[]>
  /** Same for the credentials. */
  ensureCredentials(): Promise<ICredentials[]>
  /** Marks the credentials as expired — the next `ensureCredentials` redoes the GET.
   *  Called by whoever creates/edits/deletes a credential outside the canvas, otherwise
   *  the new credential would only appear in the node's select after the 5-min TTL. */
  invalidarCredenciais(): void
  setPinnedNodes(v: IPinNodeMeta[]): void
  setNewlyAddedNodeId(v: string | undefined): void
  setNodesDrawerState(v: NodesDrawerState): void
  /** Recomputes each pin's `expired` based on the loaded `expires_at` and the
   * current clock. No-op when nothing changes — avoids re-rendering the consumers. */
  recomputeExpiredPins(): void
  /** Clears workflow-dependent fields (pinnedNodes, newlyAddedNodeId, drawer closed).
   * nodesAPI and credentials are kept — they are global to the user. */
  resetWorkflowScoped(): void
}

export const useWorkflowCatalogStore = create<WorkflowCatalogState & WorkflowCatalogActions>((set, get) => ({
  nodesAPI: [],
  credentials: [],
  nodesFetchedAt: null,
  credentialsFetchedAt: null,
  pinnedNodes: [],
  newlyAddedNodeId: undefined,
  nodesDrawerState: 'closed',

  setCredentials: (v) => set({ credentials: v, credentialsFetchedAt: Date.now() }),

  ensureNodesAPI: () => {
    const { nodesAPI, nodesFetchedAt } = get()
    if (nodesAPI.length > 0 && isFresh(nodesFetchedAt)) return Promise.resolve(nodesAPI)
    if (nodesInFlight) return nodesInFlight
    nodesInFlight = GisFlowService.getNodes()
      .then(res => {
        // The service does NOT reject on failure: it resolves with { data: undefined, error }.
        // Without this guard, a 502/401/network drop wrote `nodesAPI: []` over
        // the good catalog and the drawer, the palette and "command-add-node"
        // went empty with no error message at all. On failure, preserve what is
        // in memory and do NOT stamp the TTL — the next call tries again.
        if (res?.error || !Array.isArray(res?.data)) return get().nodesAPI
        const lista = res.data
        const atual = get().nodesAPI
        if (sameContent(atual, lista)) {
          // Identical content: renew only the validity and keep the SAME reference,
          // so as not to wake the consumers subscribed to the array.
          set({ nodesFetchedAt: Date.now() })
          return atual
        }
        set({ nodesAPI: lista, nodesFetchedAt: Date.now() })
        return lista
      })
      .finally(() => { nodesInFlight = null })
    return nodesInFlight
  },

  ensureCredentials: () => {
    const { credentials, credentialsFetchedAt } = get()
    if (credentials.length > 0 && isFresh(credentialsFetchedAt)) return Promise.resolve(credentials)
    if (credentialsInFlight) return credentialsInFlight
    credentialsInFlight = GisFlowService.getCredentials()
      .then(res => {
        // Same rule as the node catalog: a failure does not take down the good list.
        // Here the symptom would be the node's credential select going empty and
        // the user saving the node with no credential at all.
        if (res?.error || !Array.isArray(res?.data)) return get().credentials
        const lista = res.data
        const atual = get().credentials
        if (sameContent(atual, lista)) {
          set({ credentialsFetchedAt: Date.now() })
          return atual
        }
        set({ credentials: lista, credentialsFetchedAt: Date.now() })
        return lista
      })
      .finally(() => { credentialsInFlight = null })
    return credentialsInFlight
  },

  invalidarCredenciais: () => set({ credentialsFetchedAt: null }),

  setPinnedNodes: (v) => set({ pinnedNodes: v }),
  setNewlyAddedNodeId: (v) => set({ newlyAddedNodeId: v }),
  setNodesDrawerState: (v) => set({ nodesDrawerState: v }),

  recomputeExpiredPins: () => set(state => {
    const now = Date.now()
    let changed = false
    const updated = state.pinnedNodes.map(p => {
      if (!p.expires_at) return p
      // expires_at comes as naive UTC (no offset). A raw `new Date()` interpreted it
      // as local, shifting the epoch by the time zone offset → the pin expiration
      // was off by ~hours. fromBackend treats it as UTC; valueOf() gives the correct
      // absolute epoch to compare with Date.now().
      const expiresAtMs = fromBackend(p.expires_at)?.valueOf() ?? Number.POSITIVE_INFINITY
      const expired = now > expiresAtMs
      if (expired === p.expired) return p
      changed = true
      return { ...p, expired }
    })
    return changed ? { pinnedNodes: updated } : {}
  }),

  resetWorkflowScoped: () => set({
    pinnedNodes: [],
    newlyAddedNodeId: undefined,
    nodesDrawerState: 'closed',
  }),
}))
