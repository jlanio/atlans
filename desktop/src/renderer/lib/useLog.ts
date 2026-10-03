// desktop/src/renderer/lib/useLog.ts
//
// Renderer log buffer, fed by the incremental channel.
//
// The log does not come inside the state: it is append-only and large, and
// sending it whole on every change cost ~150-200 KB of structured clone per
// window, per broadcast — and there was one broadcast PER LINE. See the header
// of `main/state/store.ts`.
//
// The stitching of batches lives in `mesclarLog`, which is PURE and tested. The
// first version did this inside the `setState` updater and had three defects
// that do not show up on a casual read:
//
//   1. the `setState` updater runs AFTER the handler, and the `seq` comparison
//      read a ref that had already been advanced — no incremental batch was
//      applied, and the log froze right after mounting;
//   2. the updater fired a `window.atlas.log()` — a side effect inside a
//      function React may call twice;
//   3. the initial load REPLACED the buffer, discarding the lines that arrived
//      between the snapshot being taken in the main process and the promise
//      resolving here — right at boot, which is when the most lines arrive.
import { useEffect, useRef, useState } from 'react'
import type { LinhaLog, LoteLog } from '../../main/state/store.js'

/** Same ceiling as the main process. Diverging would only make both ends disagree. */
export const MAX_LOG = 1000

/**
 * A line with the search text already lowercased.
 *
 * The panel filter called `msg.toLowerCase()` and `alias.toLowerCase()` for
 * each of the 1000 lines ON EVERY KEYSTROKE — two thousand string allocations
 * per letter, and the lag showed between the key and the letter on screen.
 * Here the cost is paid ONCE per line, when it comes in.
 *
 * It lives in the renderer, not in `LinhaLog` in the main process: the field
 * would double the size of each log batch over IPC, which is precisely what
 * this channel was designed to trim.
 */
export interface LinhaVisivel extends LinhaLog {
  /**
   * `alias` and `msg` lowercased, separated by a line break.
   *
   * The separator is not decoration: the search field is single-line, so no
   * typed term matches across both — the result is identical to the
   * `msg.includes(t) || alias.includes(t)` there was before.
   */
  busca: string
}

function comBusca(l: LinhaLog): LinhaVisivel {
  return { ...l, busca: (l.alias + '\n' + l.msg).toLowerCase() }
}

export interface EstadoLog {
  linhas: LinhaVisivel[]
  /** `seq` of the last line already incorporated. */
  ultimoSeq: number
}

export const LOG_VAZIO: EstadoLog = { linhas: [], ultimoSeq: 0 }

/**
 * Incorporates a batch into the local buffer.
 *
 * `modo: 'completo'` is the response of `atlas.log()` — the main process's
 * whole buffer. `modo: 'incremental'` is a batch from the push channel.
 *
 * Returns `recarregar: true` when the main process has already discarded lines
 * this buffer never saw; stitching in that case would produce a log with an
 * invisible jump in the middle, which is worse than reloading.
 *
 * Returns the SAME state object when nothing changes — the caller uses that to
 * avoid pointless renders.
 */
export function mesclarLog(
  atual: EstadoLog,
  lote: LoteLog,
  modo: 'completo' | 'incremental',
): { estado: EstadoLog; recarregar: boolean } {
  if (lote.linhas.length === 0) return { estado: atual, recarregar: false }

  const ultimoDoLote = lote.linhas[lote.linhas.length - 1]!.seq

  if (modo === 'completo') {
    // The lines we already have that are NEWER than the snapshot survive: they
    // arrived via push after the main process built the response, and simply
    // replacing would lose them forever (`ultimoSeq` would already have passed
    // them).
    const posteriores = atual.linhas.filter((l) => l.seq > ultimoDoLote)
    const linhas = lote.linhas.map(comBusca).concat(posteriores)
    return {
      estado: {
        linhas: linhas.length > MAX_LOG ? linhas.slice(-MAX_LOG) : linhas,
        ultimoSeq: Math.max(atual.ultimoSeq, ultimoDoLote),
      },
      recarregar: false,
    }
  }

  // `primeiroSeq` is the oldest line the main process still keeps. If it is
  // already later than the next one we expected, what was missing was
  // discarded there.
  if (atual.ultimoSeq > 0 && lote.primeiroSeq > atual.ultimoSeq + 1) {
    return { estado: atual, recarregar: true }
  }

  // A batch may repeat lines after a reload.
  const novas = lote.linhas.filter((l) => l.seq > atual.ultimoSeq)
  if (novas.length === 0) return { estado: atual, recarregar: false }

  const linhas = atual.linhas.concat(novas.map(comBusca))
  return {
    estado: {
      linhas: linhas.length > MAX_LOG ? linhas.slice(-MAX_LOG) : linhas,
      ultimoSeq: Math.max(atual.ultimoSeq, ultimoDoLote),
    },
    recarregar: false,
  }
}

export function useLog(): LinhaVisivel[] {
  const [linhas, setLinhas] = useState<LinhaVisivel[]>(LOG_VAZIO.linhas)
  // The source of truth is the ref, updated SYNCHRONOUSLY. The state is only the
  // mirror for rendering — mixing the two is what produced defect 1.
  const estadoRef = useRef<EstadoLog>(LOG_VAZIO)

  useEffect(() => {
    let vivo = true

    const aplicar = (lote: LoteLog, modo: 'completo' | 'incremental') => {
      if (!vivo) return
      const { estado, recarregar } = mesclarLog(estadoRef.current, lote, modo)

      if (recarregar) {
        void window.atlas.log().then((l) => aplicar(l, 'completo'))
        return
      }
      if (estado === estadoRef.current) return   // nothing new: does not re-render

      estadoRef.current = estado
      setLinhas(estado.linhas)
    }

    // The subscription comes BEFORE the invoke: a batch arriving while the promise
    // is in flight is applied, and `mesclarLog` in complete mode preserves it.
    const cancelar = window.atlas.aoReceberLog((l) => aplicar(l, 'incremental'))
    void window.atlas.log().then((l) => aplicar(l, 'completo'))

    return () => { vivo = false; cancelar() }
  }, [])

  return linhas
}
