// desktop/src/renderer/components/Execucoes.test.tsx
//
// The run list formats the duration with the SAME function as the Painel. The
// local copy it had rounded AFTER choosing the range: 59.97 s appeared as
// "60.0s" and 3599.7 s as "59m 60s" — values that do not exist on a clock, and
// that the Painel no longer showed.
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { HistoryJob } from '../../main/state/store.js'
import type { Snapshot } from '../../shared/events.js'
import { Execucoes } from './Execucoes.js'

function concluido(duration_s: number, i: number): HistoryJob {
  return { job_id: `job-${i}`, run_id: null, status: 'ok', duration_s, ts: 1_700_000_000 + i }
}

function rodando(elapsed_s: number): Snapshot {
  return {
    running: [{ job_id: 'job-vivo', run_id: null, elapsed_s, node: 'buffer_1', nodes_done: 1, nodes_total: 3 }],
  } as unknown as Snapshot
}

/** The screen's duration texts, in the order they appear. */
function duracoes(html: string): string[] {
  return [...html.matchAll(/>(\d+(?:\.\d)?s|\d+m \d+s|\d+h \d+m)</g)].map((m) => m[1]!)
}

describe('Execucoes — duração', () => {
  it('o histórico mostra 1m 0s e 1h 0m, e não 60.0s e 59m 60s', () => {
    const html = renderToStaticMarkup(
      <Execucoes snapshot={null} jobs={[concluido(59.97, 1), concluido(3599.7, 2)]} />,
    )
    expect(duracoes(html)).toEqual(['1m 0s', '1h 0m'])
  })

  it('o job em andamento usa a mesma formatação', () => {
    const html = renderToStaticMarkup(<Execucoes snapshot={rodando(59.97)} jobs={[]} />)
    expect(duracoes(html)).toEqual(['1m 0s'])
  })
})
