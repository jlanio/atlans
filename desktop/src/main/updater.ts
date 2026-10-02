// desktop/src/main/updater.ts
//
// Auto-update via electron-updater, consumindo os mesmos GitHub Releases que o
// workflow do executor Docker ja usa.
//
// A regra que dita todo o desenho: **nunca atualizar no meio de uma execucao**.
// O update substitui o `python.exe` e a arvore inteira de `resources/`; fazer
// isso com um workflow rodando mataria o job sem confirmar o resultado ao
// servidor, que o marcaria como orfao. Por isso o `quitAndInstall` so acontece
// depois de um shutdown ORDENADO do executor, e so quando nao ha job em curso.
//
// O download diferencial vem do `.blockmap` que o alvo NSIS gera: se
// `resources/python` nao mudou entre releases, seus blocos sao identicos e nao
// sao baixados. E o que torna viavel um app de ~400 MB se atualizar sem
// rebaixar tudo — e o motivo de o lock do executor (com hash) e a release do
// python-build-standalone serem pinados.
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
 * @param aoMudar  notificado quando um update termina de baixar.
 */
export async function iniciarUpdater(aoMudar: (e: EstadoUpdate) => void): Promise<void> {
  // Em dev nao ha o que atualizar, e o electron-updater loga um erro chamativo
  // ("dev-app-update.yml not found") que so confunde.
  if (!app.isPackaged) return

  // Import dinamico: o pacote inteiro so e carregado no app empacotado.
  const { autoUpdater } = await import('electron-updater')
  updater = autoUpdater

  // O download comeca sozinho; a INSTALACAO e que espera. Baixar cedo faz o
  // update estar pronto quando a janela de oportunidade aparecer.
  autoUpdater.autoDownload = true
  autoUpdater.autoInstallOnAppQuit = false   // ver `instalarAgora`

  autoUpdater.on('update-downloaded', (info) => {
    estado.baixado = true
    estado.versao = info.version
    aoMudar(estadoDoUpdate())
  })

  // Falha de update NAO pode derrubar nem alarmar: o app funciona igual sem
  // atualizar. O listener existe mesmo sem ninguem ler o erro: sem nenhum, o
  // EventEmitter LANCA o `error` — e o electron-updater o emite de dentro do
  // `quitAndInstall`, no caminho de saida do app.
  autoUpdater.on('error', () => { /* ver acima */ })

  const verificar = () => {
    void autoUpdater.checkForUpdates().catch(() => { /* o handler de erro cobre */ })
  }

  verificar()
  timer = setInterval(verificar, INTERVALO_MS)
}

/**
 * Instala e reinicia. Devolve `false` se ainda nao ha update baixado — a
 * decisao de "pode reiniciar agora?" e de quem chama, que precisa parar o
 * executor de forma ordenada ANTES.
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
