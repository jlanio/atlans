// desktop/src/renderer/components/Execucoes.tsx
//
// Execuções em andamento e histórico.
//
// O histórico vem dos eventos `job` imediatos do canal NDJSON, não do snapshot:
// o snapshot guarda `last_finished`, que é UM job, e com tick de 1s dois
// workflows terminando no mesmo segundo fariam o primeiro desaparecer.
import { useMemo, useState } from 'react'
import {
  TbBan, TbCircleCheck, TbCircleX, TbHistory, TbPlayerPlay,
} from 'react-icons/tb'
import type { JobHistorico } from '../../main/state/store.js'
import type { Snapshot } from '../../shared/events.js'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from './ui/card.js'
import { duracao } from '../lib/formato.js'
import { cn } from '../lib/utils.js'

function quando(ts: number): string {
  return new Date(ts * 1000).toLocaleString('pt-BR', { hour12: false })
}

/**
 * Desfecho de um job: ícone, rótulo e cor.
 *
 * Ícone além da cor porque cor sozinha não distingue nada para quem não a
 * enxerga — e num histórico de trinta linhas o ícone também é mais rápido de
 * varrer que ler "Concluída" trinta vezes.
 */
const DESFECHO: Record<string, { icone: React.ReactNode; rotulo: string; cor: string }> = {
  ok: { icone: <TbCircleCheck size={16} />, rotulo: 'Concluída', cor: 'text-green-500' },
  error: { icone: <TbCircleX size={16} />, rotulo: 'Com erro', cor: 'text-destructive' },
  cancelled: { icone: <TbBan size={16} />, rotulo: 'Cancelada', cor: 'text-warning' },
}

const FILTROS = [
  { v: 'todos', r: 'Todas' },
  { v: 'ok', r: 'Concluídas' },
  { v: 'error', r: 'Com erro' },
  { v: 'cancelled', r: 'Canceladas' },
] as const

