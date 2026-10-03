import { describe, expect, it } from "vitest"
import {
  MAXIMO_DE_ITENS, haQuantoTempo, montarAtencao, textoDeVazio,
} from "@/app/components/observability/atencao"
import type { IExecutorMetrics, IObservabilityMetrics, IStuckRun, ITopFailingWorkflow } from "@/service/types"

// Minimal fixtures: what `montarAtencao` reads, nothing more.
function metricas(extra: Partial<IObservabilityMetrics> = {}): IObservabilityMetrics {
  return {
    period_days: 30,
    total_workflows: 0, active_workflows: 0, total_runs: 100, failed_runs: 5,
    success_rate: 0.95, avg_duration_seconds: 10, runs_last_24h: 0, runs_last_7d: 0, runs_prev_7d: 0,
    success_rate_prev_7d: null,
    by_status: { success: 95, failed: 5, running: 0, other: 0 },
    top_failing_workflows: [],
    ...extra,
  }
}

function presa(extra: Partial<IStuckRun> = {}): IStuckRun {
  return {
    run_id: "run-1", workflow_hash: "wf-a", workflow_name: "Cadastro rural · lote 7",
    agent_host: "executor:geo-02", executor_name: "geo-02", started_at: null,
    elapsed_seconds: 8040, typical_seconds: 360, ...extra,
  }
}

function falhando(extra: Partial<ITopFailingWorkflow> = {}): ITopFailingWorkflow {
  return {
    workflow_hash: "wf-sicar", workflow_name: "Integração SICAR", failure_count: 28, total_runs: 61,
    failure_rate: 0.46, last_error: "Timeout ao consultar o WFS do SICAR (30 s)",
    last_error_category: "timeout", last_failed_at: null, ...extra,
  }
}

function executor(extra: Partial<IExecutorMetrics> = {}): IExecutorMetrics {
  return {
    agent_host: "executor:geo-02", display_name: "geo-02", total_runs: 10, success_runs: 10, failed_runs: 0,
    success_rate: 1, avg_duration_seconds: 30, last_run_at: null, online: true,
    capacity: { running: 4, queued: 12, max_concurrent: 4, max_queue: 50 }, p50_seconds: 180, ...extra,
  }
}

