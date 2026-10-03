// desktop/src/main/python/supervisor.test.ts
//
// Restart and shutdown policy. The spawn is injected, so nothing here depends
// on Python being installed.
import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { PythonSupervisor, type SupervisorState } from './supervisor.js'

class FakeProc extends EventEmitter {
  stdout = new PassThrough()
  stderr = new PassThrough()
  stdin = new PassThrough()
  pid = 4242
  escrito: string[] = []
  killed = false

  constructor() {
    super()
    this.stdin.on('data', (c: Buffer) => this.escrito.push(c.toString()))
  }

  kill(): boolean { this.killed = true; return true }

  /** Simulates the process exiting. */
  sair(codigo: number | null, sinal: NodeJS.Signals | null = null): void {
    this.emit('exit', codigo, sinal)
  }

  emitir(obj: unknown): void {
    this.stdout.write(JSON.stringify(obj) + '\n')
  }
}

function criar() {
  const procs: FakeProc[] = []
  const spawnFn = vi.fn(() => {
    const p = new FakeProc()
    procs.push(p)
    return p
  })
  const estados: Array<[SupervisorState, string | undefined]> = []
  const sup = new PythonSupervisor({
    pythonExe: 'python',
    cwd: '.',
    env: {},
    spawnFn: spawnFn as never,
  })
  sup.on('estado', (e, d) => estados.push([e, d]))
  return { sup, procs, estados, spawnFn }
}

/** Waits for stdout to be drained (PassThrough delivers on the next tick). */
const tick = () => new Promise((r) => setImmediate(r))

beforeEach(() => { vi.useFakeTimers({ shouldAdvanceTime: true }) })
afterEach(() => { vi.useRealTimers() })

describe('start', () => {
  it('vai para running ao receber o hello', async () => {
    const { sup, procs, estados } = criar()
    sup.start()
    expect(sup.estado).toBe('starting')

    procs[0]!.emitir({ v: 1, t: 'hello', ts: 1, data: { pid: 1 } })
    await tick()
    expect(sup.estado).toBe('running')
    expect(estados.map(([e]) => e)).toEqual(['starting', 'running'])
  })

  it('start duplicado nao cria um segundo processo', () => {
    // Two executors with the same EXECUTOR_ID would create duplicate connections
    // on the server.
    const { sup, spawnFn } = criar()
    sup.start()
    sup.start()
    expect(spawnFn).toHaveBeenCalledTimes(1)
  })

  it('falha de spawn nao entra em loop de retry', async () => {
    // A missing python.exe or one without permission does not fix itself.
    const { sup, procs } = criar()
    sup.start()
    procs[0]!.emit('error', new Error('ENOENT'))
    await tick()
    expect(sup.estado).toBe('failed')
  })
})

