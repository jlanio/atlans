import { INodeStatusWorkFlow } from "@/context/useFlowContext"
import { RunEvent, RunOutcome } from "@/app/stores/workflowExecutionStore"

/** Id de nó sintético que o backend usa para sinalizar o fim do run. */
export const WF_COMPLETE = "__workflow_complete__"

/** `unknown`: o run terminou e o término deste nó nunca chegou — ver
 *  `StatusNodeStatusWorkFlow` em useFlowContext. É distinto de `pending`
 *  (não começou) e de `running` (está acontecendo agora). */
export type NodeRunStatus = "pending" | "running" | "completed" | "failed" | "unknown"

export interface NodePrint {
  offsetMs: number
  text: string
}

export interface NodeProblem {
  message: string
  traceback?: string | null
  category?: string | null
  retryable?: boolean | null
}

/** Um nó do workflow visto como uma ÚNICA linha que evolui de estado.
 *
 * O painel antigo empilhava dois eventos por nó (`started` e depois
 * `completed`), então um workflow de 30 nós virava 60 linhas que apenas
 * repetiam a animação do canvas e afogavam prints e erros.
 */
export interface NodeRun {
  nodeId: string
  /** Nó do canvas que esta linha representa. Igual a `nodeId` para os nós do
   *  fluxo; para um nó de dentro de sub-fluxo é o nó SubWorkflow que o chamou —
   *  o único ponto do canvas que existe para focar, destacar ou configurar. */
  canvasNodeId: string
  /** Preenchido quando a linha veio de dentro de um sub-fluxo: nome do nó
   *  SubWorkflow no canvas do pai. */
  subFlow: string | null
  name: string
  type: string
  status: NodeRunStatus
  /** ms desde o início do run — responde "quanto tempo até chegar aqui". */
  startOffsetMs: number | null
  startedAt: number | null
  durationMs: number | null
  outputKeys: string[]
  cacheHit: boolean
  branchResult?: boolean
  schemaDrift?: { missing: string[]; extra: string[] } | null
  debug: Record<string, string> | null
  prints: NodePrint[]
  problem: NodeProblem | null
  /** Ordem de início; nós ainda não iniciados vão para o fim. */
  order: number
}

export interface RunTimeline {
  startTs: number | null
  nodes: NodeRun[]
  problems: NodeRun[]
  totalPrints: number
  slowest: NodeRun | null
  counts: { total: number; done: number; failed: number; running: number; pending: number; unknown: number }
  workflow: {
    status: "idle" | "running" | "completed" | "failed" | "cancelled"
    durationMs: number | null
    error: string | null
    category: string | null
    retryable: boolean | null
  }
}

/** Nome legível de um nó do canvas (o evento traz `node_name`; o canvas, alias). */
function canvasNodeLabel(node: INodeStatusWorkFlow): string {
  const data = (node as { data?: { alias?: string; name?: string } }).data
  return data?.alias || data?.name || node.id
}

function canvasNodeType(node: INodeStatusWorkFlow): string {
  return (node as { data?: { name?: string } }).data?.name ?? ""
}

function emptyNodeRun(nodeId: string, name: string, type: string, order: number): NodeRun {
  return {
    nodeId, canvasNodeId: nodeId, subFlow: null, name, type,
    status: "pending",
    startOffsetMs: null,
    startedAt: null,
    durationMs: null,
    outputKeys: [],
    cacheHit: false,
    schemaDrift: null,
    debug: null,
    prints: [],
    problem: null,
    order,
  }
}

const CANVAS_STATUS: Record<string, NodeRunStatus> = {
  idle:      "pending",
  started:   "running",
  completed: "completed",
  failed:    "failed",
  unknown:   "unknown",
}

/** Semeia a linha do tempo com o estado que o canvas já conhece.
 *
 * O estado por nó no canvas é acumulado mensagem a mensagem e NÃO passa por
 * rotação — enquanto a lista de eventos tem teto (aqui e no histórico do Redis,
 * limitado a 5000). Num run que imprime muito, os eventos de ciclo de vida mais
 * antigos somem, e derivar só deles faria um nó concluído reaparecer como
 * "aguardando", contradizendo o próprio canvas. Partindo do canvas, os eventos
 * apenas enriquecem (offset, saídas, prints, traceback) o que já é verdade.
 */
function seedFromCanvas(node: INodeStatusWorkFlow, order: number): NodeRun {
  const run = emptyNodeRun(node.id, canvasNodeLabel(node), canvasNodeType(node), order)
  run.status = CANVAS_STATUS[node.status] ?? "pending"
  if (node.duration != null) run.durationMs = node.duration
  if (node.output_keys) run.outputKeys = node.output_keys
  if (node.cache_hit !== undefined) run.cacheHit = !!node.cache_hit
  if (node.branch_result !== undefined) run.branchResult = node.branch_result
  if (node.schema_drift) run.schemaDrift = node.schema_drift
  if (node.status === "failed" && node.error) {
    run.problem = { message: node.error, traceback: null, category: null, retryable: null }
  }
  return run
}

