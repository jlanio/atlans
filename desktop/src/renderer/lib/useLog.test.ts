// desktop/src/renderer/lib/useLog.test.ts
//
// The stitching of log batches. Tested as a pure function because the first
// version lived inside the `setState` updater and hid three defects:
//
//   1. the updater runs AFTER the handler, and the `seq` comparison read a ref
//      that had already advanced — no incremental batch got in, and the log
//      froze right after mounting. A bug that only shows up in use, and as "the
//      log stopped updating";
//   2. there was a `window.atlas.log()` inside the updater — a side effect in a
//      function React may call twice;
//   3. the initial load replaced the buffer and discarded the lines arriving in
//      the interval between the main process building the response and it
//      arriving here.
//
// All three are invisible on a casual read and would come back with the first
// "simplification".
import { describe, expect, it } from 'vitest'
import {
  LOG_VAZIO, MAX_LOG, mesclarLog, type EstadoLog, type LinhaVisivel,
} from './useLog.js'
import type { LinhaLog, LoteLog } from '../../main/state/store.js'

function linha(seq: number): LinhaLog {
  return { seq, ts: seq, level: 'INFO', alias: 'X', msg: `l${seq}` }
}

/**
 * A line already in the local buffer — with the search text `mesclarLog` adds.
 *
 * What arrives over IPC is `LinhaLog`; what is stored here is `LinhaVisivel`,
 * with `msg`+`alias` lowercased so the panel filter does not redo it on every
 * keystroke.
 */
function guardada(seq: number): LinhaVisivel {
  const l = linha(seq)
  return { ...l, busca: `${l.alias}\n${l.msg}`.toLowerCase() }
}

function lote(seqs: number[], primeiroSeq = seqs[0] ?? 1): LoteLog {
  return { linhas: seqs.map(linha), primeiroSeq }
}

const seqs = (e: EstadoLog) => e.linhas.map((l) => l.seq)

describe('carregamento completo', () => {
  it('monta o buffer a partir do zero', () => {
    const { estado } = mesclarLog(LOG_VAZIO, lote([1, 2, 3]), 'completo')
    expect(seqs(estado)).toEqual([1, 2, 3])
    expect(estado.ultimoSeq).toBe(3)
  })

  it('PRESERVA as linhas que chegaram enquanto o snapshot vinha', () => {
    // Defect 3. The push delivers 10 and 11 before the response of `atlas.log()`
    // (taken at 9) arrives. Simply replacing would lose both forever, because
    // `ultimoSeq` has already passed them and no future batch resends them.
    const comPush = mesclarLog(LOG_VAZIO, lote([10, 11], 10), 'incremental').estado
    const { estado } = mesclarLog(comPush, lote([8, 9]), 'completo')

    expect(seqs(estado)).toEqual([8, 9, 10, 11])
    expect(estado.ultimoSeq).toBe(11)
  })

  it('não deixa o ultimoSeq andar para trás', () => {
    const adiantado: EstadoLog = { linhas: [guardada(50)], ultimoSeq: 50 }
    expect(mesclarLog(adiantado, lote([1, 2]), 'completo').estado.ultimoSeq).toBe(50)
  })
})

describe('lotes incrementais', () => {
  it('emenda as linhas novas', () => {
    // The case defect 1 broke: in use, the log stopped updating.
    let e = mesclarLog(LOG_VAZIO, lote([1, 2]), 'completo').estado
    e = mesclarLog(e, lote([3, 4], 1), 'incremental').estado
    e = mesclarLog(e, lote([5], 1), 'incremental').estado

    expect(seqs(e)).toEqual([1, 2, 3, 4, 5])
    expect(e.ultimoSeq).toBe(5)
  })

  it('ignora linhas repetidas depois de um recarregamento', () => {
    const e = mesclarLog(LOG_VAZIO, lote([1, 2, 3]), 'completo').estado
    const r = mesclarLog(e, lote([2, 3, 4], 1), 'incremental')

    expect(seqs(r.estado)).toEqual([1, 2, 3, 4])
  })

  it('lote inteiramente repetido devolve o MESMO objeto', () => {
    // It is what lets the hook avoid pointless re-renders.
    const e = mesclarLog(LOG_VAZIO, lote([1, 2, 3]), 'completo').estado
    expect(mesclarLog(e, lote([1, 2, 3], 1), 'incremental').estado).toBe(e)
  })

  it('lote vazio não mexe em nada', () => {
    const e = mesclarLog(LOG_VAZIO, lote([1]), 'completo').estado
    const r = mesclarLog(e, { linhas: [], primeiroSeq: 1 }, 'incremental')
    expect(r.estado).toBe(e)
    expect(r.recarregar).toBe(false)
  })
})

describe('buraco no meio', () => {
  it('pede recarga quando o main já descartou o que faltava', () => {
    // We were at 5; the batch says the oldest line the main process still has is
    // 900. Lines 6..899 no longer exist anywhere, and stitching would produce a
    // log with an invisible jump.
    const e: EstadoLog = { linhas: [guardada(5)], ultimoSeq: 5 }
    const r = mesclarLog(e, lote([1000], 900), 'incremental')

    expect(r.recarregar).toBe(true)
    expect(r.estado).toBe(e)   // does not touch the buffer until the reload comes
  })

  it('buffer cheio no main, mas SEM buraco, não pede recarga', () => {
    // The normal case with the log full: the main process has already trimmed the
    // start (high primeiroSeq), but we are up to date. Confusing the two would
    // make the app reload the whole log on every batch — exactly the cost this
    // design eliminated.
    const e: EstadoLog = { linhas: [guardada(1200)], ultimoSeq: 1200 }
    expect(mesclarLog(e, lote([1201], 201), 'incremental').recarregar).toBe(false)
  })

  it('buffer local vazio nunca pede recarga', () => {
    // With nothing applied yet, there cannot be a gap — and requesting a reload
    // here would create a loop with the initial load.
    expect(mesclarLog(LOG_VAZIO, lote([500], 500), 'incremental').recarregar).toBe(false)
  })
})

describe('teto do buffer', () => {
  it('apara pelo início e mantém as mais novas', () => {
    const todas = Array.from({ length: MAX_LOG + 50 }, (_, i) => i + 1)
    const { estado } = mesclarLog(LOG_VAZIO, lote(todas), 'completo')

    expect(estado.linhas).toHaveLength(MAX_LOG)
    expect(estado.linhas[0]!.seq).toBe(51)
    expect(estado.ultimoSeq).toBe(MAX_LOG + 50)
  })

  it('vale também para a emenda incremental', () => {
    const e = mesclarLog(
      LOG_VAZIO, lote(Array.from({ length: MAX_LOG }, (_, i) => i + 1)), 'completo',
    ).estado
    const r = mesclarLog(e, lote([MAX_LOG + 1], 1), 'incremental')

    expect(r.estado.linhas).toHaveLength(MAX_LOG)
    expect(r.estado.linhas.at(-1)!.seq).toBe(MAX_LOG + 1)
  })
})
