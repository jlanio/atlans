// desktop/src/main/python/status.test.ts
//
// The session cache of the status query. What is tested here is the WINDOW:
// the query spawns a Python and takes up to 30 s, and in that interval the
// link may be redone or the user may ask to "Atualizar" (refresh). Serving data
// from the OLD link makes the GeoSync tab offer a workspace this certificate no
// longer reaches — and writing it to geosync.json silently turns sync off.
import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { spawnMock } = vi.hoisted(() => ({ spawnMock: vi.fn() }))

vi.mock('node:child_process', () => ({ spawn: spawnMock }))

// `paths.js` imports `electron` at the top (and calls `app.setName`), which
// does not exist outside the main process. Nothing here depends on the real
// paths.
vi.mock('../paths.js', () => ({
  ARTIFACTS_DIR_PADRAO: 'C:/artefatos',
  PYTHON_EXE: 'python',
  RESOURCES: '.',
  ambienteDoSpawn: (env: unknown) => env,
  envDoExecutor: () => ({}),
}))

const { consultarStatusCacheado, invalidarStatus } = await import('./status.js')

class FakeProc extends EventEmitter {
  stdout = new PassThrough()
  stderr = new PassThrough()
  killed = false
  kill(): boolean { this.killed = true; return true }
}

const tick = () => new Promise((r) => setImmediate(r))

/** Enfileira o proximo `spawn` e devolve o processo falso. */
function nextProcess(): FakeProc {
  const p = new FakeProc()
  spawnMock.mockReturnValueOnce(p)
  return p
}

/** Escreve a resposta JSON e encerra o processo, como o Python faria. */
async function responder(p: FakeProc, executorId: string): Promise<void> {
  p.stdout.write(JSON.stringify({
    ok: true, executor_id: executorId, server_url: 'https://x', status: 'active',
    workspaces: [{ id_hash: executorId }],
  }) + '\n')
  await tick()
  p.emit('close', 0)
  await tick()
}

beforeEach(() => {
  spawnMock.mockReset()
  invalidarStatus()   // the cache is module state: reset it between tests
})

describe('cache', () => {
  it('guarda o sucesso e nao spawna de novo', async () => {
    const p1 = nextProcess()
    const consulta = consultarStatusCacheado()
    await responder(p1, 'a')
    await expect(consulta).resolves.toMatchObject({ executor_id: 'a' })

    await expect(consultarStatusCacheado()).resolves.toMatchObject({ executor_id: 'a' })
    expect(spawnMock).toHaveBeenCalledTimes(1)
  })

  it('dois pedidos simultaneos compartilham um unico spawn', async () => {
    const p1 = nextProcess()
    const a = consultarStatusCacheado()
    const b = consultarStatusCacheado()
    expect(spawnMock).toHaveBeenCalledTimes(1)
    await responder(p1, 'a')
    await expect(a).resolves.toMatchObject({ executor_id: 'a' })
    await expect(b).resolves.toMatchObject({ executor_id: 'a' })
  })
})

describe('invalidarStatus', () => {
  it('descarta o resultado da consulta que ficou em voo', async () => {
    // Enrollment redone in the middle of a query: the certificate that started it
    // is no longer valid, and its `.then` used to repopulate the cache with the
    // old link.
    const velho = nextProcess()
    const consulta = consultarStatusCacheado()
    invalidarStatus()
    await responder(velho, 'velho')
    await expect(consulta).resolves.toMatchObject({ executor_id: 'velho' })

    // The prefetch of the NEW executor must not inherit the invalidated query.
    const novo = nextProcess()
    const segunda = consultarStatusCacheado()
    expect(spawnMock).toHaveBeenCalledTimes(2)
    await responder(novo, 'novo')
    await expect(segunda).resolves.toMatchObject({ executor_id: 'novo' })

    await expect(consultarStatusCacheado()).resolves.toMatchObject({ executor_id: 'novo' })
    expect(spawnMock).toHaveBeenCalledTimes(2)
  })

  it('consulta vencida que responde depois nao sobrescreve o cache novo', async () => {
    const velho = nextProcess()
    const vencida = consultarStatusCacheado()
    invalidarStatus()

    const novo = nextProcess()
    const atual = consultarStatusCacheado()
    await responder(novo, 'novo')
    await responder(velho, 'velho')          // arrives last, from the old link
    await expect(atual).resolves.toMatchObject({ executor_id: 'novo' })
    await expect(vencida).resolves.toMatchObject({ executor_id: 'velho' })

    await expect(consultarStatusCacheado()).resolves.toMatchObject({ executor_id: 'novo' })
    expect(spawnMock).toHaveBeenCalledTimes(2)
  })
})

describe('forcar', () => {
  it('"Atualizar" reconsulta em vez de devolver a consulta em voo', async () => {
    // The in-flight query may have started BEFORE the change that prompted the
    // click. Returning it made the spinner spin and the stale list stay.
    const antigo = nextProcess()
    const primeira = consultarStatusCacheado()
    const recente = nextProcess()
    const forced = consultarStatusCacheado(true)
    expect(spawnMock).toHaveBeenCalledTimes(2)

    await responder(recente, 'novo')
    await responder(antigo, 'velho')
    await expect(forced).resolves.toMatchObject({ executor_id: 'novo' })
    await expect(primeira).resolves.toMatchObject({ executor_id: 'velho' })

    // The cache keeps the most recent query, not the one that answered last.
    await expect(consultarStatusCacheado()).resolves.toMatchObject({ executor_id: 'novo' })
  })
})

describe('falha do spawn', () => {
  it('erro sincrono vira resultado e libera a consulta em voo', async () => {
    // Without the catch, the rejection leaked to the renderer's `invoke` and
    // `emVoo` stayed stuck forever — the screen froze on "carregando" (loading).
    spawnMock.mockImplementationOnce(() => { throw new Error('ENOENT') })
    await expect(consultarStatusCacheado()).resolves.toMatchObject({
      ok: false, codigo: 'falha',
    })

    const p = nextProcess()
    const segunda = consultarStatusCacheado()
    expect(spawnMock).toHaveBeenCalledTimes(2)
    await responder(p, 'a')
    await expect(segunda).resolves.toMatchObject({ executor_id: 'a' })
  })
})