/**
 * Converte o fluxo cronológico de eventos numa linha do tempo por nó.
 *
 * `canvasNodes` entra para que nós ainda não executados apareçam como
 * "aguardando" — o painel mostra o grafo inteiro, não só o que já emitiu evento.
 */
export function buildTimeline(
  events: RunEvent[],
  canvasNodes: INodeStatusWorkFlow[],
  runStartedTs: number | null = null,
): RunTimeline {
  const byId = new Map<string, NodeRun>()
  let order = 0

  for (const node of canvasNodes) {
    byId.set(node.id, seedFromCanvas(node, Number.MAX_SAFE_INTEGER))
  }

  // Início do run: registrado na store quando o primeiro evento chega, e não
  // lido de `events[0]` — a lista tem rotação, e ao descartar o começo TODOS os
  // offsets passariam a ser relativos ao evento sobrevivente mais antigo.
  // Timestamps vêm do backend, então isto também vale no replay de re-anexação.
  const startTs = runStartedTs ?? (events.length > 0 ? events[0].ts : null)

  const workflow: RunTimeline["workflow"] = {
    status: events.length > 0 ? "running" : "idle",
    durationMs: null,
    error: null,
    category: null,
    retryable: null,
  }

  const offsetOf = (ts: number) => (startTs == null ? 0 : Math.max(0, ts - startTs))

  for (const ev of events) {
    const nodeId = ev.node
    if (!nodeId) continue

    if (nodeId === WF_COMPLETE) {
      workflow.status = ev.status === "failed" ? "failed"
        : ev.status === "cancelled" ? "cancelled"
        : "completed"
      workflow.durationMs = ev.duration_ms ?? null
      workflow.error = ev.message ?? null
      workflow.category = ev.error_category ?? null
      workflow.retryable = ev.retryable ?? null
      continue
    }

    let run = byId.get(nodeId)
    if (!run) {
      // Nó que emitiu evento mas não está no canvas: um nó de DENTRO de um
      // sub-fluxo, publicado com o id prefixado `pai::filho`. A linha entra na
      // lista amarrada ao nó SubWorkflow do pai — sem isso ela mostrava o id
      // cru, não dizia que era de outro fluxo, e clicar nela era um no-op
      // silencioso (`focusNode` não acha o id no canvas).
      const pai = ev.subworkflow_parent ?? null
      run = emptyNodeRun(
        nodeId,
        ev.node_name ?? (pai ? nodeId.slice(pai.length + 2) : nodeId),
        ev.node_type ?? "",
        Number.MAX_SAFE_INTEGER,
      )
      if (pai) {
        run.canvasNodeId = pai
        run.subFlow = byId.get(pai)?.name ?? pai
      }
      byId.set(nodeId, run)
    }
    if (ev.node_name) run.name = ev.node_name
    if (ev.node_type) run.type = ev.node_type

    if (ev.kind === "stdout") {
      // O executor agrega a saída em janelas de ~200 ms, então um evento traz
      // VÁRIAS linhas em `lines` — uma linha de painel por item. `lines` é a
      // única fonte: o executor parou de repetir o mesmo texto em `message`
      // porque a duplicação estourava o teto de 64 KB do evento e o lote inteiro
      // chegava aqui reduzido aos campos de controle, sem saída nenhuma.
      const offset = offsetOf(ev.ts)
      if (ev.lines) {
        for (const linha of ev.lines) run.prints.push({ offsetMs: offset, text: linha })
      }
      continue
    }

    if (ev.kind === "debug") {
      if (ev.debug_output) run.debug = { ...(run.debug ?? {}), ...ev.debug_output }
      continue
    }

    // kind === "lifecycle"
    if (ev.status === "started") {
      run.status = "running"
      run.startedAt = ev.ts
      run.startOffsetMs = offsetOf(ev.ts)
      run.order = order++
      continue
    }

    if (ev.status === "completed" || ev.status === "failed") {
      run.status = ev.status === "failed" ? "failed" : "completed"
      // Não zera o que o canvas já sabia: um evento sem `duration_ms` apagaria
      // a duração semeada.
      if (ev.duration_ms != null) run.durationMs = ev.duration_ms
      if (ev.output_keys) run.outputKeys = ev.output_keys
      if (ev.cache_hit !== undefined) run.cacheHit = !!ev.cache_hit
      if (ev.branch_result !== undefined) run.branchResult = ev.branch_result
      if (ev.schema_drift) run.schemaDrift = ev.schema_drift
      if (run.order === Number.MAX_SAFE_INTEGER) run.order = order++
      // Nó que terminou sem `started` observado (replay truncado): reconstrói
      // o início a partir do fim menos a duração, para não perder o offset.
      if (run.startOffsetMs == null) {
        run.startOffsetMs = Math.max(0, offsetOf(ev.ts) - (ev.duration_ms ?? 0))
      }
      if (ev.status === "failed") {
        run.problem = {
          message: ev.message ?? "Falha sem mensagem.",
          traceback: ev.traceback,
          category: ev.error_category,
          retryable: ev.retryable,
        }
      }
    }
  }

  const nodes = [...byId.values()].sort((a, b) => {
    if (a.order !== b.order) return a.order - b.order
    return a.name.localeCompare(b.name)
  })

  // Passe único: seis varreduras separadas sobre a lista de nós custavam caro
  // porque isto roda a cada atualização do painel durante o run.
  const counts = { total: nodes.length, done: 0, failed: 0, running: 0, pending: 0, unknown: 0 }
  const problems: NodeRun[] = []
  let totalPrints = 0
  let slowest: NodeRun | null = null

  for (const node of nodes) {
    if (node.status === "completed") counts.done++
    else if (node.status === "failed") counts.failed++
    else if (node.status === "running") counts.running++
    // `unknown` tem contador próprio: somado a `pending`, a barra de progresso
    // do painel nunca fecharia num run já terminado, e o número contradiria o
    // canvas, que mostra o nó como resolvido-sem-resposta.
    else if (node.status === "unknown") counts.unknown++
    else counts.pending++

    if (node.problem != null) problems.push(node)
    totalPrints += node.prints.length
    if (node.durationMs != null && (slowest == null || node.durationMs > slowest.durationMs!)) {
      slowest = node
    }
  }

  return { startTs, nodes, problems, totalPrints, slowest, counts, workflow }
}

