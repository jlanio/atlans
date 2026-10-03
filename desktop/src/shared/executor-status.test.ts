// desktop/src/shared/executor-status.test.ts
//
// `derivarStatus` is the choke point of the read-only bridge: everything the
// web UI can read comes out of here. The tests pin down the derivation of the
// four states and the dedupe — and, by extension, what does NOT influence the
// status (resource metrics).
import { describe, expect, it } from 'vitest'
import type { Snapshot } from './events.js'
import type { EstadoApp } from '../main/state/store.js'
import { assinaturaStatus, derivarStatus } from './executor-status.js'

type EntradaEstado = Pick<EstadoApp, 'supervisor' | 'snapshot'>

function snap(over: Partial<Snapshot> = {}): Snapshot {
  return {
    conn_state: 'connected', running_count: 0, max_concurrent: 4,
    queued: 0, uptime_s: 10, proc_cpu_pct: 1, proc_rss_mb: 100,
    ...over,
  } as unknown as Snapshot
}

const VINCULADO = { configurado: true, executorId: 'exec-123' }

describe('derivarStatus', () => {
  it('running + conectado + ocioso → online', () => {
    const s = derivarStatus({ supervisor: 'running', snapshot: snap() }, VINCULADO)
    expect(s.estado).toBe('online')
    expect(s.emExecucao).toBe(0)
    expect(s.capacidade).toBe(4)
    expect(s.executorId).toBe('exec-123')
    expect(s.vinculado).toBe(true)
  })

  it('com execução em andamento → ocupado', () => {
    const s = derivarStatus({ supervisor: 'running', snapshot: snap({ running_count: 2 }) }, VINCULADO)
    expect(s.estado).toBe('ocupado')
    expect(s.emExecucao).toBe(2)
  })

  it('supervisor parado → offline, sem contar execução', () => {
    const s = derivarStatus({ supervisor: 'stopped', snapshot: null }, VINCULADO)
    expect(s.estado).toBe('offline')
    expect(s.emExecucao).toBe(0)
  })

  it('running mas sem conexão → offline', () => {
    // The status says "can it take a job right now?". Started but not connected: no.
    const s = derivarStatus({ supervisor: 'running', snapshot: snap({ conn_state: 'reconnecting' }) }, VINCULADO)
    expect(s.estado).toBe('offline')
  })

  it('offline não anuncia execução, mesmo com snapshot antigo dizendo o contrário', () => {
    const s = derivarStatus(
      { supervisor: 'draining', snapshot: snap({ running_count: 3 }) },
      VINCULADO,
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
  const base: EntradaEstado = { supervisor: 'running', snapshot: snap() }

  it('NÃO muda com métricas que o status não expõe', () => {
    const a = assinaturaStatus(derivarStatus(base, VINCULADO))
    const b = assinaturaStatus(derivarStatus(
      { supervisor: 'running', snapshot: snap({ proc_cpu_pct: 99, proc_rss_mb: 999, uptime_s: 9999 }) },
      VINCULADO,
    ))
    expect(a).toBe(b)
  })

  it('muda quando começa uma execução', () => {
    const a = assinaturaStatus(derivarStatus(base, VINCULADO))
    const b = assinaturaStatus(derivarStatus({ supervisor: 'running', snapshot: snap({ running_count: 1 }) }, VINCULADO))
    expect(a).not.toBe(b)
  })

  it('muda quando cai a conexão', () => {
    const a = assinaturaStatus(derivarStatus(base, VINCULADO))
    const b = assinaturaStatus(derivarStatus({ supervisor: 'running', snapshot: snap({ conn_state: 'offline' }) }, VINCULADO))
    expect(a).not.toBe(b)
  })

  it('é estável para o mesmo estado', () => {
    expect(assinaturaStatus(derivarStatus(base, VINCULADO)))
      .toBe(assinaturaStatus(derivarStatus(base, VINCULADO)))
  })

  it('muda quando a capacidade (max_concurrent) muda', () => {
    // `capacidade` is part of the key: if it were left out, a push with a new
    // capacity would be deduplicated and the web UI would never receive it.
    // Other fields equal.
    const a = assinaturaStatus(derivarStatus({ supervisor: 'running', snapshot: snap({ max_concurrent: 4 }) }, VINCULADO))
    const b = assinaturaStatus(derivarStatus({ supervisor: 'running', snapshot: snap({ max_concurrent: 8 }) }, VINCULADO))
    expect(a).not.toBe(b)
  })
})
