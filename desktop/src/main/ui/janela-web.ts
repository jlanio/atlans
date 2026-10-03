// desktop/src/main/ui/janela-web.ts
//
// The app's main window: shows the installation's web interface, giving the
// executor — which already runs in the background — the face of standalone
// software.
//
// ## Isolation
//
// This window loads REMOTE content, and that is why it is deliberately
// separate from the panel window (windows.ts):
//
//   - its OWN, minimal preload (web-preload.cjs): it exposes neither
//     `window.atlas` nor `ipcRenderer`, only the READ-ONLY bridge
//     `window.atlansDesktop` (public executor status) — see the header of
//     preload/web.ts;
//   - `partition: 'persist:atlans'`, an isolated, persistent session: the
//     login (the NextAuth session cookie) survives restarts, like in a native
//     app, and does not mix with anything local;
//   - `sandbox: true`, `contextIsolation: true`, `nodeIntegration: false`.
//
// Any XSS in the web UI stays contained in an unprivileged browser — it does
// not reach the executor, the filesystem or IPC.
//
// ## Navigation
//
// The web UI authenticates with a same-origin credential (no third-party
// OAuth), so the rule is strict: the UI and its API navigate inside;
// everything else goes to the system browser, where the user sees the address.
import { BrowserWindow, shell } from 'electron'
import { ICONE_APP, arquivoDoApp } from '../paths.js'
import { UI_URL, ehExternoSeguro, ehOrigemInterna, hostsInternos } from '../../shared/ui.js'
import { ehDeepLink } from '../deeplink.js'
import { estaEncerrando, trazerParaFrente } from './windows.js'

let janela: BrowserWindow | null = null

export function janelaWebPrincipal(): BrowserWindow | null {
  return janela && !janela.isDestroyed() ? janela : null
}

// Who processes an `atlans://` clicked INSIDE the web window. Injected by main
// (index.ts) because deep link dispatch — validating, filling in the form,
// bringing the panel to the front — lives there. Without this, a click on
// "Abrir no app" (open in app) in the embedded web UI would have nowhere to go
// and would die in `will-navigate`.
let encaminharDeepLink: ((url: string) => void) | null = null

/**
 * Registers the handler for a deep link clicked in the web window. Called once
 * at boot (index.ts) with the SAME function that handles a deep link coming
 * from outside, so that "Abrir no app" behaves the same inside and outside the
 * app.
 */
export function definirTratadorDeepLink(fn: (url: string) => void): void {
  encaminharDeepLink = fn
}

/**
 * Effective UI URL. Fixed at {@link UI_URL}; `ATLANS_UI_URL` only redirects it
 * to a staging/local one during development. Read HERE, in main — never in the
 * shared module, which the sandboxed renderer also imports.
 */
function urlDaUI(): string {
  const bruta = process.env.ATLANS_UI_URL?.trim()
  if (!bruta) return UI_URL
  try {
    const u = new URL(bruta)
    if (u.protocol === 'https:' || u.protocol === 'http:') return u.toString()
  } catch {
    /* invalid input falls back to the default */
  }
  return UI_URL
}

/** Local HTML shown when the UI does not load (network down, server down). */
function paginaOffline(url: string): string {
  // INLINE page, without depending on a packaged file: works the same in dev
  // (no `vite build`) and in the packaged app. "Tentar de novo" (try again) is
  // a link to the UI itself — `will-navigate` recognizes the origin and lets
  // it through.
  return `<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sem conexão — Atlans</title>
<style>
  :root { color-scheme: dark }
  * { box-sizing: border-box }
  body {
    margin: 0; height: 100vh; display: flex; align-items: center;
    justify-content: center; background: #1d1a17; color: #e7e2da;
    font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    -webkit-user-select: none; user-select: none;
    /* A janela é sem barra de título: sem a faixa de arrasto da UI web aqui,
       a página offline arrasta pelo corpo inteiro (o botão é no-drag abaixo). */
    -webkit-app-region: drag;
  }
  .caixa { max-width: 380px; padding: 32px; text-align: center }
  h1 { font-size: 18px; font-weight: 600; margin: 0 0 8px }
  p { margin: 0 0 24px; color: #a8a099 }
  a.botao {
    display: inline-block; padding: 10px 20px; border-radius: 8px;
    background: #c2703d; color: #fff; text-decoration: none; font-weight: 600;
    -webkit-app-region: no-drag;
  }
  a.botao:hover { background: #d17f4a }
</style></head>
<body><div class="caixa">
  <h1>Sem conexão com o Atlans</h1>
  <p>Não foi possível carregar a interface. Verifique sua conexão e tente novamente.</p>
  <a class="botao" href="${url}">Tentar de novo</a>
</div></body></html>`
}

