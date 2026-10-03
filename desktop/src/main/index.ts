// desktop/src/main/index.ts
//
// Main process: ties together supervisor, state, window and tray.
//
// The app name (which defines `%APPDATA%\AtlansExecutor`) is set inside
// paths.ts, at the top of the module that reads the path — see the note there.
// Doing it here does not work: ESM imports are evaluated before this line.
//
// Single instance comes before everything: two instances would spawn two
// executors with the same EXECUTOR_ID, and the server would see duplicate
// connections.
import { BrowserWindow, app, dialog, ipcMain, shell } from 'electron'
import fs from 'node:fs'
import {
  ARTIFACTS_DIR_PADRAO, CERT_DIR, ENV_FILE, IS_DEV, LOG_DIR, PYTHON_EXE,
  RESOURCES, ambienteDoSpawn, envDoExecutor, garantirDiretorios, migrarDadosAntigos,
} from './paths.js'
import { PythonSupervisor } from './python/supervisor.js'
import { enrolar, type PedidoEnroll } from './python/enroll.js'
import {
  artifactsDirEfetivo, descartarEnrollment, gravarExecucao, gravarGeoSync,
  lerConfiguracao, lerExecucao, lerGeoSync, validarPasta,
  type ConfigExecucao, type ConfigGeoSync, type EstadoConfiguracao,
} from './state/config.js'
import { ESTRATEGIAS, MODOS_SYNC, PADRAO_SYNC } from '../shared/geosync.js'
import { consultarStatusCacheado, invalidarStatus } from './python/status.js'
import { interpretar, registrarProtocolo, urlDosArgumentos } from './deeplink.js'
import { iniciarUpdater, instalarAgora, pararUpdater } from './updater.js'
import { AppStore } from './state/store.js'
import { atualizarTray, criarTray, destruirTray } from './ui/tray.js'
import {
  abrirJanela, abrirJanelaDeLog, janelaPrincipal, permitirEncerramento,
} from './ui/windows.js'
import { abrirJanelaWeb, definirTratadorDeepLink, janelaWebPrincipal } from './ui/janela-web.js'
import { CANAIS_WEB, assinaturaStatus, derivarStatus } from '../shared/executor-status.js'
import { definirAutostart, iniciadoOculto, lerAutostart } from './ui/autostart.js'
import { notificarSeMudou } from './ui/notificacoes.js'
import { ACOES_JANELA, CANAIS, type AcaoJanela, type InfoApp } from '../shared/ipc.js'
import { COMMANDS, type CommandName, type ExecutorEvent } from '../shared/events.js'

if (!app.requestSingleInstanceLock()) {
  app.quit()
  process.exit(0)
}

/**
 * The app's identity for Windows — the same `appId` as in electron-builder.
 *
 * Without this Windows infers the identity from the executable: in dev it
 * becomes "Electron", and the app window shows up grouped in the taskbar under
 * the Electron icon, separate from the Start Menu shortcut. Notification
 * toasts also depend on this ID.
 */
app.setAppUserModelId('app.atlans.executor')

const store = new AppStore()

// Deep link that arrived before the renderer existed. Without this, an
// `atlans://` that OPENS the app would be lost: the window has not yet
// subscribed to the channel when the event is emitted, and the form would
// show up empty.
let deepLinkPendente: ReturnType<typeof interpretar> = null
let supervisor: PythonSupervisor | null = null
let encerrando = false
// Signature of the last status sent to the web window — push dedupe. See the
// `store.assinar` callback below and shared/executor-status.ts.
let ultimaAssinaturaStatusWeb = ''

// Cached configuration for the status HOT PATH. `lerConfiguracao` does
// synchronous I/O (readFileSync of the .env + existsSync of the PEMs) and the
// `store.assinar` callback runs on every tick — rereading the disk there, at
// ~12 Hz in a burst, is the pattern the project has already treated as a
// defect (see the cache in autostart.ts). Only enrollment changes
// `configurado`/`executorId`, so we invalidate only at those points; the
// on-demand `CANAIS.configuracao` handler keeps reading fresh.
let cfgCache: EstadoConfiguracao | null = null
function configAtual(): EstadoConfiguracao {
  if (!cfgCache) cfgCache = lerConfiguracao()
  return cfgCache
}
function invalidarConfig(): void { cfgCache = null }

// ── Supervisor ───────────────────────────────────────────────────────────────

