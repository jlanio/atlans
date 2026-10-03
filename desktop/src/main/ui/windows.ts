// desktop/src/main/ui/windows.ts
import { BrowserWindow, shell, type WebContents } from 'electron'
import { ICONE_APP, IS_DEV, arquivoDoApp } from '../paths.js'
import { ehExternoSeguro } from '../../shared/ui.js'

let janela: BrowserWindow | null = null
let janelaLog: BrowserWindow | null = null

/** URL of the Vite dev server, when `npm run dev` set it. */
const DEV_SERVER = process.env.VITE_DEV_SERVER_URL

/**
 * Hash that tells the renderer which screen to mount.
 *
 * Hash and not query: with `loadFile` Electron serves the page via `file://`,
 * and the `search` of a `file://` URL is accepted but disappears from
 * `location` on some navigation paths. The fragment survives both schemes.
 */
export const HASH_LOG = '#log'

export function janelaPrincipal(): BrowserWindow | null {
  return janela && !janela.isDestroyed() ? janela : null
}

/** Subset of `BrowserWindow` used by `trazerParaFrente`. */
export interface JanelaVisivel {
  isMinimized(): boolean
  isVisible(): boolean
  restore(): void
  show(): void
  focus(): void
}

/**
 * Brings an existing window to the front, wherever it comes from.
 *
 * The three states are independent and each one requires its own call:
 *
 *   minimized  → `restore()`
 *   HIDDEN     → `show()`
 *   behind     → `focus()`
 *
 * The `show()` was missing, and it was the MOST common case: the red button in
 * the title bar hides the window instead of quitting the app (it lives in the
 * tray). After that, "Abrir painel" (open panel) in the tray menu called
 * `focus()` on a hidden window — and `focus()` does not make anything visible.
 * The menu looked dead.
 */
export function trazerParaFrente(win: JanelaVisivel): void {
  if (win.isMinimized()) win.restore()
  if (!win.isVisible()) win.show()
  win.focus()
}

/** Subset of `WebContents` used by `protegerNavegacao`. */
export type ConteudoNavegavel = Pick<WebContents, 'setWindowOpenHandler' | 'on' | 'getURL'>

/**
 * The same page the window already shows (scheme, host and path), with any
 * hash or query: it is `location.reload()` — Vite calls it on every full
 * reload in dev, and it fires `will-navigate`.
 */
export function mesmaPagina(atual: string, destino: string): boolean {
  try {
    const a = new URL(atual)
    const d = new URL(destino)
    return a.protocol === d.protocol && a.host === d.host && a.pathname === d.pathname
  } catch {
    return false
  }
}

/**
 * An external link opens in the system browser, never in a BrowserWindow
 * without an address bar — the user needs to see where they are going. But
 * only http(s) and mailto (`ehExternoSeguro`, the same allowlist as the web
 * window): `shell.openExternal` hands the destination to the OS, and a `file:`
 * or `smb:` (UNC → NTLM hash leak on Windows) coming from a URL in a log or
 * from an XSS in the panel must not get out of here. Previously the panel
 * windows passed along any scheme.
 *
 * And the top frame does not leave the panel. The page is an SPA loaded once
 * (`loadFile`/`loadURL` and hash changes do not fire `will-navigate`); what
 * fires it is reloading the page itself — let through — or swapping it for
 * another, with the preload attached — blocked and sent to the browser by the
 * same rule. `will-redirect` gets the same treatment: a 30x redirect in the
 * middle of a reload must not end up rendering another origin here.
 */
export function protegerNavegacao(conteudo: ConteudoNavegavel): void {
  const abrirFora = (destino: string): void => {
    if (ehExternoSeguro(destino)) void shell.openExternal(destino)
  }
  conteudo.setWindowOpenHandler(({ url }) => {
    abrirFora(url)
    return { action: 'deny' }
  })
  const barrarSeSair = (evento: { preventDefault: () => void }, destino: string): void => {
    if (mesmaPagina(conteudo.getURL(), destino)) return
    evento.preventDefault()
    abrirFora(destino)
  }
  conteudo.on('will-navigate', barrarSeSair)
  conteudo.on('will-redirect', barrarSeSair)
}