export function abrirJanelaWeb(): BrowserWindow {
  const existente = janelaWebPrincipal()
  if (existente) {
    trazerParaFrente(existente)
    return existente
  }

  const url = urlDaUI()
  const alvo = new URL(url)
  const hosts = hostsInternos(alvo.hostname)
  // Staging/local over `http:` loosens the scheme; production is HTTPS, period.
  const protocolos = alvo.protocol === 'http:' ? ['https:', 'http:'] : ['https:']
  const interno = (u: string): boolean => ehOrigemInterna(u, { hosts, protocolos })

  janela = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 900,
    minHeight: 600,
    icon: ICONE_APP,
    // Avoids the flash between the window appearing and the UI painting — same
    // background as the other windows (see windows.ts).
    backgroundColor: '#1d1a17',
    show: false,
    autoHideMenuBar: true,
    // The window buttons are painted by Windows on the right, over the content;
    // the drag strip comes from web-preload. See preload/web.ts.
    titleBarStyle: 'hidden',
    titleBarOverlay: { color: '#1d1a17', symbolColor: '#e7e2da', height: 32 },
    webPreferences: {
      preload: arquivoDoApp('dist', 'main', 'web-preload.cjs'),
      partition: 'persist:atlans',
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  // REMOTE content (the web UI) runs in this session. Electron APPROVES
  // permission requests by default — without a handler, an XSS in the remote
  // page could obtain camera, microphone, geolocation or OS notifications
  // without a prompt, breaking the containment that the rest of the isolation
  // (sandbox, no nodeIntegration) guarantees. We deny everything by default;
  // the only exception is clipboard WRITE, which the UI's "Copiar" (copy)
  // buttons use (clipboard read and the rest stay out).
  const PERMISSOES_WEB = new Set(['clipboard-sanitized-write'])
  const sessaoWeb = janela.webContents.session
  sessaoWeb.setPermissionRequestHandler((_wc, permissao, cb) => cb(PERMISSOES_WEB.has(permissao)))
  sessaoWeb.setPermissionCheckHandler((_wc, permissao) => PERMISSOES_WEB.has(permissao))

  janela.once('ready-to-show', () => janela?.show())

  // Closing HIDES, it does not quit: the app lives in the tray and the executor
  // keeps running — the same contract as the panel window. Only an explicit
  // quit closes it.
  janela.on('close', (evento) => {
    if (!estaEncerrando()) {
      evento.preventDefault()
      janela?.hide()
    }
  })
  janela.on('closed', () => { janela = null })

  // Destination that is NOT an internal origin. Three ways out:
  //   - `atlans://` → enrollment deep link. The web UI's "Abrir no app" is an
  //     `<a href="atlans://…">`; in a browser the OS routes it to the app, but
  //     clicked IN HERE it is just navigation and, without this detour, would
  //     die below (it is neither internal nor a safe external scheme). It is
  //     forwarded to the SAME handler as the external deep link — it opens the
  //     panel with the form filled in.
  //   - http(s)/mailto → system browser, where the user sees the destination.
  //   - anything else → silently discarded.
  //
  // `shell.openExternal` hands the destination to the OS, so the scheme must
  // go through an allowlist (ehExternoSeguro): an XSS or redirect in the remote
  // page could trigger `file:`, `smb:` (UNC → NTLM hash leak on Windows) — and
  // `atlans://` itself does NOT go this way, it is diverted earlier.
  // `interpretar` (in main) revalidates the link and never enrolls on its own:
  // it requires human confirmation.
  const tratarExterno = (destino: string): void => {
    if (ehDeepLink(destino)) { encaminharDeepLink?.(destino); return }
    if (ehExternoSeguro(destino)) void shell.openExternal(destino)
  }

  // `target=_blank`/`window.open`: an internal origin reuses this window; an
  // external one (safe scheme) goes to the browser. Never opens a
  // BrowserWindow without an address bar for external content — the user
  // needs to see the destination.
  janela.webContents.setWindowOpenHandler(({ url: destino }) => {
    if (interno(destino)) void janela?.loadURL(destino)
    else tratarExterno(destino)
    return { action: 'deny' }
  })

  // Top-frame navigation: internal proceeds; external goes to the browser.
  // `will-redirect` gets the SAME treatment — a server 30x redirect does not
  // fire `will-navigate`, and without this an internal origin redirected
  // outside would end up RENDERED in this window without an address bar, with
  // the preload attached. Both events have the same signature (event, url).
  janela.webContents.on('will-navigate', (evento, destino) => {
    if (interno(destino)) return
    evento.preventDefault()
    tratarExterno(destino)
  })
  janela.webContents.on('will-redirect', (evento, destino) => {
    if (interno(destino)) return
    evento.preventDefault()
    tratarExterno(destino)
  })

  // Without an address bar, DevTools via shortcut is the only way to inspect
  // the embedded UI on the user's machine — same as the other windows.
  janela.webContents.on('before-input-event', (_evento, input) => {
    if (input.type !== 'keyDown') return
    const f12 = input.key === 'F12'
    const ctrlShiftI = input.control && input.shift && input.key.toLowerCase() === 'i'
    if (f12 || ctrlShiftI) janela?.webContents.toggleDevTools()
  })

  // Network/server down: the main frame fails and the window would stay blank.
  // Swap in the local page with "Tentar de novo" (try again).
  janela.webContents.on('did-fail-load', (_e, codigo, _desc, urlQueFalhou, ehFramePrincipal) => {
    // Only the top frame, and only while loading the remote UI. `-3` = ABORTED,
    // a navigation replaced by another — swapping there would flicker for
    // nothing; and the offline page itself (data:) never matches `^https?:`,
    // so there is no loop.
    if (!ehFramePrincipal || codigo === -3) return
    if (!/^https?:/i.test(urlQueFalhou)) return
    const html = paginaOffline(url)
    void janela?.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`)
  })

  void janela.loadURL(url)
  return janela
}
