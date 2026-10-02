// desktop/src/main/ui/janela-web.ts
//
// A janela principal do app: exibe a interface web da instalação, dando ao
// executor — que já roda em segundo plano — a cara de um software próprio.
//
// ## Isolamento
//
// Esta janela carrega conteúdo REMOTO, e por isso é deliberadamente separada da
// janela do painel (windows.ts):
//
//   - preload PRÓPRIO e mínimo (web-preload.cjs): não expõe `window.atlas` nem
//     o `ipcRenderer`, apenas a ponte READ-ONLY `window.atlansDesktop` (status
//     público do executor) — ver o cabeçalho de preload/web.ts;
//   - `partition: 'persist:atlans'`, sessão isolada e persistente: o login (o
//     cookie de sessão do NextAuth) sobrevive a reinícios, como num app nativo,
//     e não se mistura com nada local;
//   - `sandbox: true`, `contextIsolation: true`, `nodeIntegration: false`.
//
// Qualquer XSS na UI web fica contido num navegador sem privilégios — não
// alcança o executor, o filesystem nem o IPC.
//
// ## Navegação
//
// A UI web autentica por credencial same-origin (sem OAuth de terceiros),
// então a regra é estrita: a UI e a sua API navegam dentro; todo o resto vai
// para o navegador do sistema, onde o usuário vê o endereço.
import { BrowserWindow, shell } from 'electron'
import { ICONE_APP, arquivoDoApp } from '../paths.js'
import { UI_URL, ehExternoSeguro, ehOrigemInterna, hostsInternos } from '../../shared/ui.js'
import { ehDeepLink } from '../deeplink.js'
import { estaEncerrando, trazerParaFrente } from './windows.js'

let janela: BrowserWindow | null = null

export function janelaWebPrincipal(): BrowserWindow | null {
  return janela && !janela.isDestroyed() ? janela : null
}

// Quem processa um `atlans://` clicado DENTRO da janela web. Injetado pelo main
// (index.ts) porque o despacho do deep link — validar, preencher o formulário,
// trazer o painel à frente — mora lá. Sem isto, o clique no "Abrir no app" da
// UI web embutida não teria para onde ir e morreria no `will-navigate`.
let encaminharDeepLink: ((url: string) => void) | null = null

/**
 * Registra o tratador do deep link clicado na janela web. Chamado uma vez no
 * boot (index.ts) com a MESMA função que trata o deep link vindo de fora, para
 * que "Abrir no app" se comporte igual dentro e fora do app.
 */
export function definirTratadorDeepLink(fn: (url: string) => void): void {
  encaminharDeepLink = fn
}

/**
 * URL efetiva da UI. Fixa em {@link UI_URL}; `ATLANS_UI_URL` só a redireciona
 * para um staging/local em desenvolvimento. Lido AQUI, no main — nunca no
 * módulo shared, que o renderer em sandbox também importa.
 */
function urlDaUI(): string {
  const bruta = process.env.ATLANS_UI_URL?.trim()
  if (!bruta) return UI_URL
  try {
    const u = new URL(bruta)
    if (u.protocol === 'https:' || u.protocol === 'http:') return u.toString()
  } catch {
    /* entrada inválida cai no default */
  }
  return UI_URL
}

