import { create } from 'zustand'

export type RunPanelTab = 'nodes' | 'output' | 'problems' | 'raw'

/** Height of the always-visible bar (the "HUD"). */
export const RUN_BAR_HEIGHT = 34
const DEFAULT_HEIGHT = 320
const MIN_HEIGHT = 160

/** Fraction of the window the panel may take when it OPENS, without the user asking. */
const FRACAO_INICIAL = 0.45

/**
 * Opening height, limited by the window.
 *
 * The fixed 320px were chosen for a monitor, where they are ~30% of the screen.
 * On a phone with 640px of usable height they became half the canvas — the user
 * opened the panel to follow a run and lost sight of precisely the graph they
 * wanted to follow. The limit only SHRINKS: on a monitor, 45% is well over
 * 320px, and the default still applies.
 *
 * It cannot become the store's initial value: the store is created on module
 * import, which also runs on the server, and reading `window` there would break
 * SSR (besides freezing the height of the first render).
 */
function alturaDeAbertura(atual: number): number {
  if (typeof window === "undefined") return atual
  return Math.max(MIN_HEIGHT, Math.min(atual, Math.round(window.innerHeight * FRACAO_INICIAL)))
}

/** UI state of the execution panel.
 *
 * It lives in its own store (and not locally in the component) because three
 * places need it: the panel, the canvas button column — which moves up so as
 * not to sit under the dock — and the canvas, which reveals a node in the panel
 * when clicked.
 */
interface RunPanelState {
  open: boolean
  height: number
  tab: RunPanelTab
  search: string
  /** Node the panel should scroll to and highlight (set by the click on the canvas). */
  revealNodeId: string | null
  /** Node under the cursor in the panel — highlighted on the canvas. */
  hoveredNodeId: string | null
}

interface RunPanelActions {
  setOpen(v: boolean): void
  /** Opens the panel straight on a specific tab (e.g. "Problemas" (problems) on failure). */
  openAt(tab: RunPanelTab): void
  setHeight(h: number): void
  setTab(tab: RunPanelTab): void
  setSearch(s: string): void
  reveal(nodeId: string | null): void
  setHovered(nodeId: string | null): void
}

export const useRunPanelStore = create<RunPanelState & RunPanelActions>((set) => ({
  open: false,
  height: DEFAULT_HEIGHT,
  tab: 'nodes',
  search: '',
  revealNodeId: null,
  hoveredNodeId: null,

  // The clamp goes on OPEN, not on `setHeight`: whoever dragged the handle chose
  // that height and may exceed the fraction as they please.
  setOpen: (v) => set(state => v ? { open: true, height: alturaDeAbertura(state.height) } : { open: false }),
  openAt: (tab) => set(state => ({ open: true, tab, height: alturaDeAbertura(state.height) })),
  setHeight: (h) => set({ height: Math.max(MIN_HEIGHT, h) }),
  setTab: (tab) => set({ tab }),
  setSearch: (search) => set({ search }),
  reveal: (revealNodeId) => set({ revealNodeId }),
  setHovered: (hoveredNodeId) => set({ hoveredNodeId }),
}))

/** Vertical space the canvas button column needs above the dock. */
const BUTTON_COLUMN_HEIGHT = 300

/** Height taken by the dock — the canvas button column uses it to shift.
 *
 * Limited so that, with the panel maximized, the column is not pushed out past
 * the top of the canvas (where it got clipped and unreachable). Past the limit
 * it sits behind the panel, which has a higher z-index — predictable behavior
 * for someone who chose to maximize the panel.
 */
export function useRunDockHeight(): number {
  const open = useRunPanelStore(s => s.open)
  const height = useRunPanelStore(s => s.height)
  if (!open) return RUN_BAR_HEIGHT
  const ceiling = typeof window !== "undefined"
    ? Math.max(RUN_BAR_HEIGHT, window.innerHeight - BUTTON_COLUMN_HEIGHT)
    : height
  return Math.min(height, ceiling)
}
