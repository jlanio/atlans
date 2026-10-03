// desktop/src/shared/servidor.ts
//
// The Atlans server is FIXED in this app.
//
// It is not a preference with a good default: it is the only origin this
// executable links to. Leaving the address editable gave anyone with access to
// the machine — or a web page firing a deep link — the chance to point the
// executor at another server, and an executor pointed at someone else's server
// runs, with the user's permissions, whatever workflows that server sends.
//
// That is why the value is written into the executable by the BUILD
// (ATLANS_DESKTOP_SERVIDOR, see scripts/enderecos.mjs), and does not come from
// `.env`, nor from a form field, nor from an IPC parameter coming from the
// renderer. `.env` still receives `EXECUTOR_SERVER_URL` because Python is what
// reads it, but whoever writes it is always the main process, always with this
// constant.
//
// The code carries no installation's address: each build writes its own. An
// installation pointed at another server requires another build. It is
// deliberate.
declare const __ATLANS_SERVIDOR__: string
export const SERVIDOR: string = __ATLANS_SERVIDOR__

/** Host of {@link SERVIDOR} — the only one accepted in an enrollment deep link. */
export const SERVER_HOST = new URL(SERVIDOR).hostname
