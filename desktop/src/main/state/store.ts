// desktop/src/main/state/store.ts
//
// Estado vivo mantido pelo main process.
//
// Existe porque a janela pode ser fechada e reaberta a qualquer momento (o app
// vive no tray), e o executor continua rodando o tempo todo. Sem este cache,
// uma janela reaberta ficaria em branco ate o proximo tick, e o historico de
// jobs e as linhas de log ja emitidos estariam perdidos para sempre.
//
// Tudo aqui e limitado: um app que fica dias aberto nao pode crescer sem teto.
//
// ── Dois canais, e por que ────────────────────────────────────────────────────
//
// O log NAO faz parte de `EstadoApp`. A versao anterior o carregava junto, e o
// custo era desproporcional:
//
//   - `notificar()` entrega o estado inteiro a cada ouvinte, e `difundir` faz
//     `webContents.send`, que serializa tudo por structured clone POR JANELA.
//     Com 1000 linhas de log dentro, cada broadcast custava ~150-200 KB.
//   - `registrarLinhaBruta` notificava POR LINHA. Um workflow que imprime 100
//     linhas gerava 100 broadcasts de 1000 linhas cada, mais 100 copias do
//     array inteiro (`[...log, linha]`) — quadratico no volume de log, e
//     exatamente quando o executor esta mais ocupado.
//
// Agora sao dois fluxos com naturezas diferentes:
//
//   ESTADO   pequeno, muda por completo, entregue COALESCIDO (ver JANELA_MS).
//   LOG      append-only, entregue INCREMENTAL — so as linhas novas, com um
//            numero de sequencia para o outro lado saber se perdeu alguma.
//
// O `seq` tambem resolve um problema do renderer: e uma chave estavel para as
// linhas na lista. Com indice de array, aparar o inicio do buffer desloca todos
// os indices e invalida qualquer memoizacao de linha.
import type {
  ExecutorEvent, HelloEvent, JobEvent, Phase, Snapshot,
} from '../../shared/events.js'
import type { EstadoSupervisor } from '../python/supervisor.js'

const MAX_JOBS = 200
const MAX_LOG = 1000

/**
 * Janela de coalescencia dos broadcasts de estado, em ms.
 *
 * Curta o bastante para ser imperceptivel (um clique em "Parar" leva mais que
 * isso para virar evento) e longa o bastante para colapsar a rajada de eventos
 * que chega quando um workflow comeca.
 */
const JANELA_MS = 80

export interface LinhaLog {
  /** Monotonico e global. Chave estavel da linha e cursor do canal incremental. */
  seq: number
  ts: number
  level: string
  alias: string
  msg: string
  /** Linha bruta que nao veio do canal estruturado (stderr, ou print de um no). */
  bruta?: boolean
}

/** Lote entregue pelo canal de log. */
export interface LoteLog {
  linhas: LinhaLog[]
  /**
   * `seq` da linha mais antiga ainda no buffer do main.
   *
   * O renderer usa para detectar que ficou para tras (janela recem-aberta,
   * rajada maior que o buffer) e recarregar tudo em vez de emendar um buraco.
   */
  primeiroSeq: number
}

export interface JobHistorico {
  job_id: string
  run_id: string | null
  status: string
  duration_s: number
  ts: number
  nodes_executed?: number | null
  nodes_failed?: number | null
}

export interface EstadoApp {
  supervisor: EstadoSupervisor
  detalheSupervisor: string | null
  fase: Phase | null
  passoFase: string | null
  detalheFase: string | null
  hello: HelloEvent['data'] | null
  snapshot: Snapshot | null
  jobs: JobHistorico[]
  /**
   * Quantos ERROR ha no buffer de log.
   *
   * Vem junto do estado porque a sidebar e a barra de status mostram o
   * contador, e faze-las depender do log inteiro traria de volta exatamente o
   * peso que este desenho tirou. Mantido incrementalmente, sem varrer nada.
   */
  errosNoLog: number
}

