// desktop/src/preload/web.ts
//
// Preload of the window that displays the web UI.
//
// Unlike the panel's preload (preload/index.ts), this one exposes a MINIMAL,
// READ-ONLY bridge. The web UI is REMOTE content: giving it main's IPC —
// starting/stopping the executor, file dialogs, opening paths on disk — would
// mean any XSS in the UI could drive the local executor with the user's
// permissions. That is why `atlansDesktop` has NO commands: only
// `obterStatus`/`aoMudarStatus`, which read the redacted status from
// shared/executor-status.ts (main → web). No method accepts a channel name,
// and the panel's `window.atlas` is never exposed here.
//
// ## Window dragging
//
// The window is `titleBarStyle: 'hidden'`: Windows paints the buttons
// (min/max/close) on the right, but the rest of the top does not move the
// window by itself. Instead of injecting a drag strip here — too thin to grab,
// and under the resize edge —, the preload only MARKS the document with
// `data-atlans-desktop`. The web UI itself turns its headers (the sidebar's
// and the AppHeader) into a drag region ONLY when it sees that attribute,
// marking its own controls as `no-drag` — it knows where they are, so no
// swallowed clicks. See the `[data-atlans-desktop] .app-region-*` rules in
// web/app/globals.css.

import { contextBridge, ipcRenderer } from 'electron'
import { WEB_CHANNELS, type StatusExecutorLocal } from '../shared/executor-status.js'

/** Marks the <html> so CSS turns on header dragging only inside the desktop app. */
function markDesktop(): void {
  document.documentElement?.setAttribute('data-atlans-desktop', '1')
}
// `documentElement` already exists when the preload runs; the listener covers
// the rare case where it does not exist yet. `setAttribute` is idempotent, so
// repeating it costs nothing.
markDesktop()
document.addEventListener('DOMContentLoaded', markDesktop, { once: true })

// ── Read-only bridge ───────────────────────────────────────────────────────
//
// `window.atlansDesktop` — read-only, no channel name as a parameter. The UI
// feature-detects: in a regular browser this object does not exist.
contextBridge.exposeInMainWorld('atlansDesktop', {
  versao: 1,
  obterStatus: (): Promise<StatusExecutorLocal> => ipcRenderer.invoke(WEB_CHANNELS.status),
  aoMudarStatus: (fn: (s: StatusExecutorLocal) => void): (() => void) => {
    const listener = (_e: unknown, s: StatusExecutorLocal): void => fn(s)
    ipcRenderer.on(WEB_CHANNELS.statusMudou, listener)
    // Returns the unsubscribe: without it, each React remount would accumulate a
    // listener (the same reason as `assinar` in preload/index.ts).
    return () => ipcRenderer.removeListener(WEB_CHANNELS.statusMudou, listener)
  },
})
