// desktop/src/main/ui/windows.ts
import { BrowserWindow, shell, type WebContents } from 'electron'
import { ICONE_APP, IS_DEV, arquivoDoApp } from '../paths.js'
import { ehExternoSeguro } from '../../shared/ui.js'

let janela: BrowserWindow | null = null
let janelaLog: BrowserWindow | null = null

/** URL do dev server do Vite, quando `npm run dev` a definiu. */
const DEV_SERVER = process.env.VITE_DEV_SERVER_URL

/**
 * Hash que diz ao renderer qual tela montar.
 *
 * Hash e não query: com `loadFile` o Electron entrega a página por `file://`, e
 * o `search` de uma URL `file://` é aceito mas some do `location` em alguns
 * caminhos de navegação. O fragmento sobrevive aos dois esquemas.
 */
export const HASH_LOG = '#log'

export function janelaPrincipal(): BrowserWindow | null {
  return janela && !janela.isDestroyed() ? janela : null
}

/** Subconjunto de `BrowserWindow` usado por `trazerParaFrente`. */
export interface JanelaVisivel {
  isMinimized(): boolean
  isVisible(): boolean
  restore(): void
  show(): void
  focus(): void
}

/**
 * Traz uma janela existente para a frente, venha ela de onde vier.
 *
 * Os três estados são independentes e cada um exige a sua chamada:
 *
 *   minimizada → `restore()`
 *   ESCONDIDA  → `show()`
 *   ao fundo   → `focus()`
 *
 * O `show()` faltava, e era o caso MAIS comum: o botão vermelho da barra de
 * título esconde a janela em vez de encerrar o app (ele vive na bandeja).
 * Depois disso, "Abrir painel" no menu da bandeja chamava `focus()` numa janela
 * escondida — e `focus()` não torna nada visível. O menu parecia morto.
 */
export function trazerParaFrente(win: JanelaVisivel): void {
  if (win.isMinimized()) win.restore()
  if (!win.isVisible()) win.show()
  win.focus()
}

/** Subconjunto de `WebContents` usado por `protegerNavegacao`. */
export type ConteudoNavegavel = Pick<WebContents, 'setWindowOpenHandler' | 'on' | 'getURL'>

