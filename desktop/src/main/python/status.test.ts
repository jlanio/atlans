// desktop/src/main/python/status.test.ts
//
// O cache de sessao da consulta de status. O que se testa aqui e a JANELA: a
// consulta spawna um Python e leva ate 30 s, e nesse intervalo o vinculo pode
// ser refeito ou o usuario pode pedir "Atualizar". Servir dado do vinculo
// ANTIGO faz a aba GeoSync oferecer um workspace que este certificado nao
// alcanca mais — e grava-lo em geosync.json desliga a sincronizacao em silencio.
import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { spawnMock } = vi.hoisted(() => ({ spawnMock: vi.fn() }))

vi.mock('node:child_process', () => ({ spawn: spawnMock }))

// `paths.js` importa `electron` no topo (e chama `app.setName`), que nao existe
// fora do processo principal. Nada aqui depende dos caminhos reais.
vi.mock('../paths.js', () => ({
  ARTIFACTS_DIR_PADRAO: 'C:/artefatos',
  PYTHON_EXE: 'python',
  RESOURCES: '.',
  ambienteDoSpawn: (env: unknown) => env,
  envDoExecutor: () => ({}),
}))

const { consultarStatusCacheado, invalidarStatus } = await import('./status.js')

class ProcFalso extends EventEmitter {
  stdout = new PassThrough()
  stderr = new PassThrough()
  killed = false
  kill(): boolean { this.killed = true; return true }
}

const tick = () => new Promise((r) => setImmediate(r))

/** Enfileira o proximo `spawn` e devolve o processo falso. */
function proximoProcesso(): ProcFalso {
  const p = new ProcFalso()
  spawnMock.mockReturnValueOnce(p)
  return p
}

/** Escreve a resposta JSON e encerra o processo, como o Python faria. */
async function responder(p: ProcFalso, executorId: string): Promise<void> {
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
  invalidarStatus()   // o cache e estado de modulo: zera entre os testes
})

describe('cache', () => {
  it('guarda o sucesso e nao spawna de novo', async () => {
    const p1 = proximoProcesso()
    const consulta = consultarStatusCacheado()
    await responder(p1, 'a')
    await expect(consulta).resolves.toMatchObject({ executor_id: 'a' })

    await expect(consultarStatusCacheado()).resolves.toMatchObject({ executor_id: 'a' })
    expect(spawnMock).toHaveBeenCalledTimes(1)
  })

  it('dois pedidos simultaneos compartilham um unico spawn', async () => {
    const p1 = proximoProcesso()
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
    // Enrollment refeito no meio de uma consulta: o certificado que a originou
    // ja nao vale, e o `.then` dela repovoava o cache com o vinculo antigo.
    const velho = proximoProcesso()
    const consulta = consultarStatusCacheado()
    invalidarStatus()
    await responder(velho, 'velho')
    await expect(consulta).resolves.toMatchObject({ executor_id: 'velho' })

    // O prefetch do executor NOVO nao pode herdar a consulta invalidada.
    const novo = proximoProcesso()
    const segunda = consultarStatusCacheado()
    expect(spawnMock).toHaveBeenCalledTimes(2)
    await responder(novo, 'novo')
    await expect(segunda).resolves.toMatchObject({ executor_id: 'novo' })

    await expect(consultarStatusCacheado()).resolves.toMatchObject({ executor_id: 'novo' })
    expect(spawnMock).toHaveBeenCalledTimes(2)
  })

  it('consulta vencida que responde depois nao sobrescreve o cache novo', async () => {
    const velho = proximoProcesso()
    const vencida = consultarStatusCacheado()
    invalidarStatus()

    const novo = proximoProcesso()
    const atual = consultarStatusCacheado()
    await responder(novo, 'novo')
    await responder(velho, 'velho')          // chega por ultimo, do vinculo antigo
    await expect(atual).resolves.toMatchObject({ executor_id: 'novo' })
    await expect(vencida).resolves.toMatchObject({ executor_id: 'velho' })

    await expect(consultarStatusCacheado()).resolves.toMatchObject({ executor_id: 'novo' })
    expect(spawnMock).toHaveBeenCalledTimes(2)
  })
})

describe('forcar', () => {
  it('"Atualizar" reconsulta em vez de devolver a consulta em voo', async () => {
    // A consulta em voo pode ter comecado ANTES da mudanca que motivou o
    // clique. Devolve-la fazia o spinner girar e a lista velha continuar.
    const antigo = proximoProcesso()
    const primeira = consultarStatusCacheado()
    const recente = proximoProcesso()
    const forcada = consultarStatusCacheado(true)
    expect(spawnMock).toHaveBeenCalledTimes(2)

    await responder(recente, 'novo')
    await responder(antigo, 'velho')
    await expect(forcada).resolves.toMatchObject({ executor_id: 'novo' })
    await expect(primeira).resolves.toMatchObject({ executor_id: 'velho' })

    // O cache fica com a consulta mais recente, nao com a que respondeu por ultimo.
    await expect(consultarStatusCacheado()).resolves.toMatchObject({ executor_id: 'novo' })
  })
})

describe('falha do spawn', () => {
  it('erro sincrono vira resultado e libera a consulta em voo', async () => {
    // Sem o catch, a rejeicao vazava para o `invoke` do renderer e `emVoo`
    // ficava preso para sempre — a tela congelava em "carregando".
    spawnMock.mockImplementationOnce(() => { throw new Error('ENOENT') })
    await expect(consultarStatusCacheado()).resolves.toMatchObject({
      ok: false, codigo: 'falha',
    })

    const p = proximoProcesso()
    const segunda = consultarStatusCacheado()
    expect(spawnMock).toHaveBeenCalledTimes(2)
    await responder(p, 'a')
    await expect(segunda).resolves.toMatchObject({ executor_id: 'a' })
  })
})
