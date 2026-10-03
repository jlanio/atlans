// desktop/src/main/python/supervisor.ts
//
// Lifecycle of the Python process: spawn, restart with backoff and orderly
// shutdown.
//
// Why the restart lives HERE and not in Python: `executor/main.py` has an
// auto-restart that uses `os.execve`. On POSIX that replaces the process, but
// on Windows CPython's implementation creates a NEW process and terminates the
// current one — Node's `ChildProcess` would see the child die, lose track of
// the real executor (alive, with a new PID, holding the WebSocket under the
// same EXECUTOR_ID) and start a second one. That is why the spawn passes
// `EXECUTOR_AUTO_RESTART=never`.
//
// Why shutdown is by command and not by signal: on Windows there is no
// SIGTERM. `child.kill()` becomes `TerminateProcess`, immediate death — running
// jobs lost and results never confirmed. The correct path is the `shutdown`
// command on stdin, which triggers in Python the SAME orderly shutdown as a
// SIGTERM.
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { EventEmitter } from 'node:events'
import { execFile } from 'node:child_process'
import type { Command, ExecutorEvent } from '../../shared/events.js'
import { LineSplitter, NdjsonParser } from './ndjson.js'

export type EstadoSupervisor =
  | 'stopped'      // stopped by the user's decision
  | 'starting'     // spawn feito, aguardando o `hello`
  | 'running'
  | 'draining'     // shutdown ordenado em curso
  | 'restarting'   // caiu, aguardando o backoff
  | 'failed'       // gave up; requires user action

/** Mesma politica de executor/main.py:_MAX_RESTARTS / _RESTART_WINDOW_SEC. */
const MAX_TENTATIVAS = 5
const JANELA_MS = 300_000
const BACKOFF_BASE_MS = 2_000
const BACKOFF_MAX_MS = 60_000

/**
 * Ceiling for the orderly shutdown: 120 s of job draining + 30 s of result
 * confirmation are the real limits in executor/main.py, plus headroom.
 */
export const TIMEOUT_SHUTDOWN_MS = 150_000

export interface OpcoesSupervisor {
  pythonExe: string
  cwd: string
  env: NodeJS.ProcessEnv
  /** Injectable for testing. */
  spawnFn?: typeof spawn
  agora?: () => number
}

export interface SupervisorEvents {
  evento: (evt: ExecutorEvent) => void
  /** A stderr line (human log) or a stdout line that was not an event. */
  linha: (texto: string, origem: 'stderr' | 'stdout') => void
  estado: (estado: EstadoSupervisor, detalhe?: string) => void
}

export class PythonSupervisor extends EventEmitter {
  private proc: ChildProcessWithoutNullStreams | null = null
  private _estado: EstadoSupervisor = 'stopped'
  private tentativas: number[] = []
  private timerBackoff: NodeJS.Timeout | null = null
  private timerShutdown: NodeJS.Timeout | null = null
  /**
   * Stop in progress, so that `stop()` is idempotent.
   *
   * Without this, two stop requests on the SAME process (double click on
   * "Parar", or `reiniciar` crossing paths with the app shutting down) resent
   * `shutdown` and overwrote the watchdog handle without clearing the previous
   * one. The first timer was orphaned and, 150 s later, called `matarAForca()`
   * — which reads `this.proc` AT FIRING TIME — cold-killing the NEXT executor,
   * in the middle of a job, with results never confirmed to the server.
   */
  private paradaEmCurso: Promise<void> | null = null
  /** Instant at which the watchdog of the stop in progress fires. */
  private prazoShutdown = 0
  /**
   * How many stops were REQUESTED (not how many happened).
   *
   * `restart()` compares the value before and after draining: if another stop
   * came in meanwhile (the tray's "Parar", the app shutting down), restarting
   * would resurrect the executor against the most recent request.
   */
  private geracaoParada = 0
  /** Distingue "o usuario mandou parar" de "caiu sozinho". */
  private pareiDeProposito = false
  /** O Python emitiu `state: draining` — a saida seguinte e esperada. */
  private drenando = false
  private readonly agora: () => number
  private readonly spawnFn: typeof spawn

  constructor(private readonly opcoes: OpcoesSupervisor) {
    super()
    this.agora = opcoes.agora ?? Date.now
    this.spawnFn = opcoes.spawnFn ?? spawn
  }

  get estado(): EstadoSupervisor { return this._estado }
  get pid(): number | undefined { return this.proc?.pid }

  // ── Start ────────────────────────────────────────────────────────────────

