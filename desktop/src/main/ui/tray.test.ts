// desktop/src/main/ui/tray.test.ts
//
// O tray é notificado a CADA atualização do store — uma vez por segundo
// enquanto o executor roda.
//
// O caso que estes testes protegem: reconstruir o menu de contexto a 1 Hz o
// fecha na cara de quem acabou de abri-lo, e é um bug que não aparece em
// nenhum log. A guarda é `assinaturaDoTray`, que precisa ignorar tudo que o
// tray NÃO mostra (uptime, CPU, memória, contadores) e mudar exatamente quando
// o que ele mostra muda.
import { describe, expect, it, vi } from 'vitest'
import type { EstadoApp } from '../state/store.js'
import type { Snapshot } from '../../shared/events.js'

vi.mock('electron', () => ({
  Menu: { buildFromTemplate: vi.fn() },
  Tray: vi.fn(),
  app: { getVersion: () => '0.0.0' },
  nativeImage: { createEmpty: vi.fn(), createFromPath: vi.fn() },
}))
vi.mock('../paths.js', () => ({ arquivoDoApp: (...p: string[]) => p.join('/') }))
vi.mock('./windows.js', () => ({ abrirJanela: vi.fn() }))
vi.mock('./janela-web.js', () => ({ abrirJanelaWeb: vi.fn() }))
vi.mock('./autostart.js', () => ({ autostartAtivo: () => false, definirAutostart: vi.fn() }))

const { assinaturaDoTray, estadoDoIcone, resumo } = await import('./tray.js')

function snap(over: Partial<Snapshot> = {}): Snapshot {
  return {
    conn_state: 'connected', running_count: 0, uptime_s: 10,
    proc_cpu_pct: 1, proc_rss_mb: 100, total_ok: 0, queued: 0,
  } as unknown as Snapshot & typeof over as Snapshot
}

function estado(over: Partial<EstadoApp> = {}): EstadoApp {
  return {
    supervisor: 'running', detalheSupervisor: null, fase: 'running',
    passoFase: null, detalheFase: null, hello: null,
    snapshot: snap(), jobs: [], log: [],
    ...over,
  } as EstadoApp
}

// ── Ícone ────────────────────────────────────────────────────────────────────

describe('estadoDoIcone', () => {
  it('conectado e ocioso → online', () => {
    expect(estadoDoIcone(estado())).toBe('online')
  })

  it('com execução em andamento → busy', () => {
    expect(estadoDoIcone(estado({ snapshot: { ...snap(), running_count: 2 } }))).toBe('busy')
  })

  it('conectando ainda é offline', () => {
    // O ícone diz "dá para receber job agora?". Um executor que subiu mas não
    // conectou não dá.
    expect(estadoDoIcone(estado({ snapshot: { ...snap(), conn_state: 'reconnecting' } }))).toBe('offline')
  })

  it.each(['stopped', 'failed', 'draining', 'restarting'] as const)(
    'supervisor %s → offline', (supervisor) => {
      expect(estadoDoIcone(estado({ supervisor }))).toBe('offline')
    })

  it('sem estado → offline', () => {
    expect(estadoDoIcone(null)).toBe('offline')
  })
})

// ── Resumo ───────────────────────────────────────────────────────────────────

describe('resumo', () => {
  it('conta as execuções em andamento', () => {
    expect(resumo(estado({ snapshot: { ...snap(), running_count: 3 } })))
      .toContain('3 execução')
  })

  it('durante a drenagem diz quantas faltam', () => {
    // É o número que justifica a espera de até 150s; sem ele o usuário acha
    // que o app travou.
    const r = resumo(estado({ supervisor: 'draining', snapshot: { ...snap(), running_count: 2 } }))
    expect(r).toContain('2')
    expect(r.toLowerCase()).toContain('encerrando')
  })

  it('falha mostra a causa, não só "falhou"', () => {
    expect(resumo(estado({ supervisor: 'failed', detalheSupervisor: 'cert expirado' })))
      .toContain('cert expirado')
  })

  it('parado mostra o detalhe quando existe', () => {
    expect(resumo(estado({ supervisor: 'stopped', detalheSupervisor: 'Certificado descartado.' })))
      .toBe('Certificado descartado.')
  })

  it('sem conexão nomeia o estado', () => {
    expect(resumo(estado({ snapshot: { ...snap(), conn_state: 'reconnecting' } })))
      .toContain('reconnecting')
  })
})

// ── Guarda de reconstrução ───────────────────────────────────────────────────

describe('assinaturaDoTray', () => {
  it('NÃO muda com métricas que o tray não exibe', () => {
    // O caso central. Estes campos mudam a cada snapshot; se entrassem na
    // assinatura, o menu seria reconstruído uma vez por segundo.
    const a = assinaturaDoTray(estado())
    const b = assinaturaDoTray(estado({
      snapshot: { ...snap(), uptime_s: 9999, proc_cpu_pct: 87, proc_rss_mb: 512, total_ok: 42 },
    }))
    expect(a).toBe(b)
  })

  it('NÃO muda com histórico novo nem com erro no log', () => {
    // O log deixou de viajar no estado (ver store.ts); o que sobrou dele aqui é
    // o contador de erros, e nem ele pode reconstruir o menu — a bandeja não o
    // mostra.
    const a = assinaturaDoTray(estado())
    const b = assinaturaDoTray(estado({
      errosNoLog: 7,
      jobs: [{ job_id: 'j', run_id: 'r', status: 'ok', duration_s: 1, ts: 1 }],
    }))
    expect(a).toBe(b)
  })

  it('muda quando começa uma execução (ícone vira busy)', () => {
    expect(assinaturaDoTray(estado()))
      .not.toBe(assinaturaDoTray(estado({ snapshot: { ...snap(), running_count: 1 } })))
  })

  it('muda quando o supervisor muda de estado', () => {
    expect(assinaturaDoTray(estado()))
      .not.toBe(assinaturaDoTray(estado({ supervisor: 'stopped' })))
  })

  it('muda quando a conexão cai', () => {
    expect(assinaturaDoTray(estado()))
      .not.toBe(assinaturaDoTray(estado({ snapshot: { ...snap(), conn_state: 'reconnecting' } })))
  })

  it('é estável para o mesmo estado', () => {
    expect(assinaturaDoTray(estado())).toBe(assinaturaDoTray(estado()))
  })
})