export class AppStore {
  private estado: EstadoApp = {
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

  private log: LinhaLog[] = []
  private proximoSeq = 1

  private ouvintes = new Set<(e: EstadoApp) => void>()
  private ouvintesLog = new Set<(lote: LoteLog) => void>()

  /** Linhas acumuladas desde o ultimo flush. */
  private pendentes: LinhaLog[] = []
  private timer: ReturnType<typeof setTimeout> | null = null
  private estadoSujo = false

  // ── Leitura ────────────────────────────────────────────────────────────────

  instantaneo(): EstadoApp { return this.estado }

  /** Buffer completo. Usado por uma janela que acabou de abrir. */
  logCompleto(): LoteLog {
    // Cópia: o IPC serializa este objeto num microtask posterior, e devolver o
    // array vivo apostaria que nada o mutou nesse intervalo. Custa um slice de
    // 1000 elementos uma vez por janela aberta.
    return { linhas: this.log.slice(), primeiroSeq: this.log[0]?.seq ?? this.proximoSeq }
  }

  assinar(fn: (e: EstadoApp) => void): () => void {
    this.ouvintes.add(fn)
    return () => this.ouvintes.delete(fn)
  }

  assinarLog(fn: (lote: LoteLog) => void): () => void {
    this.ouvintesLog.add(fn)
    return () => this.ouvintesLog.delete(fn)
  }

  // ── Entrega ────────────────────────────────────────────────────────────────

  /**
   * Marca que ha o que entregar e agenda o flush.
   *
   * Agendar em vez de entregar na hora e o que colapsa a rajada. O timer NAO e
   * reiniciado a cada chamada (isso seria debounce, e num executor falante o
   * flush nunca aconteceria): a janela e fixa a partir da primeira mudanca.
   */
  private agendar(): void {
    if (this.timer) return
    this.timer = setTimeout(() => {
      this.timer = null
      this.entregar()
    }, JANELA_MS)
  }

  private entregar(): void {
    if (this.estadoSujo) {
      this.estadoSujo = false
      for (const fn of this.ouvintes) {
        try { fn(this.estado) } catch { /* um ouvinte quebrado nao derruba os outros */ }
      }
    }
    if (this.pendentes.length > 0) {
      const lote: LoteLog = {
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
   * Entrega agora o que estiver pendente.
   *
   * Existe para o encerramento: um `state: failed` no ultimo instante de vida
   * do processo nao pode ficar preso num timer que nunca vai disparar.
   */
  descarregar(): void {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
    this.entregar()
  }

  // ── Escrita ────────────────────────────────────────────────────────────────

  aplicarEstadoSupervisor(estado: EstadoSupervisor, detalhe?: string): void {
    this.estado = { ...this.estado, supervisor: estado, detalheSupervisor: detalhe ?? null }
    // Um executor parado nao tem snapshot valido; manter o ultimo faria a UI
    // mostrar "conectado" com o processo morto.
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
        return   // log nao suja o estado; `errosNoLog` cuida do que ele afeta
      default:
        // ack, sync, conn e warn nao mudam o estado agregado, e nao ha mais
        // stream cru para o renderer: o que a UI mostra desses eventos ja vem
        // pelo snapshot (conn_state, contadores de sync) ou pelo log.
        return
    }
    this.estadoSujo = true
    this.agendar()
  }

  registrarLinhaBruta(texto: string, origem: 'stderr' | 'stdout'): void {
    this.registrarLog({
      seq: 0,
      ts: Date.now() / 1000,
      // O log humano do stderr ja vem formatado com o nivel embutido; nao ha o
      // que extrair sem parsear texto — que e exatamente o que este projeto
      // evita. Fica marcado como bruto e a UI o mostra sem colorir por nivel.
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

  private registrarLog(linha: LinhaLog): void {
    linha.seq = this.proximoSeq++

    // `push` e `shift`, e nao `[...log, linha]`: a copia do array inteiro a
    // cada linha era metade do custo quadratico. Ninguem observa este array por
    // identidade — o renderer recebe lotes, nao a referencia.
    this.log.push(linha)
    if (linha.level === 'ERROR') this.contarErro(+1)
    while (this.log.length > MAX_LOG) {
      const saiu = this.log.shift()
      if (saiu?.level === 'ERROR') this.contarErro(-1)
    }

    this.pendentes.push(linha)
    // Uma rajada maior que o buffer inteiro dentro de uma janela de 80ms não
    // deve virar um lote maior que o buffer: o excedente já foi descartado
    // acima e o renderer o jogaria fora de qualquer forma. `primeiroSeq`
    // continua denunciando o corte, e o outro lado recarrega.
    if (this.pendentes.length > MAX_LOG) {
      this.pendentes.splice(0, this.pendentes.length - MAX_LOG)
    }
  }

  /** Mantem `errosNoLog` sem varrer o buffer, e marca o estado para entrega. */
  private contarErro(delta: number): void {
    this.estado = { ...this.estado, errosNoLog: this.estado.errosNoLog + delta }
    this.estadoSujo = true
  }
}
