// desktop/src/preload/web.ts
//
// Preload da janela que exibe a UI web.
//
// Ao contrário do preload do painel (preload/index.ts), este expõe uma ponte
// MÍNIMA e SÓ LEITURA. A UI web é conteúdo REMOTO: dar a ela o IPC do main
// — iniciar/parar executor, diálogos de arquivo, abrir caminhos no disco —
// significaria que qualquer XSS na UI dirigiria o executor local com as
// permissões do usuário. Por isso `atlansDesktop` não tem NENHUM comando: só
// `obterStatus`/`aoMudarStatus`, que leem o status redigido de
// shared/executor-status.ts (main → web). Nenhum método aceita nome de canal,
// e o `window.atlas` do painel jamais é exposto aqui.
//
// ## Arrasto da janela
//
// A janela é `titleBarStyle: 'hidden'`: o Windows pinta os botões (min/max/
// fechar) à direita, mas o resto do topo não move a janela sozinho. Em vez de
// injetar uma faixa de arrasto aqui — fina demais para agarrar, e sob a borda
// de resize —, o preload apenas MARCA o documento com `data-atlans-desktop`. A
// própria UI web transforma os seus headers (o da sidebar e o AppHeader) em
// região de arrasto SÓ quando vê esse atributo, marcando os próprios controles
// como `no-drag` — ela sabe onde eles ficam, então nada de clique engolido. Ver
// as regras `[data-atlans-desktop] .app-region-*` em web/app/globals.css.

import { contextBridge, ipcRenderer } from 'electron'
import { CANAIS_WEB, type StatusExecutorLocal } from '../shared/executor-status.js'

/** Marca o <html> para o CSS ligar o arrasto dos headers só dentro do desktop. */
function marcarDesktop(): void {
  document.documentElement?.setAttribute('data-atlans-desktop', '1')
}
// `documentElement` já existe quando o preload roda; o listener cobre o caso
// raro de ainda não existir. `setAttribute` é idempotente, então repetir custa
// nada.
marcarDesktop()
document.addEventListener('DOMContentLoaded', marcarDesktop, { once: true })

// ── Ponte read-only ────────────────────────────────────────────────────────
//
// `window.atlansDesktop` — só leitura, sem nome de canal como parâmetro. A UI
// faz feature-detect: no navegador comum este objeto não existe.
contextBridge.exposeInMainWorld('atlansDesktop', {
  versao: 1,
  obterStatus: (): Promise<StatusExecutorLocal> => ipcRenderer.invoke(CANAIS_WEB.status),
  aoMudarStatus: (fn: (s: StatusExecutorLocal) => void): (() => void) => {
    const ouvinte = (_e: unknown, s: StatusExecutorLocal): void => fn(s)
    ipcRenderer.on(CANAIS_WEB.statusMudou, ouvinte)
    // Devolve o cancelamento: sem ele, cada remontagem no React acumularia um
    // ouvinte (o mesmo motivo do `assinar` em preload/index.ts).
    return () => ipcRenderer.removeListener(CANAIS_WEB.statusMudou, ouvinte)
  },
})