function criarSupervisor(): PythonSupervisor {
  const sup = new PythonSupervisor({
    pythonExe: PYTHON_EXE,
    cwd: RESOURCES,
    // Reads the `.env` on every spawn: setting the folder in Ajustes (Settings)
    // and restarting the executor has to take effect without reopening the app.
    env: ambienteDoSpawn(envDoExecutor(artifactsDirEfetivo(ARTIFACTS_DIR_PADRAO))),
  })

  sup.on('estado', (estado, detalhe) => {
    store.aplicarEstadoSupervisor(estado, detalhe)
    // Executor up: the right moment to fetch the workspace list ahead of time,
    // which the GeoSync tab asks for and takes seconds to answer (spawn of a
    // second Python + mTLS). Not at boot, so as not to compete with the
    // executor starting, and only once — `consultarStatusCacheado` returns the
    // cache without spawning.
    if (estado === 'running') void consultarStatusCacheado()
  })
  // Every event ALSO went raw to all windows, over a channel no renderer
  // subscribed to: one structured clone per event, per window, for nobody —
  // two per synced file, plus the 1 Hz snapshot. What the UI shows comes out
  // of the store, which already delivers coalesced state and incremental log.
  sup.on('evento', (evt: ExecutorEvent) => {
    store.aplicarEvento(evt)
  })
  sup.on('linha', (texto, origem) => {
    store.registrarLinhaBruta(texto, origem)
  })
  return sup
}

function difundir(canal: string, dado: unknown): void {
  // The web window hosts REMOTE content (the web UI) and is deliberately
  // skipped: the panel's channels carry state, log and the deep link's OTP, and
  // none of that may go to the remote origin. Today its preload neither listens
  // to those channels nor exposes `ipcRenderer` — but not delivering is the
  // guarantee, not luck. Its redacted status goes over its own channel (CANAIS_WEB).
  const web = janelaWebPrincipal()
  for (const win of BrowserWindow.getAllWindows()) {
    if (win.isDestroyed()) continue
    if (web && win.id === web.id) continue
    win.webContents.send(canal, dado)
  }
}

/**
 * Nothing may spawn the executor once shutdown has started.
 *
 * `encerrarApp()` sets `encerrando` and only then AWAITS the drain (up to
 * 150 s); during that wait the tray and the window are still up, and an
 * "Iniciar" (start) there would launch a Python that nobody kills anymore —
 * main exits right after and the process is orphaned, holding the WebSocket
 * with the same EXECUTOR_ID.
 */
function iniciarExecutor(): void {
  if (encerrando) return
  supervisor?.start()
}

const acoesTray = {
  iniciar: iniciarExecutor,
  parar: () => { void supervisor?.stop() },
  sair: () => { void encerrarApp() },
}

// The log goes over its own INCREMENTAL channel — see the header of store.ts.
store.assinarLog((lote) => difundir(CANAIS.aoReceberLog, lote))

store.assinar((estado) => {
  difundir(CANAIS.aoAtualizarEstado, estado)
  atualizarTray(estado, acoesTray)
  // Guarded by comparison with the previous condition — see notificacoes.ts.
  // This callback runs once per second with the executor running.
  notificarSeMudou(estado, () => abrirJanela())

  // Pushes the redacted status to the web window — only when it exists (the
  // `lerConfiguracao`, which is I/O, does not even run without an open window)
  // and only when the signature changes (state is re-evaluated on every tick;
  // status, rarely).
  const janelaWeb = janelaWebPrincipal()
  if (janelaWeb) {
    const status = derivarStatus(estado, configAtual())
    const assinatura = assinaturaStatus(status)
    if (assinatura !== ultimaAssinaturaStatusWeb) {
      ultimaAssinaturaStatusWeb = assinatura
      janelaWeb.webContents.send(CANAIS_WEB.statusMudou, status)
    }
  }
})

// ── IPC ──────────────────────────────────────────────────────────────────────

