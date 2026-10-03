import { fromBackend, dayjs } from "@/lib/dayjs"
import type { IExecutorMetrics, IObservabilityMetrics } from "@/service/types"
import { formatarDuracao, plural, rotuloDaCategoria } from "@/lib/formatos"

/**
 * "Needs attention" (docs/specs/metrics-history.md §4.3): what would change a
 * decision today, in up to 5 items, in this order — stuck runs, repeated
 * failures, executors at the ceiling. Pure: takes what the data hook already
 * has and returns text and action; rendering and navigation stay out of here.
 */

export type AcaoDeAtencao =
  | { tipo: "abrir-execucao"; runId: string }
  | { tipo: "filtrar-workflow"; workflowHash: string; status: "failed" }
  | { tipo: "abrir-executor"; agentHost: string }

export interface ItemDeAtencao {
  chave: string
  tipo: "presa" | "falhas" | "saturado"
  /** Who the subject is (workflow, executor): the list highlights it at the start of the title. */
  nome: string
  /** Full sentence, starting with `nome`. */
  titulo: string
  detalhe: string
  acao: AcaoDeAtencao
  /** Button verb: "Abrir", "Ver falhas", "Ver executor" (open, see failures, see executor). */
  rotuloDaAcao: string
  /**
   * Origin of the item's workflow ("assistente" gets a badge), when the item
   * HAS a workflow and the composer managed to resolve it. An executor at the
   * ceiling has none.
   */
  origem?: string | null
  /**
   * Signature of the current SEVERITY, so that "dismiss" does not blind the
   * user: a dismissed item stays hidden only while the signature does not
   * change. If the problem gets worse — a new stuck run, one more failure, the
   * executor's queue grows — the signature changes and the alert comes back.
   * See `atencao-dispensados.ts`.
   */
  assinatura: string
}

export const MAXIMO_DE_ITENS = 5
/** Falhas repetidas: `failure_count ≥ 3` ou `failure_rate ≥ 0.2` (spec §4.3). */
export const MINIMO_DE_FALHAS = 3
export const MINIMO_DE_TAXA_DE_FALHA = 0.2

function nomeDoWorkflow(nome: string | null | undefined, hash: string): string {
  return nome?.trim() || `workflow ${hash.slice(0, 8)}`
}

