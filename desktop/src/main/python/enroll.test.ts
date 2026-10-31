// desktop/src/main/python/enroll.test.ts
//
// The one-shot `python -m executor enroll`. The spawn is mocked: what is
// tested here is how the app talks to that process, not the enrollment itself
// (that one is covered in executor/).
import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { spawnMock } = vi.hoisted(() => ({ spawnMock: vi.fn() }))

vi.mock('node:child_process', () => ({ spawn: spawnMock }))

// `paths.js` imports `electron` at the top, which does not exist outside the
// main process. Nothing here depends on the real paths.
vi.mock('../paths.js', () => ({
  ARTIFACTS_DIR_PADRAO: 'C:/artefatos',
  CERT_DIR: 'C:/certs',
  PYTHON_EXE: 'python',
  RESOURCES: '.',
  ambienteDoSpawn: (env: unknown) => env,
  envDoExecutor: () => ({}),
}))

const { enrolar } = await import('./enroll.js')

class FakeProc extends EventEmitter {
  stdout = new PassThrough()
  stderr = new PassThrough()
  stdin = new PassThrough()
  killed = false
  kill(): boolean { this.killed = true; return true }
}

const tick = () => new Promise((r) => setImmediate(r))

function nextProcess(): FakeProc {
  const p = new FakeProc()
  spawnMock.mockReturnValueOnce(p)
  return p
}

beforeEach(() => { spawnMock.mockReset() })

describe('enrolar', () => {
  it('stdin quebrado não derruba o main e explica o motivo', async () => {
    // Python died at startup (or never started) and the OTP write failed
    // asynchronously. Unhandled, that 'error' was an uncaught exception in main.
    const p = nextProcess()
    const r = enrolar({ executorId: 'abc', otp: '123' })
    p.stdin.destroy(new Error('write EPIPE'))
    await tick()
    p.emit('close', 1)

    const res = await r
    expect(res.ok).toBe(false)
    if (!res.ok) {
      expect(res.codigo).toBe('saida_invalida')
      expect(res.erro).toContain('EPIPE')
    }
  })
})

describe('enrolar concorrente', () => {
  const RESULTADO_OK = {
    ok: true, executor_id: 'abc', serial: null, fingerprint: null, expires_at: null,
    cert_dir: 'C:/certs', env_path: 'C:/.env',
  }

  async function concluir(p: FakeProc): Promise<void> {
    p.stdout.write(JSON.stringify(RESULTADO_OK) + '\n')
    await tick()
    p.emit('close', 0)
  }

  it('um segundo pedido com o primeiro em andamento é recusado, sem novo processo', async () => {
    // Two enroll processes replace cert.pem and key.pem file by file; run
    // together, the pair on disk could come from different runs.
    const p = nextProcess()
    const primeiro = enrolar({ executorId: 'abc', otp: '111' })
    const segundo = await enrolar({ executorId: 'abc', otp: '222' })

    expect(spawnMock).toHaveBeenCalledTimes(1)
    // Not `enroll_recusado`: the server refused nothing, and the OTP may still be good.
    expect(segundo).toMatchObject({ ok: false, codigo: 'enroll_em_andamento' })

    await concluir(p)
    expect(await primeiro).toMatchObject({ ok: true })
  })

  it('terminado o primeiro, o próximo pedido roda', async () => {
    const p1 = nextProcess()
    const primeiro = enrolar({ executorId: 'abc', otp: '111' })
    await concluir(p1)
    await primeiro

    const p2 = nextProcess()
    const segundo = enrolar({ executorId: 'abc', otp: '222' })
    await concluir(p2)
    expect(await segundo).toMatchObject({ ok: true })
    expect(spawnMock).toHaveBeenCalledTimes(2)
  })
})
