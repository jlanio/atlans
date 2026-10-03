import { create } from "zustand"

/**
 * Open/closed state of the assistant drawer.
 *
 * In a store, and not in the editor's local state, because three places need
 * it: the drawer, the button that opens it and the keyboard shortcut — which
 * lives in a global effect and cannot depend on the drawer being mounted.
 *
 * The WIDTH does not live here: it belongs to `useResizablePanel`, which already
 * handles dragging, keyboard, viewport clamp and `localStorage`. Two memories for
 * the same drawer would diverge at the first change.
 */

/** `localStorage` key. The width uses `CHAVE_LARGURA`, in the component. */
const CHAVE_ABERTO = "atlans:assistente:aberto"

function lembrado(): boolean | null {
  if (typeof window === "undefined") return null
  try {
    let cru = window.localStorage.getItem(CHAVE_ABERTO)
    if (cru === null) {
      // F4 renamed the key (it was atlans:copiloto:aberto) without a migration — the
      // panel "forgot" everyone's preference. Reads the old one once and
      // rewrites it under the new one; the old one stays, for anyone going back to
      // an earlier version.
      cru = window.localStorage.getItem("atlans:copiloto:aberto")
      if (cru !== null) window.localStorage.setItem(CHAVE_ABERTO, cru)
    }
    return cru === null ? null : cru === "1"
  } catch {
    // Private window or full quota. The preference is disposable.
    return null
  }
}

function lembrar(aberto: boolean): void {
  try {
    window.localStorage.setItem(CHAVE_ABERTO, aberto ? "1" : "0")
  } catch {
    /* disposable preference */
  }
}

interface AssistenteEditorState {
  aberto: boolean
}

interface AssistenteEditorActions {
  fechar(): void
  alternar(): void
  /**
   * Reads the browser preference. `padrao` applies when nothing is stored: the
   * create screen opens the drawer (the canvas starts empty and it is the
   * shortest path), the editor of an existing workflow does not (whoever opens
   * a finished workflow came for the canvas).
   */
  hidratar(padrao: boolean): void
}

export const useAssistenteEditorStore = create<AssistenteEditorState & AssistenteEditorActions>((set) => ({
  aberto: false,

  fechar: () => set(() => { lembrar(false); return { aberto: false } }),
  alternar: () => set(state => { lembrar(!state.aberto); return { aberto: !state.aberto } }),

  // Does not write: hydrating is READING the preference, and writing here would
  // turn the create screen's default into a choice the person never made — and
  // one that would start applying in the editor too.
  hidratar: (padrao) => set(() => ({ aberto: lembrado() ?? padrao })),
}))