describe("montarAtencao", () => {
  it("a origem do fluxo entra nos itens que TÊM fluxo, quando quem compõe sabe resolvê-la", () => {
    const itens = montarAtencao({
      metrics: metricas({
        top_failing_workflows: [falhando()],
        now: { running: 1, pending: 0, stuck_count: 1, stuck: [presa()], executors: { online: 1, total: 1 }, queued_on_executors: null, overdue_acks: null },
      }),
      executores: [executor()],
      origemDoWorkflow: hash => (hash === "wf-a" ? "assistente" : "usuario"),
    })
    const porTipo = Object.fromEntries(itens.map(i => [i.tipo, i]))
    expect(porTipo.presa.origem).toBe("assistente")
    expect(porTipo.falhas.origem).toBe("usuario")
    // An executor at its ceiling doesn't belong to a workflow: no made-up origin.
    expect(porTipo.saturado.origem).toBeUndefined()
  })

  it("sem o resolvedor, nenhum item afirma origem (a tela simplesmente não pinta o selo)", () => {
    const [item] = montarAtencao({ metrics: metricas({ top_failing_workflows: [falhando()] }), executores: [] })
    expect(item.origem).toBeUndefined()
  })

  it("vazio sem métricas e sem executores", () => {
    expect(montarAtencao({ metrics: null, executores: [] })).toEqual([])
  })

  it("presa: nome, tempo, executor e duração típica; ação abre a execução", () => {
    const [item] = montarAtencao({
      metrics: metricas({ now: { running: 1, pending: 0, stuck_count: 1, stuck: [presa()], executors: { online: 1, total: 1 }, queued_on_executors: null, overdue_acks: null } }),
      executores: [],
    })
    expect(item.tipo).toBe("presa")
    expect(item.nome).toBe("Cadastro rural · lote 7")
    expect(item.titulo).toBe("Cadastro rural · lote 7 está em andamento há 2 h 14 min")
    expect(item.detalhe).toBe("Em geo-02 · a duração típica é 6 min")
    expect(item.acao).toEqual({ tipo: "abrir-execucao", runId: "run-1" })
    expect(item.rotuloDaAcao).toBe("Abrir")
    expect(item.chave).toBe("presa:run-1")
  })

  it("presa sem executor nem típica não inventa nada", () => {
    const [item] = montarAtencao({
      metrics: metricas({ now: { running: 1, pending: 0, stuck_count: 1, stuck: [presa({ agent_host: null, executor_name: null, typical_seconds: null, workflow_name: null })], executors: { online: 0, total: 0 }, queued_on_executors: null, overdue_acks: null } }),
      executores: [],
    })
    expect(item.nome).toBe("workflow wf-a")
    expect(item.detalhe).toBe("Sem executor · sem duração típica conhecida")
  })

  it("falhas repetidas: por contagem (≥ 3) com último erro e categoria; ação filtra por falhas", () => {
    const [item] = montarAtencao({ metrics: metricas({ top_failing_workflows: [falhando()] }), executores: [] })
    expect(item.tipo).toBe("falhas")
    expect(item.titulo).toBe("Integração SICAR falhou 28 vezes em 30 dias")
    expect(item.detalhe).toBe("Último erro: tempo esgotado · Timeout ao consultar o WFS do SICAR (30 s)")
    expect(item.acao).toEqual({ tipo: "filtrar-workflow", workflowHash: "wf-sicar", status: "failed" })
    expect(item.rotuloDaAcao).toBe("Ver falhas")
  })

  it("falhas repetidas: por taxa (≥ 0,2) com poucas execuções mostra o denominador", () => {
    const [item] = montarAtencao({
      metrics: metricas({ top_failing_workflows: [falhando({ failure_count: 2, total_runs: 5, failure_rate: 0.4, last_error: null, last_error_category: null })] }),
      executores: [],
    })
    expect(item.titulo).toBe("Integração SICAR falhou em 2 de 5 execuções em 30 dias")
    expect(item.detalhe).toBe("Sem mensagem de erro registrada")
  })

  it("uma falha isolada com taxa baixa fica de fora", () => {
    const itens = montarAtencao({
      metrics: metricas({ top_failing_workflows: [falhando({ failure_count: 1, total_runs: 50, failure_rate: 0.02 })] }),
      executores: [],
    })
    expect(itens).toEqual([])
  })

  it("último erro em branco cai para a data da última falha", () => {
    const agora = new Date()
    const ha3h = new Date(agora.getTime() - 3 * 3600_000).toISOString()
    const [item] = montarAtencao({
      metrics: metricas({ top_failing_workflows: [falhando({ last_error: "   ", last_failed_at: ha3h })] }),
      executores: [],
    })
    expect(item.detalhe).toBe("Última falha há 3 h")
  })

  it("executor no teto: running ≥ max_concurrent E fila > 0; ação abre o executor", () => {
    const [item] = montarAtencao({ metrics: null, executores: [executor()] })
    expect(item.tipo).toBe("saturado")
    expect(item.titulo).toBe("geo-02 está no teto: 4 de 4 em execução")
    // 12 na fila ÷ 4 vagas = 3 levas × 3 min = 9 min.
    expect(item.detalhe).toBe("12 execuções na fila · as próximas esperam cerca de 9 min")
    expect(item.acao).toEqual({ tipo: "abrir-executor", agentHost: "executor:geo-02" })
    expect(item.rotuloDaAcao).toBe("Ver executor")
  })

  it("executor cheio mas sem fila, sem capacidade publicada ou sem host não entra", () => {
    const itens = montarAtencao({
      metrics: null,
      executores: [
        executor({ capacity: { running: 4, queued: 0, max_concurrent: 4, max_queue: 50 } }),
        executor({ agent_host: "executor:geo-03", capacity: null }),
        executor({ agent_host: null, display_name: "Sem executor", unassigned: true }),
        executor({ agent_host: "executor:geo-04", capacity: { running: 2, queued: 5, max_concurrent: 4, max_queue: 50 } }),
      ],
    })
    expect(itens).toEqual([])
  })

  it("sem p50 não estima espera", () => {
    const [item] = montarAtencao({ metrics: null, executores: [executor({ p50_seconds: null })] })
    expect(item.detalhe).toBe("12 execuções na fila")
  })

  it("ordem: presas, depois falhas, depois executores; e no máximo 5", () => {
    const stuck = [1, 2, 3].map(i => presa({ run_id: `run-${i}` }))
    const itens = montarAtencao({
      metrics: metricas({
        now: { running: 3, pending: 0, stuck_count: 3, stuck, executors: { online: 1, total: 1 }, queued_on_executors: 12, overdue_acks: null },
        top_failing_workflows: [falhando(), falhando({ workflow_hash: "wf-b", workflow_name: "Uso do solo" })],
      }),
      executores: [executor()],
    })
    expect(itens).toHaveLength(MAXIMO_DE_ITENS)
    expect(itens.map(i => i.tipo)).toEqual(["presa", "presa", "presa", "falhas", "falhas"])
    expect(itens.map(i => i.chave)).toEqual(["presa:run-1", "presa:run-2", "presa:run-3", "falhas:wf-sicar", "falhas:wf-b"])
  })
})

describe("textoDeVazio", () => {
  const agora = new Date(2026, 8, 6, 12, 0)
  it("diz quando foi a última falha", () => {
    const ha3dias = new Date(2026, 8, 3, 9, 0).toISOString()
    const m = metricas({ failed_runs: 4, top_failing_workflows: [falhando({ last_failed_at: ha3dias })] })
    expect(textoDeVazio(m, agora)).toBe("Nada pendente. Última falha há 3 dias.")
  })
  it("sem falha no período", () => {
    expect(textoDeVazio(metricas({ failed_runs: 0 }), agora)).toBe("Nenhuma falha no período.")
    expect(textoDeVazio(null, agora)).toBe("Nenhuma falha no período.")
  })
})

describe("haQuantoTempo", () => {
  const agora = new Date(2026, 8, 6, 12, 0)
  it("grão grosso: min, h, dias", () => {
    expect(haQuantoTempo(new Date(2026, 8, 6, 11, 48).toISOString(), agora)).toBe("há 12 min")
    expect(haQuantoTempo(new Date(2026, 8, 6, 8, 30).toISOString(), agora)).toBe("há 3 h")
    expect(haQuantoTempo(new Date(2026, 8, 5, 12, 0).toISOString(), agora)).toBe("há 1 dia")
    expect(haQuantoTempo(new Date(2026, 8, 6, 11, 59, 40).toISOString(), agora)).toBe("agora")
    expect(haQuantoTempo(null, agora)).toBe("—")
  })
})
