import { create } from 'zustand'
import { Edge } from '@xyflow/react'
import { INodeStatusWorkFlow, IStatusWorkflow, StatusNodeStatusWorkFlow, StatusWorkflow } from '@/context/useFlowContext'

/** Origem da linha — separada do ciclo de vida (`status`).
 *
 * Antes tudo vivia em `status` ("started"/"completed"/"failed" misturados com
 * "debug" e "log"), e o painel precisava filtrar por negação ("tudo que não é
 * erro nem print"). Com `kind` cada aba do painel tem um predicado direto.
 */
export type EventKind = 'lifecycle' | 'stdout' | 'debug'

/** Severidade — independente do ciclo de vida. */
export type EventLevel = 'info' | 'warn' | 'error'

/** Evento de execução normalizado, como chega do WebSocket ou do replay HTTP. */
export interface RunEvent {
  /** Ordem de chegada, atribuída pela store. É a `key` das linhas da aba
   *  "Bruto": chavear pelo índice do array fazia a rotação (que remove stdout
   *  do MEIO da lista) deslocar o índice de todos os sobreviventes, e o React
   *  desmontava/remontava milhares de linhas de uma vez. */
  seq: number
  /** Epoch ms do evento no BACKEND — não a hora de chegada no browser.
   *  Usar a hora local quebrava a linha do tempo no replay de re-anexação:
   *  o histórico inteiro ganhava o timestamp do momento da reconexão. */
  ts: number
  node?: string
  kind: EventKind
  level: EventLevel
  status?: string
  node_name?: string
  node_type?: string
  message?: string | null
  /** Linhas de `print()` de um evento de stdout AGREGADO (o executor junta a
   *  saída em janelas de ~200 ms em vez de emitir um evento por linha).
   *
   *  É a ÚNICA fonte de verdade da saída: o executor parou de repetir o mesmo
   *  texto em `message`, porque a duplicação estourava o teto de 64 KB do frame
   *  e o evento chegava reduzido aos campos de controle — o painel perdia as
   *  200 linhas do lote de uma vez, em silêncio. */
  lines?: string[] | null
  duration_ms?: number | null
  output_keys?: string[] | null
  debug_output?: Record<string, string> | null
  traceback?: string | null
  error_category?: string | null
  retryable?: boolean | null
  branch_result?: boolean
  cache_hit?: boolean
  schema_drift?: { missing: string[]; extra: string[] } | null
  /** Id do nó SubWorkflow do canvas, quando o evento veio de DENTRO de um
   *  sub-fluxo. Os nós do filho não existem no canvas do pai; sem isto a linha
   *  aparecia no painel sem dizer de onde veio, e clicar nela não fazia nada. */
  subworkflow_parent?: string | null
  raw: object
}

export type WsState = 'idle' | 'connecting' | 'open' | 'closed'

/** Teto de eventos mantidos na memória do painel.
 *
 *  Exportado porque o produtor (o buffer por quadro em `useExecuteWorkflow`)
 *  precisa do MESMO número: com a aba oculta o `requestAnimationFrame` não roda
 *  e o buffer cru cresceria sem limite antes de a rotação daqui ter chance de
 *  agir — um `for i in range(200000): print(i)` enchia centenas de MB. */
export const MAX_RUN_EVENTS = 2000

/** Payload cru do canal de eventos (WS ou histórico HTTP). */
export interface RawEvent {
  node?: string
  kind?: string
  level?: string
  status?: string
  timestamp?: number
  duration_ms?: number | null
  error?: string | null
  message?: string | null
  extra?: {
    node_name?: string
    node_type?: string
    message?: string
    lines?: string[]
    output_keys?: string[]
    output_columns?: Record<string, string[]>
    debug_output?: Record<string, string>
    traceback?: string
    error_category?: string
    retryable?: boolean
    branch_result?: boolean
    cache_hit?: boolean
    schema_drift?: { missing: string[]; extra: string[] }
    subworkflow_parent_node?: string
  } | null
}

/** Normaliza o payload do canal para `RunEvent`.
 *
 * `kind`/`level` são derivados de `status` quando ausentes: o histórico no Redis
 * tem TTL de 1h, então logo após um deploy ainda existem eventos publicados pelo
 * schema antigo circulando no replay.
 */
/** Origem da linha, com a derivação do schema antigo num lugar só.
 *
 *  Quem decide se um evento mexe no canvas usa exatamente esta função — apostar
 *  em `data.kind` cru trataria um `status:"debug"` sem `kind` (histórico do
 *  Redis, até 1h após deploy) como ciclo de vida. */
