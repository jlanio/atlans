// desktop/src/main/state/store.test.ts
//
// O store entrega para o renderer via IPC, e cada entrega custa um structured
// clone POR JANELA. A versão anterior mandava o log inteiro (até 1000 linhas)
// dentro do estado, e notificava UMA VEZ POR LINHA — 100 linhas de um workflow
// viravam 100 broadcasts de 1000 linhas, mais 100 cópias do array inteiro.
// Quadrático no volume de log, e exatamente quando o executor está mais ocupado.
//
// Estes testes travam as duas propriedades que consertaram isso:
//
//   COALESCE     uma rajada de eventos vira UM broadcast de estado.
//   INCREMENTAL  o log sai por canal próprio, só com as linhas novas.
//
// Nenhuma das duas é visível em code review — as duas voltam se alguém trocar
// `agendar()` por uma chamada direta "para simplificar".
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppStore, type EstadoApp, type LoteLog } from './store.js'
import type { ExecutorEvent } from '../../shared/events.js'

function log(msg: string, level = 'INFO'): ExecutorEvent {
  return { v: 1, t: 'log', ts: 1, data: { ts: 1, level, alias: 'X', msg } } as ExecutorEvent
}

let store: AppStore
let estados: EstadoApp[]
let lotes: LoteLog[]

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
    expect(lotes).toHaveLength(0)   // nada antes do flush

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
    // O último estado vence — é o que a UI precisa mostrar.
    expect(estados[0]!.supervisor).toBe('running')
  })

  it('a janela é FIXA, e não reiniciada a cada evento', () => {
    // Debounce seria um bug: num executor falante o timer nunca venceria e a
    // tela congelaria enquanto houvesse log chegando.
    store.aplicarEvento(log('a'))
    vi.advanceTimersByTime(60)
    store.aplicarEvento(log('b'))   // não pode adiar o flush
    vi.advanceTimersByTime(30)

    expect(lotes).toHaveLength(1)
    expect(lotes[0]!.linhas.map((l) => l.msg)).toEqual(['a', 'b'])
  })

  it('log NÃO arrasta um broadcast de estado junto', () => {
    // O ponto do canal separado: linha de log não muda o estado agregado.
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
    // 1200 linhas com teto de 1000: as 200 primeiras já não existem mais, e o
    // renderer precisa saber disso para recarregar em vez de emendar um buraco.
    for (let i = 0; i < 1200; i++) store.aplicarEvento(log(`l${i}`))
    vi.runAllTimers()

    const completo = store.logCompleto()
    expect(completo.linhas).toHaveLength(1000)
    expect(completo.primeiroSeq).toBe(201)
    expect(completo.linhas[0]!.msg).toBe('l200')
  })

  it('o contador de erros acompanha o descarte do buffer', () => {
    // O erro sai do buffer, e o contador tem de sair junto — senão a sidebar
    // mostra "3 erros" para sempre, sem nenhuma linha correspondente no log.
    store.aplicarEvento(log('erro antigo', 'ERROR'))
    for (let i = 0; i < 1000; i++) store.aplicarEvento(log(`l${i}`))
    vi.runAllTimers()

    expect(store.instantaneo().errosNoLog).toBe(0)
  })

  it('o estado NÃO carrega o log', () => {
    // A regressão que este arquivo inteiro existe para impedir.
    store.aplicarEvento(log('nao devo viajar no estado'))
    store.aplicarEstadoSupervisor('running')
    vi.runAllTimers()

    expect(estados[0]).not.toHaveProperty('log')
    expect(JSON.stringify(estados[0])).not.toContain('nao devo viajar')
  })
})
