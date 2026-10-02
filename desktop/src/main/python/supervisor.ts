// desktop/src/main/python/supervisor.ts
//
// Ciclo de vida do processo Python: spawn, reinicio com backoff e encerramento
// ordenado.
//
// Por que o restart mora AQUI e nao no Python: `executor/main.py` tem um
// auto-restart que usa `os.execve`. Em POSIX isso substitui o processo, mas no
// Windows a implementacao do CPython cria um processo NOVO e encerra o atual —
// o `ChildProcess` do Node veria o filho morrer, perderia o rastro do executor
// real (vivo, com PID novo, segurando o WebSocket sob o mesmo EXECUTOR_ID) e
// subiria um segundo. Por isso o spawn passa `EXECUTOR_AUTO_RESTART=never`.
//
// Por que o encerramento e por comando e nao por sinal: no Windows nao ha
// SIGTERM. `child.kill()` vira `TerminateProcess`, morte imediata — jobs em
// andamento perdidos e resultados nunca confirmados. O caminho correto e o
// comando `shutdown` no stdin, que dispara no Python o MESMO shutdown ordenado
// de um SIGTERM.
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { EventEmitter } from 'node:events'
import { execFile } from 'node:child_process'
import type { Command, ExecutorEvent } from '../../shared/events.js'
import { LineSplitter, NdjsonParser } from './ndjson.js'

export type EstadoSupervisor =
  | 'stopped'      // parado por decisao do usuario
  | 'starting'     // spawn feito, aguardando o `hello`
  | 'running'
  | 'draining'     // shutdown ordenado em curso
  | 'restarting'   // caiu, aguardando o backoff
  | 'failed'       // desistiu; exige acao do usuario

/** Mesma politica de executor/main.py:_MAX_RESTARTS / _RESTART_WINDOW_SEC. */
const MAX_TENTATIVAS = 5
const JANELA_MS = 300_000
const BACKOFF_BASE_MS = 2_000
const BACKOFF_MAX_MS = 60_000

/**
 * Teto do shutdown ordenado: 120 s de drenagem de jobs + 30 s de confirmacao de
 * resultados sao os limites reais em executor/main.py, mais folga.
 */
export const TIMEOUT_SHUTDOWN_MS = 150_000

export interface OpcoesSupervisor {
  pythonExe: string
  cwd: string
  env: NodeJS.ProcessEnv
  /** Injetavel para teste. */
  spawnFn?: typeof spawn
  agora?: () => number
}