export function abrirJanela(): BrowserWindow {
  const existente = janelaPrincipal()
  if (existente) {
    trazerParaFrente(existente)
    return existente
  }

  janela = new BrowserWindow({
    // Smaller than the previous 1100x720: with the navigation on the side the
    // content no longer needs a tab strip and a status header, and this is a
    // background app — taking up half the screen to show eight numbers is
    // disproportionate.
    //
    // The minimum width fits the sidebar (192px) plus the four metric cards at
    // the `md` breakpoint (768px).
    width: 980,
    height: 680,
    minWidth: 820,
    minHeight: 520,
    // Taskbar and Alt+Tab. Without this dev runs with the Electron icon.
    icon: ICONE_APP,
    // No Windows frame: the title bar is drawn by the renderer, with the
    // controls on the left, macOS-style.
    //
    // `frame: false` instead of `titleBarStyle: 'hidden'` + `titleBarOverlay`
    // because the Windows overlay draws the native buttons on the RIGHT and
    // does not allow moving them — the result would be two sets of controls.
    // With `frame: false` the window loses edge resizing, so `resizable` stays
    // on and Electron keeps the invisible drag edges.
    frame: false,
    resizable: true,
    // Rounded corners on Windows 11 (no-op on earlier versions).
    roundedCorners: true,
    // Avoids the flash between the window appearing and React painting. It is
    // the `--background` from index.css — oklch(0.188 0.008 55) — in hex; any
    // other value shows up as a flash of the wrong color. `show: false` +
    // `ready-to-show` does the rest.
    backgroundColor: '#1d1a17',
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: arquivoDoApp('dist', 'main', 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  janela.once('ready-to-show', () => janela?.show())

  // Closing the window does NOT quit the app: it lives in the tray and the
  // executor keeps running. Without this, closing the window would kill the
  // executor in the middle of a job — the opposite of what the user expects
  // from a background agent.
  janela.on('close', (evento) => {
    if (!encerrandoDeVerdade) {
      evento.preventDefault()
      janela?.hide()
    }
  })

  janela.on('closed', () => { janela = null })

  protegerNavegacao(janela.webContents)

  // F12 and Ctrl+Shift+I. Without a frame there is no system menu, so the
  // shortcut has to be handled here — it is the only way to open DevTools in
  // the packaged app when something needs to be investigated on the user's
  // machine.
  janela.webContents.on('before-input-event', (_evento, input) => {
    if (input.type !== 'keyDown') return
    const f12 = input.key === 'F12'
    const ctrlShiftI = input.control && input.shift && input.key.toLowerCase() === 'i'
    if (f12 || ctrlShiftI) janela?.webContents.toggleDevTools()
  })

  if (DEV_SERVER) {
    void janela.loadURL(DEV_SERVER)
    // It does NOT open by itself. Chromium's DevTools dumps onto the terminal
    // console a handful of its own internal errors — "Unknown VE context",
    // "Autofill.enable wasn't found" — that have nothing to do with the app
    // and make any `npm run dev` look broken.
    //
    // Whoever wants DevTools open from the start asks for it:
    // ATLANS_DEVTOOLS=1 npm run dev.
    if (process.env.ATLANS_DEVTOOLS === '1') {
      janela.webContents.openDevTools({ mode: 'detach' })
    }
  } else {
    void janela.loadFile(arquivoDoApp('dist', 'renderer', 'index.html'))
  }
  return janela
}

/**
 * Window dedicated to the log.
 *
 * It exists so the log can sit next to something else — the app's panel, the
 * Studio in the browser, an editor. In a single window, reading the log costs
 * losing sight of everything else, and it is precisely while investigating a
 * problem that you want both.
 *
 * Differences from the main window, both deliberate:
 *
 *  - closing CLOSES. It keeps no state at all (the log lives in main's store),
 *    so hiding it like the main window would only create a ghost window.
 *  - wide, short proportions by default: log lines are long, and the nearly
 *    square shape of the main window would waste height on line wrapping.
 */
export function abrirJanelaDeLog(): BrowserWindow {
  if (janelaLog && !janelaLog.isDestroyed()) {
    trazerParaFrente(janelaLog)
    return janelaLog
  }

  const win = new BrowserWindow({
    width: 900,
    height: 520,
    minWidth: 520,
    minHeight: 280,
    title: 'Log — Atlans Executor',
    icon: ICONE_APP,
    frame: false,
    resizable: true,
    roundedCorners: true,
    backgroundColor: '#1d1a17',
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: arquivoDoApp('dist', 'main', 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })
  janelaLog = win

  win.once('ready-to-show', () => win.show())
  win.on('closed', () => { janelaLog = null })

  protegerNavegacao(win.webContents)
  win.webContents.on('before-input-event', (_evento, input) => {
    if (input.type !== 'keyDown') return
    const f12 = input.key === 'F12'
    const ctrlShiftI = input.control && input.shift && input.key.toLowerCase() === 'i'
    if (f12 || ctrlShiftI) win.webContents.toggleDevTools()
  })

  if (DEV_SERVER) {
    void win.loadURL(`${DEV_SERVER}${HASH_LOG}`)
  } else {
    void win.loadFile(arquivoDoApp('dist', 'renderer', 'index.html'), { hash: HASH_LOG })
  }
  return win
}

let encerrandoDeVerdade = false

/** Releases `close` to actually close. Called on the app's exit path. */
export function permitirEncerramento(): void {
  encerrandoDeVerdade = true
}

/**
 * Tells whether the app is already on its exit path.
 *
 * The web window (janela-web.ts) also hides on `close` instead of quitting,
 * and needs to consult this same decision — without it, each window would keep
 * its own copy of the state and one of them would really close in the middle
 * of the drain.
 */
export function estaEncerrando(): boolean {
  return encerrandoDeVerdade
}

