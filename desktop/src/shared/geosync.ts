// desktop/src/shared/geosync.ts
//
// GeoSync constants shared between main and renderer.
//
// They live in `shared/` and not in `main/state/config.ts` for a concrete
// reason: the renderer runs in Chromium, without `node:fs` or `electron`.
// Importing a VALUE from a main-process module drags those dependencies into
// the screen's bundle, and the page dies blank on the first load — with no
// visible error, because the window has already painted the background before
// React tries to mount. Types may come from main (they are erased at compile
// time); values may not.

/**
 * `EXECUTOR_SYNC_INTERVAL` that the app writes on every GeoSync save — a choice
 * of THIS app, not the executor's default (30 s, which only applies when the
 * line is missing from `.env`). The `.env.example`, which seeds `.env` at
 * enrollment, has the same 10. `limites.test.ts` checks that the executor
 * accepts the value.
 */
export const INTERVALO_SYNC = 10

/** Directions accepted by `EXECUTOR_SYNC_MODE`. */
export const MODOS_SYNC = ['upload', 'download', 'bidirectional', 'catalog'] as const
export type ModoSync = (typeof MODOS_SYNC)[number]

/** Valores aceitos por `EXECUTOR_SYNC_CONFLICT_STRATEGY`. */
export const ESTRATEGIAS = ['local-wins', 'remote-wins', 'keep-both'] as const
export type EstrategiaConflito = (typeof ESTRATEGIAS)[number]

/**
 * What the executor does when `EXECUTOR_SYNC_MODE` / `_CONFLICT_STRATEGY` are
 * missing from `.env` — the defaults of `executor/config.py` (`limites.test.ts`
 * compares them).
 *
 * The screen fell back to `bidirectional` and lied: the executor ran `upload`,
 * and saving any GeoSync setting wrote the screen's `bidirectional`, so it
 * started downloading from the Drive without anyone having chosen to. `upload`
 * is also the safe default: nothing that happens in the Drive deletes or
 * overwrites a local file.
 */
export const PADRAO_SYNC = {
  modo: 'upload',
  conflito: 'remote-wins',
} as const satisfies { modo: ModoSync; conflito: EstrategiaConflito }
