// desktop/src/shared/ui.ts
//
// The Atlans web interface — the origin the desktop app now displays as its
// main window.
//
// Same discipline as servidor.ts: the origin is FIXED. The web window navigates
// WITHIN itself only on this origin (and on the product's API); any other goes
// to the system browser. Leaving the origin editable at runtime would give a
// page opened there the chance to pass itself off as the Atlans UI with the
// preload — minimal, but still ours — that we inject into it.
//
// The environment override (ATLANS_UI_URL) is read in the MAIN process, never
// here: this module is also imported by the sandboxed renderer, where `process`
// does not exist — touching `process.env` at the top would paint the window and
// mount nothing (see the guard in vite.config.ts).

/**
 * The installation's UI. Fixed, written by the build (ATLANS_DESKTOP_UI_URL,
 * see scripts/enderecos.mjs); the staging/local override lives in main.
 */
declare const __ATLANS_UI_URL__: string
export const UI_URL: string = __ATLANS_UI_URL__

/** Host of {@link UI_URL}. */
export const UI_HOST = new URL(UI_URL).hostname

/**
 * Hosts that navigate INSIDE the web window: the UI and its API — the same
 * product.
 *
 * The API is included because a download or callback may take the top frame to
 * it; ordinary calls are `fetch` and do not even trigger navigation.
 * Third-party origins (documentation, "abrir no site" links) are external on
 * purpose: opening them in the browser lets the user see where they are going.
 *
 * Login is no exception: the web UI authenticates by credential (NextAuth,
 * Credentials provider) with a same-origin session cookie — there is no
 * third-party OAuth redirect to accommodate, so the rule can be strict without
 * taking the user out of the app during sign-in.
 */
export function hostsInternos(uiHost: string = UI_HOST): string[] {
  return [uiHost, `api.${uiHost}`]
}

/**
 * Is the URL the UI's own (navigates inside) or external (goes to the browser)?
 *
 * Pure function — the decision is testable without Electron. Rejects by default
 * anything that is not HTTPS on one of the {@link hostsInternos}; `protocolos`
 * only relaxes to `http:` when the main process points the window at a local
 * staging.
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

/** Schemes that may go to the system browser via `shell.openExternal`. */
const EXTERNAL_SCHEMES = ['https:', 'http:', 'mailto:']

/**
 * Is an EXTERNAL target safe to hand to `shell.openExternal`?
 *
 * `openExternal` hands the target to the OS handler, so the scheme must be
 * blocked: an XSS or a redirect in the remote page could fire `file:`, `smb:`
 * (UNC → NTLM hash leak on Windows) or `atlans://` itself (enrollment deep
 * link). Only http(s) and mailto get through — what a normal link needs; any
 * other scheme is rejected.
 */
export function ehExternoSeguro(bruta: string): boolean {
  let url: URL
  try {
    url = new URL(bruta)
  } catch {
    return false
  }
  return EXTERNAL_SCHEMES.includes(url.protocol)
}
