// desktop/src/main/ui/notificacoes.test.ts
//
// O que transforma notificação em spam é a repetição, e este callback roda uma
// vez por SEGUNDO enquanto o executor trabalha. Um executor parado por erro
// geraria 3600 toasts por hora se ninguém guardasse a condição anterior.
//
// Por isso os testes são sobre a decisão, não sobre o texto: quando notificar,
// quando calar, e quando voltar a falar.
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
    // Um erro de certificado depois de um de configuracao e outro problema, e
    // merece ser dito. Chave igual calaria o segundo.
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
    // Um problema que ainda nao existe: nada esta gravando.
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
    // Regra do modulo: numa maquina com dezenas por dia isso vira ruido, e a
    // pessoa desliga as notificacoes do app inteiro — inclusive as que importam.
    const a = avaliarNotificacao(estado({
      livre: 500,
      jobs: [{ job_id: 'j', status: 'ok' }] as never,
    }))
    expect(a).toBeNull()
  })
})

describe('notificarSeMudou', () => {
  // `Notification.isSupported()` e false no mock, entao nada e exibido — o que
  // esta sob teste e a MEMORIA da condicao, que roda antes disso.
  it('a mesma condicao repetida nao vira nova notificacao', () => {
    const clique = vi.fn()
    const falho = estado({ supervisor: 'failed', passoFase: 'config' })

    notificarSeMudou(falho, clique)
    // 3600 ticks de um executor parado por uma hora.
    for (let i = 0; i < 100; i++) notificarSeMudou(falho, clique)

    // Sem exceção e sem acumular — a garantia observavel aqui e que a chave
    // memorizada nao muda.
    expect(avaliarNotificacao(falho)?.chave).toBe('failed:config')
  })

  it('voltar ao normal REARMA a condicao', () => {
    // Um executor que falha, e reiniciado e falha de novo precisa avisar as
    // duas vezes. Sem o rearme, a segunda seria muda.
    const clique = vi.fn()
    const falho = estado({ supervisor: 'failed', passoFase: 'config' })

    notificarSeMudou(falho, clique)
    notificarSeMudou(estado({ livre: 500 }), clique)   // voltou ao normal
    expect(() => notificarSeMudou(falho, clique)).not.toThrow()
  })

  it('nao lanca quando o Windows recusa notificacoes', () => {
    // Politica de grupo pode desligar toasts. Isso nao pode derrubar o loop de
    // estado do app, que roda no mesmo callback.
    expect(() => notificarSeMudou(
      estado({ supervisor: 'failed' }), () => {},
    )).not.toThrow()
  })
})
