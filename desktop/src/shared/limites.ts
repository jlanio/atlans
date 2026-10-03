// desktop/src/shared/limites.ts
//
// Defaults and ranges of the execution variables the Ajustes screen edits — the
// mirror, in a single place, of `executor/config.py`.
//
// The executor is in charge: it reads each variable with
// `executor/_ambiente.py::ler_int`, which discards an out-of-range value and
// uses the default. A different range here makes the screen lie — and, worse,
// makes saving write ITS number over what the executor was using.
// `limites.test.ts` reads `executor/config.py` and fails if the two sides
// diverge.
//
// In `shared/` because the main process (reading and writing `.env`) and the
// renderer (the screen's validation) need the SAME numbers, and the renderer
// cannot import a value from `src/main` (see vite.config.ts). A JSON in
// `executor/`, read by Python and imported here, would be a single source of
// truth; but the Vite dev server only serves files from inside `desktop/`
// (`server.fs.allow`), and the renderer would break under `npm run dev`.

export interface Faixa {
  /** What the executor uses when the variable is missing or invalid. */
  padrao: number
  min: number
  /** `null` when the executor imposes no ceiling. */
  max: number | null
}

export const LIMITES = {
  /** EXECUTOR_MAX_CONCURRENT */
  workers: { padrao: 4, min: 1, max: 256 },
  /** EXECUTOR_MAX_QUEUE_SIZE */
  filaMax: { padrao: 50, min: 1, max: 10_000 },
  /**
   * EXECUTOR_JOB_TIMEOUT. No ceiling, as in the executor: the screen had one of
   * 86,400 s, and with 100,000 in `.env` it showed 3600 while the executor used
   * 100,000 — and saving any setting wrote the 3600.
   */
  timeoutS: { padrao: 3600, min: 1, max: null },
} as const satisfies Record<string, Faixa>

export function withinRange(n: number, faixa: Faixa): boolean {
  return Number.isSafeInteger(n) && n >= faixa.min && (faixa.max === null || n <= faixa.max)
}

/**
 * The integer the executor sees in a `.env` value, or the default.
 *
 * Mimics Python's `int()` over what python-dotenv delivers: surrounding spaces,
 * sign and `_` between digits are allowed; the end-of-line comment (` # ...`)
 * has already been dropped by dotenv; anything else is invalid. The previous
 * `parseInt` read "8x" as 8 — the screen showed 8 workers and the executor,
 * which rejects "8x", ran with 4.
 */
export function inteiroDoEnv(bruto: string | undefined, faixa: Faixa): number {
  const m = /^\s*([+-]?\d+(?:_\d+)*)(?:\s+#.*)?\s*$/.exec(bruto ?? '')
  const n = m ? Number(m[1]!.replace(/_/g, '')) : Number.NaN
  return withinRange(n, faixa) ? n : faixa.padrao
}