function registrarIpc(): void {
  ipcMain.handle(CANAIS.estado, () => store.instantaneo())
  ipcMain.handle(CANAIS.log, () => store.logCompleto())

  // Read-only bridge of the web window (preload/web.ts): the executor's redacted
  // status for the first render. Pushes of changes come from the `store.assinar` callback.
  ipcMain.handle(CANAIS_WEB.status, () => derivarStatus(store.instantaneo(), configAtual()))

  ipcMain.handle(CANAIS.info, (): InfoApp => ({
    versao: app.getVersion(),
    versaoElectron: process.versions.electron,
    envFile: ENV_FILE,
    certDir: CERT_DIR,
    logDir: LOG_DIR,
    artifactsDir: ARTIFACTS_DIR_PADRAO,
    dev: IS_DEV,
  }))

  ipcMain.handle(CANAIS.configuracao, () => lerConfiguracao())

  // The renderer asks on mount; the push covers the case of the app already being open.
  ipcMain.handle(CANAIS.deepLinkPendente, () => {
    const p = deepLinkPendente
    deepLinkPendente = null   // consumed only once
    return p
  })

  ipcMain.handle(CANAIS.enrolar, async (_e, pedido: unknown) => {
    const p = pedido as Partial<PedidoEnroll>
    if (!p?.executorId?.trim() || !p.otp?.trim()) {
      return { ok: false, codigo: 'executor_id_ausente', erro: 'Preencha todos os campos.' }
    }
    // No `servidor`: it is the SERVIDOR constant, resolved inside
    // `enrolar`. See shared/servidor.ts.
    const r = await enrolar({ executorId: p.executorId.trim(), otp: p.otp.trim() })
    // Success: there is no reason to make the user click "Iniciar" (start) next —
    // they have just said what they wanted.
    if (r.ok) {
      // New binding, new certificate: the reachable workspaces are different ones.
      invalidarStatus()
      invalidarConfig()   // executorId/certificado mudaram — releia no proximo status
      iniciarExecutor()
    }
    return r
  })

  ipcMain.handle(CANAIS.refazerEnrollment, async () => {
    // Stops FIRST: with the executor alive, the PEMs may be open, and an executor
    // running without a cert has nowhere to go. The `await` here is legitimate
    // (10 s ceiling) and the order is what matters.
    await supervisor?.stop(10_000)
    invalidarStatus()
    invalidarConfig()   // certificado descartado — o status volta a "sem-vinculo"
    const { removidos } = descartarEnrollment()
    store.aplicarEstadoSupervisor(
      'stopped',
      removidos.length
        ? 'Certificado descartado — vincule este computador novamente.'
        : 'Nenhum certificado a descartar.',
    )
    return lerConfiguracao()
  })

  ipcMain.handle(CANAIS.iniciar, () => { iniciarExecutor() })

  // Fire and return. `stop()` only resolves on Python's `exit`, that is, after
  // the whole drain (up to 150 s): waiting for it here kept the renderer
  // "busy" the whole time and disabled precisely the "Forcar" (force) buttons,
  // which are the way out of the wait. The `state: draining` and the snapshots
  // tell the rest through the state subscription.
  ipcMain.handle(CANAIS.parar, () => { void supervisor?.stop() })

  // STOP -> START sequence on this side. Done in the renderer with two
  // invokes, it would break now that `parar` returns immediately: `start()`
  // exits without doing anything while the old process is still alive, and the
  // executor would stay stopped after draining.
  //
  // The supervisor's `restart()` is what guards the restart: the drain can
  // take 150 s, and in that interval the user may have asked to "Sair" (quit)
  // from the tray (hence the `!encerrando` guard) or another stop. Restarting
  // anyway would leave an orphaned Python — see the header of `restart()`.
  ipcMain.handle(CANAIS.reiniciar, async () => {
    await supervisor?.restart(() => !encerrando)
  })

  ipcMain.handle(CANAIS.forcar, () => { supervisor?.forcar() })

  ipcMain.handle(CANAIS.comando, (_e, cmd: unknown) => {
    // Validates against the closed list. The renderer cannot inject an arbitrary
    // command into the Python process's stdin.
    if (typeof cmd !== 'string' || !COMMANDS.includes(cmd as CommandName)) return false
    return supervisor?.enviar({ cmd: cmd as CommandName }) ?? false
  })

  ipcMain.handle(CANAIS.escolherPasta, async (_e, atual?: string) => {
    const win = janelaPrincipal()
    const r = await dialog.showOpenDialog(win ?? undefined as never, {
      properties: ['openDirectory', 'createDirectory'],
      defaultPath: typeof atual === 'string' && atual ? atual : ARTIFACTS_DIR_PADRAO,
    })
    return r.canceled || !r.filePaths[0] ? null : r.filePaths[0]
  })

  ipcMain.handle(CANAIS.abrirCaminho, async (_e, caminho: unknown) => {
    // Only paths the app itself knows. Opening an arbitrary path coming from
    // the renderer would give any displayed content (a workflow log, for
    // example) the power to launch an executable.
    const permitidos = [
      ENV_FILE, CERT_DIR, LOG_DIR, ARTIFACTS_DIR_PADRAO,
      artifactsDirEfetivo(ARTIFACTS_DIR_PADRAO),
      // Pasta do GeoSync: o usuario a escolheu, e a tela oferece 'Abrir'.
      lerGeoSync().pasta,
    ].filter((p): p is string => Boolean(p))
    if (typeof caminho !== 'string' || !permitidos.includes(caminho)) return
    await shell.openPath(caminho)
  })

  ipcMain.handle(CANAIS.geosync, () => lerGeoSync())

  ipcMain.handle(CANAIS.salvarGeosync, (_e, cfg: unknown) => {
    const c = cfg as ConfigGeoSync
    if (!c) return { salvo: false, invalidas: [] }

    const pasta = typeof c.pasta === 'string' && c.pasta.trim() ? c.pasta.trim() : null
    const invalida = validarPasta(pasta)

    gravarGeoSync({
      // An invalid folder is not saved, but the rest of the settings are: refusing
      // everything because the folder was removed from disk would block editing
      // the mode and the workspace. The reason goes back to the renderer in
      // `invalidas`.
      pasta: invalida ? null : pasta,
      modo: MODOS_SYNC.includes(c.modo) ? c.modo : PADRAO_SYNC.modo,
      conflito: ESTRATEGIAS.includes(c.conflito) ? c.conflito : PADRAO_SYNC.conflito,
      workspaceId: typeof c.workspaceId === 'string' && c.workspaceId.trim() ? c.workspaceId.trim() : null,
    })
    return { salvo: true, invalidas: invalida ? [invalida] : [] }
  })

  ipcMain.handle(CANAIS.workspaces, (_e, atualizar?: unknown) => (
    consultarStatusCacheado(atualizar === true)
  ))

  ipcMain.handle(CANAIS.execucao, () => lerExecucao(ARTIFACTS_DIR_PADRAO))

  ipcMain.handle(CANAIS.salvarExecucao, (_e, cfg: unknown) => {
    // `gravarExecucao` reapplies the ranges from executor/config.py — the
    // renderer validates to give immediate feedback, but this side is the one
    // that guarantees it.
    gravarExecucao(cfg as ConfigExecucao)
    return lerExecucao(ARTIFACTS_DIR_PADRAO)
  })

  ipcMain.handle(CANAIS.exportarLog, async (_e, texto: unknown) => {
    if (typeof texto !== 'string') return null
    const win = janelaPrincipal()
    const r = await dialog.showSaveDialog(win ?? undefined as never, {
      title: 'Exportar log',
      defaultPath: `atlans-executor-${new Date().toISOString().slice(0, 10)}.log`,
      filters: [{ name: 'Log', extensions: ['log', 'txt'] }],
    })
    if (r.canceled || !r.filePath) return null
    await fs.promises.writeFile(r.filePath, texto, 'utf8')
    return r.filePath
  })

  ipcMain.handle(CANAIS.janela, (e, acao: unknown) => {
    // The SENDER's window, not `janelaPrincipal()`: with the log window open,
    // both renderers draw the same title bar, and always resolving to the main
    // one would make the log's close button hide the panel.
    const win = BrowserWindow.fromWebContents(e.sender)
    if (!win || typeof acao !== 'string' || !ACOES_JANELA.includes(acao as AcaoJanela)) return false
    switch (acao as AcaoJanela) {
      case 'minimizar': win.minimize(); return false
      case 'alternar-maximizar':
        if (win.isMaximized()) win.unmaximize()
        else win.maximize()
        return win.isMaximized()
      case 'fechar':
        // On the main window, hides instead of quitting: the app lives in the tray
        // and the executor keeps running — closing in the middle of a job would
        // be destructive. The log window's `close` has no such guard, so it
        // actually closes (see abrirJanelaDeLog).
        win.close()
        return false
      case 'esta-maximizada': return win.isMaximized()
    }
  })

  ipcMain.handle(CANAIS.abrirJanelaLog, () => { abrirJanelaDeLog() })

  ipcMain.handle(CANAIS.autostart, (_e, ativar?: unknown) => {
    if (typeof ativar === 'boolean') return definirAutostart(ativar)
    return lerAutostart()
  })
}

