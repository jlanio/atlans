// desktop/src/main/ui/autostart.ts
//
// Start together with Windows.
//
// Uses `setLoginItemSettings`, which writes to
// HKCU\Software\Microsoft\Windows\CurrentVersion\Run — no administrator
// privilege and no scheduled task.
//
// Deliberately NOT a Windows Service: a service runs outside the user's
// session, and GeoSync needs it — mapped network drives, `%USERPROFILE%` and
// the permissions of whoever actually uses the files. A service would also
// require an elevated installation, which is what the per-user installer
// avoids.
//
// ## Two API pitfalls, both proven on the machine
//
// 1. **`openAtLogin` compares the ARGUMENTS.** `getLoginItemSettings()` without
//    options assumes `args: []`, and the command written here ends in
//    `--hidden`. The read returned `false` with the entry written and correct
//    in the registry — the result was a checkbox that turned on and flipped
//    back by itself. Every read must use the SAME `path`/`args` as the write.
//
// 2. **`openAtLogin` ignores disabling from Task Manager.** The user can turn
//    the item off under Startup; the entry stays in the registry
//    (`openAtLogin: true`) and the app simply does not start.
//    `executableWillLaunchAtLogin` is what answers "will it really run?".
//
// The name of the registry entry is the AppUserModelID (`app.atlans.executor`,
// defined in index.ts) — changing that ID orphans this entry.
import { app } from 'electron'

/** Makes the app start without a window: only tray + executor spawn. */
export const ARG_OCULTO = '--hidden'

export function startedHidden(): boolean {
  return process.argv.includes(ARG_OCULTO)
}

export interface AutostartState {
  /** A entrada existe e o comando bate exatamente com o deste app. */
  ativo: boolean
  /**
   * Windows will REALLY run it at logon.
   *
   * Differs from `ativo` when the item was disabled in Task Manager →
   * Startup: the entry stays in the registry, but does not run.
   */
  efetivo: boolean
  /** The command that sits in the registry. Shown in the UI so it is not magic. */
  comando: string
  /** Running via `npm run dev` — see the note in `alvo()`. */
  dev: boolean
  /** Message when the registry refused the write (group policy, AV). */
  erro: string | null
}

/**
 * Executable and arguments of the logon entry.
 *
 * In dev the executable is `electron.exe` from node_modules, and without the
 * project path Windows would launch Electron's DEFAULT app on every logon — a
 * gray window that has nothing to do with Atlans, and that would outlive the
 * end of `npm run dev`. Same treatment as `registerProtocol` in deeplink.ts.
 */
function alvo(): { path: string; args: string[] } {
  if (process.defaultApp && process.argv.length >= 2) {
    return { path: process.execPath, args: [process.argv[1]!, ARG_OCULTO] }
  }
  return { path: process.execPath, args: [ARG_OCULTO] }
}

function commandOf({ path, args }: { path: string; args: string[] }): string {
  return [path.includes(' ') ? `"${path}"` : path, ...args].join(' ')
}

/**
 * Last read of the registry.
 *
 * `getLoginItemSettings` is a SYNCHRONOUS query to HKCU\...\Run (and to
 * StartupApproved, for `executableWillLaunchAtLogin`), and the tray called it
 * on every state update — at least once per second with the executor running,
 * and up to twelve in a burst of ERRORs. Synchronous I/O on the thread that
 * serves windows, tray and IPC, for a value that only changes when the user
 * themselves clicks the tray menu or the checkbox in Settings.
 */
let cache: AutostartState | null = null

/** Actually reads from the registry and repopulates the cache. */
export function lerAutostart(): AutostartState {
  const a = alvo()
  const base = { comando: commandOf(a), dev: Boolean(process.defaultApp) }
  try {
    // The SAME path/args as the write — see pitfall 1 in the header.
    const s = app.getLoginItemSettings(a)
    cache = { ...base, ativo: s.openAtLogin, efetivo: s.executableWillLaunchAtLogin, erro: null }
  } catch (e) {
    cache = { ...base, ativo: false, efetivo: false, erro: (e as Error).message }
  }
  return cache
}

/**
 * The tray menu's boolean, served from the cache.
 *
 * The only way for this value to change from outside the app is the user
 * disabling the entry in Task Manager — which already did not show up without
 * reopening the Settings screen, and that screen still forces a re-read via
 * IPC.
 */
export function autostartAtivo(): boolean {
  return (cache ?? lerAutostart()).ativo
}

/**
 * Turns it on or off, and returns the state RE-READ from the registry.
 *
 * Re-read instead of trusting the request: if the write was blocked (group
 * policy, antivirus), the UI must show the real state, not the desired one.
 * The re-read is also what repopulates the cache with the RE-READ value — this
 * is the only path through which autostart changes with the app open.
 */
export function definirAutostart(ativar: boolean): AutostartState {
  const a = alvo()
  try {
    app.setLoginItemSettings({ openAtLogin: ativar, path: a.path, args: a.args })
  } catch (e) {
    return { ...lerAutostart(), erro: (e as Error).message }
  }
  return lerAutostart()
}