export function montarAtencao(entrada: {
  metrics: IObservabilityMetrics | null
  executores: IExecutorMetrics[]
  /**
   * Workflow origin by hash, for the assistant badge. The metrics do not
   * carry it (the alert is born from the run, not from the inventory), so the
   * screen composer — which already has the workflow list — resolves it.
   * Absent → no badge.
   */
  origemDoWorkflow?: (hash: string) => string | null | undefined
}): ItemDeAtencao[] {
  const { metrics, executores, origemDoWorkflow } = entrada
  const itens: ItemDeAtencao[] = []
  const periodo = metrics?.period_days ?? 30

  // 1. Stuck: `now.stuck` already comes sorted from oldest to newest.
  for (const s of metrics?.now?.stuck ?? []) {
    const nome = nomeDoWorkflow(s.workflow_name, s.workflow_hash)
    const onde = s.executor_name || s.agent_host
    const tipica = s.typical_seconds != null && s.typical_seconds > 0
      ? `a duração típica é ${formatarDuracao(s.typical_seconds)}`
      : "sem duração típica conhecida"
    itens.push({
      chave: `presa:${s.run_id}`,
      tipo: "presa",
      nome,
      titulo: `${nome} está em andamento há ${formatarDuracao(s.elapsed_seconds)}`,
      detalhe: onde ? `Em ${onde} · ${tipica}` : `Sem executor · ${tipica}`,
      acao: { tipo: "abrir-execucao", runId: s.run_id },
      rotuloDaAcao: "Abrir",
      origem: origemDoWorkflow?.(s.workflow_hash),
      // A stuck item is unique per run (the run_id); dismissing it hides it while
      // this run stays stuck — another that jams has its own `chave`.
      assinatura: s.run_id,
    })
  }

  // 2. Repeated failures. The backend already sorts by `failure_count` desc.
  for (const w of metrics?.top_failing_workflows ?? []) {
    const repetida = w.failure_count >= MINIMO_DE_FALHAS || (w.failure_rate ?? 0) >= MINIMO_DE_TAXA_DE_FALHA
    if (!repetida || w.failure_count <= 0) continue
    const nome = nomeDoWorkflow(w.workflow_name, w.workflow_hash)
    // A high count speaks for itself; a high rate with few runs needs the
    // denominator so it does not look like little ("2 vezes" × "2 de 3").
    const quanto = w.failure_count >= MINIMO_DE_FALHAS
      ? `falhou ${plural(w.failure_count, "vez", "vezes")} em ${periodo} dias`
      : `falhou em ${w.failure_count} de ${plural(w.total_runs, "execução", "execuções")} em ${periodo} dias`
    const categoria = rotuloDaCategoria(w.last_error_category)
    const erro = w.last_error?.trim()
    const detalhe = erro
      ? `Último erro: ${categoria ? `${categoria} · ` : ""}${erro}`
      : w.last_failed_at
        ? `Última falha ${haQuantoTempo(w.last_failed_at)}`
        : "Sem mensagem de erro registrada"
    itens.push({
      chave: `falhas:${w.workflow_hash}`,
      tipo: "falhas",
      nome,
      titulo: `${nome} ${quanto}`,
      detalhe,
      acao: { tipo: "filtrar-workflow", workflowHash: w.workflow_hash, status: "failed" },
      rotuloDaAcao: "Ver falhas",
      origem: origemDoWorkflow?.(w.workflow_hash),
      // The failure count only grows: dismissing hides the current state, and a
      // NEW failure (higher count) changes the signature and brings the alert back.
      assinatura: String(w.failure_count),
    })
  }

  // 3. Executors at the ceiling: `running ≥ max_concurrent` AND queue > 0. Only
  // with published capacity and a known host — the "Sem executor" row is not
  // an executor to open.
  for (const e of executores) {
    const c = e.capacity
    if (!c || !e.agent_host || e.unassigned) continue
    if (c.max_concurrent <= 0 || c.running < c.max_concurrent || c.queued <= 0) continue
    const nome = e.display_name || e.agent_host
    const p50 = e.p50_seconds ?? null
    // Estimated wait: the queue advances `max_concurrent` at a time, each batch
    // lasting the median. It is an order of magnitude, and the text says "cerca de".
    const espera = p50 != null && p50 > 0
      ? ` · as próximas esperam cerca de ${formatarDuracao(Math.ceil(c.queued / c.max_concurrent) * p50)}`
      : ""
    itens.push({
      chave: `saturado:${e.agent_host}`,
      tipo: "saturado",
      nome,
      titulo: `${nome} está no teto: ${c.running} de ${c.max_concurrent} em execução`,
      detalhe: `${plural(c.queued, "execução", "execuções")} na fila${espera}`,
      acao: { tipo: "abrir-executor", agentHost: e.agent_host },
      rotuloDaAcao: "Ver executor",
      // The executor's load changes over time: dismissing hides the current state;
      // if running/queue change (gets worse), the signature changes and the alert comes back.
      assinatura: `${c.running}:${c.queued}`,
    })
  }

  return itens.slice(0, MAXIMO_DE_ITENS)
}

/** "há 12 min", "há 3 h", "há 3 dias" (ago) — coarse grain, for an empty-state sentence. */
export function haQuantoTempo(iso: string | null | undefined, agora: Date = new Date()): string {
  const d = fromBackend(iso)
  if (!d) return "—"
  const ref = dayjs(agora)
  const minutos = Math.max(0, ref.diff(d, "minute"))
  if (minutos < 1) return "agora"
  if (minutos < 60) return `há ${minutos} min`
  const horas = Math.floor(minutos / 60)
  if (horas < 24) return `há ${horas} h`
  const diasInteiros = Math.floor(horas / 24)
  return `há ${plural(diasInteiros, "dia")}`
}

/** Empty-list sentence: when the last failure was, or that there was none. */
export function textoDeVazio(metrics: IObservabilityMetrics | null, agora: Date = new Date()): string {
  // The list comes sorted by number of failures: the period's last failure
  // is the most recent AMONG all items, not the first item's.
  const ultima = (metrics?.top_failing_workflows ?? [])
    .map(w => w.last_failed_at)
    .filter((d): d is string => !!d)
    .sort()
    .at(-1)
  if (ultima && (metrics?.failed_runs ?? 0) > 0) return `Nada pendente. Última falha ${haQuantoTempo(ultima, agora)}.`
  return "Nenhuma falha no período."
}