export function eventKind(data: RawEvent): EventKind {
  if (data.kind) return data.kind as EventKind
  if (data.status === 'log') return 'stdout'
  if (data.status === 'debug') return 'debug'
  return 'lifecycle'
}

export function toRunEvent(data: RawEvent): RunEvent {
  const status = data.status
  const kind = eventKind(data)
  const level: EventLevel =
    (data.level as EventLevel) ?? (status === 'failed' || status === 'error' ? 'error' : 'info')

  return {
    // Substituído por um valor monotônico em `appendEvents`/`loadHistoricalEvents`
    // — quem normaliza não conhece o contador do run.
    seq: 0,
    ts: data.timestamp != null ? data.timestamp * 1000 : Date.now(),
    node: data.node,
    kind,
    level,
    status,
    node_name: data.extra?.node_name,
    node_type: data.extra?.node_type,
    message: data.extra?.message ?? data.error ?? data.message ?? null,
    lines: data.extra?.lines ?? null,
    duration_ms: data.duration_ms ?? null,
    output_keys: data.extra?.output_keys ?? null,
    debug_output: data.extra?.debug_output ?? null,
    traceback: data.extra?.traceback ?? null,
    error_category: data.extra?.error_category ?? null,
    retryable: data.extra?.retryable ?? null,
    branch_result: data.extra?.branch_result,
    cache_hit: data.extra?.cache_hit,
    schema_drift: data.extra?.schema_drift ?? null,
    subworkflow_parent: data.extra?.subworkflow_parent_node ?? null,
    raw: data as object,
  }
}

/** Adjacência `origem → arestas`, memoizada pela identidade do array.
 *
 * Sem índice a BFS abaixo varria TODAS as arestas para cada nó visitado —
 * O(ramos × nós × arestas) a cada mensagem do WebSocket. O array de arestas vem
 * de `useEdges()` e só troca quando a topologia muda, então o WeakMap acerta em
 * praticamente toda chamada e libera a entrada sozinho quando o array morre.
 */
const adjacenciaPorArestas = new WeakMap<Edge[], Map<string, Edge[]>>()

function adjacencia(allEdges: Edge[]): Map<string, Edge[]> {
  let index = adjacenciaPorArestas.get(allEdges)
  if (index) return index
  index = new Map<string, Edge[]>()
  for (const edge of allEdges) {
    const lista = index.get(edge.source)
    if (lista) lista.push(edge)
    else index.set(edge.source, [edge])
  }
  adjacenciaPorArestas.set(allEdges, index)
  return index
}

function computeLosingBranches(statusNodes: INodeStatusWorkFlow[], allEdges: Edge[]) {
  const losingNodeIds = new Set<string>()
  const losingEdgeIds = new Set<string>()
  const porOrigem = adjacencia(allEdges)

  for (const node of statusNodes) {
    if (node.branch_result === undefined) continue
    const losingHandle = node.branch_result ? "false" : "true"
    // Índice de leitura no lugar de `queue.shift()`, que é O(n) em array e
    // tornava a BFS quadrática em ramos longos.
    const queue: string[] = []
    let head = 0
    for (const edge of porOrigem.get(node.id) ?? []) {
      if (edge.sourceHandle === losingHandle) {
        losingEdgeIds.add(edge.id)
        queue.push(edge.target)
      }
    }
    const visited = new Set<string>()
    while (head < queue.length) {
      const nodeId = queue[head++]
      if (visited.has(nodeId)) continue
      visited.add(nodeId)
      losingNodeIds.add(nodeId)
      for (const edge of porOrigem.get(nodeId) ?? []) {
        losingEdgeIds.add(edge.id)
        if (!visited.has(edge.target)) queue.push(edge.target)
      }
    }
  }
  return { losingNodeIds, losingEdgeIds }
}

/** Assinatura dos ramos já resolvidos — muda só quando um Conditional decide. */
function assinaturaDeRamos(statusNodes: INodeStatusWorkFlow[]): string {
  let assinatura = ""
  for (const node of statusNodes) {
    if (node.branch_result === undefined) continue
    assinatura += node.id + (node.branch_result ? "1" : "0") + "|"
  }
  return assinatura
}

