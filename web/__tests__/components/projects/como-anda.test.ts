import { describe, expect, it } from "vitest"
import { JANELA_EM_DIAS, derivarComoAnda } from "@/app/components/projects/como-anda"
import { formatarQuando } from "@/lib/formatos"
import type { RunningRun } from "@/context/ActiveRunsContext"
import type { IWorkflowMetricsRow } from "@/service/types"

const agora = new Date("2026-09-07T12:00:00Z")
const haMin = (min: number) => new Date(agora.getTime() - min * 60_000).toISOString()
const haDias = (dias: number) => new Date(agora.getTime() - dias * 86_400_000).toISOString()

function metrica(extra: Partial<IWorkflowMetricsRow> = {}): IWorkflowMetricsRow {
  return {
    workflow_hash: "wf-1", workflow_name: "Fluxo", workspace_id: "ws-1", workspace_name: "Cadastro", active: true,
    total_runs: 61, success_runs: 58, failed_runs: 3, running_runs: 0, success_rate: 0.95, p50_seconds: 180,
    last_run_at: haMin(180), last_status: "success", last_error: null, last_error_category: null, ...extra,
  }
}

function run(extra: Partial<RunningRun> = {}): RunningRun {
  return {
    runId: "run-1", workflowHash: "wf-1", name: "Fluxo",
    startedAt: haMin(4), triggerSource: "schedule", executorName: "geo-01", ...extra,
  }
}

const novo = { created_at: haDias(2) }
const antigo = { created_at: haDias(45) }

describe("derivarComoAnda", () => {
  it("run vivo vence a métrica — inclusive uma falha registrada", () => {
    const r = derivarComoAnda(antigo, metrica({ last_status: "failed", last_error: "boom" }), run(), false, agora)
    expect(r).toEqual({
      tipo: "executando",
      desde: "há 4 min",
      instante: new Date(haMin(4)).getTime(),
      origem: "agendado",
      executor: "geo-01",
      tipica: 180,
    })
  })

  it("run vivo vence até a falta de métricas", () => {
    const r = derivarComoAnda(antigo, undefined, run(), true, agora)
    expect(r.tipo).toBe("executando")
    if (r.tipo === "executando") {
      expect(r.tipica).toBeNull()
      expect(r.origem).toBe("agendado")
    }
  })

  it("run vivo ainda na fila: sem 'desde', e conta como agora para ordenar", () => {
    const r = derivarComoAnda(antigo, metrica(), run({ startedAt: null, triggerSource: null, executorName: null }), false, agora)
    expect(r).toMatchObject({ tipo: "executando", desde: "", instante: agora.getTime(), origem: null, executor: null })
  })

  it("métricas indisponíveis, sem run vivo", () => {
    expect(derivarComoAnda(antigo, undefined, undefined, true, agora)).toEqual({ tipo: "indisponivel" })
  })

  it("concluída: quando formatado, números crus, sem erro", () => {
    const m = metrica()
    const r = derivarComoAnda(antigo, m, undefined, false, agora)
    expect(r).toEqual({
      tipo: "concluida",
      quando: formatarQuando(m.last_run_at, agora),
      instante: new Date(m.last_run_at!).getTime(),
      erro: null,
      total: 61,
      falhas: 3,
      mediana: 180,
    })
  })

  it("falhou: leva o erro aparado", () => {
    const r = derivarComoAnda(antigo, metrica({ last_status: "failed", last_error: "  Timeout no WFS  ", last_run_at: haMin(40) }), undefined, false, agora)
    expect(r).toMatchObject({ tipo: "falhou", quando: "há 40 min", erro: "Timeout no WFS", total: 61, falhas: 3 })
    // `error` (per-node status the backend also uses) counts as a failure; an empty error becomes null.
    const semTexto = derivarComoAnda(antigo, metrica({ last_status: "error", last_error: "   " }), undefined, false, agora)
    expect(semTexto).toMatchObject({ tipo: "falhou", erro: null })
  })

  it("cancelada", () => {
    expect(derivarComoAnda(antigo, metrica({ last_status: "cancelled" }), undefined, false, agora)).toMatchObject({ tipo: "cancelada", erro: null })
  })

  it("métrica diz 'rodando' mas o contexto não tem o run: em execução com o que se sabe", () => {
    const r = derivarComoAnda(antigo, metrica({ last_status: "running", last_run_at: haMin(2) }), undefined, false, agora)
    expect(r).toMatchObject({ tipo: "executando", desde: "há 2 min", origem: null, executor: null, tipica: 180 })
  })

  it("nunca: nada na janela e criado há menos de 30 dias", () => {
    expect(derivarComoAnda(novo, undefined, undefined, false, agora)).toEqual({ tipo: "nunca" })
    expect(derivarComoAnda(novo, metrica({ total_runs: 0, last_run_at: null, last_status: null }), undefined, false, agora)).toEqual({ tipo: "nunca" })
    expect(derivarComoAnda({ created_at: haDias(JANELA_EM_DIAS - 1) }, undefined, undefined, false, agora)).toEqual({ tipo: "nunca" })
  })

  it("sem execuções: nada na janela e o workflow é antigo (ou não se sabe quando nasceu)", () => {
    expect(derivarComoAnda(antigo, undefined, undefined, false, agora)).toEqual({ tipo: "sem-execucoes" })
    expect(derivarComoAnda({ created_at: haDias(JANELA_EM_DIAS) }, undefined, undefined, false, agora)).toEqual({ tipo: "sem-execucoes" })
    expect(derivarComoAnda({}, undefined, undefined, false, agora)).toEqual({ tipo: "sem-execucoes" })
    // A row with runs but no `last_run_at` is not "never": there were runs.
    expect(derivarComoAnda(novo, metrica({ total_runs: 3, last_run_at: null }), undefined, false, agora)).toEqual({ tipo: "sem-execucoes" })
  })
})
