// desktop/src/main/deeplink.ts
//
// Deep link `atlans://enroll?executor_id=…&otp=…&server=…`.
//
// Elimina o copiar-colar de dois valores entre o navegador e o app — hoje a
// maior fricção do vínculo.
//
// ## Segurança
//
// **Qualquer página web pode disparar um deep link.** Basta um `<a href>` ou um
// `location.href` para o app abrir com parâmetros escolhidos por quem escreveu
// a página. Por isso, duas defesas:
//
//   1. O app NUNCA enrola automaticamente. Ele preenche o formulário e espera
//      confirmação humana.
//   2. O servidor não é escolhido pelo link. Ele é a constante SERVIDOR, e um
//      `server=` apontando para outro host faz o link inteiro ser descartado.
//      Um enrollment contra servidor atacante entregaria a esta máquina jobs
//      assinados por ele — que o executor rodaria com as permissões do usuário.
//
// O OTP na URL não vai para o histórico do navegador (não é navegação), mas
// aparece na linha de comando do processo. Como é de uso único e dura 24 h,
// é aceitável — e o mesmo já vale para o `--otp` do CLI.
import { app } from 'electron'
import { SERVIDOR_HOST } from '../shared/servidor.js'

export const PROTOCOLO = 'atlans'

/**
 * O `servidor` NÃO está aqui: ele é fixo. O que a URL traz é apenas a
 * identidade a vincular.
 */
export interface PedidoDeepLink {
  executorId: string
  otp: string
}

/**
 * Interpreta uma URL `atlans://`. Devolve `null` para tudo que não seja um
 * pedido de enrollment válido e confiável.
 *
 * Função pura — a decisão de segurança fica testável sem Electron.
 */
export function interpretar(bruta: string): PedidoDeepLink | null {
  let url: URL
  try {
    url = new URL(bruta)
  } catch {
    return null
  }

  if (url.protocol !== `${PROTOCOLO}:`) return null
  // `atlans://enroll?…` coloca "enroll" no host, não no pathname.
  const acao = (url.host || url.pathname.replace(/^\/+/, '')).toLowerCase()
  if (acao !== 'enroll') return null

  const executorId = (url.searchParams.get('executor_id') || '').trim()
  const otp = (url.searchParams.get('otp') || '').trim()
  if (!executorId || !otp) return null

  // `server=` é opcional — o app usa o seu de qualquer forma. Quando vem,
  // precisa CONFERIR: um link apontando para outro host revela intenção de
  // desviar o vínculo, e o certo aí é recusar, não ignorar o parâmetro e
  // enrolar contra o servidor certo como se nada tivesse acontecido.
  const servidor = (url.searchParams.get('server') || '').trim()
  if (servidor) {
    let alvo: URL
    try {
      alvo = new URL(servidor)
    } catch {
      return null
    }
    // Só HTTPS/WSS: um `http://` aceito aqui indicaria um link forjado.
    if (alvo.protocol !== 'https:' && alvo.protocol !== 'wss:') return null
    if (alvo.hostname !== SERVIDOR_HOST) return null
  }

  return { executorId, otp }
}

/**
 * A URL usa o esquema do deep link (`atlans://`)?
 *
 * Só o esquema — a validação de conteúdo é do {@link interpretar}. Serve à
 * janela web (janela-web.ts), que precisa separar um `atlans://` clicado ali
 * dentro (deep link a encaminhar ao main) de um link externo comum (vai ao
 * navegador). Um `atlans://` malformado ainda retorna `true` aqui e é recusado
 * depois por `interpretar` — a mesma recusa silenciosa do fluxo externo.
 */
export function ehDeepLink(bruta: string): boolean {
  try {
    return new URL(bruta).protocol === `${PROTOCOLO}:`
  } catch {
    return false
  }
}

/**
 * Registra o app como handler do protocolo.
 *
 * Em dev o executável é o do Electron, e sem apontar o caminho do projeto o
 * Windows registraria "abrir com electron.exe" — que abriria o app padrão do
 * Electron, não este.
 */
export function registrarProtocolo(): void {
  if (process.defaultApp && process.argv.length >= 2) {
    app.setAsDefaultProtocolClient(PROTOCOLO, process.execPath, [process.argv[1]!])
  } else {
    app.setAsDefaultProtocolClient(PROTOCOLO)
  }
}

/**
 * Extrai a URL `atlans://` de uma lista de argumentos.
 *
 * No Windows o deep link chega em `argv` — na primeira execução, no argv do
 * processo; com o app já aberto, no evento `second-instance`. (O `open-url` do
 * Electron é só macOS.)
 */
export function urlDosArgumentos(argv: string[]): string | null {
  return argv.find((a) => a.startsWith(`${PROTOCOLO}://`)) ?? null
}
