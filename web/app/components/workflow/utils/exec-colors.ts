/**
 * Execution color of the edge — a pure, testable mapping.
 *
 * Exists as its own module for two reasons. The first is to give the mapping a
 * test surface: the omissions below are deliberate and do not explain
 * themselves when read in the middle of the component. The second is to get rid
 * of the raw hex values that lived in `custom-edges` — they were identical in
 * both themes, while the card of the same node already changed tone with the theme.
 */

/** Execution tone — the same vocabulary as the card (globals.css, `.exec-card`). */
export type ExecTone = "idle" | "running" | "success" | "error" | "unknown"

const TOM_POR_STATUS: Record<string, ExecTone> = {
  started: "running",
  completed: "success",
  failed: "error",
  // `unknown` was missing: the card turned amber and the edge leaving it fell to
  // gray, saying two different things about the same node.
  unknown: "unknown",
  // `idle` is absent ON PURPOSE — it falls to the handle color, so a `true`
  // edge stays green before any run.
  //
  // `cancelled` is not included: it is a WORKFLOW status, never a node one.
  // Cancellation returns nodes to `idle` (see `completeExecution` in workflowExecutionStore).
}

const TOM_POR_HANDLE: Record<string, ExecTone> = {
  true: "success",
  false: "error",
}

/** Looks up in the map ONLY what it declares itself.
 *
 *  A port name is user data: `output_vars` is free text and dynamic ports
 *  accept any identifier. With raw bracket access, a port named `constructor`
 *  returned the `Object` function instead of `undefined`, and the color
 *  became `var(--exec-function Object() { [native code] })` — an invalid
 *  `var()`, property dropped, port invisible on the canvas. */
function buscarTom(mapa: Record<string, ExecTone>, chave: string): ExecTone | undefined {
  // `hasOwnProperty.call` and not `Object.hasOwn`: this is the only color module
  // on the render path of EVERY edge, and `Object.hasOwn` is ES2022 — the project
  // declares no browserslist and Next's polyfill bundle does not cover it. It
  // costs the same and has no version floor.
  return Object.prototype.hasOwnProperty.call(mapa, chave) ? mapa[chave] : undefined
}

/** Tone that the handle ID suggests on its own — `undefined` when the handle is
 *  not a routing one.
 *
 *  Exposed so the node's PORT paints itself with the same rule as the edge.
 *  Without this the handle would have to repeat the `true → verde` map, and the
 *  two ends of the same connection could diverge without anyone noticing. */
export function tomDoHandle(handle: string | null | undefined): ExecTone | undefined {
  return handle ? buscarTom(TOM_POR_HANDLE, handle) : undefined
}

/** Edge tone from the source's status and the output handle. */
export function tomDaAresta(
  status: string | undefined,
  handle: string,
  perdedora: boolean,
): ExecTone {
  if (perdedora) return "idle"
  return (status ? buscarTom(TOM_POR_STATUS, status) : undefined)
    ?? buscarTom(TOM_POR_HANDLE, handle)
    ?? "idle"
}

/** CSS token of the tone — resolved in `:root`/`.dark`, therefore theme-aware. */
export const corDoTom = (tom: ExecTone) => `var(--exec-${tom})`
