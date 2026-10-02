// desktop/src/main/index.ts
//
// Processo principal: amarra supervisor, estado, janela e tray.
//
// O nome do app (que define `%APPDATA%\AtlansExecutor`) e fixado dentro de
// paths.ts, no topo do modulo que le o caminho — ver a nota la. Fazer isso aqui
// nao funciona: os imports ESM sao avaliados antes desta linha.
//
// Single instance vem antes de tudo: duas instancias dariam spawn em dois
// executores com o mesmo EXECUTOR_ID, e o servidor veria conexoes duplicadas.
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
 * Identidade do app para o Windows — o mesmo `appId` do electron-builder.
 *
 * Sem isto o Windows deduz a identidade do executavel: em dev vira "Electron",
 * e a janela do app aparece agrupada na barra de tarefas sob o icone do
 * Electron, separada do atalho do Menu Iniciar. Toast de notificacao tambem
 * depende deste ID.
 */
app.setAppUserModelId('app.atlans.executor')

const store = new AppStore()

// Deep link que chegou antes de o renderer existir. Sem isto, um `atlans://`
// que ABRE o app se perderia: a janela ainda nao assinou o canal quando o
// evento e emitido, e o formulario apareceria vazio.
let deepLinkPendente: ReturnType<typeof interpretar> = null
let supervisor: PythonSupervisor | null = null
let encerrando = false
// Assinatura do último status enviado à janela web — dedupe do push. Ver o
// callback de `store.assinar` abaixo e shared/executor-status.ts.
let ultimaAssinaturaStatusWeb = ''

// Configuração em cache para o HOT PATH do status. `lerConfiguracao` faz I/O
// síncrono (readFileSync do .env + existsSync dos PEMs) e o callback de
// `store.assinar` roda a cada tick — reler o disco ali, a ~12 Hz numa rajada,
// é o padrão que o projeto já tratou como defeito (ver o cache de autostart.ts).
// Só o enrollment muda `configurado`/`executorId`, então invalidamos apenas
// nesses pontos; o handler on-demand `CANAIS.configuracao` segue lendo fresco.
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
    // Le do `.env` a cada spawn: configurar a pasta em Ajustes e reiniciar o
    // executor precisa surtir efeito sem reabrir o app.
    env: ambienteDoSpawn(envDoExecutor(artifactsDirEfetivo(ARTIFACTS_DIR_PADRAO))),
  })

  sup.on('estado', (estado, detalhe) => {
    store.aplicarEstadoSupervisor(estado, detalhe)
    // Executor no ar: momento certo de adiantar a lista de workspaces, que a
    // aba GeoSync pede e leva segundos para responder (spawn de um segundo
    // Python + mTLS). Nao no boot, para nao competir com a subida do executor,
    // e so uma vez — `consultarStatusCacheado` devolve o cache sem spawn.
    if (estado === 'running') void consultarStatusCacheado()
  })
  // Cada evento ia TAMBEM cru para todas as janelas, por um canal que nenhum
  // renderer assinava: era um structured clone por evento, por janela, para
  // ninguem — dois por arquivo sincronizado, mais o snapshot de 1 Hz. O que a
  // UI mostra sai do store, que ja entrega estado coalescido e log incremental.
  sup.on('evento', (evt: ExecutorEvent) => {
    store.aplicarEvento(evt)
  })
  sup.on('linha', (texto, origem) => {
    store.registrarLinhaBruta(texto, origem)
  })
  return sup
}

function difundir(canal: string, dado: unknown): void {
  // A janela web hospeda conteúdo REMOTO (a UI web) e é deliberadamente
  // pulada: os canais do painel carregam estado, log e o OTP do deep link, e
  // nada disso pode ir para a origem remota. Hoje o preload dela nem escuta
  // esses canais nem expõe `ipcRenderer` — mas não entregar é a garantia, não a
  // sorte. O status redigido dela vai por canal próprio (CANAIS_WEB).
  const web = janelaWebPrincipal()
  for (const win of BrowserWindow.getAllWindows()) {
    if (win.isDestroyed()) continue
    if (web && win.id === web.id) continue
    win.webContents.send(canal, dado)
  }
}

