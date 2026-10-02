import { fromBackend, dayjs } from "@/lib/dayjs"
import type { IExecutorMetrics, IObservabilityMetrics } from "@/service/types"
import { formatarDuracao, plural, rotuloDaCategoria } from "@/lib/formatos"

/**
 * "Precisa de atenção" (docs/specs/historico-metricas.md §4.3): o que mudaria
 * uma decisão hoje, em até 5 itens, nesta ordem — presas, falhas repetidas,
 * executores no teto. Puro: recebe o que o hook de dados já tem e devolve
 * texto e ação; quem renderiza e quem navega ficam fora daqui.
 */

export type AcaoDeAtencao =
  | { tipo: "abrir-execucao"; runId: string }
  | { tipo: "filtrar-workflow"; workflowHash: string; status: "failed" }
  | { tipo: "abrir-executor"; agentHost: string }

export interface ItemDeAtencao {
  chave: string
  tipo: "presa" | "falhas" | "saturado"
  /** Quem é o assunto (workflow, executor): a lista o destaca no começo do título. */
  nome: string
  /** Frase inteira, começando por `nome`. */
  titulo: string
  detalhe: string
  acao: AcaoDeAtencao
  /** Verbo do botão: "Abrir", "Ver falhas", "Ver executor". */
  rotuloDaAcao: string
  /**
   * Origem do fluxo do item ("assistente" ganha selo), quando o item TEM um
   * fluxo e quem compõe soube resolvê-la. Executor no teto não tem.
   */
  origem?: string | null
  /**
   * Assinatura da GRAVIDADE atual, para "dispensar" não cegar o usuário: um item
   * dispensado só continua oculto enquanto a assinatura não muda. Se o problema
   * piora — nova execução presa, mais uma falha, a fila do executor cresce — a
   * assinatura muda e o alerta volta. Ver `atencao-dispensados.ts`.
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
   * Origem do fluxo por hash, para o selo do assistente. As métricas não a
   * trazem (o alerta nasce do run, não do inventário), então quem compõe a
   * tela — que já tem a lista de fluxos — resolve. Ausente → sem selo.
   */
  origemDoWorkflow?: (hash: string) => string | null | undefined
}): ItemDeAtencao[] {
  const { metrics, executores, origemDoWorkflow } = entrada
  const itens: ItemDeAtencao[] = []
  const periodo = metrics?.period_days ?? 30

  // 1. Presas: `now.stuck` já vem ordenado da mais antiga para a mais nova.
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
      // A presa é única por execução (o run_id); dispensá-la a esconde enquanto
      // esta execução seguir presa — outra que emperre tem `chave` própria.
      assinatura: s.run_id,
    })
  }

  // 2. Falhas repetidas. O backend já ordena por `failure_count` desc.
  for (const w of metrics?.top_failing_workflows ?? []) {
    const repetida = w.failure_count >= MINIMO_DE_FALHAS || (w.failure_rate ?? 0) >= MINIMO_DE_TAXA_DE_FALHA
    if (!repetida || w.failure_count <= 0) continue
    const nome = nomeDoWorkflow(w.workflow_name, w.workflow_hash)
    // Contagem alta fala por si; taxa alta com poucas execuções precisa do
    // denominador para não parecer pouca coisa ("2 vezes" × "2 de 3").
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
      // A contagem de falhas só cresce: dispensar esconde o estado atual, e uma
      // NOVA falha (contagem maior) muda a assinatura e traz o alerta de volta.
      assinatura: String(w.failure_count),
    })
  }

  // 3. Executores no teto: `running ≥ max_concurrent` E fila > 0. Só com
  // capacidade publicada e host conhecido — a linha "Sem executor" não é um
  // executor para abrir.
  for (const e of executores) {
    const c = e.capacity
    if (!c || !e.agent_host || e.unassigned) continue
    if (c.max_concurrent <= 0 || c.running < c.max_concurrent || c.queued <= 0) continue
    const nome = e.display_name || e.agent_host
    const p50 = e.p50_seconds ?? null
    // Espera estimada: a fila avança `max_concurrent` de cada vez, cada leva
    // durando a mediana. É ordem de grandeza, e o texto diz "cerca de".
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
      // A carga do executor muda com o tempo: dispensar esconde o estado atual;
      // se rodando/fila mudam (piora), a assinatura muda e o alerta volta.
      assinatura: `${c.running}:${c.queued}`,
    })
  }

  return itens.slice(0, MAXIMO_DE_ITENS)
}

/** "há 12 min", "há 3 h", "há 3 dias" — grão grosso, para uma frase de estado vazio. */
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

/** Frase da lista vazia: quando foi a última falha, ou que não houve nenhuma. */
export function textoDeVazio(metrics: IObservabilityMetrics | null, agora: Date = new Date()): string {
  // A lista vem ordenada por quantidade de falhas: a última falha do período
  // é a mais recente ENTRE todos os itens, não a do primeiro.
  const ultima = (metrics?.top_failing_workflows ?? [])
    .map(w => w.last_failed_at)
    .filter((d): d is string => !!d)
    .sort()
    .at(-1)
  if (ultima && (metrics?.failed_runs ?? 0) > 0) return `Nada pendente. Última falha ${haQuantoTempo(ultima, agora)}.`
  return "Nenhuma falha no período."
}