export interface SupervisorEvents {
  evento: (evt: ExecutorEvent) => void
  /** Linha do stderr (log humano) ou do stdout que nao era evento. */
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
   * Parada em curso, para `stop()` ser idempotente.
   *
   * Sem isto, dois pedidos de parada sobre o MESMO processo (duplo clique em
   * "Parar", ou o `reiniciar` cruzando com o encerramento do app) reenviavam
   * `shutdown` e sobrescreviam o handle do watchdog sem limpar o anterior. O
   * primeiro timer ficava orfao e, 150 s depois, chamava `matarAForca()` — que
   * le `this.proc` NO MOMENTO DO DISPARO — matando a frio o executor SEGUINTE,
   * no meio de um job, com os resultados nunca confirmados ao servidor.
   */
  private paradaEmCurso: Promise<void> | null = null
  /** Instante em que o watchdog da parada em curso dispara. */
  private prazoShutdown = 0
  /**
   * Quantas paradas foram PEDIDAS (nao quantas aconteceram).
   *
   * `restart()` compara o valor antes e depois da drenagem: se outra parada
   * entrou no meio (o tray "Parar", o encerramento do app), religar seria
   * ressuscitar o executor contra o pedido mais recente.
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
      // Um `print()` de um no de workflow. Nao e erro — e informacao.
      onRaw: (linha) => this.emit('linha', linha, 'stdout'),
    })
    const stderr = new LineSplitter((linha) => this.emit('linha', linha, 'stderr'))

    proc.stdout.setEncoding('utf8')
    proc.stdout.on('data', (c: string) => parser.push(c))
    proc.stderr.setEncoding('utf8')
    proc.stderr.on('data', (c: string) => stderr.push(c))

    proc.on('error', (err) => {
      // Falha no proprio spawn (python.exe ausente, permissao). Nao adianta
      // tentar de novo com backoff: nao vai se resolver sozinho.
      this.proc = null
      this.limparParada()
      this.mudarEstado('failed', `nao foi possivel iniciar o executor: ${err.message}`)
    })

    proc.on('exit', (codigo, sinal) => {
      parser.flush()
      stderr.flush()
      this.proc = null
      // Antes do `aoSair` e antes do `resolve` do stop(): o proximo `stop()`
      // tem de encontrar o campo limpo, senao devolveria a promessa de uma
      // parada que ja terminou.
      this.limparParada()
      this.aoSair(codigo, sinal)
    })
  }

  // ── Stop ─────────────────────────────────────────────────────────────────

  /**
   * Shutdown ordenado. Resolve quando o processo sai — ou quando o teto de
   * graca estoura e ele e morto a forca.
   *
   * A UI mostra o progresso real durante a espera usando os snapshots que
   * continuam chegando (`running_count`, `result_queue_size`): o canal JSON
   * fica de pe ate o fim do bloco 8 do executor justamente para isso.
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

    // Idempotente: um segundo pedido sobre a MESMA drenagem devolve a MESMA
    // promessa. Nao reenvia `shutdown` (o Python ja esta drenando) e, acima de
    // tudo, nao arma um segundo watchdog — ver `paradaEmCurso`.
    if (this.paradaEmCurso) {
      // A excecao e um teto MENOR: `refazerEnrollment` para com 10 s porque
      // precisa apagar os PEMs, e herdar os 150 s do pedido anterior deixaria
      // o usuario esperando por uma drenagem que ele ja abreviou.
      if (this.agora() + timeoutMs < this.prazoShutdown) this.armarWatchdog(timeoutMs)
      return this.paradaEmCurso
    }

    this.paradaEmCurso = new Promise<void>((resolve) => {
      proc.once('exit', () => resolve())
      this.mudarEstado('draining')
      if (!this.enviar({ cmd: 'shutdown', id: 'stop' })) {
        // stdin ja fechou — nao ha como pedir com educacao.
        this.matarAForca()
        return
      }
      this.armarWatchdog(timeoutMs)
    })
    return this.paradaEmCurso
  }

  /**
   * Parar e religar.
   *
   * Mora aqui, e nao no processo principal, porque so o supervisor sabe se
   * alguem pediu OUTRA parada durante a drenagem — que pode levar 150 s. Sem
   * essa checagem, clicar "Salvar e reiniciar" e, cansado da espera, "Sair" no
   * tray deixava um Python ORFAO: o `start()` do reinicio ganhava a corrida com
   * o `app.quit()`, spawnava um executor novo e o main morria sem mata-lo — ele
   * ficava segurando o WebSocket com o mesmo EXECUTOR_ID, sem supervisor.
   *
   * `podeReligar` e a guarda de quem chama (no main, "o app nao esta
   * encerrando"), avaliada DEPOIS da drenagem, que e quando ela importa.
   */
  async restart(podeReligar: () => boolean = () => true): Promise<void> {
    const parada = this.stop()
    const geracao = this.geracaoParada
    await parada
    if (this.geracaoParada !== geracao) return   // outra parada entrou no meio
    if (!podeReligar()) return
    this.start()
  }

  /**
   * Encerramento imediato, a pedido explicito do usuario ("Forcar agora").
   *
   * Nao mexe em `geracaoParada`: forcar durante um `restart()` e "tenha
   * pressa", nao "desista do reinicio" — quem clicou ali acabou de pedir o
   * reinicio e ficaria sem executor.
   */
  forcar(): void {
    this.pareiDeProposito = true
    this.cancelarBackoff()
    this.matarAForca()
  }

  /** Teto de graca da drenagem. Sempre limpa o anterior antes de armar. */
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
    // `/T` mata a arvore inteira: o executor cria threads e pode ter
    // subprocessos. `process.kill()` no Windows nao alcanca os filhos, e um
    // deles segurando o cert dir impediria a proxima atualizacao de gravar.
    if (process.platform === 'win32') {
      execFile('taskkill', ['/pid', String(proc.pid), '/T', '/F'], () => {})
    } else {
      proc.kill('SIGKILL')
    }
  }

  // ── Comandos ─────────────────────────────────────────────────────────────

  /** Escreve um comando no stdin. False se nao ha para onde escrever. */
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
        // Falha de boot com causa conhecida (cert, chave do servidor). Repetir
        // nao resolve: a condicao e persistente e o usuario precisa agir.
        this.pareiDeProposito = true
        this.mudarEstado('failed', evt.data.detail ?? evt.data.step ?? 'falha no boot')
      }
    }
    this.emit('evento', evt)
  }

  private aoSair(codigo: number | null, sinal: NodeJS.Signals | null): void {
    if (this._estado === 'failed') return          // ja reportado com causa
    if (this.pareiDeProposito) {
      this.mudarEstado('stopped')
      return
    }

    // Saida com codigo 1 logo apos `state: draining` e restart PEDIDO pelo
    // servidor (control `config_changed`, em executor/main.py). Nao e falha:
    // religa rapido e nao consome a janela anti-loop, senao um servidor que
    // reatribui workspaces algumas vezes derrubaria o executor de vez.
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
      // Religar em loop esconderia a causa e queimaria CPU. Parar e pedir acao
      // e mais honesto — e a mesma politica do auto-restart do Python.
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

  /** Fim da parada: o watchdog nao pode sobreviver ao processo que ele vigiava. */
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