/** HTML local mostrado quando a UI não carrega (rede fora, servidor fora). */
function paginaOffline(url: string): string {
  // Página INLINE, sem depender de arquivo empacotado: funciona igual em dev
  // (sem `vite build`) e no app empacotado. O "Tentar de novo" é um link para a
  // própria UI — o `will-navigate` reconhece a origem e deixa passar.
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
  // Staging/local por `http:` afrouxa o esquema; produção é HTTPS e ponto.
  const protocolos = alvo.protocol === 'http:' ? ['https:', 'http:'] : ['https:']
  const interno = (u: string): boolean => ehOrigemInterna(u, { hosts, protocolos })

  janela = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 900,
    minHeight: 600,
    icon: ICONE_APP,
    // Evita o flash entre a janela aparecer e a UI pintar — mesmo fundo das
    // outras janelas (ver windows.ts).
    backgroundColor: '#1d1a17',
    show: false,
    autoHideMenuBar: true,
    // Os botões da janela são pintados pelo Windows à direita, sobre o
    // conteúdo; a faixa de arrasto vem do web-preload. Ver preload/web.ts.
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

  // Conteúdo REMOTO (a UI web) roda nesta sessão. O Electron APROVA pedidos de
  // permissão por padrão — sem handler, um XSS na página remota poderia obter
  // câmera, microfone, geolocalização ou notificações do SO sem prompt, furando
  // a contenção que o resto do isolamento (sandbox, sem nodeIntegration) garante.
  // Negamos tudo por padrão; a única exceção é a ESCRITA na área de transferência,
  // que os botões "Copiar" da UI usam (leitura de clipboard e o resto ficam fora).
  const PERMISSOES_WEB = new Set(['clipboard-sanitized-write'])
  const sessaoWeb = janela.webContents.session
  sessaoWeb.setPermissionRequestHandler((_wc, permissao, cb) => cb(PERMISSOES_WEB.has(permissao)))
  sessaoWeb.setPermissionCheckHandler((_wc, permissao) => PERMISSOES_WEB.has(permissao))

  janela.once('ready-to-show', () => janela?.show())

  // Fechar ESCONDE, não encerra: o app vive na bandeja e o executor segue
  // rodando — o mesmo contrato da janela do painel. Só a saída explícita fecha.
  janela.on('close', (evento) => {
    if (!estaEncerrando()) {
      evento.preventDefault()
      janela?.hide()
    }
  })
  janela.on('closed', () => { janela = null })

  // Destino que NÃO é origem interna. Três saídas:
  //   - `atlans://` → deep link de enrollment. O "Abrir no app" da UI web é
  //     um `<a href="atlans://…">`; num navegador o SO o roteia ao app, mas
  //     clicado AQUI DENTRO é só navegação e, sem este desvio, morreria abaixo
  //     (não é interno nem esquema externo seguro). Encaminha ao MESMO tratador
  //     do deep link externo — abre o painel com o formulário preenchido.
  //   - http(s)/mailto → navegador do sistema, onde o usuário vê o destino.
  //   - resto → descartado em silêncio.
  //
  // `shell.openExternal` entrega o destino ao SO, então o esquema precisa passar
  // por allowlist (ehExternoSeguro): um XSS ou redirect na página remota poderia
  // disparar `file:`, `smb:` (UNC → vazamento de hash NTLM no Windows) — e o
  // próprio `atlans://` NÃO vai por aqui, é desviado antes. `interpretar` (no
  // main) revalida o link e nunca enrola sozinho: exige confirmação humana.
  const tratarExterno = (destino: string): void => {
    if (ehDeepLink(destino)) { encaminharDeepLink?.(destino); return }
    if (ehExternoSeguro(destino)) void shell.openExternal(destino)
  }

  // `target=_blank`/`window.open`: origem interna reaproveita esta janela;
  // externa (esquema seguro) vai para o navegador. Nunca abre uma BrowserWindow
  // sem barra de endereço para conteúdo externo — o usuário precisa ver o destino.
  janela.webContents.setWindowOpenHandler(({ url: destino }) => {
    if (interno(destino)) void janela?.loadURL(destino)
    else tratarExterno(destino)
    return { action: 'deny' }
  })

  // Navegação do frame de topo: interna segue; externa vai para o navegador.
  // `will-redirect` recebe o MESMO tratamento — um redirect 30x do servidor não
  // dispara `will-navigate`, e sem isto uma origem interna redirecionada para
  // fora terminaria RENDERIZADA nesta janela sem barra de endereço, com o
  // preload anexado. Os dois eventos têm a mesma assinatura (evento, url).
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

  // Sem barra de endereço, o DevTools por atalho é a única forma de investigar
  // a UI embutida na máquina do usuário — igual às outras janelas.
  janela.webContents.on('before-input-event', (_evento, input) => {
    if (input.type !== 'keyDown') return
    const f12 = input.key === 'F12'
    const ctrlShiftI = input.control && input.shift && input.key.toLowerCase() === 'i'
    if (f12 || ctrlShiftI) janela?.webContents.toggleDevTools()
  })

  // Rede/servidor fora: o frame principal falha e a janela ficaria branca.
  // Troca pela página local com "Tentar de novo".
  janela.webContents.on('did-fail-load', (_e, codigo, _desc, urlQueFalhou, ehFramePrincipal) => {
    // Só o frame de topo, e só carregando a UI remota. `-3` = ABORTED, uma
    // navegação substituída por outra — trocar aí piscaria à toa; e a própria
    // página offline (data:) nunca casa com `^https?:`, então não há laço.
    if (!ehFramePrincipal || codigo === -3) return
    if (!/^https?:/i.test(urlQueFalhou)) return
    const html = paginaOffline(url)
    void janela?.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`)
  })

  void janela.loadURL(url)
  return janela
}
