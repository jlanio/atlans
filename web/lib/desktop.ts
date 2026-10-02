// web/lib/desktop.ts
//
// Acesso à ponte read-only exposta pelo app desktop (Electron) em
// `window.atlansDesktop` — ver desktop/src/preload/web.ts.
//
// No navegador comum a ponte NÃO existe: tudo aqui degrada para `null`, e a UI
// que a consome (o selo do executor) simplesmente não renderiza. É o único
// ponto de acoplamento com o desktop, e é feature-detect puro — nenhum campo é
// assumido sem checar.

/** Espelha `StatusExecutorLocal` de desktop/src/shared/executor-status.ts.
 *  Duplicado de propósito: são dois pacotes sem código compartilhado. */
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

/** A ponte do desktop, ou `null` fora dele. */
export function ponteDesktop(): PonteDesktop | null {
  if (typeof window === 'undefined') return null
  const p = (window as unknown as { atlansDesktop?: PonteDesktop }).atlansDesktop
  return p && typeof p.obterStatus === 'function' && typeof p.aoMudarStatus === 'function'
    ? p
    : null
}
