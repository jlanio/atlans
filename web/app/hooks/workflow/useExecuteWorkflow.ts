import { useParams } from "next/navigation"
import { useSaveWorkflow } from "./useSaveWorkflow"
import { useEffect, useRef } from "react"
import { useSession } from "next-auth/react"
import { INodeContext, INodeStatusWorkFlow, StatusWorkflow } from "@/context/useFlowContext"
import { createToast } from "@/utils/createToast"
import { dayjs } from "@/lib/dayjs"
import { useNodes, useEdges, useReactFlow, Edge } from "@xyflow/react"
import { GisFlowService } from "@/service/GisFlowService"
import { getWsUrl } from "@/utils/env"
import { useWorkflowExecutionStore, toRunEvent, eventKind, RawEvent, MAX_RUN_EVENTS, RUN_ENCERRADO } from "@/app/stores/workflowExecutionStore"
import { useKnownColumnsStore } from "@/app/stores/knownColumnsStore"

/** Id sintético que o backend usa para sinalizar o fim do run. */
const WF_COMPLETE = "__workflow_complete__"

/** Tentativas de reconexão antes de desistir do acompanhamento ao vivo.
 *  Com backoff exponencial até 15s, cobre ~2 minutos de instabilidade. */
const MAX_RECONEXOES = 8

/** Silêncio máximo tolerado no socket antes de assumi-lo morto e recuperar.
 *
 *  O servidor manda um heartbeat (lote vazio) a cada ~20s durante o run, então
 *  uma conexão saudável nunca passa nem perto disto. Só estoura quando o socket
 *  morreu de fato — o caso do Safari, que derruba WebSocket ocioso SEM disparar
 *  `onclose`: sem este watchdog, a reconexão (que vive no `onclose`) nunca era
 *  acionada e o painel girava para sempre. É a rede de segurança do transporte;
 *  o heartbeat do servidor é a prevenção. */
const SILENCIO_MAX_MS = 50_000
const WATCHDOG_INTERVALO_MS = 15_000

/** Status do run no backend → status do painel. Só os terminais entram: os
 *  demais significam "ainda vivo", e a ausência aqui é o próprio teste. */
const DESFECHO_TERMINAL: Record<string, StatusWorkflow> = {
  success:   "completed",
  failed:    "failed",
  cancelled: "cancelled",
}

/** Ponte para o DONO do socket.
 *
 *  Este hook é montado em mais de um lugar ao mesmo tempo — o botão Executar do
 *  canvas e a aba "Testar" do nó Webhook, dentro do modal de configuração.
 *  Todos podem DISPARAR um run, mas só um pode governar o socket: a store de
 *  execução é global, então uma segunda instância abria um WebSocket
 *  concorrente, escrevia no mesmo `wsState` e, ao montar durante um run, ainda
 *  chamava `startExecution`, zerando o canvas de quem já estava acompanhando.
 *  Quem dispara sem ser dono entrega o task_id para o dono anexar. */
let anexarNoDono: ((taskId: string) => void) | null = null

/** Item do buffer por quadro, com o run de origem carimbado.
 *
 *  O carimbo existe porque um flush atrasado é assíncrono por natureza: o rAF
 *  agendado enquanto o usuário estava no workflow A dispara DEPOIS da troca para
 *  B. Sem o carimbo, os eventos de A caíam na store recém-limpa de B. */
interface ItemDoLote {
  runId: string
  data: RawEvent
}

