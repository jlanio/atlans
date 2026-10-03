// desktop/src/main/state/store.ts
//
// Live state kept by the main process.
//
// It exists because the window can be closed and reopened at any moment (the
// app lives in the tray), and the executor keeps running the whole time.
// Without this cache, a reopened window would stay blank until the next tick,
// and the job history and log lines already emitted would be lost forever.
//
// Everything here is bounded: an app that stays open for days cannot grow
// without a ceiling.
//
// ── Two channels, and why ─────────────────────────────────────────────────────
//
// The log is NOT part of `EstadoApp`. The previous version carried it along,
// and the cost was disproportionate:
//
//   - `notificar()` delivers the whole state to every listener, and `difundir`
//     does `webContents.send`, which serializes everything by structured clone
//     PER WINDOW. With 1000 log lines inside, each broadcast cost ~150-200 KB.
//   - `registrarLinhaBruta` notified PER LINE. A workflow that prints 100
//     lines generated 100 broadcasts of 1000 lines each, plus 100 copies of
//     the whole array (`[...log, linha]`) — quadratic in log volume, and
//     exactly when the executor is busiest.
//
// Now there are two flows of different natures:
//
//   ESTADO   small, changes wholesale, delivered COALESCED (see JANELA_MS).
//   LOG      append-only, delivered INCREMENTALLY — only the new lines, with a
//            sequence number so the other side knows whether it missed any.
//
// `seq` also solves a renderer problem: it is a stable key for the lines in
// the list. With an array index, trimming the start of the buffer shifts every
// index and invalidates any per-line memoization.
import type {
  ExecutorEvent, HelloEvent, JobEvent, Phase, Snapshot,
} from '../../shared/events.js'
import type { SupervisorState } from '../python/supervisor.js'

const MAX_JOBS = 200
const MAX_LOG = 1000

/**
 * Coalescing window for state broadcasts, in ms.
 *
 * Short enough to be imperceptible (a click on "Parar" takes longer than that
 * to become an event) and long enough to collapse the burst of events that
 * arrives when a workflow starts.
 */
const WINDOW_MS = 80

export interface LogLine {
  /** Monotonic and global. Stable key of the line and cursor of the incremental channel. */
  seq: number
  ts: number
  level: string
  alias: string
  msg: string
  /** Raw line that did not come from the structured channel (stderr, or a node's print). */
  bruta?: boolean
}

/** Batch delivered by the log channel. */
export interface LogBatch {
  linhas: LogLine[]
  /**
   * `seq` of the oldest line still in main's buffer.
   *
   * The renderer uses it to detect that it fell behind (freshly opened window,
   * burst larger than the buffer) and reload everything instead of patching
   * over a gap.
   */
  primeiroSeq: number
}

export interface HistoryJob {
  job_id: string
  run_id: string | null
  status: string
  duration_s: number
  ts: number
  nodes_executed?: number | null
  nodes_failed?: number | null
}

export interface AppState {
  supervisor: SupervisorState
  detalheSupervisor: string | null
  fase: Phase | null
  passoFase: string | null
  detalheFase: string | null
  hello: HelloEvent['data'] | null
  snapshot: Snapshot | null
  jobs: HistoryJob[]
  /**
   * How many ERRORs are in the log buffer.
   *
   * It comes with the state because the sidebar and the status bar show the
   * counter, and making them depend on the whole log would bring back exactly
   * the weight this design removed. Maintained incrementally, without scanning
   * anything.
   */
  errosNoLog: number
}

export class AppStore {
  private estado: AppState = {
    supervisor: 'stopped',
    detalheSupervisor: null,
    fase: null,
    passoFase: null,
    detalheFase: null,
    hello: null,
    snapshot: null,
    jobs: [],
    errosNoLog: 0,
  }

  private log: LogLine[] = []
  private proximoSeq = 1

  private ouvintes = new Set<(e: AppState) => void>()
  private ouvintesLog = new Set<(lote: LogBatch) => void>()

  /** Linhas acumuladas desde o ultimo flush. */
  private pendentes: LogLine[] = []
  private timer: ReturnType<typeof setTimeout> | null = null
  private estadoSujo = false

  // ── Leitura ────────────────────────────────────────────────────────────────

  instantaneo(): AppState { return this.estado }

  /** Full buffer. Used by a window that has just opened. */
  logCompleto(): LogBatch {
    // A copy: IPC serializes this object in a later microtask, and returning the
    // live array would bet that nothing mutated it in that interval. It costs
    // a slice of 1000 elements once per opened window.
    return { linhas: this.log.slice(), primeiroSeq: this.log[0]?.seq ?? this.proximoSeq }
  }

  assinar(fn: (e: AppState) => void): () => void {
    this.ouvintes.add(fn)
    return () => this.ouvintes.delete(fn)
  }

  assinarLog(fn: (lote: LogBatch) => void): () => void {
    this.ouvintesLog.add(fn)
    return () => this.ouvintesLog.delete(fn)
  }

  // ── Entrega ────────────────────────────────────────────────────────────────

