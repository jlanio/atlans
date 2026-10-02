// desktop/src/renderer/components/Execucoes.test.tsx
//
// A lista de execuções formata a duração com a MESMA função do Painel. A cópia
// local que ela tinha arredondava DEPOIS de escolher a faixa: 59.97 s aparecia
// como "60.0s" e 3599.7 s como "59m 60s" — valores que não existem no relógio,
// e que o Painel já não mostrava.
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { JobHistorico } from '../../main/state/store.js'
import type { Snapshot } from '../../shared/events.js'
import { Execucoes } from './Execucoes.js'

function concluido(duration_s: number, i: number): JobHistorico {
  return { job_id: `job-${i}`, run_id: null, status: 'ok', duration_s, ts: 1_700_000_000 + i }
}

function rodando(elapsed_s: number): Snapshot {
  return {
    running: [{ job_id: 'job-vivo', run_id: null, elapsed_s, node: 'buffer_1', nodes_done: 1, nodes_total: 3 }],
  } as unknown as Snapshot
}

/** Os textos de duração da tela, na ordem em que aparecem. */
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