describe('reinicio', () => {
  it('religa com backoff quando o processo cai', async () => {
    const { sup, procs, spawnFn } = criar()
    sup.start()
    procs[0]!.sair(1)
    await tick()
    expect(sup.estado).toBe('restarting')

    await vi.advanceTimersByTimeAsync(3_000)
    expect(spawnFn).toHaveBeenCalledTimes(2)
  })

  it('desiste apos um loop de quedas dentro da janela', async () => {
    // Restarting forever would hide the cause and burn CPU.
    //
    // The advance is `advanceTimersToNextTimerAsync`, not a fixed value: each
    // attempt waits for its own backoff (2s, 4s, 8s… up to 60s, with jitter),
    // and a fixed number large enough for the last one would make the WINDOW
    // slide, resetting the counter — the test would end up measuring something
    // else.
    const { sup, procs } = criar()
    sup.start()
    for (let i = 0; i < 6; i++) {
      procs[procs.length - 1]!.sair(1)
      await tick()
      if (sup.estado === 'failed') break
      await vi.advanceTimersToNextTimerAsync()
    }
    expect(sup.estado).toBe('failed')
  })

  it('quedas espacadas NAO consomem a janela', async () => {
    // An executor that runs fine for minutes and then crashes is not in a loop:
    // it is an intermittent failure, and giving up on it would leave the user's
    // machine without an executor until someone noticed.
    const { sup, procs } = criar()
    sup.start()
    for (let i = 0; i < 6; i++) {
      procs[procs.length - 1]!.sair(1)
      await tick()
      await vi.advanceTimersByTimeAsync(120_000)   // > backoff, < janela/2
    }
    expect(sup.estado).not.toBe('failed')
  })

  it('exit 1 apos draining e restart pedido pelo servidor, nao falha', async () => {
    // `config_changed` makes the executor exit with 1 after draining. Counting
    // that as a failure would take the executor down for good on a server that
    // reassigns workspaces a few times in a row.
    const { sup, procs, estados } = criar()
    sup.start()
    procs[0]!.emitir({ v: 1, t: 'hello', ts: 1, data: {} })
    await tick()
    procs[0]!.emitir({ v: 1, t: 'state', ts: 2, data: { phase: 'draining', step: null, detail: null } })
    await tick()
    procs[0]!.sair(1)
    await tick()

    expect(sup.estado).toBe('restarting')
    expect(estados.at(-1)?.[1]).toContain('servidor')
  })

  it('state failed interrompe o retry', async () => {
    // Expired cert, server key unavailable: a persistent cause, the user needs
    // to act. Trying again would only waste time.
    const { sup, procs, spawnFn } = criar()
    sup.start()
    procs[0]!.emitir({
      v: 1, t: 'state', ts: 1,
      data: { phase: 'failed', step: 'server_key', detail: 'sem rede' },
    })
    await tick()
    procs[0]!.sair(1)
    await tick()
    await vi.advanceTimersByTimeAsync(120_000)

    expect(sup.estado).toBe('failed')
    expect(spawnFn).toHaveBeenCalledTimes(1)
  })
})

describe('stop', () => {
  it('pede shutdown pelo stdin, e nao mata o processo', async () => {
    // On Windows there is no SIGTERM: kill() becomes TerminateProcess, immediate
    // death, with jobs lost and results never confirmed.
    const { sup, procs } = criar()
    sup.start()
    const proc = procs[0]!
    const p = sup.stop()
    await tick()

    expect(JSON.parse(proc.escrito.join('').trim())).toMatchObject({ cmd: 'shutdown' })
    expect(proc.killed).toBe(false)
    expect(sup.estado).toBe('draining')

    proc.sair(0)
    await p
    expect(sup.estado).toBe('stopped')
  })

  it('nao religa depois de uma parada pedida', async () => {
    const { sup, procs, spawnFn } = criar()
    sup.start()
    const p = sup.stop()
    procs[0]!.sair(0)
    await p
    await vi.advanceTimersByTimeAsync(120_000)
    expect(spawnFn).toHaveBeenCalledTimes(1)
  })

  it('stop sem processo resolve na hora', async () => {
    const { sup } = criar()
    await expect(sup.stop()).resolves.toBeUndefined()
  })

  it('duplo clique em "Parar" nao deixa um watchdog orfao', async () => {
    // The second click arrived before the `draining` state painted the screen
    // and armed a SECOND grace ceiling, overwriting the first one's handle
    // without clearing it. The orphan outlived the process exit and, at the end
    // of the deadline, cold-killed the NEXT executor, in the middle of a job.
    const { sup, procs, spawnFn } = criar()
    const linhas: string[] = []
    sup.on('linha', (t) => linhas.push(t))
    sup.start()

    const p1 = sup.stop(5_000)
    const p2 = sup.stop(5_000)
    expect(p2).toBe(p1)                       // idempotente: a MESMA parada
    await tick()
    // A single `shutdown` on stdin — Python was already draining.
    expect(procs[0]!.escrito.join('').trim().split('\n')).toHaveLength(1)

    procs[0]!.sair(0)
    await p1

    sup.start()                               // executor SEGUINTE
    await vi.advanceTimersByTimeAsync(10_000)
    expect(spawnFn).toHaveBeenCalledTimes(2)
    expect(linhas.filter((l) => l.includes('forcando'))).toEqual([])
    expect(procs[1]!.killed).toBe(false)
  })

  it('um pedido com teto menor encurta a drenagem em curso', async () => {
    // `refazerEnrollment` stops with 10 s because it needs to delete the PEMs.
    // Inheriting the 150 s of an earlier "Parar" (stop) would leave the user
    // waiting for a drain they already cut short.
    const { sup, procs } = criar()
    const linhas: string[] = []
    sup.on('linha', (t) => linhas.push(t))
    sup.start()

    const p = sup.stop(150_000)
    void sup.stop(5_000)
    await tick()
    await vi.advanceTimersByTimeAsync(6_000)
    expect(linhas.some((l) => l.includes('forcando'))).toBe(true)

    procs[0]!.sair(null, 'SIGKILL')
    await p
  })

  it('forca o encerramento quando o teto de graca estoura', async () => {
    const { sup, procs } = criar()
    sup.start()
    const proc = procs[0]!
    const p = sup.stop(5_000)
    await tick()
    await vi.advanceTimersByTimeAsync(6_000)
    // On Windows the kill is via taskkill /T (whole tree); on other OSes,
    // SIGKILL. The test runs on the developer's OS, so only one of the two
    // applies.
    if (process.platform !== 'win32') expect(proc.killed).toBe(true)
    proc.sair(null, 'SIGKILL')
    await p
  })
})