/**
 * Resumo para a BARRA do painel, sem tocar na lista de eventos.
 *
 * Com o painel recolhido o único consumidor da linha do tempo é a barra de
 * 34px, que precisa de contagens, status, nó mais lento e nó em execução —
 * nada disso exige percorrer os até 2000 eventos, alocar prints nem ordenar.
 * Reconstruir tudo oito vezes por segundo era CPU que nunca chegava à tela.
 *
 * O desfecho do run (duração total, erro) vem da store, que o registra a O(1)
 * quando o evento `__workflow_complete__` chega.
 */
export function buildHudTimeline(
  canvasNodes: INodeStatusWorkFlow[],
  runStartedTs: number | null,
  outcome: RunOutcome | null,
  temEventos: boolean,
): RunTimeline {
  const nodes: NodeRun[] = []
  const problems: NodeRun[] = []
  const counts = { total: 0, done: 0, failed: 0, running: 0, pending: 0, unknown: 0 }
  let slowest: NodeRun | null = null

  for (const node of canvasNodes) {
    const run = seedFromCanvas(node, Number.MAX_SAFE_INTEGER)
    nodes.push(run)
    if (run.status === "completed") counts.done++
    else if (run.status === "failed") counts.failed++
    else if (run.status === "running") counts.running++
    else if (run.status === "unknown") counts.unknown++
    else counts.pending++
    if (run.problem != null) problems.push(run)
    if (run.durationMs != null && (slowest == null || run.durationMs > slowest.durationMs!)) {
      slowest = run
    }
  }
  counts.total = nodes.length

  return {
    startTs: runStartedTs,
    nodes,
    problems,
    totalPrints: 0,
    slowest,
    counts,
    workflow: {
      status: outcome?.status ?? (temEventos ? "running" : "idle"),
      durationMs: outcome?.durationMs ?? null,
      error: outcome?.error ?? null,
      category: outcome?.category ?? null,
      retryable: outcome?.retryable ?? null,
    },
  }
}

/** Renderiza a timeline como texto puro — usado por "copiar tudo" e "baixar". */
export function timelineToText(timeline: RunTimeline, runId: string | null): string {
  const lines: string[] = []
  lines.push(`# Execução ${runId ?? "(sem id)"}`)
  lines.push(`# status: ${timeline.workflow.status}`)
  if (timeline.workflow.durationMs != null) lines.push(`# duração: ${timeline.workflow.durationMs.toFixed(0)}ms`)
  lines.push("")

  for (const node of timeline.nodes) {
    const offset = node.startOffsetMs != null ? `+${(node.startOffsetMs / 1000).toFixed(2)}s` : "—"
    const duration = node.durationMs != null ? `${node.durationMs.toFixed(0)}ms` : "—"
    // O recuo mantém no texto colado a mesma leitura da tela: dá para ver o
    // que aconteceu dentro do sub-fluxo sem confundir com os nós do pai.
    const dentro = node.subFlow ? `  ↳ [${node.subFlow}] ` : "  "
    lines.push(`${offset.padStart(8)}${dentro}${node.status.padEnd(9)} ${node.name}  (${node.type}) ${duration}`)
    for (const print of node.prints) {
      lines.push(`            | ${print.text}`)
    }
    if (node.problem) {
      lines.push(`            ! ${node.problem.message}`)
      if (node.problem.category) lines.push(`            ! categoria: ${node.problem.category}`)
      if (node.problem.traceback) {
        for (const tl of node.problem.traceback.split("\n")) lines.push(`            ! ${tl}`)
      }
    }
  }

  if (timeline.workflow.error) {
    lines.push("")
    lines.push(`# erro do workflow: ${timeline.workflow.error}`)
  }
  return lines.join("\n")
}