  start(): void {
    if (this.proc) return
    this.pareiDeProposito = false
    this.drenando = false
    this.cancelarBackoff()
    this.mudarEstado('starting')

    const proc = this.spawnFn(this.opcoes.pythonExe, ['-X', 'utf8', '-m', 'executor'], {
      cwd: this.opcoes.cwd,
      env: this.opcoes.env,
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe'],
    }) as ChildProcessWithoutNullStreams
    this.proc = proc

    const parser = new NdjsonParser({
      onEvent: (evt) => this.receberEvento(evt),
      // A `print()` from a workflow node. Not an error — it is information.
      onRaw: (linha) => this.emit('linha', linha, 'stdout'),
    })
    const stderr = new LineSplitter((linha) => this.emit('linha', linha, 'stderr'))

    proc.stdout.setEncoding('utf8')
    proc.stdout.on('data', (c: string) => parser.push(c))
    proc.stderr.setEncoding('utf8')
    proc.stderr.on('data', (c: string) => stderr.push(c))

    proc.on('error', (err) => {
      // Failure in the spawn itself (missing python.exe, permissions). No point
      // retrying with backoff: it will not fix itself.
      this.proc = null
      this.limparParada()
      this.mudarEstado('failed', `nao foi possivel iniciar o executor: ${err.message}`)
    })

    proc.on('exit', (codigo, sinal) => {
      parser.flush()
      stderr.flush()
      this.proc = null
      // Before `aoSair` and before stop()'s `resolve`: the next `stop()` must
      // find the field cleared, otherwise it would return the promise of a
      // stop that has already finished.
      this.limparParada()
      this.aoSair(codigo, sinal)
    })
  }

  // ── Stop ─────────────────────────────────────────────────────────────────

  /**
   * Orderly shutdown. Resolves when the process exits — or when the grace
   * ceiling runs out and it is forcibly killed.
   *
   * The UI shows real progress during the wait using the snapshots that keep
   * arriving (`running_count`, `result_queue_size`): the JSON channel stays up
   * until the end of the executor's block 8 precisely for this.
   */
  stop(timeoutMs = TIMEOUT_SHUTDOWN_MS): Promise<void> {
    this.pareiDeProposito = true
    this.cancelarBackoff()
    this.geracaoParada++

    const proc = this.proc
    if (!proc) {
      this.mudarEstado('stopped')
      return Promise.resolve()
    }

    // Idempotent: a second request on the SAME drain returns the SAME promise.
    // It does not resend `shutdown` (Python is already draining) and, above
    // all, does not arm a second watchdog — see `paradaEmCurso`.
    if (this.paradaEmCurso) {
      // The exception is a LOWER ceiling: `refazerEnrollment` stops with 10 s
      // because it needs to delete the PEMs, and inheriting the 150 s of the
      // earlier request would leave the user waiting for a drain they already
      // cut short.
      if (this.agora() + timeoutMs < this.prazoShutdown) this.armarWatchdog(timeoutMs)
      return this.paradaEmCurso
    }

    this.paradaEmCurso = new Promise<void>((resolve) => {
      proc.once('exit', () => resolve())
      this.mudarEstado('draining')
      if (!this.enviar({ cmd: 'shutdown', id: 'stop' })) {
        // stdin already closed — there is no way to ask politely.
        this.matarAForca()
        return
      }
      this.armarWatchdog(timeoutMs)
    })
    return this.paradaEmCurso
  }

  /**
   * Stop and restart.
   *
   * Lives here, and not in the main process, because only the supervisor knows
   * whether someone requested ANOTHER stop during the drain — which can take
   * 150 s. Without that check, clicking "Salvar e reiniciar" (save and restart)
   * and then, tired of waiting, "Sair" (quit) in the tray left an ORPHAN
   * Python: the restart's `start()` won the race against `app.quit()`, spawned
   * a new executor and main died without killing it — it stayed holding the
   * WebSocket with the same EXECUTOR_ID, with no supervisor.
   *
   * `podeReligar` is the caller's guard (in main, "the app is not shutting
   * down"), evaluated AFTER the drain, which is when it matters.
   */
  async restart(podeReligar: () => boolean = () => true): Promise<void> {
    const parada = this.stop()
    const geracao = this.geracaoParada
    await parada
    if (this.geracaoParada !== geracao) return   // another stop came in meanwhile
    if (!podeReligar()) return
    this.start()
  }

  /**
   * Immediate shutdown, at the user's explicit request ("Forcar agora", force
   * now).
   *
   * Does not touch `geracaoParada`: forcing during a `restart()` means "hurry
   * up", not "give up on the restart" — whoever clicked there just asked for
   * the restart and would be left without an executor.
   */
  forcar(): void {
    this.pareiDeProposito = true
    this.cancelarBackoff()
    this.matarAForca()
  }

  /** Grace ceiling for the drain. Always clears the previous one before arming. */
  private armarWatchdog(timeoutMs: number): void {
    this.limparTimerShutdown()
    this.prazoShutdown = this.agora() + timeoutMs
    this.timerShutdown = setTimeout(() => {
      this.timerShutdown = null
      this.emit('linha', `[supervisor] shutdown excedeu ${Math.round(timeoutMs / 1000)}s — forcando`, 'stderr')
      this.matarAForca()
    }, timeoutMs)
  }