  /**
   * Marks that there is something to deliver and schedules the flush.
   *
   * Scheduling instead of delivering immediately is what collapses the burst.
   * The timer is NOT restarted on each call (that would be debounce, and on a
   * chatty executor the flush would never happen): the window is fixed from
   * the first change.
   */
  private agendar(): void {
    if (this.timer) return
    this.timer = setTimeout(() => {
      this.timer = null
      this.entregar()
    }, WINDOW_MS)
  }

  private entregar(): void {
    if (this.estadoSujo) {
      this.estadoSujo = false
      for (const fn of this.ouvintes) {
        try { fn(this.estado) } catch { /* a broken listener does not take down the others */ }
      }
    }
    if (this.pendentes.length > 0) {
      const lote: LogBatch = {
        linhas: this.pendentes,
        primeiroSeq: this.log[0]?.seq ?? this.proximoSeq,
      }
      this.pendentes = []
      for (const fn of this.ouvintesLog) {
        try { fn(lote) } catch { /* idem */ }
      }
    }
  }

  /**
   * Delivers whatever is pending now.
   *
   * Exists for shutdown: a `state: failed` in the last instant of the
   * process's life must not get stuck in a timer that will never fire.
   */
  descarregar(): void {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
    this.entregar()
  }

  // ── Escrita ────────────────────────────────────────────────────────────────

  aplicarEstadoSupervisor(estado: SupervisorState, detalhe?: string): void {
    this.estado = { ...this.estado, supervisor: estado, detalheSupervisor: detalhe ?? null }
    // A stopped executor has no valid snapshot; keeping the last one would make
    // the UI show "connected" with the process dead.
    if (estado === 'stopped' || estado === 'failed') {
      this.estado.snapshot = null
      this.estado.fase = estado === 'failed' ? 'failed' : null
    }
    this.estadoSujo = true
    this.agendar()
  }

  aplicarEvento(evt: ExecutorEvent): void {
    switch (evt.t) {
      case 'hello':
        this.estado = { ...this.estado, hello: evt.data }
        break
      case 'state':
        this.estado = {
          ...this.estado,
          fase: evt.data.phase,
          passoFase: evt.data.step,
          detalheFase: evt.data.detail,
        }
        break
      case 'snapshot':
        this.estado = { ...this.estado, snapshot: evt.data }
        break
      case 'job':
        this.registrarJob(evt)
        break
      case 'log':
        this.registrarLog({
          seq: 0, ts: evt.data.ts, level: evt.data.level,
          alias: evt.data.alias, msg: evt.data.msg,
        })
        this.agendar()
        return   // log does not dirty the state; `errosNoLog` handles what it affects
      default:
        // ack, sync, conn and warn do not change the aggregate state, and there is
        // no raw stream to the renderer anymore: what the UI shows of these
        // events already comes via the snapshot (conn_state, sync counters) or
        // via the log.
        return
    }
    this.estadoSujo = true
    this.agendar()
  }

  registrarLinhaBruta(texto: string, origem: 'stderr' | 'stdout'): void {
    this.registrarLog({
      seq: 0,
      ts: Date.now() / 1000,
      // The human log from stderr already comes formatted with the level embedded;
      // there is nothing to extract without parsing text — which is exactly
      // what this project avoids. It is marked as raw and the UI shows it
      // without coloring by level.
      level: 'RAW',
      alias: origem === 'stderr' ? 'LOG' : 'OUT',
      msg: texto,
      bruta: true,
    })
    this.agendar()
  }

  private registrarJob(evt: JobEvent): void {
    if (evt.data.event === 'started') return   // so o desfecho entra no historico
    const jobs = [
      {
        job_id: evt.data.job_id,
        run_id: evt.data.run_id,
        status: evt.data.status ?? evt.data.event,
        duration_s: evt.data.duration_s ?? 0,
        ts: evt.ts,
        nodes_executed: evt.data.nodes_executed,
        nodes_failed: evt.data.nodes_failed,
      },
      ...this.estado.jobs,
    ].slice(0, MAX_JOBS)
    this.estado = { ...this.estado, jobs }
  }

  private registrarLog(linha: LogLine): void {
    linha.seq = this.proximoSeq++

    // `push` and `shift`, not `[...log, linha]`: copying the whole array on
    // every line was half of the quadratic cost. Nobody observes this array by
    // identity — the renderer receives batches, not the reference.
    this.log.push(linha)
    if (linha.level === 'ERROR') this.contarErro(+1)
    while (this.log.length > MAX_LOG) {
      const saiu = this.log.shift()
      if (saiu?.level === 'ERROR') this.contarErro(-1)
    }

    this.pendentes.push(linha)
    // A burst larger than the whole buffer within an 80ms window must not
    // become a batch larger than the buffer: the excess was already discarded
    // above and the renderer would throw it away anyway. `primeiroSeq` still
    // gives away the cut, and the other side reloads.
    if (this.pendentes.length > MAX_LOG) {
      this.pendentes.splice(0, this.pendentes.length - MAX_LOG)
    }
  }

  /** Maintains `errosNoLog` without scanning the buffer, and marks the state for delivery. */
  private contarErro(delta: number): void {
    this.estado = { ...this.estado, errosNoLog: this.estado.errosNoLog + delta }
    this.estadoSujo = true
  }
}