export function Execucoes({
  snapshot, jobs,
}: {
  snapshot: Snapshot | null
  jobs: JobHistorico[]
}) {
  const [filtro, setFiltro] = useState<(typeof FILTROS)[number]['v']>('todos')

  const contagem = useMemo(() => {
    const c: Record<string, number> = { todos: jobs.length }
    for (const j of jobs) c[j.status] = (c[j.status] ?? 0) + 1
    return c
  }, [jobs])

  const visiveis = useMemo(
    () => (filtro === 'todos' ? jobs : jobs.filter((j) => j.status === filtro)),
    [jobs, filtro],
  )

  const emAndamento = snapshot?.running ?? []

  return (
    <div className="flex flex-col gap-4">
      {/* ── Em andamento ────────────────────────────────────────────── */}
      <Card>
        {/* O contador acompanha o título e por isso mora DENTRO de `CardTitle`.
            Solto no header — que é grid — ele virava uma linha própria: uma
            faixa azul da largura inteira do cartão com um "2" na ponta. */}
        <CardHeader className="px-6">
          <CardTitle className="flex items-center gap-2 text-base font-medium">
            Em andamento
            {emAndamento.length > 0 && (
              <span className="flex items-center gap-1.5 rounded-full bg-blue-500/15 px-2 py-0.5 text-xs font-semibold text-blue-400 animate-in fade-in-0 zoom-in-95 duration-200">
                {/* Respiração, não `animate-ping`: o anel que se expande a cada
                    segundo, na única tela que fica aberta em segundo plano,
                    puxa o olho sem ter nada novo a dizer. */}
                <span className="size-1.5 rounded-full bg-blue-400 animate-pulso-vivo" />
                {emAndamento.length}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 px-6">
          {emAndamento.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <TbPlayerPlay size={24} className="text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                Nada rodando agora. Quando o servidor despachar um workflow para
                esta máquina, ele aparece aqui com o progresso nó a nó.
              </p>
            </div>
          ) : emAndamento.map((j) => {
            const pct = j.nodes_total ? Math.min(100, (j.nodes_done / j.nodes_total) * 100) : null
            return (
              <div
                key={j.job_id}
                className="rounded-lg border border-blue-500/25 bg-blue-500/[0.04] px-3 py-3 animate-in fade-in-0 slide-in-from-left-2 duration-300"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <span className="truncate font-mono text-xs select-text">{j.run_id ?? j.job_id}</span>
                    <span className="truncate text-xs text-muted-foreground">
                      {j.node ?? 'iniciando…'}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-4">
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {j.nodes_done}/{j.nodes_total ?? '?'} nós
                    </span>
                    <span className="text-sm font-medium tabular-nums">{duracao(j.elapsed_s)}</span>
                  </div>
                </div>
                {pct != null && (
                  <div className="mt-2.5 flex items-center gap-2">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                      <div className="h-full rounded-full bg-primary transition-[width] duration-500"
                           style={{ width: `${pct}%` }} />
                    </div>
                    <span className="w-9 shrink-0 text-right text-[11px] text-muted-foreground tabular-nums">
                      {Math.round(pct)}%
                    </span>
                  </div>
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>

      {/* ── Histórico ───────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="items-center px-6">
          <CardTitle className="text-base font-medium">Histórico da sessão</CardTitle>
          <CardAction className="flex flex-wrap justify-end gap-1">
            {FILTROS.map((f) => {
              const n = contagem[f.v] ?? 0
              return (
                <button
                  key={f.v}
                  type="button"
                  aria-pressed={filtro === f.v}
                  // Um filtro sem nada a mostrar leva a uma tela vazia sem
                  // motivo aparente; melhor não deixar clicar.
                  disabled={n === 0 && f.v !== 'todos'}
                  onClick={() => setFiltro(f.v)}
                  className={cn(
                    'flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                    'disabled:pointer-events-none disabled:opacity-40',
                    filtro === f.v
                      ? 'bg-muted text-foreground'
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
                  )}
                >
                  {f.r}
                  <span className="text-muted-foreground tabular-nums">{n}</span>
                </button>
              )
            })}
          </CardAction>
        </CardHeader>
        <CardContent className="px-6">
          {visiveis.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <TbHistory size={24} className="text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                {jobs.length === 0
                  ? 'Nada executado desde que o app abriu. Os totais acumulados de sempre estão no Painel.'
                  : 'Nenhuma execução com este filtro.'}
              </p>
            </div>
          ) : (
            <div className="-mx-2 flex max-h-[52vh] flex-col overflow-y-auto">
              {visiveis.map((j, i) => {
                const d = DESFECHO[j.status]
                return (
                  <div
                    key={`${j.job_id}-${i}`}
                    className="flex items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-muted/40"
                  >
                    <span className={cn('shrink-0', d?.cor ?? 'text-muted-foreground')}
                          title={d?.rotulo ?? j.status}>
                      {d?.icone ?? <TbCircleCheck size={16} />}
                    </span>
                    <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <span className="truncate font-mono text-xs select-text">
                        {j.run_id ?? j.job_id}
                      </span>
                      <span className="truncate text-xs text-muted-foreground">
                        {quando(j.ts)}
                        {/* Só aparece quando o executor reportou: nós contados vêm
                            do bloco `run` das métricas, que nem todo job carrega. */}
                        {typeof j.nodes_executed === 'number' && ` · ${j.nodes_executed} nós`}
                        {typeof j.nodes_failed === 'number' && j.nodes_failed > 0 &&
                          ` · ${j.nodes_failed} com falha`}
                      </span>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-0.5">
                      <span className="text-xs font-medium tabular-nums">{duracao(j.duration_s)}</span>
                      <span className={cn('text-[11px]', d?.cor ?? 'text-muted-foreground')}>
                        {d?.rotulo ?? j.status}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {jobs.length > 0 && (
            <p className="mt-3 border-t pt-3 text-xs text-muted-foreground">
              Esta lista vive na memória do app e recomeça quando ele é encerrado.
              Os totais do Painel vêm do executor e sobrevivem a isso.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
