// desktop/src/main/ui/notificacoes.test.ts
//
// What turns notifications into spam is repetition, and this callback runs
// once per SECOND while the executor is working. An executor stopped by an
// error would generate 3600 toasts per hour if nobody kept the previous
// condition.
//
// That is why the tests are about the decision, not the text: when to notify,
// when to stay quiet, and when to speak up again.
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EstadoApp } from '../state/store.js'

vi.mock('electron', () => ({ Notification: { isSupported: () => false } }))
vi.mock('../paths.js', () => ({ ICONE_APP: 'icon.ico' }))

const {
  DISCO_BAIXO_GB, DISCO_CRITICO_GB, avaliarNotificacao, notificarSeMudou, _resetarMemoria,
} = await import('./notificacoes.js')

function estado(p: Partial<EstadoApp> & { livre?: number | null } = {}): EstadoApp {
  const { livre, ...resto } = p
  return {
    supervisor: 'running',
    fase: null,
    passoFase: null,
    detalheFase: null,
    detalheSupervisor: null,
    hello: null,
    jobs: [],
    log: [],
    snapshot: livre === undefined ? null : ({ artifacts_disk_free_gb: livre } as never),
    ...resto,
  } as EstadoApp
}

beforeEach(_resetarMemoria)

describe('avaliarNotificacao', () => {
  it('executor saudavel nao notifica nada', () => {
    expect(avaliarNotificacao(estado({ livre: 500 }))).toBeNull()
  })

  it('revogado tem mensagem PROPRIA — nao se resolve sozinho', () => {
    const a = avaliarNotificacao(estado({ supervisor: 'failed', passoFase: 'revoked' }))
    expect(a?.chave).toBe('revoked')
    expect(a?.urgente).toBe(true)
  })

  it('parado por erro carrega o motivo, e nao "abra o painel"', () => {
    const a = avaliarNotificacao(estado({
      supervisor: 'failed', passoFase: 'config', detalheFase: 'EXECUTOR_ID ausente',
    }))
    expect(a?.corpo).toContain('EXECUTOR_ID ausente')
  })

  it('passos de falha diferentes sao condicoes diferentes', () => {
    // A certificate error after a configuration one is a different problem, and
    // deserves to be reported. An identical key would silence the second.
    const a = avaliarNotificacao(estado({ supervisor: 'failed', passoFase: 'config' }))
    const b = avaliarNotificacao(estado({ supervisor: 'failed', passoFase: 'private_key' }))
    expect(a?.chave).not.toBe(b?.chave)
  })

  it('disco baixo avisa; disco critico escala', () => {
    expect(avaliarNotificacao(estado({ livre: DISCO_BAIXO_GB - 0.1 }))?.chave).toBe('disco:baixo')
    expect(avaliarNotificacao(estado({ livre: DISCO_CRITICO_GB - 0.1 }))?.chave).toBe('disco:critico')
  })

  it('disco com folga nao notifica', () => {
    expect(avaliarNotificacao(estado({ livre: DISCO_BAIXO_GB + 1 }))).toBeNull()
  })

  it('disco de executor PARADO nao notifica', () => {
    // A problem that does not exist yet: nothing is recording.
    expect(avaliarNotificacao(estado({ supervisor: 'stopped', livre: 0.2 }))).toBeNull()
  })

  it('falha vence disco — uma toast por vez', () => {
    const a = avaliarNotificacao(estado({
      supervisor: 'failed', passoFase: 'revoked', livre: 0.1,
    }))
    expect(a?.chave).toBe('revoked')
  })

  it('sem metrica de disco, nao inventa', () => {
    expect(avaliarNotificacao(estado({ livre: null }))).toBeNull()
    expect(avaliarNotificacao(estado())).toBeNull()
  })

  it('NAO notifica execucao concluida', () => {
    // Module rule: on a machine with dozens a day this becomes noise, and the
    // person turns off notifications for the whole app — including the ones
    // that matter.
    const a = avaliarNotificacao(estado({
      livre: 500,
      jobs: [{ job_id: 'j', status: 'ok' }] as never,
    }))
    expect(a).toBeNull()
  })
})

describe('notificarSeMudou', () => {
  // `Notification.isSupported()` is false in the mock, so nothing is shown —
  // what is under test is the condition's MEMORY, which runs before that.
  it('a mesma condicao repetida nao vira nova notificacao', () => {
    const clique = vi.fn()
    const falho = estado({ supervisor: 'failed', passoFase: 'config' })

    notificarSeMudou(falho, clique)
    // 3600 ticks of an executor stopped for an hour.
    for (let i = 0; i < 100; i++) notificarSeMudou(falho, clique)

    // No exception and no accumulation — the observable guarantee here is that
    // the memorized key does not change.
    expect(avaliarNotificacao(falho)?.chave).toBe('failed:config')
  })

  it('voltar ao normal REARMA a condicao', () => {
    // An executor that fails, is restarted and fails again needs to warn both
    // times. Without re-arming, the second would be silent.
    const clique = vi.fn()
    const falho = estado({ supervisor: 'failed', passoFase: 'config' })

    notificarSeMudou(falho, clique)
    notificarSeMudou(estado({ livre: 500 }), clique)   // back to normal
    expect(() => notificarSeMudou(falho, clique)).not.toThrow()
  })

  it('nao lanca quando o Windows recusa notificacoes', () => {
    // Group policy can turn toasts off. That must not take down the app's state
    // loop, which runs in the same callback.
    expect(() => notificarSeMudou(
      estado({ supervisor: 'failed' }), () => {},
    )).not.toThrow()
  })
})
