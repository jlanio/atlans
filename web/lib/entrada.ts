// web/lib/entrada.ts
//
// Os caminhos da ENTRADA (login e cadastro). Desde que a Home abre sem sessão
// e o login virou um modal sobre o globo, "ir para o login" é "ir para a Home
// com o modal aberto": `/?entrar=1` ou `/?cadastro=1`, mais um `callbackUrl`
// só quando há para onde voltar depois (o admin que pediu /projects sem
// sessão). Puro e sem React, de propósito: o middleware (Edge) importa daqui,
// e as rotas /login e /register (server components) também.

/**
 * Os cinco painéis do modal. `recuperar` pede o link por e-mail e `redefinir`
 * grava a senha nova com o token que veio nele; `verificar` mostra o "abra o
 * link do e-mail" e, com o token do link, ativa a conta — eram as páginas
 * /forgot-password, /reset-password e /verify-email, do modelo antigo de
 * página inteira.
 */
export type ModoDeEntrada = "entrar" | "cadastro" | "recuperar" | "redefinir" | "verificar"

/**
 * Os painéis que vêm de um LINK DE E-MAIL, e não do portão de login. Valem
 * duas exceções, as duas pelo mesmo motivo:
 *
 * 1. Eles abrem COM ou SEM sessão. Quem esqueceu a senha — ou ainda não
 *    verificou o e-mail — costuma ter uma sessão velha aberta no mesmo
 *    navegador, e é nele que o link chega. Com o portão de `anonimo` valendo
 *    para todos, esse link abria a Home e não fazia nada: o defeito mais
 *    silencioso possível.
 * 2. Uma sessão que chegue no meio (login noutra aba) não os fecha. O token do
 *    link é de USO ÚNICO: fechar o painel por baixo de quem está usando o
 *    queimaria sem ter feito nada.
 */
export function ehPainelDeEmail(modo: ModoDeEntrada | null | undefined): boolean {
  return modo === "recuperar" || modo === "redefinir" || modo === "verificar"
}

/**
 * Só um caminho INTERNO serve de volta: começa com `/` e não com `//` nem `/\`
 * (que o navegador leria como outro host — open redirect). O resto vira
 * `undefined`. É a regra que a página de login aplicava ao `callbackUrl`.
 */
export function caminhoInterno(valor: unknown): string | undefined {
  if (typeof valor !== "string") return undefined
  // Recusa caracteres de controle (TAB/CR/LF e demais C0/DEL). O navegador os
  // REMOVE ao navegar, então `/\t/evil.com` viraria `//evil.com` — um host
  // externo (open redirect). Precisa vir antes do teste de prefixo.
  if (/[\u0000-\u001f\u007f]/.test(valor)) return undefined
  if (!/^\/(?![/\\])/.test(valor)) return undefined
  return valor
}

/**
 * A Home com o modal de entrada aberto. O `callbackUrl` só entra quando é
 * interno e não é a própria Home — voltar a `/` é o que já acontece sem ele.
 */
export function destinoDaEntrada(modo: ModoDeEntrada, callbackUrl?: string): string {
  const params = new URLSearchParams()
  params.set(modo, "1")
  const volta = caminhoInterno(callbackUrl)
  if (volta && volta !== "/") params.set("callbackUrl", volta)
  return `/?${params.toString()}`
}

/**
 * A Home com o painel de nova senha aberto, levando o token do e-mail. Sem
 * token não há o que redefinir: cai no painel que pede um link novo — é o que
 * a tela "Link inválido" oferecia, em um passo a menos.
 */
export function destinoDaRedefinicao(token?: string): string {
  if (!token) return destinoDaEntrada("recuperar")
  return `/?${new URLSearchParams({ redefinir: "1", token }).toString()}`
}

/**
 * A Home com o painel de verificação aberto. COM token, o painel o gasta no GET
 * e a conta é ativada; SEM token (o acesso direto, ou o "Reenviar e-mail de
 * verificação" de um cache antigo) ele é a tela de "abra o link do e-mail",
 * com o reenvio — que é o que a página fazia nos dois casos.
 */
export function destinoDaVerificacao(token?: string): string {
  if (!token) return destinoDaEntrada("verificar")
  return `/?${new URLSearchParams({ verificar: "1", token }).toString()}`
}
