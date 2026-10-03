// desktop/src/main/ui/tray.ts
//
// Tray icon: it is the app's presence when the window is closed.
//
// The icon communicates the state at a glance — connected, busy, offline.
// Without it the user has no way of knowing whether the executor is receiving
// jobs without opening the window.
//
// ⚠️ This module is notified on EVERY store update, that is, once per second
// while the executor runs. Everything here is guarded by comparison with the
// previous state: rebuilding the menu at 1 Hz closes it in the face of whoever
// just opened it, and reloading the icon from disk at 1 Hz is pure wasted I/O.
import { Menu, Tray, app, nativeImage, type NativeImage } from 'electron'
import fs from 'node:fs'
import { arquivoDoApp } from '../paths.js'
import type { AppState } from '../state/store.js'
import { abrirJanela } from './windows.js'
import { abrirJanelaWeb } from './janela-web.js'
import { autostartAtivo, definirAutostart } from './autostart.js'

let tray: Tray | null = null

export type IconState = 'online' | 'busy' | 'offline'

const ICON_FILE: Record<IconState, string> = {
  online: 'icon.ico',
  busy: 'icon-busy.ico',
  offline: 'icon-offline.ico',
}

/** Icons loaded once. See the header note about I/O at 1 Hz. */
const iconCache = new Map<IconState, NativeImage>()

function loadIcon(estado: IconState): NativeImage {
  const emCache = iconCache.get(estado)
  if (emCache) return emCache

  const caminho = arquivoDoApp('build', ICON_FILE[estado])
  // `createFromPath` on a missing file returns an EMPTY image instead of
  // throwing, and the result is an invisible tray — the app seems not to have
  // opened. A visible generic icon is better than none.
  let img = nativeImage.createEmpty()
  if (fs.existsSync(caminho)) {
    const carregada = nativeImage.createFromPath(caminho)
    if (!carregada.isEmpty()) img = carregada
  }
  iconCache.set(estado, img)
  return img
}

// ── Pure functions (testable without Electron) ───────────────────────────────

export function estadoDoIcone(estado: AppState | null): IconState {
  if (!estado || estado.supervisor !== 'running') return 'offline'
  const snap = estado.snapshot
  if (!snap || snap.conn_state !== 'connected') return 'offline'
  return snap.running_count > 0 ? 'busy' : 'online'
}

export function resumo(estado: AppState | null): string {
  if (!estado) return 'Iniciando…'
  switch (estado.supervisor) {
    case 'stopped': return estado.detalheSupervisor ?? 'Parado'
    case 'starting': return 'Iniciando…'
    case 'draining': {
      const n = estado.snapshot?.running_count ?? 0
      return n > 0 ? `Encerrando — ${n} execução(ões) em andamento` : 'Encerrando…'
    }
    case 'restarting': return estado.detalheSupervisor ?? 'Reiniciando…'
    case 'failed': return `Parado por erro — ${estado.detalheSupervisor ?? 'ver detalhes'}`
    case 'running': {
      const snap = estado.snapshot
      if (!snap) return 'Conectando…'
      if (snap.conn_state !== 'connected') return `Sem conexão (${snap.conn_state})`
      return snap.running_count > 0
        ? `${snap.running_count} execução(ões) em andamento`
        : 'Conectado, ocioso'
    }
  }
}

/**
 * Slice of the state the tray actually displays.
 *
 * This string is what decides whether to rebuild the menu. Comparing the whole
 * `AppState` would be useless: it changes on every snapshot (uptime, CPU,
 * memory), and none of that appears in the tray.
 *
 * `autostartAtivo()` answers from the module cache (see autostart.ts): it used
 * to read the Windows registry synchronously, right here, on every state
 * update — the only spot in the file that escaped the 1 Hz shielding.
 */
export function assinaturaDoTray(estado: AppState | null): string {
  return [
    estadoDoIcone(estado),
    resumo(estado),
    estado?.supervisor ?? '',
    autostartAtivo() ? '1' : '0',
  ].join('|')
}

// ── Lifecycle ────────────────────────────────────────────────────────────────

export interface TrayActions {
  iniciar: () => void
  parar: () => void
  sair: () => void
}

let lastSignature = ''

export function createTray(acoes: TrayActions): Tray {
  tray = new Tray(loadIcon('offline'))

  // A single click opens the app — the web window, which is the face of the
  // product. It is the gesture the user tries first, and not responding gives
  // the impression of a frozen app. No `double-click`: on Windows a double
  // click fires `click` twice AND `double-click`, which would open the window
  // three times.
  tray.on('click', () => abrirJanelaWeb())

  lastSignature = ''
  updateTray(null, acoes)
  return tray
}

export function updateTray(estado: AppState | null, acoes: TrayActions): void {
  if (!tray) return

  const assinatura = assinaturaDoTray(estado)
  if (assinatura === lastSignature) return    // nada que o tray mostre mudou
  lastSignature = assinatura

  const texto = resumo(estado)
  tray.setImage(loadIcon(estadoDoIcone(estado)))
  // The Windows tooltip cuts off at 127 characters; a long error detail would
  // fill the limit and hide the beginning, which is the useful part.
  tray.setToolTip(`Atlans Executor — ${texto}`.slice(0, 127))

  const rodando = estado?.supervisor === 'running' || estado?.supervisor === 'starting'
  const encerrando = estado?.supervisor === 'draining'

  tray.setContextMenu(Menu.buildFromTemplate([
    { label: texto, enabled: false },
    { type: 'separator' },
    { label: 'Abrir Atlans', click: () => abrirJanelaWeb() },
    { label: 'Painel do executor', click: () => abrirJanela() },
    { type: 'separator' },
    { label: 'Iniciar executor', enabled: !rodando && !encerrando, click: acoes.iniciar },
    { label: 'Parar executor', enabled: rodando, click: acoes.parar },
    { type: 'separator' },
    {
      label: 'Iniciar com o Windows',
      type: 'checkbox',
      checked: autostartAtivo(),
      click: (item) => {
        definirAutostart(item.checked)
        // The menu keeps the checkbox's own state; forcing the rebuild makes the
        // check mark reflect what the system ACTUALLY wrote, not what the click
        // asked for — `definirAutostart` can fail silently.
        lastSignature = ''
        updateTray(estado, acoes)
      },
    },
    { type: 'separator' },
    { label: `Versão ${app.getVersion()}`, enabled: false },
    { label: 'Sair', click: acoes.sair },
  ]))
}

export function destroyTray(): void {
  tray?.destroy()
  tray = null
  iconCache.clear()
  lastSignature = ''
}