export const useExecuteWorkflow = () => {

  const { saveWorkflow } = useSaveWorkflow()
  const { id } = useParams<{ id: string }>()
  const nodes = useNodes<INodeContext>()
  const edges = useEdges<Edge>()
  const reactFlowInstance = useReactFlow<INodeContext, Edge>()
  // Refs sempre sincronizadas — a primeira execução do workflow acontecia
  // com closures staled capturadas ANTES do canvas hidratar (nodes=[]).
  // Resultado: initialNodes virava vazio e o feedback visual no canvas não
  // aparecia na 1ª exec. Lendo via ref, qualquer closure consome o valor
  // mais recente no momento do click.
  const nodesRef = useRef(nodes)
  useEffect(() => { nodesRef.current = nodes }, [nodes])
  const edgesRef = useRef(edges)
  useEffect(() => { edgesRef.current = edges }, [edges])
  // WS ativo do run (disparo OU re-anexação). Mantido em ref para (a) fechar a
  // conexão anterior antes de abrir outra e (b) fechar ao trocar de workflow —
  // evita conexões duplicadas/órfãs alimentando a store ao mesmo tempo.
  const wsRef = useRef<WebSocket | null>(null)
  // Se ESTA montagem disparou um run pelo botão. A re-anexação usa isto (e NÃO
  // o isExecuting global, que é volátil e sobra entre acessos) para decidir se
  // deve re-anexar — evita clobberar um run recém-disparado.
  const sessionTriggeredRef = useRef(false)
  const { data: session } = useSession()

  // Acessa store para isExecuting e debugMode
  const isExecuting = useWorkflowExecutionStore(s => s.isExecuting)
  const debugMode = useWorkflowExecutionStore(s => s.debugMode)
  const setDebugMode = useWorkflowExecutionStore(s => s.setDebugMode)

  // Lote do quadro atual. Cada mensagem do WS é uma macrotask própria, então
  // sem isto o React não conseguia agrupar nada: um replay de 5000 eventos
  // virava 5000 ciclos de render do canvas inteiro, em sequência, na mesma
  // thread — a aba congelava por segundos ao reabrir um run em andamento.
  const bufferRef = useRef<ItemDoLote[]>([])
  const frameRef = useRef<number | null>(null)
  // Run cujo socket está ativo AGORA. É o gate do flush: um rAF pendente do
  // workflow A que dispare depois da troca para B encontra aqui outro id (ou
  // null) e não despeja nada na store de B. Assim a corretude deixa de depender
  // de todos os caminhos de limpeza estarem certos.
  const runAtivoRef = useRef<string | null>(null)
  // Drenagem síncrona do attach ativo. Vive numa ref porque quem precisa dela
  // (o listener de visibilidade, registrado uma vez na montagem) não conhece a
  // closure de `attachToRun`.
  const drenarAgoraRef = useRef<() => void>(() => {})

  // ── Recuperação do stream ────────────────────────────────────────────────
  // Nada aqui existia antes, e a ausência era o bug: o cliente tratava o canal
  // como se fosse sem perdas, quando toda camada do caminho pode descartar
  // evento e o socket pode morrer sem aviso.
  const reconexaoRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const tentativasRef = useRef(0)
  // Sockets que NÓS fechamos (fim do run, troca de workflow, novo attach).
  // O close code não serve para distinguir: o servidor encerra com 1000 em todo
  // caminho normal — inclusive quando a assinatura do Redis termina sem o run
  // ter acabado, que é exatamente o caso que precisa reconectar.
  const fechadosDePropositoRef = useRef(new WeakSet<WebSocket>())
  // Watchdog de inatividade: horário da última mensagem recebida e o timer que
  // vigia o silêncio. Existe porque no Safari um socket morto não dispara
  // `onclose` — sem isto, a queda passava despercebida e o painel girava para
  // sempre. Ver `SILENCIO_MAX_MS`.
  const ultimaMsgRef = useRef(0)
  const watchdogRef = useRef<ReturnType<typeof setInterval> | null>(null)

  function fecharDeProposito(sock: WebSocket | null | undefined) {
    if (!sock) return
    fechadosDePropositoRef.current.add(sock)
    sock.close(1000)
  }

  function cancelarReconexao() {
    if (reconexaoRef.current != null) {
      clearTimeout(reconexaoRef.current)
      reconexaoRef.current = null
    }
  }

  function pararWatchdog() {
    if (watchdogRef.current != null) {
      clearInterval(watchdogRef.current)
      watchdogRef.current = null
    }
  }

  /** Vigia o silêncio do socket. No Safari uma conexão morta não dispara
   *  `onclose`; aqui detectamos pela ausência de tráfego e tratamos como queda:
   *  fecha (para um `onclose` tardio não duplicar) e cai na recuperação, que
   *  reconcilia pela API ou reconecta e reconstrói pelo replay do Redis. */
  function iniciarWatchdog(sock: WebSocket, taskId: string) {
    pararWatchdog()
    watchdogRef.current = setInterval(() => {
      if (wsRef.current !== sock) return          // socket já substituído
      if (runAtivoRef.current !== taskId) return
      if (!useWorkflowExecutionStore.getState().isExecuting) return
      if (Date.now() - ultimaMsgRef.current <= SILENCIO_MAX_MS) return
      console.warn(
        `[ws/workflow] ${taskId} sem tráfego há >${SILENCIO_MAX_MS}ms — ` +
        "socket presumido morto (Safari não dispara onclose) — recuperando",
      )
      pararWatchdog()
      fecharDeProposito(sock)
      if (wsRef.current === sock) wsRef.current = null
      recuperarStream(taskId).catch(err =>
        console.error("[ws/workflow] falha ao recuperar o stream", err),
      )
    }, WATCHDOG_INTERVALO_MS)
  }

  /** Fecha o painel com o desfecho REAL do run, perguntando à API.
   *
   *  Devolve true quando o run já terminou (e o painel foi encerrado). É a rede
   *  de segurança para o `__workflow_complete__` que não chegou: o banco sabe o
   *  desfecho mesmo quando o canal ao vivo falhou. */
  async function reconciliarRun(taskId: string): Promise<boolean> {
    try {
      const detail = await GisFlowService.getRunDetail(taskId)
      const desfecho = DESFECHO_TERMINAL[detail?.data?.status ?? ""]
      if (!desfecho) return false
      const store = useWorkflowExecutionStore.getState()
      if (!store.isExecuting) return true
      // `completeExecution` liquida os nós presos: eles começaram, o run
      // acabou, e o término deles não chegou — viram `unknown`, não verde.
      store.completeExecution(desfecho, store.statusWorkflow?.nodes ?? [], edgesRef.current)
      return true
    } catch {
      // Rede ruim: não dá para afirmar nada sobre o run. Deixa a reconexão
      // tentar — afirmar "falhou" aqui seria inventar um desfecho.
      return false
    }
  }

  /** O stream caiu com o run ainda aberto: descobre se ele já acabou e, se não,
   *  reconecta com backoff. Ao reconectar, o replay do histórico reconstrói o
   *  que se perdeu na janela — por isso reconectar é barato e correto. */
  async function recuperarStream(taskId: string) {
    // Aplica AGORA o que já chegou. O quadro do `requestAnimationFrame` pode
    // estar pendente há muito tempo (aba em segundo plano não o executa) e
    // esses eventos são informação legítima: precisam entrar no canvas ANTES
    // da liquidação, para que `completeExecution` decida sobre o estado mais
    // recente. Depois dela o lote vira lixo — e é descartado logo abaixo.
    drenarAgoraRef.current()
    if (await reconciliarRun(taskId)) {
      // O run foi liquidado. Qualquer coisa ainda no buffer (ou um quadro já
      // agendado) reescreveria o canvas por cima do desfecho, ressuscitando em
      // `started` um nó que acabou de ser resolvido.
      descartarLote()
      return
    }
    // `reconciliarRun` tem um await no meio: durante ele o usuário pode ter
    // trocado de workflow, ou um `attachToRun` pode já ter reaberto o socket
    // (o botão Executar, a re-anexação). Reconectar por cima abriria uma
    // segunda conexão para o mesmo run.
    if (runAtivoRef.current !== taskId) return
    if (wsRef.current) return

    if (tentativasRef.current >= MAX_RECONEXOES) {
      // Desistir do AO VIVO não é desistir do run: ele segue no servidor. Dizer
      // isso é o que separa "perdi a conexão" de "seu workflow falhou".
      useWorkflowExecutionStore.getState().failExecution()
      createToast.error(
        "Acompanhamento ao vivo interrompido",
        "A execução continua no servidor. Recarregue a página ou acompanhe pela observabilidade.",
      )
      return
    }

    const base = Math.min(1000 * 2 ** tentativasRef.current, 15_000)
    tentativasRef.current += 1
    cancelarReconexao()
    // Jitter de 50-100%, como no backoff do executor: várias abas que caíram
    // juntas não voltam em rajada contra o mesmo servidor.
    reconexaoRef.current = setTimeout(() => {
      reconexaoRef.current = null
      // O usuário pode ter trocado de workflow — ou reconectado por outra via —
      // durante a espera.
      if (runAtivoRef.current !== taskId || wsRef.current) return
      attachToRun(taskId)
    }, base * (0.5 + Math.random() * 0.5))
  }

  // Descarta o lote pendente. Chamada nos TRÊS pontos de saída (novo attach,
  // troca de workflow, desmontagem): fechar o WebSocket não impede um flush já
  // agendado de rodar no quadro seguinte com os eventos do run anterior.
  function descartarLote() {
    bufferRef.current = []
    runAtivoRef.current = null
    cancelarReconexao()
    pararWatchdog()
    if (frameRef.current != null) {
      cancelAnimationFrame(frameRef.current)
      frameRef.current = null
    }
  }

  // Quem chegou primeiro governa o socket; os demais só disparam. Ref sempre
  // fresca porque `attachToRun` é recriada a cada render.
  const souDonoRef = useRef(false)
  const attachRef = useRef<(taskId: string) => void>(() => {})
  attachRef.current = (taskId: string) => { attachToRun(taskId) }

  useEffect(() => {
    if (anexarNoDono === null) {
      souDonoRef.current = true
      anexarNoDono = (taskId) => attachRef.current(taskId)
    }
    return () => {
      if (souDonoRef.current) {
        anexarNoDono = null
        souDonoRef.current = false
      }
    }
  }, [])

  useEffect(() => {
    // Com a aba em segundo plano o navegador NÃO executa callbacks de
    // `requestAnimationFrame` (idem no Electron, com backgroundThrottling
    // ligado): o lote ficaria preso no buffer, crescendo sem teto, até o usuário
    // voltar. Drenar ao esconder a aba entrega o que já chegou e esvazia tudo.
    const aoTrocarVisibilidade = () => {
      if (document.visibilityState === "hidden") drenarAgoraRef.current()
    }
    document.addEventListener("visibilitychange", aoTrocarVisibilidade)
    return () => {
      document.removeEventListener("visibilitychange", aoTrocarVisibilidade)
      descartarLote()
    }
    // Só na montagem/desmontagem. `descartarLote` é recriada a cada render, mas
    // opera exclusivamente sobre refs — declará-la como dependência
    // re-registraria o listener a cada render sem mudar nada.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleExecuteWorkflow(inputs: Record<string, unknown> = {}) {

    const store = useWorkflowExecutionStore.getState()
    if (store.isExecuting)
      return
    // Marca que esta montagem disparou um run — a re-anexação usa isto para não
    // clobberar o run recém-disparado caso sua descoberta esteja em voo.
    sessionTriggeredRef.current = true

    // Feedback visual imediato — canvas reage em <16ms, antes do save/POST.
    // Fonte dos nós em ordem de prioridade:
    //   1. nodesRef.current — hook useNodes via ref (evita closure stale)
    //   2. reactFlowInstance.getNodes() — fallback se ref ainda vazio no 1º click
    //      (hidrata direto do store interno do React Flow, sempre atualizado)
    // Sem esse fallback o store ficava com nodes=[] e nenhum evento do WS
    // encontrava match (ver [ws/workflow] evento sem match de node_id).
    const liveNodes = nodesRef.current.length > 0
      ? nodesRef.current
      : reactFlowInstance.getNodes()
    const initialNodes = liveNodes.map((node) => ({
      ...node,
      id: node.id,
      status: "idle" as const,
    }))
    if (initialNodes.length === 0) {
      createToast.error("Canvas vazio", "Carregue o workflow antes de executar.")
      return
    }
    store.startExecution(initialNodes)

    const respSave = await saveWorkflow({ silent: true })

    if (respSave?.error) {
      store.resetExecution()
      return
    }

    const respExec = await executeWorkflow(inputs)

    if (respExec?.error) {
      createToast.error("Ocorreu um erro no workflow!", respExec?.error.message)
      store.resetExecution()
      return
    }

    // Defesa extra: se o backend não devolveu task_id, nunca abrir WS com
    // "undefined" na URL (seria 4404 garantido). Trata como erro e para.
    const taskId = respExec?.data?.task_id
    if (!taskId) {
      console.error("[useExecuteWorkflow] POST /execute retornou sem task_id", respExec)
      createToast.error("Falha ao iniciar workflow", "Servidor não retornou task_id.")
      store.resetExecution()
      return
    }

    // Se esta instância não é a dona do socket (o disparo veio da aba "Testar"
    // do webhook, por exemplo), entrega o run para quem governa — em vez de
    // abrir um segundo socket sobre a mesma store.
    ;(anexarNoDono ?? attachToRun)(taskId)
  }

  // Abre o WebSocket de um run e instala os handlers que alimentam a store
  // (animação dos nós + console de execução). Usada tanto no disparo quanto na
  // re-anexação a um run já em andamento — ao conectar, o backend faz replay de
  // todo o histórico do run (Redis) e depois transmite ao vivo. Retorna o socket
  // para o chamador poder fechá-lo (ex.: ao trocar de workflow).
  function attachToRun(taskId: string): WebSocket {
    // Fecha qualquer conexão anterior (intencional) antes de abrir a nova, para
    // não haver dois WS escrevendo na store simultaneamente.
    fecharDeProposito(wsRef.current)
    // Descarta o que sobrou do run anterior: um flush pendente aplicaria
    // eventos de outro run (e fecharia o socket errado) no próximo quadro.
    descartarLote()
    const ws = new WebSocket(`${getWsUrl()}/ws/workflow/${taskId}`)
    wsRef.current = ws
    runAtivoRef.current = taskId
    drenarAgoraRef.current = drenarAgora

    useWorkflowExecutionStore.getState().setWsState("connecting")

    ws.onopen = () => {
      const token = session?.user?.access_token ?? ""
      if (token) ws.send(token)
      // Estado REAL do socket — o indicador "ao vivo" do painel lê daqui em vez
      // de inferir de isExecuting, que continuava verde com o socket morto.
      useWorkflowExecutionStore.getState().setWsState("open")
      // Conexão de pé: o próximo tropeço recomeça o backoff do zero.
      tentativasRef.current = 0
      // Arma o watchdog de inatividade. O `onopen` já é tráfego; a partir daqui
      // o servidor manda heartbeat a cada ~20s, então o silêncio só cresce se o
      // socket morreu (Safari) — e aí o watchdog recupera.
      ultimaMsgRef.current = Date.now()
      iniciarWatchdog(ws, taskId)
    }

    // Transição queued → running com task_id real
    useWorkflowExecutionStore.getState().setTaskId(taskId)

    // Aplica o lote acumulado no quadro: uma passada pelos nós, um
    // `updateNodeStatuses`, um `appendEvents`. Antes cada mensagem pagava
    // sozinha o mapa de TODOS os nós, o recálculo dos ramos perdedores sobre
    // TODAS as arestas e uma cópia do array de eventos.
    function drenarLote() {
      const bruto = bufferRef.current
      bufferRef.current = []
      if (bruto.length === 0) return
      // Só entra o que é do run ativo. Sem este filtro, o rAF pendente do
      // workflow A rodava depois da troca para B e despejava o log de A na store
      // de B — inclusive o `__workflow_complete__` de A, que fechava o painel de
      // B com "Concluído · 0 nós" para um workflow que nunca executou.
      const ativo = runAtivoRef.current
      const lote = bruto.filter(item => item.runId === ativo).map(item => item.data)
      if (lote.length === 0) return

      // Alimenta o painel de execução via store — conexão WS única (antes havia
      // um segundo WS dentro do componente de log, para o mesmo run_id).
      // `toRunEvent` normaliza kind/level e converte o timestamp do BACKEND:
      // carimbar com a hora local quebrava a linha do tempo no replay de
      // re-anexação, que reentrega o histórico inteiro de uma vez.
      // Entra ANTES do filtro por `kind` abaixo, para que stdout e debug (que
      // não mexem no canvas) também apareçam no painel.
      const store = useWorkflowExecutionStore.getState()
      store.appendEvents(lote.map(toRunEvent))

      // Lê o state DEPOIS do append — e uma vez só por quadro.
      const current = useWorkflowExecutionStore.getState()
      let currentNodes = current.statusWorkflow?.nodes ?? []
      let porId = current.statusById
      // Recuperação defensiva: se o store ainda está vazio (initialNodes não
      // hidratou a tempo no click), repopula a partir do React Flow.
      if (currentNodes.length === 0 && lote.some(d => d.node && !d.node.startsWith("__"))) {
        const live = reactFlowInstance.getNodes().map((n) => ({
          ...n,
          id: n.id,
          status: "idle" as const,
        }))
        if (live.length > 0) {
          currentNodes = live
          porId = new Map(live.map(n => [n.id, n as INodeStatusWorkFlow]))
        }
      }

      // Só o CICLO DE VIDA mexe no estado dos nós. Linhas de `print()` chegam
      // com kind="stdout" e status="log": aplicá-las como status apagava o
      // `started` do nó (o anel azul sumia no primeiro print) e ainda arrastava
      // toda a cascata de re-render sobre nós e arestas.
      const alterados = new Map<string, INodeStatusWorkFlow>()
      // Colunas para a store de sugestões — que vive FORA do ciclo do run.
      // `null` = o nó completou SEM publicar colunas (saída não-tabular, ou a
      // chave cortada no transporte): a entrada dele é apagada lá, porque
      // manter o valor antigo afirmaria colunas que este run não produziu.
      const colunasDoLote = new Map<string, Record<string, string[]> | null>()
      let fim: RawEvent | null = null
      for (const data of lote) {
        if (data.node === WF_COMPLETE) {
          fim = data
          continue
        }
        if (eventKind(data) !== "lifecycle") continue
        const base = alterados.get(data.node ?? "") ?? porId.get(data.node ?? "")
        if (!base) continue
        if (data.status === "completed") {
          colunasDoLote.set(base.id, data.extra?.output_columns ?? null)
        }
        const updated: INodeStatusWorkFlow = {
          ...base,
          status: data.status as INodeStatusWorkFlow["status"],
          duration: data.duration_ms ?? undefined,
          error: data.error ?? undefined,
        }
        if (data.extra?.branch_result !== undefined) {
          updated.branch_result = data.extra.branch_result
        }
        if (data.extra?.cache_hit !== undefined) {
          updated.cache_hit = data.extra.cache_hit
        }
        // Colunas de cada saída — alimentam a sugestão de nome de coluna
        // nos campos do Join e do filtro. Só chegam de executor 2.4.0 ou
        // mais novo; versões anteriores não publicam a chave.
        if (data.extra?.output_columns !== undefined) {
          updated.output_columns = data.extra.output_columns
        }
        // Sem isso, o painel "Saídas" do InputInspector nunca via as keys
        // reais do output — só via o fallback "output" mesmo após executar.
        if (data.extra?.output_keys !== undefined) {
          updated.output_keys = data.extra.output_keys
        }
        if (data.extra?.schema_drift !== undefined) {
          updated.schema_drift = data.extra.schema_drift
        }
        alterados.set(base.id, updated)
      }

      // Nada mudou no canvas: nem novo array de nós, nem Sets de ramo novos —
      // é o que impede um run barulhento de re-renderizar o grafo à toa.
      if (alterados.size > 0) {
        current.updateNodeStatuses(
          currentNodes.map(node => alterados.get(node.id) ?? node),
          edgesRef.current,
        )
      }

      // Memória de colunas por workflow — sobrevive a reset/F5 de execução e
      // é o que o modal de configuração lê para sugerir nomes.
      if (colunasDoLote.size > 0) {
        useKnownColumnsStore.getState().aplicarDeExecucao(id, taskId, colunasDoLote)
      }

      if (fim) {
        const duration = dayjs.duration(Math.round(fim.duration_ms ?? 0)).format("mm[min ]ss[s ] SSS[ms ]")

        // Toast imediato (efêmero). A entrada persistente no sino de notificações
        // fica a cargo do ActiveRunsProvider (fonte única), para não duplicar a
        // notificação de um run que também é detectado pelo polling global.
        if (fim.status === "failed") {
          createToast.error("Ocorreu um erro no workflow!", fim.error ?? undefined)
        } else if (fim.status === "cancelled") {
          createToast.info("Execução cancelada", `Interrompida após ${duration}`)
        } else {
          createToast.success(`Workflow concluído em ${duration}`)
        }

        // Lê de novo — o bloco de status acima acabou de atualizar a store.
        const finalState = useWorkflowExecutionStore.getState()
        finalState.completeExecution(
          fim.status as StatusWorkflow,
          finalState.statusWorkflow?.nodes ?? [],
          edgesRef.current,
        )

        fecharDeProposito(ws)
        // O run acabou dentro DESTE lote. O que sobrou no buffer é de antes do
        // marcador e já não tem para onde ir; um quadro agendado que rodasse
        // depois reaplicaria `started` sobre nós recém-liquidados.
        descartarLote()
      }
    }

    function agendarFlush() {
      if (frameRef.current != null) return
      frameRef.current = requestAnimationFrame(() => {
        frameRef.current = null
        drenarLote()
      })
    }

    // Drena AGORA, cancelando o quadro pendente para não drenar duas vezes.
    function drenarAgora() {
      if (frameRef.current != null) {
        cancelAnimationFrame(frameRef.current)
        frameRef.current = null
      }
      drenarLote()
    }

    ws.onmessage = (event) => {
      // QUALQUER frame conta como sinal de vida — inclusive o heartbeat (lote
      // vazio) e até um frame ilegível: o que o watchdog vigia é o silêncio do
      // transporte, não o conteúdo. Por isso é a PRIMEIRA linha, antes de parse.
      ultimaMsgRef.current = Date.now()

      // O servidor monta o frame concatenando strings cruas do Redis, então um
      // único item corrompido invalida o JSON do lote INTEIRO — incluindo o
      // `__workflow_complete__`, se ele estiver nesse bloco. Sem esta guarda a
      // exceção subia do onmessage, o socket seguia aberto e o painel ficava em
      // "Executando" sem nada na tela dizendo que um lote se perdeu.
      let frame: { events?: unknown; dropped?: number } | null = null
      try {
        frame = JSON.parse(event.data)
      } catch (err) {
        console.error("[ws/workflow] frame ilegível — lote descartado", err)
        // Contabiliza como perda visível: a aba "Bruto" mostra o aviso em vez
        // de o log parecer completo.
        useWorkflowExecutionStore.getState().registrarDescartados(1)
        return
      }

      // Envelope ÚNICO: replay do histórico e stream ao vivo chegam no MESMO
      // formato — {"type":"events","events":[...],"dropped":N}, com os eventos
      // crus concatenados pelo servidor. Antes era um frame (e um ciclo de
      // render do canvas inteiro) por evento — até 5000 deles ao re-anexar.
      //
      // Quem decide se o run acabou é o CONTEÚDO do lote, nunca o envelope:
      // enquanto o cliente apostava no envelope, o dia em que o servidor passou
      // a mandar o ao vivo em lote deixou o caminho de conclusão imediata morto.
      const eventos: RawEvent[] = Array.isArray(frame?.events) ? frame.events : []

      // Back-pressure do SERVIDOR (o buffer de 500 slots evicta stdout antigo).
      // Sem somar isto, a aba "Bruto" some com o aviso e o usuário conclui que o
      // script simplesmente não imprimiu aquelas linhas.
      if (frame?.dropped) {
        useWorkflowExecutionStore.getState().registrarDescartados(frame.dropped)
      }

      if (eventos.length === 0) return
      for (const evento of eventos) bufferRef.current.push({ runId: taskId, data: evento })

      // O fim do run não pode esperar o próximo quadro: `completeExecution` e o
      // `ws.close()` acontecem dentro do flush. Com a aba em segundo plano o rAF
      // não roda — o run ficava preso em "Executando", com o botão em "Cancelar"
      // e o toast de conclusão só aparecendo minutos depois, ao voltar à aba.
      if (eventos.some(e => e.node === WF_COMPLETE)) {
        drenarAgora()
        return
      }

      // Teto de memória para a aba oculta, onde o rAF nunca chega: a rotação de
      // MAX_RUN_EVENTS só age DEPOIS do drain, dentro da store, então sem isto um
      // `for i in range(200000): print(i)` acumulava centenas de MB no buffer.
      if (bufferRef.current.length >= MAX_RUN_EVENTS) {
        drenarAgora()
        return
      }

      agendarFlush()
    }

    ws.onerror = (err) => {
      // Não decide nada: o `onclose` vem logo atrás e é lá que mora a
      // recuperação. Falhar aqui matava o run na primeira instabilidade, antes
      // mesmo de tentar reconectar.
      console.error("[ws/workflow] erro no socket", err)
    }

    ws.onclose = (event) => {
      // Limpa a ref e para o watchdog se este ainda é o WS ativo (pode já ter
      // sido substituído — nesse caso o watchdog em curso é de OUTRO socket).
      if (wsRef.current === ws) {
        wsRef.current = null
        pararWatchdog()
      }
      const storeState = useWorkflowExecutionStore.getState()
      storeState.setWsState("closed")

      // Fechamos de propósito (fim do run, troca de workflow, novo attach), ou
      // este socket já foi substituído, ou o run já fechou: nada a recuperar.
      if (fechadosDePropositoRef.current.has(ws)) return
      if (runAtivoRef.current !== taskId) return
      if (!storeState.isExecuting) return

      // Daqui para baixo o stream caiu com o run ainda aberto. O CÓDIGO NÃO
      // DISTINGUE: o servidor encerra com 1000 também quando a assinatura do
      // Redis termina sem o `__workflow_complete__` — e tratar isso como
      // encerramento normal era o que deixava os nós girando e o painel em
      // "Executando" para sempre, sem toast, sem log, sem saída.
      console.warn(
        `[ws/workflow] stream de ${taskId} caiu com o run aberto (code=${event.code}) — recuperando`,
      )
      // `.catch` obrigatório: `void` numa async que rejeita vira unhandled
      // rejection, que em alguns navegadores derruba a página inteira.
      recuperarStream(taskId).catch(err =>
        console.error("[ws/workflow] falha ao recuperar o stream", err),
      )
    }

    return ws
  }

  async function executeWorkflow(inputs: Record<string, unknown> = {}) {
    // Nota: NÃO checar isExecuting aqui — handleExecuteWorkflow já fez isso
    // no início e depois chamou store.startExecution() que seta isExecuting=true.
    // Um guard aqui (que existia pré-refactor Zustand) bloqueia o POST e
    // deixa respExec=undefined → task_id "undefined" na URL do WebSocket →
    // 4404. Esse era o bug real observado no canvas.
    const data = await GisFlowService.executeWorkflow(id, inputs, debugMode)
    return data
  }

  // Aguarda o canvas hidratar (React Flow popular os nós) antes de semear/anexar,
  // até `timeoutMs`. Sem isto, o replay do histórico do run podia chegar antes de
  // existir qualquer nó para pintar — daí a re-anexação animava só às vezes,
  // dependendo de quem ganhava a corrida (rede vs. hidratação do canvas).
  function waitForCanvasNodes(shouldAbort: () => boolean, timeoutMs = 8000): Promise<boolean> {
    return new Promise((resolve) => {
      const start = Date.now()
      const tick = () => {
        if (shouldAbort()) return resolve(false)
        if (reactFlowInstance.getNodes().length > 0) return resolve(true)
        if (Date.now() - start > timeoutMs) return resolve(false)
        setTimeout(tick, 100)
      }
      tick()
    })
  }

  // Re-anexa às animações de um run ainda em andamento ao (re)abrir o workflow.
  // O canvas anima 100% a partir da store, que é volátil e é zerada ao montar
  // (workflow/index.tsx). Sem isto, reabrir um workflow "running" mostrava um
  // canvas estático — parecia que nada acontecia. Aqui descobrimos o run vivo
  // mais recente e reabrimos o MESMO WebSocket do disparo: o backend faz replay
  // de todo o histórico do run e segue ao vivo, repintando os nós. Só re-anexa a
  // runs vivos (running/pending); se o último run já concluiu, o canvas fica limpo.
  useEffect(() => {
    if (!id) return
    // Só o dono do socket re-anexa. Sem esta guarda, abrir o modal de
    // configuração de um nó Webhook durante um run montava uma segunda
    // instância que chamava `startExecution` (zerando o canvas em curso) e
    // abria um socket concorrente para o MESMO run.
    if (!souDonoRef.current) return
    // NÃO usar o isExecuting global como gate: ele é volátil e, ao voltar a um
    // workflow, pode estar TRUE por sobra do acesso anterior (o reset vive noutro
    // efeito, em workflow/index.tsx, que roda DEPOIS deste). Era o que fazia a
    // re-anexação alternar entre acessos (funciona/para/funciona). Aqui zeramos o
    // controle por-montagem; um disparo manual o liga em handleExecuteWorkflow.
    sessionTriggeredRef.current = false

    let cancelled = false
    const openedFor = id
    const aborted = () => cancelled || openedFor !== id

    ;(async () => {
      const resp = await GisFlowService.getObservabilityRuns({ workflow_id: id, limit: 1 })
      const latest = resp?.data?.runs?.[0]
      // Aborta se o workflow mudou durante o await, se não há run, ou se ele não
      // está vivo. Se um disparo manual começou nesta montagem, não clobbera.
      if (aborted() || !latest) return
      if (latest.status !== "running" && latest.status !== "pending") {
        // O run mais recente já concluiu: nada para re-anexar — mas o
        // `node_stats` dele guarda `output_columns`, e semear a store de
        // sugestões daqui é o que faz as colunas aparecerem ao ABRIR o
        // workflow, sem executar nada. Antes, elas só existiam enquanto a
        // sessão do run vivia: F5 e a dica sumia ("às vezes funciona").
        //
        // Melhor-esforço deliberado: sugestão é dica, não estado — sem run
        // detalhável (403 de papel restrito, 404, stats sem a chave por
        // executor antigo ou corte de 8KB), o editor segue como hoje, sem
        // toast na abertura do workflow.
        //
        // Run VIVO não passa aqui de propósito: o replay do WebSocket reentrega
        // o histórico e escreve as colunas pelo caminho ao vivo (`fresh`).
        const detalhe = await GisFlowService.getRunDetail(latest.run_id)
        if (aborted()) return
        const stats = detalhe?.data?.node_stats ?? {}
        const colunasPorNo: Record<string, { porPorta: Record<string, string[]>; parciais?: boolean }> = {}
        for (const [nodeId, stat] of Object.entries(stats)) {
          if (stat?.output_columns) {
            // `__truncated__` = o corte de 8KB do executor reduziu cada lista
            // às primeiras 50 — o rótulo da sugestão avisa "lista parcial".
            colunasPorNo[nodeId] = { porPorta: stat.output_columns, parciais: !!stat.__truncated__ }
          }
        }
        if (Object.keys(colunasPorNo).length > 0) {
          useKnownColumnsStore.getState().semearDoHistorico(id, latest.run_id, colunasPorNo)
        }
        return
      }
      if (sessionTriggeredRef.current) return

      // Espera o canvas hidratar ANTES de semear — sem isso o replay chegava sem
      // nós para pintar (a causa da animação intermitente ao reabrir).
      await waitForCanvasNodes(aborted)
      if (aborted() || sessionTriggeredRef.current) return

      // Semeia a store com os nós atuais do canvas (idle) — mas SÓ quando ainda
      // não há estado deste run. `startExecution` zera nós e eventos, e fazer
      // isso sobre um run que já estamos acompanhando (segunda montagem do
      // hook, efeito reexecutado) apaga o progresso já pintado e aposta tudo no
      // replay chegar. Se o socket cair logo depois, o canvas fica pior do que
      // estava antes da "recuperação".
      const store = useWorkflowExecutionStore.getState()
      // ...ou quando o estado que temos deste run é um DESFECHO. O servidor
      // acabou de dizer que ele continua vivo, então o nosso encerramento foi
      // precipitado (reconciliação em corrida, ou desistência após esgotar as
      // reconexões). Sem re-semear, o replay chegaria num run que a store
      // considera fechado e a guarda de `updateNodeStatuses` o descartaria,
      // deixando o canvas congelado no desfecho errado.
      const encerrado = !!store.statusWorkflow && RUN_ENCERRADO.has(store.statusWorkflow.status)
      if (store.viewingRunId !== latest.run_id || !store.statusWorkflow || encerrado) {
        const source = nodesRef.current.length > 0 ? nodesRef.current : reactFlowInstance.getNodes()
        const liveNodes = source.map((node) => ({ ...node, id: node.id, status: "idle" as const }))
        store.startExecution(liveNodes)
        createToast.info("Reconectado à execução em andamento")
      }
      attachToRun(latest.run_id)
    })()

    return () => {
      cancelled = true
      // Fecha o WS ativo ao sair/trocar de workflow. Marcado como intencional,
      // senão o `onclose` trataria a troca de tela como queda e tentaria
      // reconectar a um run que o usuário deixou para trás.
      fecharDeProposito(wsRef.current)
      // Navegar /workflow/A → /workflow/B NÃO remonta o componente: buffer e
      // quadro pendente sobrevivem à troca. Fechar o socket não basta — as
      // mensagens já enfileiradas no event loop ainda seriam entregues.
      descartarLote()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  return {
    executeWorkflow: handleExecuteWorkflow,
    isExecuting,
    debugMode,
    setDebugMode,
  }
}