describe('restart', () => {
  it('religa o executor depois da drenagem', async () => {
    const { sup, procs, spawnFn } = criar()
    sup.start()
    const p = sup.restart()
    await tick()
    procs[0]!.sair(0)
    await p
    expect(spawnFn).toHaveBeenCalledTimes(2)
  })

  it('NAO religa se o app comecou a encerrar durante a drenagem', async () => {
    // Draining takes up to 150 s; in that interval the user gets tired and
    // clicks "Sair" (quit) in the tray. Restarting at that point spawned a
    // Python that the following `app.quit()` did not kill — it was left
    // orphaned, holding the WebSocket with the same EXECUTOR_ID.
    const { sup, procs, spawnFn } = criar()
    sup.start()
    let encerrando = false
    const p = sup.restart(() => !encerrando)
    await tick()
    encerrando = true
    procs[0]!.sair(0)
    await p
    expect(spawnFn).toHaveBeenCalledTimes(1)
    expect(sup.estado).toBe('stopped')
  })

  it('NAO religa se outra parada foi pedida durante a drenagem', async () => {
    // The tray's "Parar" (stop) in the middle of a "Salvar e reiniciar" (save and
    // restart) is the most recent request: restarting would resurrect the
    // executor against it.
    const { sup, procs, spawnFn } = criar()
    sup.start()
    const p = sup.restart()
    await tick()
    void sup.stop()
    procs[0]!.sair(0)
    await p
    expect(spawnFn).toHaveBeenCalledTimes(1)
  })
})

describe('comandos', () => {
  it('escreve uma linha JSON por comando', async () => {
    const { sup, procs } = criar()
    sup.start()
    expect(sup.enviar({ cmd: 'ping', id: 'c1' })).toBe(true)
    await tick()
    expect(procs[0]!.escrito.join('')).toBe('{"cmd":"ping","id":"c1"}\n')
  })

  it('devolve false sem processo', () => {
    const { sup } = criar()
    expect(sup.enviar({ cmd: 'ping' })).toBe(false)
  })
})

describe('streams', () => {
  it('encaminha stderr como linha bruta', async () => {
    const { sup, procs } = criar()
    const linhas: Array<[string, string]> = []
    sup.on('linha', (t, o) => linhas.push([t, o]))
    sup.start()
    procs[0]!.stderr.write('14:00:00 INFO conectado\n')
    await tick()
    expect(linhas).toEqual([['14:00:00 INFO conectado', 'stderr']])
  })

  it('print() de um no vira linha bruta do stdout, nao evento', async () => {
    const { sup, procs } = criar()
    const linhas: Array<[string, string]> = []
    const eventos: unknown[] = []
    sup.on('linha', (t, o) => linhas.push([t, o]))
    sup.on('evento', (e) => eventos.push(e))
    sup.start()
    procs[0]!.stdout.write('processando...\n')
    await tick()
    expect(linhas).toEqual([['processando...', 'stdout']])
    expect(eventos).toHaveLength(0)
  })
})