/** Ramos perdedores com curto-circuito por (assinatura, identidade das arestas).
 *
 * A recomputação não é só cara: devolver Sets NOVOS a cada mensagem re-renderiza
 * todo nó e toda aresta que os assinam, mesmo quando nenhum Conditional decidiu
 * nada. Preservar a identidade é metade do ganho.
 */
let ultimaAssinatura: string | null = null
let ultimasArestas: Edge[] | null = null
let ultimosRamos = { losingNodeIds: new Set<string>(), losingEdgeIds: new Set<string>() }

function ramosPerdedores(statusNodes: INodeStatusWorkFlow[], allEdges: Edge[]) {
  const assinatura = assinaturaDeRamos(statusNodes)
  if (assinatura === ultimaAssinatura && allEdges === ultimasArestas) return ultimosRamos
  ultimaAssinatura = assinatura
  ultimasArestas = allEdges
  ultimosRamos = computeLosingBranches(statusNodes, allEdges)
  return ultimosRamos
}

/** Índice `id → estado` do canvas.
 *
 * Cada nó e cada aresta montava o PRÓPRIO Map sobre a lista inteira de nós, a
 * cada mensagem — o custo O(1) prometido pelo comentário multiplicado por N+E.
 * Aqui ele é construído uma vez, e os componentes assinam só a própria entrada.
 */
function indexarPorId(nodes: INodeStatusWorkFlow[]): Map<string, INodeStatusWorkFlow> {
  const index = new Map<string, INodeStatusWorkFlow>()
  for (const node of nodes) index.set(node.id, node)
  return index
}

/** Desfechos a partir dos quais o run é história: nada mais escreve no canvas.
 *
 *  O cliente aplica os eventos em LOTE, por quadro de `requestAnimationFrame`.
 *  Com a aba em segundo plano (ou a janela do desktop sem foco) o quadro não
 *  roda, mas o WebSocket continua entregando — então o lote fica pendente por
 *  tempo indeterminado enquanto o run termina e é liquidado. Quando o usuário
 *  volta, o quadro atrasado dispara e reaplica eventos ANTIGOS sobre um run já
 *  encerrado: o nó cujo último evento no lote era `started` volta a girar, e
 *  agora não há mais socket, nem `isExecuting`, nem quem o liquide de novo.
 *  Por isso o desfecho precisa ser definitivo aqui dentro, e não só no
 *  instante em que é decidido. */
export const RUN_ENCERRADO: ReadonlySet<string> = new Set(['completed', 'failed', 'cancelled'])

const SEM_STATUS: Map<string, INodeStatusWorkFlow> = new Map()

/** Aplica o teto de eventos descartando os `stdout` MAIS ANTIGOS.
 *
 * Eventos de ciclo de vida nunca são as vítimas: são a fonte do estado por nó na
 * aba "Nós", e jogá-los fora fazia um nó já concluído voltar a aparecer como
 * "aguardando" (contradizendo o próprio canvas) em runs que imprimem muito.
 * O corte é em bloco para amortizar o custo desta varredura.
 */
function rotacionar(eventos: RunEvent[]): { events: RunEvent[]; dropped: number } {
  if (eventos.length <= MAX_RUN_EVENTS) return { events: eventos, dropped: 0 }

  const bloco = Math.floor(MAX_RUN_EVENTS * 0.2)
  const alvo = eventos.length - MAX_RUN_EVENTS + bloco
  const kept: RunEvent[] = []
  let dropped = 0
  for (const candidate of eventos) {
    if (dropped < alvo && candidate.kind === "stdout") {
      dropped++
      continue
    }
    kept.push(candidate)
  }
  // Sem stdout suficiente para liberar espaço (workflow gigante, quase tudo
  // ciclo de vida): cai no descarte cronológico puro.
  if (kept.length > MAX_RUN_EVENTS) {
    const corte = Math.min(kept.length, kept.length - MAX_RUN_EVENTS + bloco)
    kept.splice(0, corte)
    dropped += corte
  }
  return { events: kept, dropped }
}

