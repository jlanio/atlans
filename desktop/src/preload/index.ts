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
import { CHANNELS } from '../shared/ipc.js'
import type { AtlasApi } from '../shared/ipc.js'
import type { CommandName } from '../shared/events.js'
import type { AppState } from '../main/state/store.js'

function assinar<T>(canal: string, fn: (dado: T) => void): () => void {
  const listener = (_e: unknown, dado: T) => fn(dado)
  ipcRenderer.on(canal, listener)
  // Returning the unsubscribe is not a courtesy: without it, each React
  // component remount accumulates a listener, and Electron warns of a memory
  // leak after the eleventh.
  return () => ipcRenderer.removeListener(canal, listener)
}

const api: AtlasApi = {
  estado: () => ipcRenderer.invoke(CHANNELS.estado),
  info: () => ipcRenderer.invoke(CHANNELS.info),
  configuracao: () => ipcRenderer.invoke(CHANNELS.configuracao),
  enrolar: (pedido) => ipcRenderer.invoke(CHANNELS.enrolar, pedido),
  refazerEnrollment: () => ipcRenderer.invoke(CHANNELS.refazerEnrollment),
  iniciar: () => ipcRenderer.invoke(CHANNELS.iniciar),
  parar: () => ipcRenderer.invoke(CHANNELS.parar),
  reiniciar: () => ipcRenderer.invoke(CHANNELS.reiniciar),
  forcar: () => ipcRenderer.invoke(CHANNELS.forcar),
  comando: (cmd: CommandName) => ipcRenderer.invoke(CHANNELS.comando, cmd),
  escolherPasta: (atual?: string) => ipcRenderer.invoke(CHANNELS.escolherPasta, atual),
  abrirCaminho: (caminho: string) => ipcRenderer.invoke(CHANNELS.abrirCaminho, caminho),
  autostart: (ativar?: boolean) => ipcRenderer.invoke(CHANNELS.autostart, ativar),
  janela: (acao) => ipcRenderer.invoke(CHANNELS.janela, acao),
  geosync: () => ipcRenderer.invoke(CHANNELS.geosync),
  salvarGeosync: (cfg) => ipcRenderer.invoke(CHANNELS.salvarGeosync, cfg),
  workspaces: (atualizar?: boolean) => ipcRenderer.invoke(CHANNELS.workspaces, atualizar),
  deepLinkPendente: () => ipcRenderer.invoke(CHANNELS.deepLinkPendente),
  execucao: () => ipcRenderer.invoke(CHANNELS.execucao),
  salvarExecucao: (cfg) => ipcRenderer.invoke(CHANNELS.salvarExecucao, cfg),
  exportarLog: (texto) => ipcRenderer.invoke(CHANNELS.exportarLog, texto),
  abrirJanelaLog: () => ipcRenderer.invoke(CHANNELS.abrirJanelaLog),
  log: () => ipcRenderer.invoke(CHANNELS.log),

  aoAtualizarEstado: (fn: (e: AppState) => void) => assinar(CHANNELS.aoAtualizarEstado, fn),
  aoReceberLog: (fn) => assinar(CHANNELS.aoReceberLog, fn),
  aoReceberDeepLink: (fn) => assinar(CHANNELS.aoReceberDeepLink, fn),
}

contextBridge.exposeInMainWorld('atlas', api)
