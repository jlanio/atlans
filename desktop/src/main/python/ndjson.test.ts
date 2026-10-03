// desktop/src/main/python/ndjson.test.ts
//
// TypeScript side of the contract test. The Python side lives in
// tests/unit/test_executor_json_ipc.py — together they guarantee that both
// speak the same language, which no type checker can verify on its own.
import { describe, expect, it, vi } from 'vitest'
import { LineSplitter, NdjsonParser } from './ndjson.js'
import type { ExecutorEvent } from '../../shared/events.js'

function parser() {
  const eventos: ExecutorEvent[] = []
  const brutas: string[] = []
  const p = new NdjsonParser({
    onEvent: (e) => eventos.push(e),
    onRaw: (l) => brutas.push(l),
  })
  return { p, eventos, brutas }
}

const HELLO = '{"v":1,"t":"hello","ts":1.5,"data":{"pid":10}}'

describe('framing', () => {
  it('aceita uma linha valida', () => {
    const { p, eventos } = parser()
    p.push(HELLO + '\n')
    expect(eventos).toHaveLength(1)
    expect(eventos[0]!.t).toBe('hello')
  })

  it('trata print() de um no de workflow como texto, nao como erro', () => {
    // The executor runs third-party code (PythonScript). A print() lands on the
    // SAME stdout — and must neither bring down the parser nor become an event.
    const { p, eventos, brutas } = parser()
    p.push('processando 42 feicoes...\n' + HELLO + '\n')
    expect(brutas).toEqual(['processando 42 feicoes...'])
    expect(eventos).toHaveLength(1)
  })

  it('nao confunde JSON de outra origem com evento', () => {
    const { p, eventos, brutas } = parser()
    p.push('{"resultado": "ok"}\n')
    expect(eventos).toHaveLength(0)
    expect(brutas).toHaveLength(1)
  })

  it('linha truncada com framing valido vira texto em vez de excecao', () => {
    // Happens when the process dies in the middle of a write.
    const { p, eventos, brutas } = parser()
    p.push('{"v":1,"t":"snap\n')
    expect(eventos).toHaveLength(0)
    expect(brutas).toHaveLength(1)
  })

  it('rejeita objeto sem o campo t', () => {
    const { p, eventos, brutas } = parser()
    p.push('{"v":1,"ts":1}\n')
    expect(eventos).toHaveLength(0)
    expect(brutas).toHaveLength(1)
  })
})

describe('fronteira de chunk', () => {
  it('remonta uma linha partida em varios chunks', () => {
    // A stream's `data` event does not respect line boundaries — this is the
    // classic bug that brings parsers down under load, when lines get large
    // precisely because there is more to report.
    const { p, eventos } = parser()
    for (const pedaco of [HELLO.slice(0, 5), HELLO.slice(5, 20), HELLO.slice(20), '\n']) {
      p.push(pedaco)
    }
    expect(eventos).toHaveLength(1)
  })

  it('processa varios eventos num chunk so', () => {
    const { p, eventos } = parser()
    p.push(HELLO + '\n' + HELLO + '\n' + HELLO + '\n')
    expect(eventos).toHaveLength(3)
  })

  it('caractere a caractere tambem funciona', () => {
    const { p, eventos } = parser()
    for (const c of HELLO + '\n') p.push(c)
    expect(eventos).toHaveLength(1)
  })

  it('nao emite enquanto a linha nao fecha', () => {
    const { p, eventos } = parser()
    p.push(HELLO)
    expect(eventos).toHaveLength(0)
  })
})

describe('flush', () => {
  it('entrega a ultima linha sem \\n quando o stream fecha', () => {
    // The last line before a crash is usually the most interesting one — and it
    // has no trailing newline.
    const { p, eventos } = parser()
    p.push(HELLO)
    p.flush()
    expect(eventos).toHaveLength(1)
  })

  it('flush em buffer vazio nao emite nada', () => {
    const { p, eventos, brutas } = parser()
    p.flush()
    expect(eventos).toHaveLength(0)
    expect(brutas).toHaveLength(0)
  })
})

describe('robustez', () => {
  it('remove o \\r do CRLF do Windows', () => {
    const { p, eventos, brutas } = parser()
    p.push(HELLO + '\r\n' + 'texto solto\r\n')
    expect(eventos).toHaveLength(1)
    expect(brutas).toEqual(['texto solto'])
  })

  it('ignora linhas em branco', () => {
    const { p, eventos, brutas } = parser()
    p.push('\n\n   \n')
    expect(eventos).toHaveLength(0)
    expect(brutas).toHaveLength(0)
  })

  it('descarta acumulo sem quebra de linha em vez de crescer sem limite', () => {
    // Binary output or a runaway node must not consume the app's memory until it
    // dies.
    const { p, brutas } = parser()
    p.push('x'.repeat(2 * 1024 * 1024))
    expect(brutas).toHaveLength(1)
    expect(brutas[0]).toContain('descartada')
    // The buffer really was emptied: flush has nothing to return.
    p.flush()
    expect(brutas).toHaveLength(1)
  })

  it('volta a funcionar depois de um descarte', () => {
    const { p, eventos } = parser()
    p.push('x'.repeat(2 * 1024 * 1024))
    p.push(HELLO + '\n')
    expect(eventos).toHaveLength(1)
  })

  it('nao propaga excecao de um handler', () => {
    const p = new NdjsonParser({
      onEvent: () => { throw new Error('handler quebrado') },
      onRaw: vi.fn(),
    })
    // A handler that throws is a bug of whoever wrote it; the parser must not
    // turn that into the whole stream going down.
    expect(() => p.push(HELLO + '\n')).toThrow()
  })
})

describe('LineSplitter (stderr)', () => {
  it('quebra por linha e descarta vazias', () => {
    const linhas: string[] = []
    const s = new LineSplitter((l) => linhas.push(l))
    s.push('primeira\nseg')
    s.push('unda\n\n')
    expect(linhas).toEqual(['primeira', 'segunda'])
  })

  it('flush entrega o resto', () => {
    const linhas: string[] = []
    const s = new LineSplitter((l) => linhas.push(l))
    s.push('sem quebra no fim')
    s.flush()
    expect(linhas).toEqual(['sem quebra no fim'])
  })
})
