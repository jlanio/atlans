// desktop/src/main/state/store.test.ts
//
// The store delivers to the renderer via IPC, and each delivery costs one
// structured clone PER WINDOW. The previous version sent the whole log (up to
// 1000 lines) inside the state, and notified ONCE PER LINE — 100 lines from a
// workflow became 100 broadcasts of 1000 lines, plus 100 copies of the whole
// array. Quadratic in log volume, and exactly when the executor is busiest.
//
// These tests lock in the two properties that fixed it:
//
//   COALESCE     a burst of events becomes ONE state broadcast.
//   INCREMENTAL  the log goes out on its own channel, with only the new lines.
//
// Neither is visible in code review — both come back if someone replaces
// `agendar()` with a direct call "to simplify".
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppStore, type AppState, type LogBatch } from './store.js'
import type { ExecutorEvent } from '../../shared/events.js'

function log(msg: string, level = 'INFO'): ExecutorEvent {
  return { v: 1, t: 'log', ts: 1, data: { ts: 1, level, alias: 'X', msg } } as ExecutorEvent
}

let store: AppStore
let estados: AppState[]
let lotes: LogBatch[]

beforeEach(() => {
  vi.useFakeTimers()
  store = new AppStore()
  estados = []
  lotes = []
  store.assinar((e) => estados.push(e))
  store.assinarLog((l) => lotes.push(l))
})

afterEach(() => { vi.useRealTimers() })

describe('coalescência', () => {
  it('uma rajada de 100 linhas vira UM lote', () => {
    for (let i = 0; i < 100; i++) store.aplicarEvento(log(`linha ${i}`))
    expect(lotes).toHaveLength(0)   // nothing before the flush

    vi.runAllTimers()

    expect(lotes).toHaveLength(1)
    expect(lotes[0]!.linhas).toHaveLength(100)
  })

  it('várias mudanças de estado viram UM broadcast', () => {
    store.aplicarEstadoSupervisor('starting')
    store.aplicarEstadoSupervisor('running')
    store.aplicarEvento({
      v: 1, t: 'state', ts: 1, data: { phase: 'running', step: null, detail: null },
    } as ExecutorEvent)
    vi.runAllTimers()

    expect(estados).toHaveLength(1)
    // The last state wins — it is what the UI needs to show.
    expect(estados[0]!.supervisor).toBe('running')
  })

  it('a janela é FIXA, e não reiniciada a cada evento', () => {
    // Debounce would be a bug: on a chatty executor the timer would never expire
    // and the screen would freeze for as long as log kept arriving.
    store.aplicarEvento(log('a'))
    vi.advanceTimersByTime(60)
    store.aplicarEvento(log('b'))   // must not postpone the flush
    vi.advanceTimersByTime(30)

    expect(lotes).toHaveLength(1)
    expect(lotes[0]!.linhas.map((l) => l.msg)).toEqual(['a', 'b'])
  })

  it('log NÃO arrasta um broadcast de estado junto', () => {
    // The point of the separate channel: a log line does not change the
    // aggregate state.
    store.aplicarEvento(log('só log'))
    vi.runAllTimers()

    expect(lotes).toHaveLength(1)
    expect(estados).toHaveLength(0)
  })

  it('um ERROR no log ATUALIZA o estado — a sidebar mostra o contador', () => {
    store.aplicarEvento(log('quebrou', 'ERROR'))
    vi.runAllTimers()

    expect(estados).toHaveLength(1)
    expect(estados[0]!.errosNoLog).toBe(1)
  })

  it('descarregar() entrega na hora — o caminho de encerramento', () => {
    store.aplicarEstadoSupervisor('failed', 'morreu')
    store.descarregar()

    expect(estados).toHaveLength(1)
    expect(estados[0]!.detalheSupervisor).toBe('morreu')
  })
})

describe('canal incremental', () => {
  it('cada lote traz só o que é novo', () => {
    store.aplicarEvento(log('a'))
    vi.runAllTimers()
    store.aplicarEvento(log('b'))
    vi.runAllTimers()

    expect(lotes.map((l) => l.linhas.map((x) => x.msg))).toEqual([['a'], ['b']])
  })

  it('seq é monotônico e serve de chave estável', () => {
    for (let i = 0; i < 5; i++) store.aplicarEvento(log(`l${i}`))
    vi.runAllTimers()

    const seqs = lotes[0]!.linhas.map((l) => l.seq)
    expect(seqs).toEqual([...seqs].sort((a, b) => a - b))
    expect(new Set(seqs).size).toBe(5)
  })

  it('o buffer é aparado, e `primeiroSeq` denuncia o que se perdeu', () => {
    // 1200 lines with a ceiling of 1000: the first 200 no longer exist, and the
    // renderer needs to know that to reload instead of patching over a gap.
    for (let i = 0; i < 1200; i++) store.aplicarEvento(log(`l${i}`))
    vi.runAllTimers()

    const completo = store.logCompleto()
    expect(completo.linhas).toHaveLength(1000)
    expect(completo.primeiroSeq).toBe(201)
    expect(completo.linhas[0]!.msg).toBe('l200')
  })

  it('o contador de erros acompanha o descarte do buffer', () => {
    // The error leaves the buffer, and the counter has to go with it — otherwise
    // the sidebar shows "3 erros" (3 errors) forever, with no matching line in
    // the log.
    store.aplicarEvento(log('erro antigo', 'ERROR'))
    for (let i = 0; i < 1000; i++) store.aplicarEvento(log(`l${i}`))
    vi.runAllTimers()

    expect(store.instantaneo().errosNoLog).toBe(0)
  })

  it('o estado NÃO carrega o log', () => {
    // The regression this whole file exists to prevent.
    store.aplicarEvento(log('nao devo viajar no estado'))
    store.aplicarEstadoSupervisor('running')
    vi.runAllTimers()

    expect(estados[0]).not.toHaveProperty('log')
    expect(JSON.stringify(estados[0])).not.toContain('nao devo viajar')
  })
})