/**
 * Nada pode dar spawn no executor depois de o encerramento comecar.
 *
 * `encerrarApp()` marca `encerrando` e so entao AGUARDA a drenagem (ate 150 s);
 * durante essa espera o tray e a janela continuam de pe, e um "Iniciar" ali
 * subiria um Python que ninguem mais mata — o main encerra logo depois e o
 * processo fica orfao, segurando o WebSocket com o mesmo EXECUTOR_ID.
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

// O log vai por canal proprio e INCREMENTAL — ver o cabecalho de store.ts.
store.assinarLog((lote) => difundir(CANAIS.aoReceberLog, lote))

store.assinar((estado) => {
  difundir(CANAIS.aoAtualizarEstado, estado)
  atualizarTray(estado, acoesTray)
  // Guardado por comparacao com a condicao anterior — ver notificacoes.ts. Este
  // callback roda uma vez por segundo com o executor rodando.
  notificarSeMudou(estado, () => abrirJanela())

  // Empurra o status redigido para a janela web — so quando ela existe (a
  // `lerConfiguracao`, que e I/O, nem roda sem janela aberta) e so quando a
  // assinatura muda (o estado e reavaliado a cada tick; o status, raramente).
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

  // Ponte read-only da janela web (preload/web.ts): status redigido do executor
  // para o primeiro render. O push das mudanças sai do callback de `store.assinar`.
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

  // O renderer pergunta ao montar; o push cobre o caso de o app ja estar aberto.
  ipcMain.handle(CANAIS.deepLinkPendente, () => {
    const p = deepLinkPendente
    deepLinkPendente = null   // consumido uma vez so
    return p
  })

  ipcMain.handle(CANAIS.enrolar, async (_e, pedido: unknown) => {
    const p = pedido as Partial<PedidoEnroll>
    if (!p?.executorId?.trim() || !p.otp?.trim()) {
      return { ok: false, codigo: 'executor_id_ausente', erro: 'Preencha todos os campos.' }
    }
    // Sem `servidor`: ele é a constante SERVIDOR, resolvida dentro de
    // `enrolar`. Ver shared/servidor.ts.
    const r = await enrolar({ executorId: p.executorId.trim(), otp: p.otp.trim() })
    // Sucesso: nao ha por que fazer o usuario clicar "Iniciar" em seguida —
    // ele acabou de dizer o que queria.
    if (r.ok) {
      // Vinculo novo, certificado novo: os workspaces ao alcance sao outros.
      invalidarStatus()
      invalidarConfig()   // executorId/certificado mudaram — releia no proximo status
      iniciarExecutor()
    }
    return r
  })

  ipcMain.handle(CANAIS.refazerEnrollment, async () => {
    // Para PRIMEIRO: com o executor vivo, os PEMs podem estar abertos, e um
    // executor rodando sem cert nao tem para onde ir. O `await` aqui e legitimo
    // (teto de 10 s) e a ordem e o que importa.
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

  // Dispara e volta. `stop()` so resolve no `exit` do Python, ou seja depois da
  // drenagem inteira (ate 150 s): esperar por ele aqui prendia o renderer em
  // "ocupado" o tempo todo e desabilitava justamente os botoes "Forcar", que
  // sao a saida da espera. O `state: draining` e os snapshots contam o resto
  // pela assinatura de estado.
  ipcMain.handle(CANAIS.parar, () => { void supervisor?.stop() })

  // Sequencia PARAR -> INICIAR do lado de ca. Feita no renderer com dois
  // invokes, ela quebraria agora que `parar` volta na hora: `start()` sai sem
  // fazer nada com o processo antigo ainda vivo, e o executor ficaria parado
  // depois de drenar.
  //
  // O `restart()` do supervisor e quem guarda a religada: a drenagem pode levar
  // 150 s, e nesse intervalo o usuario pode ter pedido "Sair" no tray (dai a
  // guarda `!encerrando`) ou outra parada. Religar assim mesmo deixaria um
  // Python orfao — ver o cabecalho de `restart()`.
  ipcMain.handle(CANAIS.reiniciar, async () => {
    await supervisor?.restart(() => !encerrando)
  })

  ipcMain.handle(CANAIS.forcar, () => { supervisor?.forcar() })

  ipcMain.handle(CANAIS.comando, (_e, cmd: unknown) => {
    // Valida contra a lista fechada. O renderer nao pode injetar um comando
    // arbitrario no stdin do processo Python.
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
    // Só caminhos que o proprio app conhece. Abrir um caminho arbitrario vindo
    // do renderer daria a qualquer conteudo exibido (log de workflow, por
    // exemplo) o poder de disparar um executavel.
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
      // Pasta inválida não é gravada, mas o resto dos ajustes é: recusar tudo
      // porque a pasta foi removida do disco travaria a edição do modo e do
      // workspace. O motivo volta ao renderer em `invalidas`.
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
    // `gravarExecucao` reaplica as faixas de executor/config.py — o renderer
    // valida para dar retorno imediato, mas quem garante é este lado.
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
    // A janela do REMETENTE, e não `janelaPrincipal()`: com a janela de log
    // aberta, os dois renderers desenham a mesma barra de título, e resolver
    // sempre para a principal faria o botao de fechar do log esconder o painel.
    const win = BrowserWindow.fromWebContents(e.sender)
    if (!win || typeof acao !== 'string' || !ACOES_JANELA.includes(acao as AcaoJanela)) return false
    switch (acao as AcaoJanela) {
      case 'minimizar': win.minimize(); return false
      case 'alternar-maximizar':
        if (win.isMaximized()) win.unmaximize()
        else win.maximize()
        return win.isMaximized()
      case 'fechar':
        // Na principal, esconde em vez de encerrar: o app vive no tray e o
        // executor continua rodando — fechar no meio de um job seria
        // destrutivo. O `close` da janela de log nao tem essa guarda, entao
        // ela fecha de fato (ver abrirJanelaDeLog).
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

// ── Ciclo de vida ────────────────────────────────────────────────────────────

app.on('second-instance', (_evento, argv) => {
  const url = urlDosArgumentos(argv)
  // Deep link é enrollment: `tratarDeepLink` já traz o PAINEL para a frente. Um
  // segundo lançamento comum quer o app — a janela WEB.
  if (url) { tratarDeepLink(url); return }
  abrirJanelaWeb()
})

function tratarDeepLink(bruta: string): void {
  const pedido = interpretar(bruta)
  if (!pedido) {
    // Recusa silenciosa para o usuario, ruidosa no log: um deep link malformado
    // e quase sempre uma pagina tentando algo, e nao vale um alerta que ensina
    // a ignorar alertas.
    store.registrarLinhaBruta(`[app] Deep link recusado: ${bruta.slice(0, 120)}`, 'stderr')
    return
  }
  deepLinkPendente = pedido
  difundir(CANAIS.aoReceberDeepLink, pedido)
  abrirJanela()
}

app.whenReady().then(() => {
  // Antes de garantirDiretorios: a migração só ocorre enquanto a pasta nova
  // ainda não existe.
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
  // "Abrir no app" na UI web embutida dispara um `atlans://`. Clicado dentro
  // da janela web é navegação in-app: ela encaminha para cá, o MESMO tratador do
  // deep link vindo do navegador — o app se comporta igual nos dois casos.
  definirTratadorDeepLink(tratarDeepLink)
  supervisor = criarSupervisor()
  criarTray(acoesTray)

  // Auto-update. A instalação só acontece em `encerrarApp`, depois do shutdown
  // ordenado do executor: substituir a árvore de `resources/` com um workflow
  // rodando mataria o job sem confirmar o resultado ao servidor, que o marcaria
  // como órfão.
  void iniciarUpdater((e) => {
    if (e.baixado) {
      store.registrarLinhaBruta(
        `[app] Atualização ${e.versao} pronta para instalar. Ela é aplicada ao sair do app.`,
        'stderr',
      )
    }
  })

  // Deep link que ABRIU o app chega no argv do proprio processo.
  const urlInicial = urlDosArgumentos(process.argv)
  if (urlInicial) {
    const pedido = interpretar(urlInicial)
    if (pedido) deepLinkPendente = pedido
  }

  const cfg = lerConfiguracao()
  if (cfg.configurado) {
    supervisor.start()
  } else {
    // Sem enrollment nao ha o que executar. Dar spawn assim mesmo faria o
    // executor sair reportando `failed: config` — correto, mas inutil. A
    // mensagem fica pronta para quem abrir o painel; a janela principal, porém,
    // é a web — é lá, em Executores, que o usuário gera o OTP do vínculo.
    store.aplicarEstadoSupervisor(
      'stopped',
      cfg.falta === 'enrollment'
        ? 'Certificado ausente — refaça o enrollment.'
        : 'Este computador ainda não foi vinculado a um executor.',
    )
  }

  // Que janela abrir no boot:
  //  - deep link pendente → PAINEL, onde mora o formulário de enrollment;
  //  - senão → a janela WEB, a cara do app (e, sem vínculo ainda, o lugar onde
  //    o usuário gera o OTP em Executores).
  //
  // Só o autostart oculto de uma instalação JÁ vinculada sobe sem janela: um
  // app não configurado que sobe no logon e não aparece deixaria a pessoa sem
  // pista do que fazer, então esse caso ainda abre a web.
  if (deepLinkPendente) abrirJanela()
  else if (!(cfg.configurado && iniciadoOculto())) abrirJanelaWeb()
})

// Sem isto o app encerraria ao fechar a ultima janela, matando o executor no
// meio de um job. Ele vive no tray; a saida e explicita.
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
    // Shutdown ORDENADO, nao kill: drena os jobs em andamento e confirma os
    // resultados. Sem isso, sair do app marcaria runs como orfaos no servidor.
    await supervisor?.stop()
  } catch { /* sair nao pode falhar */ }
  // Entrega o que estiver preso na janela de coalescencia. Sem isto, o
  // `state: failed` ou a ultima linha de log do encerramento ficariam num timer
  // de 80ms que nunca dispara, e a janela mostraria o penultimo estado.
  store.descarregar()
  pararUpdater()
  destruirTray()
  permitirEncerramento()

  // Se ha update baixado, o encerramento e a janela de oportunidade: o executor
  // ja parou de forma ordenada acima, entao substituir a arvore de resources/
  // agora nao interrompe trabalho nenhum.
  if (instalarAgora()) return
  app.quit()
}