interface WorkflowExecutionState {
  statusWorkflow: IStatusWorkflow | null
  /** Estado por nó, indexado. Os cards e as arestas assinam UMA entrada daqui
   *  em vez do objeto `statusWorkflow` inteiro — assim só re-renderiza quem de
   *  fato mudou. Sempre presente (Map vazio antes do primeiro run). */
  statusById: Map<string, INodeStatusWorkFlow>
  losingNodeIds: Set<string> | undefined
  losingEdgeIds: Set<string> | undefined
  debugMode: boolean
  isExecuting: boolean
  events: RunEvent[]
  /** Estado real do socket — o indicador "ao vivo" do painel lê daqui.
   *  Antes ele lia `isExecuting`, que é um proxy: socket morto continuava verde. */
  wsState: WsState
  /** Run cujos eventos estão carregados. Pode ser um run histórico (concluído)
   *  aberto pelo painel, não necessariamente o run em execução. */
  viewingRunId: string | null
  /** true quando os eventos vieram do endpoint HTTP e não de um run ao vivo. */
  isHistorical: boolean
  /** Quantas linhas de saída foram descartadas — pela rotação LOCAL e pelo
   *  back-pressure do SERVIDOR (campo `dropped` do frame de eventos). Exibido na
   *  aba "Bruto" — truncar em silêncio faz o painel parecer completo quando não
   *  é, e o descarte do servidor é justamente o que o usuário não tem como
   *  perceber sozinho. */
  droppedEvents: number
  /** Epoch ms do primeiro evento do run, fixado na chegada.
   *  Guardado fora de `events` porque a lista tem rotação: derivar o início do
   *  primeiro item sobrevivente deslocaria todos os offsets `+Xs` do painel. */
  runStartedTs: number | null
  /** Nós SubWorkflow do canvas que já executaram algo lá dentro.
   *
   *  Mantido aqui, e alimentado a O(1) por evento, porque o canvas precisa da
   *  resposta por nó: varrer `events` num selector custaria uma passada pela
   *  lista inteira, por nó SubWorkflow, a cada mensagem do WebSocket. Sobrevive
   *  à rotação de `events` de propósito — o nó não deixa de ter sido executado
   *  porque o evento mais antigo foi descartado. */
  subflowRoots: Set<string>
  /** Contador de `seq`. Zerado junto com a lista de eventos. */
  eventSeq: number
  /** Desfecho do run (`__workflow_complete__`), guardado a O(1) na chegada.
   *
   *  Existe para a barra do painel poder dizer "concluído em 3,2 s" SEM que
   *  ninguém precise reconstruir a linha do tempo — com o painel fechado essa
   *  reconstrução era trabalho puro de CPU que nunca chegava à tela. */
  runOutcome: RunOutcome | null
}

export interface RunOutcome {
  status: "completed" | "failed" | "cancelled"
  durationMs: number | null
  error: string | null
  category: string | null
  retryable: boolean | null
}

/** Id sintético que o backend usa para sinalizar o fim do run.
 *  Repetido aqui (e não importado de run-panel/timeline) para a store não
 *  depender de um componente. */
const WF_COMPLETE = "__workflow_complete__"

function desfechoDoEvento(event: RunEvent): RunOutcome | null {
  if (event.node !== WF_COMPLETE) return null
  return {
    status: event.status === "failed" ? "failed" : event.status === "cancelled" ? "cancelled" : "completed",
    durationMs: event.duration_ms ?? null,
    error: event.message ?? null,
    category: event.error_category ?? null,
    retryable: event.retryable ?? null,
  }
}

interface WorkflowExecutionActions {
  startExecution(nodes: INodeStatusWorkFlow[]): void
  setTaskId(taskId: string): void
  updateNodeStatuses(nodes: INodeStatusWorkFlow[], allEdges: Edge[]): void
  completeExecution(status: StatusWorkflow, nodes: INodeStatusWorkFlow[], allEdges: Edge[]): void
  failExecution(): void
  resetExecution(): void
  setDebugMode(v: boolean): void
  setWsState(v: WsState): void
  /** Anexa um LOTE de eventos com uma única cópia do array.
   *
   *  Um evento por `set()` fazia `[...events, event]` por mensagem — O(H²) no
   *  acumulado, e no replay de re-anexação (milhares de eventos) isso sozinho
   *  congelava a aba. O produtor agrupa por quadro e entrega tudo de uma vez. */
  appendEvents(events: RunEvent[]): void
  /** Soma ao contador de descarte os eventos que o SERVIDOR jogou fora por
   *  back-pressure (o buffer de 500 slots do WebSocket evicta o stdout mais
   *  antigo e informa quantos no campo `dropped` do frame).
   *
   *  Sem isto o aviso âmbar da aba "Bruto" contava só a rotação local: o painel
   *  afirmava estar completo enquanto centenas de linhas de `print()` tinham
   *  sido descartadas no caminho. */
  registrarDescartados(quantidade: number): void
  clearEvents(): void
  loadHistoricalEvents(runId: string, events: RunEvent[]): void
}