/**
 * A mesma página que a janela já mostra (esquema, host e caminho), com
 * qualquer hash ou query: é o `location.reload()` — o Vite o chama a cada
 * recarga completa em dev, e ele dispara `will-navigate`.
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
 * Link externo abre no navegador do sistema, nunca numa BrowserWindow sem
 * barra de endereço — o usuário precisa ver para onde está indo. Mas só
 * http(s) e mailto (`ehExternoSeguro`, a mesma allowlist da janela web):
 * `shell.openExternal` entrega o destino ao SO, e um `file:` ou `smb:` (UNC →
 * vazamento do hash NTLM no Windows) vindo de uma URL num log ou de um XSS no
 * painel não pode sair daqui. Antes as janelas do painel repassavam qualquer
 * esquema.
 *
 * E o frame de topo não sai do painel. A página é uma SPA carregada uma vez
 * (`loadFile`/`loadURL` e troca de hash não disparam `will-navigate`); o que
 * dispara é recarregar a própria página — deixado passar — ou trocá-la por
 * outra, com o preload anexado — barrado e mandado ao navegador pela mesma
 * regra. `will-redirect` recebe o mesmo tratamento: um redirect 30x no meio de
 * uma recarga não pode terminar renderizando outra origem aqui.
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
    // Menor que os 1100x720 anteriores: com a navegação na lateral o conteúdo
    // deixou de precisar de uma faixa de abas e de um cabeçalho de estado, e
    // este é um app de segundo plano — ocupar meia tela para mostrar oito
    // números é desproporcional.
    //
    // A largura mínima acomoda a sidebar (192px) mais os quatro cartões de
    // métrica no breakpoint `md` (768px).
    width: 980,
    height: 680,
    minWidth: 820,
    minHeight: 520,
    // Barra de tarefas e Alt+Tab. Sem isto o dev roda com o ícone do Electron.
    icon: ICONE_APP,
    // Sem a moldura do Windows: a barra de título é desenhada pelo renderer,
    // com os controles à esquerda, no formato do macOS.
    //
    // `frame: false` em vez de `titleBarStyle: 'hidden'` + `titleBarOverlay`
    // porque o overlay do Windows desenha os botões nativos à DIREITA e não
    // permite movê-los — o resultado seria dois conjuntos de controles.
    // Com `frame: false` a janela perde o redimensionamento por borda, então
    // `resizable` continua ligado e o Electron mantém as bordas invisíveis de
    // arrasto.
    frame: false,
    resizable: true,
    // Cantos arredondados no Windows 11 (no-op nas versões anteriores).
    roundedCorners: true,
    // Evita o flash entre a janela aparecer e o React pintar. É o `--background`
    // de index.css — oklch(0.188 0.008 55) — em hex; qualquer outro valor
    // aparece como um lampejo de cor errada. `show: false` + `ready-to-show`
    // faz o resto.
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

  // Fechar a janela NAO encerra o app: ele vive no tray e o executor segue
  // rodando. Sem isto, fechar a janela mataria o executor no meio de um job —
  // o oposto do que o usuario espera de um agente em background.
  janela.on('close', (evento) => {
    if (!encerrandoDeVerdade) {
      evento.preventDefault()
      janela?.hide()
    }
  })

  janela.on('closed', () => { janela = null })

  protegerNavegacao(janela.webContents)

  // F12 e Ctrl+Shift+I. Sem moldura nao ha menu do sistema, entao o atalho
  // precisa ser tratado aqui — e a unica forma de abrir o DevTools no app
  // empacotado quando algo precisa ser investigado na maquina do usuario.
  janela.webContents.on('before-input-event', (_evento, input) => {
    if (input.type !== 'keyDown') return
    const f12 = input.key === 'F12'
    const ctrlShiftI = input.control && input.shift && input.key.toLowerCase() === 'i'
    if (f12 || ctrlShiftI) janela?.webContents.toggleDevTools()
  })

  if (DEV_SERVER) {
    void janela.loadURL(DEV_SERVER)
    // NAO abre sozinho. O DevTools do Chromium despeja no console do terminal
    // um punhado de erros internos dele mesmo — "Unknown VE context",
    // "Autofill.enable wasn't found" — que nao tem relacao nenhuma com o app e
    // fazem qualquer `npm run dev` parecer quebrado.
    //
    // Quem quer o DevTools aberto de saida pede: ATLANS_DEVTOOLS=1 npm run dev.
    if (process.env.ATLANS_DEVTOOLS === '1') {
      janela.webContents.openDevTools({ mode: 'detach' })
    }
  } else {
    void janela.loadFile(arquivoDoApp('dist', 'renderer', 'index.html'))
  }
  return janela
}

/**
 * Janela dedicada ao log.
 *
 * Existe para o log poder ficar ao lado de outra coisa — o painel do app, o
 * Studio no navegador, um editor. Numa janela só, ler o log custa perder de
 * vista todo o resto, e é justamente enquanto se investiga um problema que se
 * quer os dois.
 *
 * Diferenças em relação à principal, ambas deliberadas:
 *
 *  - fechar FECHA. Ela não guarda estado nenhum (o log vive no store do main),
 *    então escondê-la como a principal só criaria uma janela fantasma.
 *  - proporção larga e baixa por padrão: linha de log é comprida, e o formato
 *    quase quadrado da janela principal desperdiçaria altura em quebra de
 *    linha.
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

/** Libera o `close` para fechar de fato. Chamado no caminho de saida do app. */
export function permitirEncerramento(): void {
  encerrandoDeVerdade = true
}

/**
 * Diz se o app já está no caminho de saída.
 *
 * A janela web (janela-web.ts) também esconde no `close` em vez de encerrar, e
 * precisa consultar esta mesma decisão — sem isso, cada janela guardaria a sua
 * cópia do estado e uma delas fecharia de verdade no meio da drenagem.
 */
export function estaEncerrando(): boolean {
  return encerrandoDeVerdade
}