  private matarAForca(): void {
    const proc = this.proc
    if (!proc?.pid) return
    // `/T` kills the whole tree: the executor creates threads and may have
    // subprocesses. `process.kill()` on Windows does not reach the children,
    // and one of them holding the cert dir would keep the next update from
    // writing.
    if (process.platform === 'win32') {
      execFile('taskkill', ['/pid', String(proc.pid), '/T', '/F'], () => {})
    } else {
      proc.kill('SIGKILL')
    }
  }

  // ── Comandos ─────────────────────────────────────────────────────────────

  /** Writes a command to stdin. False if there is nowhere to write. */
  enviar(cmd: Command): boolean {
    const proc = this.proc
    if (!proc || proc.stdin.destroyed || !proc.stdin.writable) return false
    try {
      proc.stdin.write(JSON.stringify(cmd) + '\n')
      return true
    } catch {
      return false
    }
  }

  // ── Reacao a eventos e saida ─────────────────────────────────────────────

  private receberEvento(evt: ExecutorEvent): void {
    if (evt.t === 'hello') {
      this.mudarEstado('running')
    } else if (evt.t === 'state') {
      if (evt.data.phase === 'draining') this.drenando = true
      if (evt.data.phase === 'failed') {
        // Boot failure with a known cause (cert, server key). Repeating does not
        // help: the condition is persistent and the user needs to act.
        this.pareiDeProposito = true
        this.mudarEstado('failed', evt.data.detail ?? evt.data.step ?? 'falha no boot')
      }
    }
    this.emit('evento', evt)
  }

  private aoSair(codigo: number | null, sinal: NodeJS.Signals | null): void {
    if (this._estado === 'failed') return          // already reported with a cause
    if (this.pareiDeProposito) {
      this.mudarEstado('stopped')
      return
    }

    // Exit with code 1 right after `state: draining` is a restart REQUESTED by
    // the server (control `config_changed`, in executor/main.py). It is not a
    // failure: restart quickly and do not consume the anti-loop window,
    // otherwise a server that reassigns workspaces a few times would take the
    // executor down for good.
    if (this.drenando && codigo === 1) {
      this.drenando = false
      this.agendarRestart(2_000, 'reinicio pedido pelo servidor')
      return
    }

    const motivo = sinal ? `sinal ${sinal}` : `codigo ${codigo}`
    const t = this.agora()
    this.tentativas = this.tentativas.filter((x) => t - x < JANELA_MS)
    this.tentativas.push(t)

    if (this.tentativas.length > MAX_TENTATIVAS) {
      // Restarting in a loop would hide the cause and burn CPU. Stopping and
      // asking for action is more honest — it is the same policy as Python's
      // auto-restart.
      this.mudarEstado(
        'failed',
        `o executor caiu ${this.tentativas.length} vezes em ${Math.round(JANELA_MS / 60000)} min (${motivo})`,
      )
      return
    }
    this.agendarRestart(this.backoff(this.tentativas.length), motivo)
  }

  /** Exponencial com jitter: 2s, 4s, 8s… ate 60s. */
  private backoff(tentativa: number): number {
    const base = Math.min(BACKOFF_BASE_MS * 2 ** (tentativa - 1), BACKOFF_MAX_MS)
    return Math.round(base * (0.8 + Math.random() * 0.4))
  }

  private agendarRestart(atrasoMs: number, motivo: string): void {
    this.mudarEstado('restarting', `${motivo} — nova tentativa em ${Math.round(atrasoMs / 1000)}s`)
    this.timerBackoff = setTimeout(() => {
      this.timerBackoff = null
      this.start()
    }, atrasoMs)
  }

  private cancelarBackoff(): void {
    if (this.timerBackoff) {
      clearTimeout(this.timerBackoff)
      this.timerBackoff = null
    }
  }

  private limparTimerShutdown(): void {
    if (this.timerShutdown) {
      clearTimeout(this.timerShutdown)
      this.timerShutdown = null
    }
  }

  /** End of the stop: the watchdog must not outlive the process it watched. */
  private limparParada(): void {
    this.limparTimerShutdown()
    this.prazoShutdown = 0
    this.paradaEmCurso = null
  }

  private mudarEstado(estado: EstadoSupervisor, detalhe?: string): void {
    if (this._estado === estado && !detalhe) return
    this._estado = estado
    this.emit('estado', estado, detalhe)
  }
}

export declare interface PythonSupervisor {
  on<E extends keyof SupervisorEvents>(evt: E, fn: SupervisorEvents[E]): this
  emit<E extends keyof SupervisorEvents>(evt: E, ...args: Parameters<SupervisorEvents[E]>): boolean
}
