// desktop/src/preload/index.ts
//
// The only bridge between the renderer and main.
//
// The window runs with `contextIsolation: true`, `sandbox: true` and
// `nodeIntegration: false`. The renderer has NO access to `require`, to the
// filesystem or to the raw `ipcRenderer` — only to the object built here. This
// matters even with 100% local content: the log panel displays text coming
// from workflow nodes, which run arbitrary user code.
//
// No function here accepts a channel name as a parameter: if it did, an XSS
// flaw in the renderer could invoke any handler in main.
import { contextBridge, ipcRenderer } from 'electron'
import { CANAIS } from '../shared/ipc.js'
import type { AtlasApi } from '../shared/ipc.js'
import type { CommandName } from '../shared/events.js'
import type { EstadoApp } from '../main/state/store.js'

function assinar<T>(canal: string, fn: (dado: T) => void): () => void {
  const ouvinte = (_e: unknown, dado: T) => fn(dado)
  ipcRenderer.on(canal, ouvinte)
  // Returning the unsubscribe is not a courtesy: without it, each React
  // component remount accumulates a listener, and Electron warns of a memory
  // leak after the eleventh.
  return () => ipcRenderer.removeListener(canal, ouvinte)
}

const api: AtlasApi = {
  estado: () => ipcRenderer.invoke(CANAIS.estado),
  info: () => ipcRenderer.invoke(CANAIS.info),
  configuracao: () => ipcRenderer.invoke(CANAIS.configuracao),
  enrolar: (pedido) => ipcRenderer.invoke(CANAIS.enrolar, pedido),
  refazerEnrollment: () => ipcRenderer.invoke(CANAIS.refazerEnrollment),
  iniciar: () => ipcRenderer.invoke(CANAIS.iniciar),
  parar: () => ipcRenderer.invoke(CANAIS.parar),
  reiniciar: () => ipcRenderer.invoke(CANAIS.reiniciar),
  forcar: () => ipcRenderer.invoke(CANAIS.forcar),
  comando: (cmd: CommandName) => ipcRenderer.invoke(CANAIS.comando, cmd),
  escolherPasta: (atual?: string) => ipcRenderer.invoke(CANAIS.escolherPasta, atual),
  abrirCaminho: (caminho: string) => ipcRenderer.invoke(CANAIS.abrirCaminho, caminho),
  autostart: (ativar?: boolean) => ipcRenderer.invoke(CANAIS.autostart, ativar),
  janela: (acao) => ipcRenderer.invoke(CANAIS.janela, acao),
  geosync: () => ipcRenderer.invoke(CANAIS.geosync),
  salvarGeosync: (cfg) => ipcRenderer.invoke(CANAIS.salvarGeosync, cfg),
  workspaces: (atualizar?: boolean) => ipcRenderer.invoke(CANAIS.workspaces, atualizar),
  deepLinkPendente: () => ipcRenderer.invoke(CANAIS.deepLinkPendente),
  execucao: () => ipcRenderer.invoke(CANAIS.execucao),
  salvarExecucao: (cfg) => ipcRenderer.invoke(CANAIS.salvarExecucao, cfg),
  exportarLog: (texto) => ipcRenderer.invoke(CANAIS.exportarLog, texto),
  abrirJanelaLog: () => ipcRenderer.invoke(CANAIS.abrirJanelaLog),
  log: () => ipcRenderer.invoke(CANAIS.log),

  aoAtualizarEstado: (fn: (e: EstadoApp) => void) => assinar(CANAIS.aoAtualizarEstado, fn),
  aoReceberLog: (fn) => assinar(CANAIS.aoReceberLog, fn),
  aoReceberDeepLink: (fn) => assinar(CANAIS.aoReceberDeepLink, fn),
}

contextBridge.exposeInMainWorld('atlas', api)
