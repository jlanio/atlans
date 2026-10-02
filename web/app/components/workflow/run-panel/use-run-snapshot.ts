import { useCallback, useSyncExternalStore } from "react"
import { RunEvent, useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { NodeRun, RunTimeline, buildHudTimeline, buildTimeline } from "./timeline"

/** Janela de agregação das atualizações do painel.
 *
 * Um run movimentado emite dezenas de eventos por segundo, e cada um deles
 * mudava `events` E `statusWorkflow.nodes`. Assinando a store por selector, o
 * painel re-renderizava — e reconstruía a linha do tempo inteira — uma vez por
 * mensagem, com todas as linhas de nó junto. Agregar em ~8 quadros por segundo
 * é imperceptível para o olho e corta o trabalho por uma ordem de grandeza.
 * Os cronômetros (`Elapsed`) têm tique próprio, então a sensação de "ao vivo"
 * não depende desta taxa.
 */
const REFRESH_MS = 120

export interface RunSnapshot {
  timeline: RunTimeline
  events: RunEvent[]
  droppedEvents: number
}

/**
 * Um único snapshot por janela, compartilhado por todos os consumidores.
 *
 * O painel de execução e o visualizador de sub-fluxo pedem a mesma linha do
 * tempo. Com um timer e uma reconstrução por hook, abrir o visualizador durante
 * um run dobrava o custo: `buildTimeline` percorre a lista inteira de eventos
 * (até 2000) e ordena os nós, oito vezes por segundo, na mesma thread que anima
 * o canvas. Aqui a reconstrução acontece uma vez e os dois leem o mesmo objeto.
 */
const inscritos = new Set<() => void>()
/** Subconjunto que precisa da linha do tempo COMPLETA (painel aberto,
 *  visualizador de sub-fluxo). Vazio ⇒ só o resumo da barra é construído. */
const querTimeline = new Set<() => void>()
let timer: ReturnType<typeof setTimeout> | null = null
let cancelarStore: (() => void) | null = null

function readSnapshot(anterior: RunSnapshot | null): RunSnapshot {
  const state = useWorkflowExecutionStore.getState()
  const nosDoCanvas = state.statusWorkflow?.nodes ?? []
  const timeline = querTimeline.size > 0
    ? buildTimeline(state.events, nosDoCanvas, state.runStartedTs)
    : buildHudTimeline(nosDoCanvas, state.runStartedTs, state.runOutcome, state.events.length > 0)
  return {
    timeline: anterior ? reaproveitar(anterior.timeline, timeline) : timeline,
    events: state.events,
    droppedEvents: state.droppedEvents,
  }
}

/** Um `NodeRun` é intercambiável com o anterior? Comparação rasa e barata.
 *
 * `startedAt` entra junto com `prints.length` de propósito: dois runs diferentes
 * nunca começam no mesmo instante, então nenhum array de prints atravessa a
 * troca de execução. Dentro de um mesmo run os prints só crescem, e o tamanho
 * igual implica conteúdo igual.
 */
function mesmoNo(a: NodeRun, b: NodeRun): boolean {
  return a.nodeId === b.nodeId
    && a.status === b.status
    && a.durationMs === b.durationMs
    && a.startOffsetMs === b.startOffsetMs
    && a.startedAt === b.startedAt
    && a.order === b.order
    && a.name === b.name
    && a.type === b.type
    && a.subFlow === b.subFlow
    && a.cacheHit === b.cacheHit
    && a.branchResult === b.branchResult
    && a.prints.length === b.prints.length
    && a.outputKeys.length === b.outputKeys.length
    && a.debug === b.debug
    && a.schemaDrift === b.schemaDrift
    && a.problem?.message === b.problem?.message
}

/**
 * Devolve a linha do tempo nova reusando os objetos da anterior onde nada mudou.
 *
 * `buildTimeline` é pura e realoca TODOS os `NodeRun` a cada chamada, então as
 * linhas do painel (memoizadas) re-renderizavam oito vezes por segundo mesmo
 * quando um único nó havia mudado. Aqui a identidade é restaurada por
 * comparação de valor — e, quando nada mudou em nenhum nó, o snapshot inteiro
 * anterior é devolvido, o que também segura os `useMemo` de `visible`/`groups`.
 */
function reaproveitar(anterior: RunTimeline, nova: RunTimeline): RunTimeline {
  const antes = new Map<string, NodeRun>()
  for (const node of anterior.nodes) antes.set(node.nodeId, node)

  const reusados = new Map<string, NodeRun>()
  let todosIguais = anterior.nodes.length === nova.nodes.length
  const nodes = nova.nodes.map((node, i) => {
    const velho = antes.get(node.nodeId)
    if (velho && mesmoNo(velho, node)) {
      reusados.set(node.nodeId, velho)
      if (anterior.nodes[i] !== velho) todosIguais = false
      return velho
    }
    todosIguais = false
    return node
  })

  if (
    todosIguais
    && anterior.totalPrints === nova.totalPrints
    && anterior.startTs === nova.startTs
    && anterior.workflow.status === nova.workflow.status
    && anterior.workflow.durationMs === nova.workflow.durationMs
    && anterior.workflow.error === nova.workflow.error
  ) {
    return anterior
  }

  // `problems`/`slowest` apontam para os objetos recém-criados; sem remapear,
  // a mesma linha existiria em duas instâncias diferentes na mesma tela.
  return {
    ...nova,
    nodes,
    problems: nova.problems.map(p => reusados.get(p.nodeId) ?? p),
    slowest: nova.slowest ? reusados.get(nova.slowest.nodeId) ?? nova.slowest : null,
  }
}

let snapshot: RunSnapshot = readSnapshot(null)

function agendarFlush() {
  if (timer) return // já há um flush agendado nesta janela
  timer = setTimeout(() => {
    timer = null
    snapshot = readSnapshot(snapshot)
    for (const notificar of inscritos) notificar()
  }, REFRESH_MS)
}

function inscrever(notificar: () => void, precisaTimeline: boolean) {
  const primeiroCompleto = precisaTimeline && querTimeline.size === 0
  inscritos.add(notificar)
  if (precisaTimeline) querTimeline.add(notificar)
  // Assina a store uma única vez, enquanto houver algum consumidor. O primeiro
  // a chegar recolhe na hora o que já existe — esperar a janela deixaria o
  // painel vazio por um instante ao abrir um run já carregado. O React relê o
  // snapshot logo após inscrever, então isto não precisa notificar ninguém.
  if (!cancelarStore) {
    cancelarStore = useWorkflowExecutionStore.subscribe(agendarFlush)
    snapshot = readSnapshot(null)
  } else if (primeiroCompleto) {
    // O painel acabou de abrir e o snapshot vigente só tem o resumo da barra.
    agendarFlush()
  }

  return () => {
    inscritos.delete(notificar)
    querTimeline.delete(notificar)
    if (inscritos.size > 0) return
    cancelarStore?.()
    cancelarStore = null
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }
}

/**
 * Snapshot agregado da execução.
 *
 * A store é assinada de forma imperativa (e não via selector) justamente para
 * que a alta frequência de escrita não vire alta frequência de render: os
 * componentes só atualizam quando o timer dispara.
 *
 * `precisaTimeline` diz se este consumidor mostra a linha do tempo por nó. O
 * painel passa `open`: recolhido, ele só desenha a barra de resumo, e a
 * reconstrução completa deixa de acontecer.
 */
export function useRunSnapshot(precisaTimeline = true): RunSnapshot {
  const subscribe = useCallback(
    (notificar: () => void) => inscrever(notificar, precisaTimeline),
    [precisaTimeline],
  )
  return useSyncExternalStore(subscribe, () => snapshot, () => snapshot)
}
