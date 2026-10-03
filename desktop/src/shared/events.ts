// desktop/src/shared/events.ts
//
// Typed mirror of the NDJSON protocol emitted by executor/dashboard/json_runtime.py.
//
// The bridge between the two sides is a text pipe: no type checker crosses the
// Python -> TypeScript boundary. What keeps both in sync are the contract tests
// in tests/unit/test_executor_json_ipc.py (Python side) and the ones in this
// directory (TS side). When changing a field here, change it there too.
//
// `Snapshot` maps 1:1 to `executor.stats.Snapshot` after going through
// `snapshot_to_dict`. The only fields that do not come straight from the
// dataclass are `slowest` and `last_finished`, which are tuples there and named
// objects here — see the docstring of `snapshot_to_dict`.

/** Protocol version. Bumped together with PROTOCOLO in executor/dashboard/json_runtime.py. */
export const PROTOCOLO = 1

/** Framing prefix. Every valid line starts with this. */
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
  /** How long the COUNTERS have been measuring — differs from uptime after a reset. */
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
   * Disk OF THE ARTIFACTS FOLDER — may be a different drive from the system's.
   *
   * It is what decides whether a workflow can write its result. With local
   * locality (LGPD) the artifact has a single copy, and it is on this disk:
   * filling it up stops being an inconvenience and becomes loss of customer
   * data.
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
   * Manifest inventory, published at the end of each GeoSync cycle.
   *
   * `sync_total` is what the EXECUTOR knows — not what exists in the Drive.
   * Knowing the remote total would require listing the workspace on every tick,
   * which is a network call and does not fit in a 1 Hz snapshot.
   */
  sync_total: number
  sync_synced: number
  sync_pending: number

  // footer
  //
  // No `log_tail` (and no `system`, up above): both exist for the terminal's
  // `rich` panel to draw the footer, and JsonRuntime draws nothing. The app has
  // its own log channel, incremental and with `seq` — carrying 200 lines per
  // snapshot cost tens of KB per second in the pipe, in JSON.parse and in a
  // structured clone per window, for nothing. The executor stopped emitting
  // both.
  log_warn_count: number
  log_error_count: number
}

export type ConnState = 'offline' | 'connecting' | 'connected' | 'reconnecting' | 'terminal'

// ── Eventos ──────────────────────────────────────────────────────────────────

interface Base {
  v: number
  /** epoch in seconds, with milliseconds. */
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
 * `failed` carries the exact step (`server_key`, `private_key`) and the reason —
 * it is the difference between the UI offering "redo enrollment" and offering
 * "try again".
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

/** Emitted when a line was discarded for exceeding the size ceiling. */
export interface WarnEvent extends Base {
  t: 'warn'
  data: { motivo: string; tipo: string; bytes: number }
}

export type ExecutorEvent =
  | HelloEvent | StateEvent | SnapshotEvent | JobEvent
  | SyncEvent | ConnEvent | LogEvent | AckEvent | WarnEvent

// ── Comandos ─────────────────────────────────────────────────────────────────

/** Mirror 1:1 the keys of the rich panel (executor/dashboard/runtime.py). */
export const COMMANDS = [
  'shutdown', 'reconnect', 'reset_stats', 'toggle_debug', 'ping', 'sync_now',
] as const

export type CommandName = (typeof COMMANDS)[number]

export interface Command {
  cmd: CommandName
  /** Optional; comes back in the corresponding `ack`. */
  id?: string
}
