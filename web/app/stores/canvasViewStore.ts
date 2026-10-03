import { create } from 'zustand'

/** Detail tiers. The further out the zoom, the less information on screen. */
export type LodTier = 'far' | 'mid' | 'near'

/** Highlight origin: `hover` is transient, `pin` survives the mouse leaving. */
export type FocusOrigin = 'hover' | 'pin'

const EMPTY: ReadonlySet<string> = new Set()

/** Visual state of the canvas — path highlight and zoom-based detail level.
 *
 * Both live in the same store because they are consumed by the same two
 * places: the layer that writes the CSS (`canvas-view-layer.tsx`) and the toolbar.
 *
 * Note that the sets arrive ready-made: the path computation lives in
 * `useCanvasFocus`, which has access to the edges. The store only keeps the result.
 */
interface CanvasViewState {
  /** User preference — turns off hover highlighting completely. */
  focusEnabled: boolean
  /** Anchor node of the highlight. `null` = no active highlight. */
  focusNodeId: string | null
  focusOrigin: FocusOrigin | null
  /** Ancestors ∪ anchor ∪ descendants. */
  focusNodeIds: ReadonlySet<string>
  focusEdgeIds: ReadonlySet<string>
  lod: LodTier
}

interface CanvasViewActions {
  setFocusEnabled(v: boolean): void
  toggleFocusEnabled(): void
  applyFocus(nodeId: string, origin: FocusOrigin, nodes: Set<string>, edges: Set<string>): void
  /** `clearFocus('hover')` is ignored while there is an active pin. */
  clearFocus(origin?: FocusOrigin): void
  setLod(lod: LodTier): void
  /** Resets the per-workflow state when switching canvas. */
  resetView(): void
}

export const useCanvasViewStore = create<CanvasViewState & CanvasViewActions>((set, get) => ({
  focusEnabled: true,
  focusNodeId: null,
  focusOrigin: null,
  focusNodeIds: EMPTY,
  focusEdgeIds: EMPTY,
  lod: 'near',

  setFocusEnabled: (focusEnabled) => set(
    focusEnabled
      ? { focusEnabled }
      // Turning off must clear the current highlight, otherwise it freezes on screen.
      : { focusEnabled, focusNodeId: null, focusOrigin: null, focusNodeIds: EMPTY, focusEdgeIds: EMPTY }
  ),

  toggleFocusEnabled: () => get().setFocusEnabled(!get().focusEnabled),

  applyFocus: (focusNodeId, focusOrigin, nodes, edges) => {
    if (!get().focusEnabled) return
    set({ focusNodeId, focusOrigin, focusNodeIds: nodes, focusEdgeIds: edges })
  },

  clearFocus: (origin) => {
    // The pin is deliberate; moving the mouse outside it must not clear it.
    if (origin === 'hover' && get().focusOrigin === 'pin') return
    set({ focusNodeId: null, focusOrigin: null, focusNodeIds: EMPTY, focusEdgeIds: EMPTY })
  },

  setLod: (lod) => set({ lod }),

  resetView: () => set({
    focusNodeId: null,
    focusOrigin: null,
    focusNodeIds: EMPTY,
    focusEdgeIds: EMPTY,
  }),
}))
