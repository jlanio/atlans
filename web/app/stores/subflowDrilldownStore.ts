import { create } from 'zustand'

/** One step of the descent: the SubWorkflow node crossed and the workflow it calls. */
export interface SubflowLevel {
  /** Id of the SubWorkflow node in the canvas it lives in (the parent of this level). */
  canvasNodeId: string
  /** That node's `properties.workflowHash` — the workflow to load and draw. */
  workflowHash: string
  /** Label of the SubWorkflow node, for the breadcrumb. */
  label: string
}

/**
 * Navigation into the sub-workflows of a run.
 *
 * `path` is the chain of SubWorkflow nodes crossed: `[]` means closed, and
 * `path[i].canvasNodeId` joined by `::` form exactly the prefix with which that
 * level's events reach the panel (see utils/subflow-path).
 *
 * It lives in a store, and not in the viewer's local state, because whoever
 * OPENS it is spread out — the execution panel, from an error, and the canvas
 * itself — while whoever RENDERS it is a single component mounted next to the
 * editor.
 */
interface SubflowDrilldownState {
  path: SubflowLevel[]
  /**
   * Node (local id) to center as soon as the level opens. It is what makes "open
   * sub-workflow" from a failure land straight on the node that broke, instead of
   * dropping the person into a fully framed graph to look for the red one.
   */
  focusNodeId: string | null
}

interface SubflowDrilldownActions {
  /** Abre do zero, substituindo qualquer descida em andamento. */
  open(path: SubflowLevel[], focusNodeId?: string | null): void
  /** Goes down one more level from what is already open. */
  push(level: SubflowLevel): void
  /** Goes back to an already visited level. Index -1 returns to the editor's workflow. */
  popTo(index: number): void
  close(): void
}

export const useSubflowDrilldownStore = create<SubflowDrilldownState & SubflowDrilldownActions>((set) => ({
  path: [],
  focusNodeId: null,

  open: (path, focusNodeId = null) => set({ path, focusNodeId }),
  push: (level) => set(state => ({ path: [...state.path, level], focusNodeId: null })),
  popTo: (index) => set(state => (
    index < 0
      ? { path: [], focusNodeId: null }
      : { path: state.path.slice(0, index + 1), focusNodeId: null }
  )),
  close: () => set({ path: [], focusNodeId: null }),
}))
