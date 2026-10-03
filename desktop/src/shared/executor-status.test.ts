// desktop/src/shared/executor-status.test.ts
//
// `derivarStatus` is the choke point of the read-only bridge: everything the
// web UI can read comes out of here. The tests pin down the derivation of the
// four states and the dedupe — and, by extension, what does NOT influence the
// status (resource metrics).
import { describe, expect, it } from 'vitest'
import type { Snapshot } from './events.js'
import type { AppState } from '../main/state/store.js'
import { assinaturaStatus, derivarStatus } from './executor-status.js'

type StateInput = Pick<AppState, 'supervisor' | 'snapshot'>

function snap(over: Partial<Snapshot> = {}): Snapshot {
  return {
    conn_state: 'connected', running_count: 0, max_concurrent: 4,
    queued: 0, uptime_s: 10, proc_cpu_pct: 1, proc_rss_mb: 100,
    ...over,
  } as unknown as Snapshot
}

const LINKED = { configurado: true, executorId: 'exec-123' }

describe('derivarStatus', () => {
  it('running + conectado + ocioso → online', () => {
    const s = derivarStatus({ supervisor: 'running', snapshot: snap() }, LINKED)
    expect(s.estado).toBe('online')
    expect(s.emExecucao).toBe(0)
    expect(s.capacidade).toBe(4)
    expect(s.executorId).toBe('exec-123')
    expect(s.vinculado).toBe(true)
  })

  it('com execução em andamento → ocupado', () => {
    const s = derivarStatus({ supervisor: 'running', snapshot: snap({ running_count: 2 }) }, LINKED)
    expect(s.estado).toBe('ocupado')
    expect(s.emExecucao).toBe(2)
  })

  it('supervisor parado → offline, sem contar execução', () => {
    const s = derivarStatus({ supervisor: 'stopped', snapshot: null }, LINKED)
    expect(s.estado).toBe('offline')
    expect(s.emExecucao).toBe(0)
  })

  it('running mas sem conexão → offline', () => {
    // The status says "can it take a job right now?". Started but not connected: no.
    const s = derivarStatus({ supervisor: 'running', snapshot: snap({ conn_state: 'reconnecting' }) }, LINKED)
    expect(s.estado).toBe('offline')
  })

  it('offline não anuncia execução, mesmo com snapshot antigo dizendo o contrário', () => {
    const s = derivarStatus(
      { supervisor: 'draining', snapshot: snap({ running_count: 3 }) },
      LINKED,
    )
    expect(s.estado).toBe('offline')
    expect(s.emExecucao).toBe(0)
  })

  it('sem enrollment → sem-vinculo (vence os demais)', () => {
    const s = derivarStatus(
      { supervisor: 'running', snapshot: snap({ running_count: 1 }) },
      { configurado: false, executorId: null },
    )
    expect(s.estado).toBe('sem-vinculo')
    expect(s.vinculado).toBe(false)
    expect(s.emExecucao).toBe(0)
  })
})

describe('assinaturaStatus', () => {
  const base: StateInput = { supervisor: 'running', snapshot: snap() }

  it('NÃO muda com métricas que o status não expõe', () => {
    const a = assinaturaStatus(derivarStatus(base, LINKED))
    const b = assinaturaStatus(derivarStatus(
      { supervisor: 'running', snapshot: snap({ proc_cpu_pct: 99, proc_rss_mb: 999, uptime_s: 9999 }) },
      LINKED,
    ))
    expect(a).toBe(b)
  })

  it('muda quando começa uma execução', () => {
    const a = assinaturaStatus(derivarStatus(base, LINKED))
    const b = assinaturaStatus(derivarStatus({ supervisor: 'running', snapshot: snap({ running_count: 1 }) }, LINKED))
    expect(a).not.toBe(b)
  })

  it('muda quando cai a conexão', () => {
    const a = assinaturaStatus(derivarStatus(base, LINKED))
    const b = assinaturaStatus(derivarStatus({ supervisor: 'running', snapshot: snap({ conn_state: 'offline' }) }, LINKED))
    expect(a).not.toBe(b)
  })

  it('é estável para o mesmo estado', () => {
    expect(assinaturaStatus(derivarStatus(base, LINKED)))
      .toBe(assinaturaStatus(derivarStatus(base, LINKED)))
  })

  it('muda quando a capacidade (max_concurrent) muda', () => {
    // `capacidade` is part of the key: if it were left out, a push with a new
    // capacity would be deduplicated and the web UI would never receive it.
    // Other fields equal.
    const a = assinaturaStatus(derivarStatus({ supervisor: 'running', snapshot: snap({ max_concurrent: 4 }) }, LINKED))
    const b = assinaturaStatus(derivarStatus({ supervisor: 'running', snapshot: snap({ max_concurrent: 8 }) }, LINKED))
    expect(a).not.toBe(b)
  })
})