export const useWorkflowExecutionStore = create<WorkflowExecutionState & WorkflowExecutionActions>((set) => ({
  statusWorkflow: null,
  statusById: SEM_STATUS,
  losingNodeIds: undefined,
  losingEdgeIds: undefined,
  debugMode: false,
  isExecuting: false,
  events: [],
  wsState: 'idle',
  viewingRunId: null,
  isHistorical: false,
  droppedEvents: 0,
  runStartedTs: null,
  subflowRoots: new Set(),
  eventSeq: 0,
  runOutcome: null,

  startExecution: (nodes) => {
    const iniciais = nodes.map(n => ({ ...n, status: 'idle' as const }))
    set({
      isExecuting: true,
      wsState: 'connecting',
      statusWorkflow: {
        status: 'queued',
        nodes: iniciais,
      },
      statusById: indexarPorId(iniciais),
      losingNodeIds: undefined,
      losingEdgeIds: undefined,
      // Zera os eventos da execução anterior — painel deve começar limpo.
      events: [],
      droppedEvents: 0,
      runStartedTs: null,
      viewingRunId: null,
      isHistorical: false,
      subflowRoots: new Set(),
      eventSeq: 0,
      runOutcome: null,
    })
  },

  setTaskId: (taskId) => {
    set(state => ({
      viewingRunId: taskId,
      statusWorkflow: state.statusWorkflow ? {
        ...state.statusWorkflow,
        task_id: taskId,
        status: 'running' as const,
      } : null,
    }))
  },

  updateNodeStatuses: (nodes, allEdges) => {
    set(state => {
      // Um run encerrado não volta atrás. Ver `RUN_ENCERRADO`: sem esta guarda,
      // um lote atrasado devolvia o nó a `started` E o workflow a `running`,
      // deixando o anel azul girando para sempre num run já concluído.
      if (state.statusWorkflow && RUN_ENCERRADO.has(state.statusWorkflow.status)) {
        return {}
      }
      const { losingNodeIds, losingEdgeIds } = ramosPerdedores(nodes, allEdges)
      return {
        statusWorkflow: state.statusWorkflow ? {
          ...state.statusWorkflow,
          status: 'running' as const,
          nodes,
        } : null,
        statusById: indexarPorId(nodes),
        losingNodeIds,
        losingEdgeIds,
      }
    })
  },

  completeExecution: (status, nodes, allEdges) => {
    // O run acabou: nenhum nó pode continuar em `started`. Antes só o
    // cancelamento liquidava, e por isso um `completed` de nó perdido no
    // caminho (o socket cai sem aviso, o servidor evicta sob pressão, o
    // executor descarta com a fila cheia) deixava aquele nó girando PARA
    // SEMPRE — com o run já marcado como concluído no painel e no dashboard.
    //
    // Os dois desfechos são diferentes e não podem ser confundidos:
    //   cancelled → o trabalho foi interrompido de fato; volta a `idle`.
    //   demais    → o nó provavelmente terminou e a notícia é que se perdeu;
    //               vira `unknown`, que a UI mostra como "resultado não
    //               recebido". Pintar de verde seria inventar um resultado.
    const paradoComo: StatusNodeStatusWorkFlow = status === 'cancelled' ? 'idle' : 'unknown'
    const settled = nodes.some(n => n.status === 'started')
      ? nodes.map(n => (n.status === 'started' ? { ...n, status: paradoComo } : n))
      : nodes
    const { losingNodeIds, losingEdgeIds } = ramosPerdedores(settled, allEdges)
    set(state => ({
      statusWorkflow: {
        status,
        // Preserva o task_id: o painel usa para oferecer "ver na observabilidade"
        // e para recarregar os eventos deste run depois de concluído.
        task_id: state.statusWorkflow?.task_id,
        nodes: settled,
      },
      statusById: indexarPorId(settled),
      losingNodeIds,
      losingEdgeIds,
      isExecuting: false,
      wsState: 'closed',
    }))
  },

  failExecution: () => {
    set(state => {
      // Mesmo invariante do `completeExecution`: o run fechou, então nenhum nó
      // sobrevive em `started`. Sem isto, esgotar as reconexões encerrava o
      // painel mas deixava os nós girando — o sintoma que se queria eliminar,
      // reintroduzido pelo caminho da desistência.
      const nodes = state.statusWorkflow?.nodes ?? []
      const settled = nodes.some(n => n.status === 'started')
        ? nodes.map(n => (n.status === 'started' ? { ...n, status: 'unknown' as const } : n))
        : nodes
      return {
        statusWorkflow: state.statusWorkflow ? {
          ...state.statusWorkflow,
          status: 'failed' as const,
          nodes: settled,
        } : null,
        statusById: state.statusWorkflow ? indexarPorId(settled) : state.statusById,
        isExecuting: false,
        wsState: 'closed',
        losingNodeIds: undefined,
        losingEdgeIds: undefined,
      }
    })
  },

  resetExecution: () => {
    set({
      statusWorkflow: null,
      statusById: SEM_STATUS,
      losingNodeIds: undefined,
      losingEdgeIds: undefined,
      // `debugMode` NÃO entra aqui: é preferência do usuário, não estado de run.
      // Como o botão Executar limpa o run anterior antes de disparar o novo,
      // resetá-lo aqui apagava o toggle amarelo no exato clique em que o debug
      // deveria valer — o request saía em debug, mas a UI dizia o contrário.
      isExecuting: false,
      wsState: 'idle',
      // Limpa eventos também — sem isso, ao trocar de workflow os logs do
      // anterior continuavam visíveis no painel até a próxima execução.
      events: [],
      droppedEvents: 0,
      runStartedTs: null,
      viewingRunId: null,
      isHistorical: false,
      subflowRoots: new Set(),
      eventSeq: 0,
      runOutcome: null,
    })
  },

  setDebugMode: (v) => {
    set({ debugMode: v })
  },

  setWsState: (v) => {
    set({ wsState: v })
  },

  appendEvents: (lote) => {
    if (lote.length === 0) return
    set(state => {
      let eventSeq = state.eventSeq
      let runStartedTs = state.runStartedTs
      let runOutcome = state.runOutcome
      // Um Set novo só quando entra alguém: recriá-lo a cada lote faria todo nó
      // que consulta este conjunto re-renderizar a cada quadro.
      let subflowRoots = state.subflowRoots
      for (const event of lote) {
        // Os eventos do lote acabaram de sair de `toRunEvent`, nesta mesma
        // volta do loop de eventos — ninguém mais os viu, numerá-los aqui é a
        // única forma de o contador ser o da store.
        event.seq = eventSeq++
        runStartedTs ??= event.ts
        const pai = event.subworkflow_parent
        if (pai && !subflowRoots.has(pai)) {
          if (subflowRoots === state.subflowRoots) subflowRoots = new Set(state.subflowRoots)
          subflowRoots.add(pai)
        }
        runOutcome = desfechoDoEvento(event) ?? runOutcome
      }

      // Uma cópia por lote — não uma por evento.
      const { events, dropped } = rotacionar(state.events.concat(lote))
      return {
        events,
        droppedEvents: dropped > 0 ? state.droppedEvents + dropped : state.droppedEvents,
        runStartedTs,
        subflowRoots,
        eventSeq,
        runOutcome,
      }
    })
  },

  registrarDescartados: (quantidade) => {
    if (!(quantidade > 0)) return
    set(state => ({ droppedEvents: state.droppedEvents + quantidade }))
  },

  clearEvents: () => {
    set({ events: [], droppedEvents: 0, runStartedTs: null, subflowRoots: new Set(), eventSeq: 0, runOutcome: null })
  },

  loadHistoricalEvents: (runId, events) => {
    const subflowRoots = new Set<string>()
    let runOutcome: RunOutcome | null = null
    for (const event of events) {
      if (event.subworkflow_parent) subflowRoots.add(event.subworkflow_parent)
      runOutcome = desfechoDoEvento(event) ?? runOutcome
    }
    // O mesmo teto do caminho ao vivo: o endpoint devolve até 5000 eventos e
    // renderizá-los todos de uma vez travava a aba por segundos — o caminho
    // histórico não pode ser pior que o ao vivo.
    const { events: mantidos, dropped } = rotacionar(events)
    let seq = 0
    for (const event of mantidos) event.seq = seq++
    set({
      events: mantidos,
      droppedEvents: dropped,
      runStartedTs: events.length > 0 ? events[0].ts : null,
      viewingRunId: runId,
      isHistorical: true,
      wsState: 'idle',
      subflowRoots,
      eventSeq: seq,
      runOutcome,
    })
  },
}))
