// web/lib/desktop.ts
//
// Access to the read-only bridge exposed by the desktop app (Electron) at
// `window.atlansDesktop` — see desktop/src/preload/web.ts.
//
// In a regular browser the bridge does NOT exist: everything here degrades to
// `null`, and the UI that consumes it (the executor badge) simply does not
// render. It is the only coupling point with the desktop, and it is pure
// feature detection — no field is assumed without checking.

/** Mirrors `StatusExecutorLocal` from desktop/src/shared/executor-status.ts.
 *  Duplicated on purpose: they are two packages with no shared code. */
export type EstadoExecutorLocal = 'online' | 'ocupado' | 'offline' | 'sem-vinculo'

export interface StatusExecutorLocal {
  versaoContrato: number
  executorId: string | null
  vinculado: boolean
  estado: EstadoExecutorLocal
  emExecucao: number
  capacidade: number | null
}

interface PonteDesktop {
  versao: number
  obterStatus: () => Promise<StatusExecutorLocal>
  aoMudarStatus: (fn: (s: StatusExecutorLocal) => void) => () => void
}

/** The desktop bridge, or `null` outside of it. */
export function ponteDesktop(): PonteDesktop | null {
  if (typeof window === 'undefined') return null
  const p = (window as unknown as { atlansDesktop?: PonteDesktop }).atlansDesktop
  return p && typeof p.obterStatus === 'function' && typeof p.aoMudarStatus === 'function'
    ? p
    : null
}
