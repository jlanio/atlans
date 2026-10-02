// desktop/src/shared/ui.ts
//
// A interface web do Atlans — a origem que o app desktop passa a exibir como
// janela principal.
//
// Mesma disciplina de servidor.ts: a origem é FIXA. A janela web navega DENTRO
// de si mesma apenas nesta origem (e na API do produto); qualquer outra vai
// para o navegador do sistema. Deixar a origem editável em runtime daria a uma
// página aberta ali a chance de se passar pela UI do Atlans com o preload —
// mínimo, mas ainda assim próprio — que injetamos nela.
//
// O override por ambiente (ATLANS_UI_URL) é lido no processo MAIN, nunca aqui:
// este módulo é importado também pelo renderer em sandbox, onde `process` não
// existe — tocar em `process.env` no topo pintaria a janela e não montaria
// nada (ver a guarda em vite.config.ts).

/**
 * A UI da instalação. Fixa, gravada pelo build (ATLANS_DESKTOP_UI_URL, ver
 * scripts/enderecos.mjs); o override de staging/local mora no main.
 */
declare const __ATLANS_UI_URL__: string
export const UI_URL: string = __ATLANS_UI_URL__

/** Host de {@link UI_URL}. */
export const UI_HOST = new URL(UI_URL).hostname

/**
 * Hosts que navegam DENTRO da janela web: a UI e a sua API — o mesmo produto.
 *
 * A API entra porque um download ou callback pode levar o frame de topo até
 * ela; chamadas comuns são `fetch` e nem disparam navegação. Origens de
 * terceiros (documentação, links "abrir no site") são externas de propósito:
 * abrir no navegador deixa o usuário ver para onde vai.
 *
 * Login não é exceção: a UI web autentica por credencial (NextAuth,
 * provider Credentials) com cookie de sessão same-origin — não há redirect de
 * OAuth de terceiros a acomodar, então a regra pode ser estrita sem tirar o
 * usuário do app durante o acesso.
 */
export function hostsInternos(uiHost: string = UI_HOST): string[] {
  return [uiHost, `api.${uiHost}`]
}

/**
 * A URL é da própria UI (navega dentro) ou externa (vai para o navegador)?
 *
 * Função pura — a decisão fica testável sem Electron. Recusa por padrão tudo
 * que não seja HTTPS num dos {@link hostsInternos}; `protocolos` só afrouxa
 * para `http:` quando o main aponta a janela para um staging local.
 */
export function ehOrigemInterna(
  bruta: string,
  opts: { hosts?: readonly string[]; protocolos?: readonly string[] } = {},
): boolean {
  const hosts = opts.hosts ?? hostsInternos()
  const protocolos = opts.protocolos ?? ['https:']
  let url: URL
  try {
    url = new URL(bruta)
  } catch {
    return false
  }
  if (!protocolos.includes(url.protocol)) return false
  return hosts.includes(url.hostname)
}

/** Esquemas que podem ir ao navegador do sistema via `shell.openExternal`. */
const ESQUEMAS_EXTERNOS = ['https:', 'http:', 'mailto:']

/**
 * Um destino EXTERNO é seguro para entregar ao `shell.openExternal`?
 *
 * `openExternal` repassa o destino ao handler do SO, então o esquema precisa
 * ser barrado: um XSS ou um redirect na página remota poderia disparar `file:`,
 * `smb:` (UNC → vazamento de hash NTLM no Windows) ou o próprio `atlans://`
 * (deep link de enrollment). Só passam http(s) e mailto — o que um link normal
 * precisa; qualquer outro esquema é recusado.
 */
export function ehExternoSeguro(bruta: string): boolean {
  let url: URL
  try {
    url = new URL(bruta)
  } catch {
    return false
  }
  return ESQUEMAS_EXTERNOS.includes(url.protocol)
}
