import { create } from 'zustand'
import type { Viewport } from '@xyflow/react'
import { INodesDefinition, IEdgeDefinition } from '@/service/types'

export type SaveStatus = 'idle' | 'unsaved' | 'saving' | 'saved' | 'error' | 'needs_name'

interface WorkflowSaveState {
  isSaving: boolean
  saveStatus: SaveStatus
  lastSavedSnapshot: string | null
  /** Moment (epoch ms) of the last confirmed save: the server's `updated_at` on
   *  hydration, the browser clock after a successful PUT/POST.
   *  `null` = nothing known to be saved (new workflow, or a backend without the date).
   *  It is what the chip shows at rest ("Salvo há 5 min", saved 5 min ago). */
  lastSavedAt: number | null
  /** Message of the last save that failed; `null` outside the 'error' status. */
  lastError: string | null
  /** Zoom and position written on the last save (or loaded with the workflow).
   *  Pan/zoom is NOT an edit — it does not mark "unsaved" —, but it is part of
   *  what gets saved: whoever asks for the save wants to reopen where they were.
   *  Compared on an explicit save to decide whether a PUT is worth it when the
   *  graph did not change. */
  lastSavedViewport: Viewport | null
  workflowName: string
  flagActive: boolean
  /** Moment (epoch ms) at which the reference snapshot was taken on hydration.
   *  `null` = no self-correction window is open. See `autocorrigirSnapshot`. */
  snapshotIniciadoEm: number | null
}

interface WorkflowSaveActions {
  setWorkflowName(name: string): void
  setFlagActive(v: boolean): void
  startSaving(): void
  completeSave(snapshot: string, viewport?: Viewport | null): void
  /** A save that did not reach the end. The status becomes 'error', not 'unsaved':
   *  the graph is still different from the snapshot, but what the user needs to
   *  know is that the attempt failed — and to have a place to try again. */
  failSave(mensagem?: string): void
  /** Saving with nothing to save: flashes "Salvo" with no PUT and without touching
   *  `lastSavedAt`. Before, Ctrl+S in this situation gave no response at all, and
   *  there was no way to tell "it was already saved" from "the shortcut didn't work". */
  flashSaved(): void
  setStatus(status: SaveStatus): void
  /** `savedAt` is the server's `updated_at` on hydration and `viewport` is what
   *  came in the `definition`; when omitted, they keep the current value (the
   *  reset on workflow switch is what clears them). */
  initSnapshot(nodes: INodesDefinition[], edges: IEdgeDefinition[], name: string, savedAt?: number | null, viewport?: Viewport | null): void
  isDirty(nodes: INodesDefinition[], edges: IEdgeDefinition[], name: string): boolean
  /**
   * Silently absorbs a difference that appeared within the hydration WINDOW —
   * ReactFlow still measuring dimensions/positions right after mount. Returns
   * `true` when it absorbed it; `false` when the window has already closed, and
   * then the caller needs to mark 'unsaved', because the difference is a real
   * user edit.
   *
   * The window is one of TIME, not "the first difference that shows up": with the
   * debounced change detector, the first comparison only happens after the user
   * stops editing — so a "use once" flag swallowed the ENTIRE first edit (no
   * "Não salvo", with Ctrl+S becoming a no-op and Executar firing the old
   * definition).
   */
  autocorrigirSnapshot(nodes: INodesDefinition[], edges: IEdgeDefinition[], name: string): boolean
}

/** How long the "Salvo" label (green) stays before turning into the resting state
 *  ("Salvo há N min", in a neutral tone). */
const SAVED_LABEL_DURATION_MS = 3000

/** For how long, after the hydration snapshot, a difference can still be
 *  credited to ReactFlow's re-measuring instead of to the user. */
const AUTOCORRECT_WINDOW_MS = 1000

// The 'saved' → 'idle' timer lives here, and not in the component that saved,
// because what needs to neutralize it is the change detector — which lives in
// ANOTHER component. Before, an edit made within the 3s window marked "Não
// salvo" and the old timer erased the warning right after.
let savedLabelTimer: ReturnType<typeof setTimeout> | null = null

export const useWorkflowSaveStore = create<WorkflowSaveState & WorkflowSaveActions>((set, get) => {

  function scheduleReturnToIdle() {
    if (savedLabelTimer) clearTimeout(savedLabelTimer)
    savedLabelTimer = setTimeout(() => {
      savedLabelTimer = null
      // Only clears the label if nobody touched the status in the meantime: if the
      // user edited the canvas in those 3s, the status is already 'unsaved' and
      // going back to 'idle' would hide the warning.
      if (get().saveStatus === 'saved') set({ saveStatus: 'idle' })
    }, SAVED_LABEL_DURATION_MS)
  }

  return {
    isSaving: false,
    saveStatus: 'idle',
    lastSavedSnapshot: null,
    lastSavedAt: null,
    lastError: null,
    lastSavedViewport: null,
    workflowName: '',
    flagActive: true,
    snapshotIniciadoEm: null,

    setWorkflowName: (name) => {
      set({ workflowName: name })
    },

    setFlagActive: (v) => {
      set({ flagActive: v })
    },

    startSaving: () => {
      set({ isSaving: true, saveStatus: 'saving' })
    },

    completeSave: (snapshot, viewport) => {
      // Closes the self-correction window: after a successful save there is no
      // longer any "pending ReactFlow measurement" to absorb — every difference
      // from then on is a user edit and must become "Não salvo".
      set({
        isSaving: false,
        lastSavedSnapshot: snapshot,
        lastSavedAt: Date.now(),
        lastError: null,
        saveStatus: 'saved',
        snapshotIniciadoEm: null,
        ...(viewport !== undefined ? { lastSavedViewport: viewport } : {}),
      })
      scheduleReturnToIdle()
    },

    failSave: (mensagem) => {
      set({ isSaving: false, saveStatus: 'error', lastError: mensagem ?? null })
    },

    flashSaved: () => {
      set({ saveStatus: 'saved' })
      scheduleReturnToIdle()
    },

    setStatus: (status) => {
      set({ saveStatus: status })
    },

    initSnapshot: (nodes, edges, name, savedAt, viewport) => {
      const snapshot = JSON.stringify({ name, nodes, edges })
      // Opens the self-correction window along with the snapshot: this instant is
      // what the change detector uses as reference.
      set({
        lastSavedSnapshot: snapshot,
        snapshotIniciadoEm: Date.now(),
        ...(savedAt !== undefined ? { lastSavedAt: savedAt } : {}),
        ...(viewport !== undefined ? { lastSavedViewport: viewport } : {}),
      })
    },

    isDirty: (nodes, edges, name) => {
      const currentSnapshot = JSON.stringify({ name, nodes, edges })
      return currentSnapshot !== get().lastSavedSnapshot
    },

    autocorrigirSnapshot: (nodes, edges, name) => {
      const { snapshotIniciadoEm, saveStatus } = get()
      if (saveStatus !== 'idle') return false
      if (snapshotIniciadoEm === null) return false
      if (Date.now() - snapshotIniciadoEm >= AUTOCORRECT_WINDOW_MS) return false
      set({
        lastSavedSnapshot: JSON.stringify({ name, nodes, edges }),
        // Holds once per hydration: reopening the window here would stretch it
        // indefinitely while differences kept showing up.
        snapshotIniciadoEm: null,
      })
      return true
    },
  }
})
