// desktop/src/preload/index.ts
//
// Unica ponte entre o renderer e o main.
//
// A janela roda com `contextIsolation: true`, `sandbox: true` e
// `nodeIntegration: false`. O renderer NAO tem acesso a `require`, ao
// filesystem nem ao `ipcRenderer` cru — so ao objeto montado aqui. Isso importa
// mesmo com conteudo 100% local: o painel de log exibe texto vindo de nos de
// workflow, que executam codigo arbitrario do usuario.
//
// Nenhuma funcao aqui aceita nome de canal como parametro: se aceitasse, uma
// falha de XSS no renderer poderia invocar qualquer handler do main.
import { contextBridge, ipcRenderer } from 'electron'
import { CANAIS } from '../shared/ipc.js'
import type { AtlasApi } from '../shared/ipc.js'
import type { CommandName } from '../shared/events.js'
import type { EstadoApp } from '../main/state/store.js'

function assinar<T>(canal: string, fn: (dado: T) => void): () => void {
  const ouvinte = (_e: unknown, dado: T) => fn(dado)
  ipcRenderer.on(canal, ouvinte)
  // Devolver o cancelamento nao e cortesia: sem ele, cada remontagem de
  // componente no React acumula um ouvinte, e o Electron avisa de memory leak
  // depois do decimo primeiro.
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