// ── Lifecycle ────────────────────────────────────────────────────────────────

app.on('second-instance', (_evento, argv) => {
  const url = urlDosArgumentos(argv)
  // A deep link is enrollment: `tratarDeepLink` already brings the PANEL to the
  // front. An ordinary second launch wants the app — the WEB window.
  if (url) { tratarDeepLink(url); return }
  abrirJanelaWeb()
})

function tratarDeepLink(bruta: string): void {
  const pedido = interpretar(bruta)
  if (!pedido) {
    // Silent refusal for the user, loud in the log: a malformed deep link is
    // almost always a page trying something, and it is not worth an alert that
    // teaches people to ignore alerts.
    store.registrarLinhaBruta(`[app] Deep link recusado: ${bruta.slice(0, 120)}`, 'stderr')
    return
  }
  deepLinkPendente = pedido
  difundir(CANAIS.aoReceberDeepLink, pedido)
  abrirJanela()
}

app.whenReady().then(() => {
  // Before garantirDiretorios: the migration only happens while the new folder
  // does not exist yet.
  const migrado = migrarDadosAntigos()
  garantirDiretorios()
  if (migrado) {
    store.registrarLinhaBruta(
      `[app] Dados migrados de "${migrado}" para "AtlansExecutor" — certificado e configuração preservados.`,
      'stderr',
    )
  }
  registrarProtocolo()
  registrarIpc()
  // "Abrir no app" (open in the app) in the embedded web UI fires an
  // `atlans://`. Clicked inside the web window it is in-app navigation: the
  // window forwards it here, to the SAME handler as the deep link coming from
  // the browser — the app behaves the same in both cases.
  definirTratadorDeepLink(tratarDeepLink)
  supervisor = criarSupervisor()
  criarTray(acoesTray)

  // Auto-update. Installation only happens in `encerrarApp`, after the
  // executor's orderly shutdown: replacing the `resources/` tree with a
  // workflow running would kill the job without confirming the result to the
  // server, which would mark it as orphaned.
  void iniciarUpdater((e) => {
    if (e.baixado) {
      store.registrarLinhaBruta(
        `[app] Atualização ${e.versao} pronta para instalar. Ela é aplicada ao sair do app.`,
        'stderr',
      )
    }
  })

  // A deep link that OPENED the app arrives in the process's own argv.
  const urlInicial = urlDosArgumentos(process.argv)
  if (urlInicial) {
    const pedido = interpretar(urlInicial)
    if (pedido) deepLinkPendente = pedido
  }

  const cfg = lerConfiguracao()
  if (cfg.configurado) {
    supervisor.start()
  } else {
    // Without enrollment there is nothing to run. Spawning anyway would make the
    // executor exit reporting `failed: config` — correct, but useless. The
    // message stays ready for whoever opens the panel; the main window,
    // however, is the web one — it is there, in Executores (Executors), that
    // the user generates the binding OTP.
    store.aplicarEstadoSupervisor(
      'stopped',
      cfg.falta === 'enrollment'
        ? 'Certificado ausente — refaça o enrollment.'
        : 'Este computador ainda não foi vinculado a um executor.',
    )
  }

  // Which window to open at boot:
  //  - pending deep link → PANEL, where the enrollment form lives;
  //  - otherwise → the WEB window, the face of the app (and, with no binding
  //    yet, the place where the user generates the OTP in Executores).
  //
  // Only the hidden autostart of an ALREADY bound installation starts without
  // a window: an unconfigured app that starts at logon and does not show up
  // would leave the person with no clue what to do, so that case still opens
  // the web window.
  if (deepLinkPendente) abrirJanela()
  else if (!(cfg.configurado && iniciadoOculto())) abrirJanelaWeb()
})

// Without this the app would quit when closing the last window, killing the
// executor in the middle of a job. It lives in the tray; quitting is explicit.
app.on('window-all-closed', () => { /* intencionalmente vazio */ })

app.on('before-quit', (evento) => {
  if (encerrando) return
  evento.preventDefault()
  void encerrarApp()
})

async function encerrarApp(): Promise<void> {
  if (encerrando) return
  encerrando = true
  try {
    // ORDERLY shutdown, not kill: drains the jobs in progress and confirms the
    // results. Without it, quitting the app would mark runs as orphaned on the
    // server.
    await supervisor?.stop()
  } catch { /* quitting cannot fail */ }
  // Delivers whatever is stuck in the coalescing window. Without this, the
  // `state: failed` or the last log line of the shutdown would sit in an 80ms
  // timer that never fires, and the window would show the second-to-last state.
  store.descarregar()
  pararUpdater()
  destruirTray()
  permitirEncerramento()

  // If there is a downloaded update, shutdown is the window of opportunity: the
  // executor has already stopped in an orderly way above, so replacing the
  // resources/ tree now interrupts no work at all.
  if (instalarAgora()) return
  app.quit()
}
