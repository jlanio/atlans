// web/lib/entrada.ts
//
// The paths of the ENTRY (login and sign-up). Since the Home opens without a
// session and login became a modal over the globe, "go to login" means "go to
// the Home with the modal open": `/?entrar=1` or `/?cadastro=1`, plus a
// `callbackUrl` only when there is somewhere to return to afterwards (the admin
// who requested /projects without a session). Pure and React-free, on purpose:
// the middleware (Edge) imports from here, and so do the /login and /register
// routes (server components).

/**
 * The modal's five panels. `recuperar` requests the link by e-mail and
 * `redefinir` stores the new password with the token that came in it;
 * `verificar` shows the "open the link in the e-mail" and, with the link's
 * token, activates the account — these were the /forgot-password,
 * /reset-password and /verify-email pages of the old full-page model.
 */
export type ModoDeEntrada = "entrar" | "cadastro" | "recuperar" | "redefinir" | "verificar"

/**
 * The panels that come from an E-MAIL LINK, not from the login gate. Two
 * exceptions apply, both for the same reason:
 *
 * 1. They open WITH or WITHOUT a session. Someone who forgot the password — or
 *    has not verified the e-mail yet — often has an old session open in the
 *    same browser, and that is where the link arrives. With the `anonimo` gate
 *    applying to all of them, that link opened the Home and did nothing: the
 *    quietest bug possible.
 * 2. A session that shows up midway (login in another tab) does not close them.
 *    The link's token is SINGLE-USE: closing the panel out from under someone
 *    using it would burn it without anything having been done.
 */
export function ehPainelDeEmail(modo: ModoDeEntrada | null | undefined): boolean {
  return modo === "recuperar" || modo === "redefinir" || modo === "verificar"
}

/**
 * Only an INTERNAL path works as a return target: it starts with `/` and not with
 * `//` or `/\` (which the browser would read as another host — open redirect).
 * Everything else becomes `undefined`. It is the rule the login page applied to
 * `callbackUrl`.
 */
export function caminhoInterno(valor: unknown): string | undefined {
  if (typeof valor !== "string") return undefined
  // Rejects control characters (TAB/CR/LF and other C0/DEL). The browser
  // REMOVES them when navigating, so `/\t/evil.com` would become `//evil.com` —
  // an external host (open redirect). Must come before the prefix test.
  if (/[\u0000-\u001f\u007f]/.test(valor)) return undefined
  if (!/^\/(?![/\\])/.test(valor)) return undefined
  return valor
}

/**
 * The Home with the entry modal open. `callbackUrl` is only included when it is
 * internal and is not the Home itself — returning to `/` is what already
 * happens without it.
 */
export function destinoDaEntrada(modo: ModoDeEntrada, callbackUrl?: string): string {
  const params = new URLSearchParams()
  params.set(modo, "1")
  const volta = caminhoInterno(callbackUrl)
  if (volta && volta !== "/") params.set("callbackUrl", volta)
  return `/?${params.toString()}`
}

/**
 * The Home with the new-password panel open, carrying the token from the
 * e-mail. Without a token there is nothing to reset: it falls back to the panel
 * that requests a new link — which is what the "Link inválido" (invalid link)
 * screen offered, in one step fewer.
 */
export function destinoDaRedefinicao(token?: string): string {
  if (!token) return destinoDaEntrada("recuperar")
  return `/?${new URLSearchParams({ redefinir: "1", token }).toString()}`
}

/**
 * The Home with the verification panel open. WITH a token, the panel spends it
 * on the GET and the account is activated; WITHOUT a token (direct access, or
 * the "Reenviar e-mail de verificação" (resend verification e-mail) from an old
 * cache) it is the "open the link in the e-mail" screen, with the resend —
 * which is what the page did in both cases.
 */
export function destinoDaVerificacao(token?: string): string {
  if (!token) return destinoDaEntrada("verificar")
  return `/?${new URLSearchParams({ verificar: "1", token }).toString()}`
}
