// desktop/src/main/deeplink.ts
//
// Deep link `atlans://enroll?executor_id=…&otp=…&server=…`.
//
// Eliminates copy-pasting two values between the browser and the app — today
// the biggest friction in binding.
//
// ## Security
//
// **Any web page can trigger a deep link.** An `<a href>` or a `location.href`
// is enough for the app to open with parameters chosen by whoever wrote the
// page. Hence, two defenses:
//
//   1. The app NEVER enrolls automatically. It fills in the form and waits for
//      human confirmation.
//   2. The server is not chosen by the link. It is the SERVIDOR constant, and a
//      `server=` pointing to another host makes the whole link be discarded.
//      An enrollment against an attacker's server would deliver to this machine
//      jobs signed by it — which the executor would run with the user's
//      permissions.
//
// The OTP in the URL does not go into the browser history (it is not a
// navigation), but it does show up on the process command line. Since it is
// single-use and lasts 24 h, that is acceptable — and the same already holds for
// the CLI's `--otp`.
import { app } from 'electron'
import { SERVIDOR_HOST } from '../shared/servidor.js'

export const PROTOCOLO = 'atlans'

/**
 * The `servidor` is NOT here: it is fixed. What the URL brings is only the
 * identity to bind.
 */
export interface PedidoDeepLink {
  executorId: string
  otp: string
}

/**
 * Interprets an `atlans://` URL. Returns `null` for anything that is not a
 * valid and trustworthy enrollment request.
 *
 * Pure function — the security decision stays testable without Electron.
 */
export function interpretar(bruta: string): PedidoDeepLink | null {
  let url: URL
  try {
    url = new URL(bruta)
  } catch {
    return null
  }

  if (url.protocol !== `${PROTOCOLO}:`) return null
  // `atlans://enroll?…` puts "enroll" in the host, not in the pathname.
  const acao = (url.host || url.pathname.replace(/^\/+/, '')).toLowerCase()
  if (acao !== 'enroll') return null

  const executorId = (url.searchParams.get('executor_id') || '').trim()
  const otp = (url.searchParams.get('otp') || '').trim()
  if (!executorId || !otp) return null

  // `server=` is optional — the app uses its own either way. When present, it
  // must MATCH: a link pointing to another host reveals an intent to divert
  // the binding, and the right thing then is to refuse, not ignore the
  // parameter and enroll against the right server as if nothing had happened.
  const servidor = (url.searchParams.get('server') || '').trim()
  if (servidor) {
    let alvo: URL
    try {
      alvo = new URL(servidor)
    } catch {
      return null
    }
    // HTTPS/WSS only: an `http://` accepted here would indicate a forged link.
    if (alvo.protocol !== 'https:' && alvo.protocol !== 'wss:') return null
    if (alvo.hostname !== SERVIDOR_HOST) return null
  }

  return { executorId, otp }
}

/**
 * Does the URL use the deep link scheme (`atlans://`)?
 *
 * Only the scheme — content validation is {@link interpretar}'s job. It serves
 * the web window (janela-web.ts), which needs to tell an `atlans://` clicked
 * inside it (a deep link to forward to main) from an ordinary external link
 * (goes to the browser). A malformed `atlans://` still returns `true` here and
 * is refused later by `interpretar` — the same silent refusal as the external flow.
 */
export function ehDeepLink(bruta: string): boolean {
  try {
    return new URL(bruta).protocol === `${PROTOCOLO}:`
  } catch {
    return false
  }
}

/**
 * Registers the app as the protocol handler.
 *
 * In dev the executable is Electron's, and without pointing at the project
 * path Windows would register "open with electron.exe" — which would open
 * Electron's default app, not this one.
 */
export function registrarProtocolo(): void {
  if (process.defaultApp && process.argv.length >= 2) {
    app.setAsDefaultProtocolClient(PROTOCOLO, process.execPath, [process.argv[1]!])
  } else {
    app.setAsDefaultProtocolClient(PROTOCOLO)
  }
}

/**
 * Extracts the `atlans://` URL from a list of arguments.
 *
 * On Windows the deep link arrives in `argv` — on first launch, in the
 * process's argv; with the app already open, in the `second-instance` event.
 * (Electron's `open-url` is macOS only.)
 */
export function urlDosArgumentos(argv: string[]): string | null {
  return argv.find((a) => a.startsWith(`${PROTOCOLO}://`)) ?? null
}
