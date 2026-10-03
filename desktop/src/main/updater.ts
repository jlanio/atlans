// desktop/src/main/updater.ts
//
// Auto-update via electron-updater, consuming the same GitHub Releases that
// the Docker executor workflow already uses.
//
// The rule that dictates the whole design: **never update in the middle of a
// run**. The update replaces `python.exe` and the whole `resources/` tree;
// doing that with a workflow running would kill the job without confirming the
// result to the server, which would mark it as orphaned. That is why
// `quitAndInstall` only happens after an ORDERLY shutdown of the executor, and
// only when there is no job in progress.
//
// The differential download comes from the `.blockmap` the NSIS target
// generates: if `resources/python` did not change between releases, its
// blocks are identical and are not downloaded. That is what makes it viable
// for a ~400 MB app to update itself without downloading everything again —
// and the reason the executor's lock (with hashes) and the
// python-build-standalone release are pinned.
import { app } from 'electron'
import type { AppUpdater } from 'electron-updater'

const INTERVALO_MS = 6 * 60 * 60 * 1000   // 6 h

export interface EstadoUpdate {
  versao: string | null
  baixado: boolean
}

let updater: AppUpdater | null = null
let timer: NodeJS.Timeout | null = null

const estado: EstadoUpdate = { versao: null, baixado: false }

export function estadoDoUpdate(): EstadoUpdate {
  return { ...estado }
}

/**
 * @param aoMudar  notified when an update finishes downloading.
 */
export async function iniciarUpdater(aoMudar: (e: EstadoUpdate) => void): Promise<void> {
  // In dev there is nothing to update, and electron-updater logs a flashy error
  // ("dev-app-update.yml not found") that only confuses.
  if (!app.isPackaged) return

  // Import dinamico: o pacote inteiro so e carregado no app empacotado.
  const { autoUpdater } = await import('electron-updater')
  updater = autoUpdater

  // The download starts by itself; it is the INSTALLATION that waits.
  // Downloading early makes the update ready when the window of opportunity
  // shows up.
  autoUpdater.autoDownload = true
  autoUpdater.autoInstallOnAppQuit = false   // see `instalarAgora`

  autoUpdater.on('update-downloaded', (info) => {
    estado.baixado = true
    estado.versao = info.version
    aoMudar(estadoDoUpdate())
  })

  // An update failure must NOT crash or alarm: the app works the same without
  // updating. The listener exists even with nobody reading the error: without
  // any, the EventEmitter THROWS the `error` — and electron-updater emits it
  // from inside `quitAndInstall`, on the app's exit path.
  autoUpdater.on('error', () => { /* see above */ })

  const verificar = () => {
    void autoUpdater.checkForUpdates().catch(() => { /* the error handler covers it */ })
  }

  verificar()
  timer = setInterval(verificar, INTERVALO_MS)
}

/**
 * Installs and restarts. Returns `false` if there is no downloaded update yet
 * — the "can we restart now?" decision belongs to the caller, which must stop
 * the executor in an orderly way BEFORE.
 */
export function instalarAgora(): boolean {
  if (!updater || !estado.baixado) return false
  // `isSilent: false` mostra o instalador; `isForceRunAfter: true` reabre o app.
  updater.quitAndInstall(false, true)
  return true
}

export function pararUpdater(): void {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}
