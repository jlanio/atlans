// desktop/src/main/python/supervisor.test.ts
//
// Politica de reinicio e encerramento. O spawn e injetado, entao nada aqui
// depende de Python instalado.
import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { PythonSupervisor, type EstadoSupervisor } from './supervisor.js'

class ProcFalso extends EventEmitter {
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

  /** Simula a saida do processo. */
  sair(codigo: number | null, sinal: NodeJS.Signals | null = null): void {
    this.emit('exit', codigo, sinal)
  }

  emitir(obj: unknown): void {
    this.stdout.write(JSON.stringify(obj) + '\n')
  }
}

function criar() {
  const procs: ProcFalso[] = []
  const spawnFn = vi.fn(() => {
    const p = new ProcFalso()
    procs.push(p)
    return p
  })
  const estados: Array<[EstadoSupervisor, string | undefined]> = []
  const sup = new PythonSupervisor({
    pythonExe: 'python',
    cwd: '.',
    env: {},
    spawnFn: spawnFn as never,
  })
  sup.on('estado', (e, d) => estados.push([e, d]))
  return { sup, procs, estados, spawnFn }
}

/** Espera o stdout ser drenado (PassThrough entrega no proximo tick). */
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
    // Dois executores com o mesmo EXECUTOR_ID dariam conexoes duplicadas no
    // servidor.
    const { sup, spawnFn } = criar()
    sup.start()
    sup.start()
    expect(spawnFn).toHaveBeenCalledTimes(1)
  })

  it('falha de spawn nao entra em loop de retry', async () => {
    // python.exe ausente ou sem permissao nao se resolve sozinho.
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
    // Religar para sempre esconderia a causa e queimaria CPU.
    //
    // O avanco e `advanceTimersToNextTimerAsync`, e nao um valor fixo: cada
    // tentativa espera o proprio backoff (2s, 4s, 8s… ate 60s, com jitter), e
    // um numero fixo grande o bastante para a ultima faria a JANELA deslizar,
    // zerando o contador — o teste passaria a medir outra coisa.
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
    // Um executor que roda bem por minutos e entao cai nao esta em loop: e uma
    // falha intermitente, e desistir dela deixaria a maquina do usuario sem
    // executor ate alguem reparar.
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
    // `config_changed` faz o executor sair com 1 depois de drenar. Contar isso
    // como falha derrubaria o executor de vez num servidor que reatribui
    // workspaces algumas vezes seguidas.
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
    // Cert expirado, chave do servidor indisponivel: causa persistente, o
    // usuario precisa agir. Tentar de novo so gastaria tempo.
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
    // No Windows nao ha SIGTERM: kill() vira TerminateProcess, morte imediata,
    // com jobs perdidos e resultados nunca confirmados.
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
    // O segundo clique chegava antes de o estado `draining` pintar a tela e
    // armava um SEGUNDO teto de graca, sobrescrevendo o handle do primeiro sem
    // limpa-lo. O orfao sobrevivia a saida do processo e, no fim do prazo,
    // matava a frio o executor SEGUINTE, no meio de um job.
    const { sup, procs, spawnFn } = criar()
    const linhas: string[] = []
    sup.on('linha', (t) => linhas.push(t))
    sup.start()

    const p1 = sup.stop(5_000)
    const p2 = sup.stop(5_000)
    expect(p2).toBe(p1)                       // idempotente: a MESMA parada
    await tick()
    // Um unico `shutdown` no stdin — o Python ja estava drenando.
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
    // `refazerEnrollment` para com 10 s porque precisa apagar os PEMs. Herdar
    // os 150 s de um "Parar" anterior deixaria o usuario esperando por uma
    // drenagem que ele ja abreviou.
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
    // No Windows a morte e por taskkill /T (arvore inteira); em outros SOs,
    // SIGKILL. O teste roda no SO do desenvolvedor, entao so um dos dois vale.
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
    // A drenagem leva ate 150 s; nesse intervalo o usuario cansa e clica "Sair"
    // no tray. Religar ali spawnava um Python que o `app.quit()` seguinte nao
    // matava — ele ficava orfao segurando o WebSocket com o mesmo EXECUTOR_ID.
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
    // O "Parar" do tray no meio de um "Salvar e reiniciar" e o pedido mais
    // recente: religar seria ressuscitar o executor contra ele.
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
