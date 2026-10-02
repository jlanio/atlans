// desktop/src/shared/events.ts
//
// Espelho tipado do protocolo NDJSON emitido por executor/dashboard/json_runtime.py.
//
// A ponte entre os dois lados e um pipe de texto: nao ha type checker que
// atravesse a fronteira Python -> TypeScript. O que mantem os dois em dia sao
// os testes de contrato em tests/unit/test_executor_json_ipc.py (lado Python) e
// os deste diretorio (lado TS). Ao mudar um campo aqui, mude la tambem.
//
// `Snapshot` corresponde 1:1 a `executor.stats.Snapshot` depois de
// passar por `snapshot_to_dict`. Os unicos campos que nao saem do dataclass
// direto sao `slowest` e `last_finished`, que la sao tuplas e aqui sao objetos
// nomeados — ver o docstring de `snapshot_to_dict`.

/** Versao do protocolo. Sobe junto com PROTOCOLO em executor/dashboard/json_runtime.py. */
export const PROTOCOLO = 1

/** Prefixo de framing. Toda linha valida comeca com isto. */
export const FRAMING = `{"v":${PROTOCOLO},`

// ── Snapshot ─────────────────────────────────────────────────────────────────

export interface RunningJob {
  job_id: string
  run_id: string | null
  elapsed_s: number
  node: string | null
  nodes_done: number
  nodes_total: number | null
}

export interface Snapshot {
  // identidade
  executor_id: string
  version: string
  server_url: string
  uptime_s: number
  /** Ha quanto tempo os CONTADORES medem — difere do uptime apos um reset. */
  contando_ha_s: number

  // workflows
  total_ok: number
  total_error: number
  total_cancelled: number
  success_rate: number
  last_hour_total: number
  last_hour_error: number
  throughput_per_min: number

  // tempos
  avg_duration_s: number | null
  p50_duration_s: number | null
  p95_duration_s: number | null
  slowest: { run_id: string; duration_s: number } | null
  last_finished: { run_id: string; status: string; duration_s: number } | null
  running: RunningJob[]

  // recursos
  proc_cpu_pct: number | null
  proc_cpu_pct_norm: number | null
  proc_rss_mb: number | null
  proc_threads: number | null
  cpu_cores: number | null
  ram_available_gb: number | null
  ram_total_gb: number | null
  disk_free_gb: number | null
  disk_total_gb: number | null
  /**
   * Disco DA PASTA DE ARTEFATOS — pode ser outra unidade que a do sistema.
   *
   * É o que decide se um workflow consegue gravar o resultado. Com localidade
   * local (LGPD) o artefato tem uma cópia só, e ela está nesse disco: encher
   * deixa de ser inconveniente e vira perda de dado do cliente.
   */
  artifacts_disk_free_gb: number | null
  artifacts_disk_total_gb: number | null
  wf_cpu_peak_pct: number | null
  wf_mem_peak_mb: number | null
  nodes_executed_total: number
  nodes_failed_total: number

  // fila e conexao
  queued: number
  running_count: number
  max_concurrent: number
  max_queue: number
  result_queue_size: number
  outbox_pending: number
  conn_state: ConnState
  conn_since_s: number | null
  reconnects: number
  heartbeat_age_s: number | null
  next_retry_in_s: number | null

  // geosync
  sync_dirs: string[]
  sync_files_up: number
  sync_bytes_up: number
  sync_files_down: number
  sync_bytes_down: number
  sync_errors: number
  sync_conflicts: number
  sync_current: string | null
  /**
   * Inventário do manifesto, publicado ao fim de cada ciclo do GeoSync.
   *
   * `sync_total` é o que o EXECUTOR conhece — não o que existe no Drive. Saber
   * o total remoto exigiria listar o workspace a cada tick, que é chamada de
   * rede e não cabe num snapshot de 1 Hz.
   */
  sync_total: number
  sync_synced: number
  sync_pending: number

  // rodape
  //
  // Sem `log_tail` (e sem `system`, la em cima): as duas existem para o painel
  // `rich` do terminal desenhar o rodape, e o JsonRuntime nao desenha nada. O
  // app tem canal de log proprio, incremental e com `seq` — carregar 200 linhas
  // por snapshot custava dezenas de KB por segundo no pipe, no JSON.parse e num
  // structured clone por janela, para nada. O executor parou de emitir os dois.
  log_warn_count: number
  log_error_count: number
}

export type ConnState = 'offline' | 'connecting' | 'connected' | 'reconnecting' | 'terminal'

// ── Eventos ──────────────────────────────────────────────────────────────────

interface Base {
  v: number
  /** epoch em segundos, com milissegundos. */
  ts: number
}

export interface HelloEvent extends Base {
  t: 'hello'
  data: {
    pid: number
    executor_id: string
    python: string
    comandos: CommandName[]
  }
}

/**
 * `failed` carrega o passo exato (`server_key`, `private_key`) e o motivo — e a
 * diferenca entre a UI oferecer "refazer enrollment" e oferecer "tentar de novo".
 */
export type Phase = 'booting' | 'running' | 'draining' | 'stopped' | 'failed'

export interface StateEvent extends Base {
  t: 'state'
  data: { phase: Phase; step: string | null; detail: string | null }
}

export interface SnapshotEvent extends Base {
  t: 'snapshot'
  /** Eventos perdidos por buffer cheio desde o snapshot anterior. */
  descartados: number
  data: Snapshot
}

export interface JobEvent extends Base {
  t: 'job'
  data: {
    event: 'started' | 'finished' | 'cancelled'
    job_id: string
    run_id: string | null
    status?: string
    duration_s?: number
    nodes_executed?: number | null
    nodes_failed?: number | null
    motivo?: string | null
  }
}

export interface SyncEvent extends Base {
  t: 'sync'
  data: { event: string; dataset: string; total_bytes: number }
}

export interface ConnEvent extends Base {
  t: 'conn'
  data: { state: ConnState; reconnects: number; next_retry_in_s?: number | null }
}

export interface LogEvent extends Base {
  t: 'log'
  data: { ts: number; level: string; alias: string; logger: string; msg: string }
}

export interface AckEvent extends Base {
  t: 'ack'
  cmd: CommandName | null
  id?: string | null
  ok: boolean
  detail: string | null
}

/** Emitido quando uma linha foi descartada por exceder o teto de tamanho. */
export interface WarnEvent extends Base {
  t: 'warn'
  data: { motivo: string; tipo: string; bytes: number }
}

export type ExecutorEvent =
  | HelloEvent | StateEvent | SnapshotEvent | JobEvent
  | SyncEvent | ConnEvent | LogEvent | AckEvent | WarnEvent

// ── Comandos ─────────────────────────────────────────────────────────────────

/** Espelham 1:1 as teclas do painel rich (executor/dashboard/runtime.py). */
export const COMMANDS = [
  'shutdown', 'reconnect', 'reset_stats', 'toggle_debug', 'ping', 'sync_now',
] as const

export type CommandName = (typeof COMMANDS)[number]

export interface Command {
  cmd: CommandName
  /** Opcional; volta no `ack` correspondente. */
  id?: string
}
