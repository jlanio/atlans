import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"
import type { IObservabilityMetrics } from "@/service/types"

// Só o serviço é dublado: o hook é testado de verdade (paralelismo escopado,
// espinha × seções, sequência). Ele recebe o escopo já resolvido, então não há
// WorkspaceContext para dublar.
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getObservabilityMetrics: vi.fn(),
    getRunsByDay: vi.fn(),
    getObservabilityRuns: vi.fn(),
    getExecutorMetrics: vi.fn(),
    getWorkflows: vi.fn(),
  },
}))

import { GisFlowService } from "@/service/GisFlowService"
import { useDashboardDados } from "@/app/components/dashboard/use-dashboard-dados"

const svc = GisFlowService as unknown as Record<string, ReturnType<typeof vi.fn>>

/** Janela padrão passada pelo `index` (do `?periodo=`, default 30). */
const DIAS = 30

const ok = <T,>(data: T) => ({ success: true, status: 200, data })
const falhou = (message = "boom") => ({ success: false, status: 500, error: { name: "AxiosError", message } })

const metrics = (total_runs = 1) => ({ total_runs, active_workflows: 3, top_failing_workflows: [] } as unknown as IObservabilityMetrics)

function respostasBoas() {
  svc.getObservabilityMetrics.mockResolvedValue(ok(metrics(1)))
  svc.getRunsByDay.mockResolvedValue(ok({ days: [{ day: "2026-09-01", total: 2, success: 2, failed: 0, running: 0 }] }))
  svc.getObservabilityRuns.mockResolvedValue(ok({ total: 1, limit: 6, offset: 0, runs: [{ run_id: "r1", status: "success", started_at: null, finished_at: null, duration_seconds: 1, retry_count: 0, agent_host: null }] }))
  svc.getExecutorMetrics.mockResolvedValue(ok({ executores: [{ agent_host: "h1", display_name: "h1", total_runs: 1, success_runs: 1, failed_runs: 0, success_rate: 1, avg_duration_seconds: 1, last_run_at: null }] }))
  svc.getWorkflows.mockResolvedValue(ok([{ id_hash: "wf1" }]))
}

beforeEach(() => {
  vi.resetAllMocks()
})
afterEach(() => {
  vi.useRealTimers()
})

describe("useDashboardDados", () => {
  it("cinco fontes escopadas partem juntas, com janela de 30 dias", async () => {
    respostasBoas()
    const { result } = renderHook(({ escopo, dias }) => useDashboardDados(escopo, dias), { initialProps: { escopo: "ws1" as string | null, dias: 30 } })
    expect(result.current.carregando).toBe(true)
    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(svc.getObservabilityMetrics).toHaveBeenCalledWith(DIAS, false, { workspace_id: "ws1" })
    expect(svc.getRunsByDay).toHaveBeenCalledWith(DIAS, expect.objectContaining({ workspace_id: "ws1" }))
    expect(svc.getObservabilityRuns).toHaveBeenCalledWith(expect.objectContaining({ limit: 6, workspace_id: "ws1" }))
    expect(svc.getExecutorMetrics).toHaveBeenCalledWith(DIAS, false, { workspace_id: "ws1" })
    expect(svc.getWorkflows).toHaveBeenCalledWith("ws1", { incluirDoAssistente: true })

    expect(result.current.metrics?.total_runs).toBe(1)
    expect(result.current.dias).toHaveLength(1)
    expect(result.current.runs).toHaveLength(1)
    expect(result.current.executores).toHaveLength(1)
    expect(result.current.workflows.map(w => w.id_hash)).toEqual(["wf1"])
    expect(result.current.erroEspinha).toBeNull()
    expect(result.current.falhas).toEqual({ metrics: false, dias: false, runs: false, workflows: false })
  })

  it("escopo 'todos' (null) manda workspace_id undefined a todas as fontes", async () => {
    respostasBoas()
    const { result, rerender } = renderHook(({ escopo, dias }) => useDashboardDados(escopo, dias), { initialProps: { escopo: "ws1" as string | null, dias: 30 } })
    await waitFor(() => expect(result.current.carregando).toBe(false))

    rerender({ escopo: null, dias: 30 })
    await waitFor(() => expect(svc.getWorkflows).toHaveBeenLastCalledWith(undefined, { incluirDoAssistente: true }))
    expect(svc.getObservabilityMetrics).toHaveBeenLastCalledWith(DIAS, false, { workspace_id: undefined })
  })

  it("trocar o período recarrega as três fontes de janela na nova janela", async () => {
    respostasBoas()
    const { result, rerender } = renderHook(({ escopo, dias }) => useDashboardDados(escopo, dias), { initialProps: { escopo: "ws1" as string | null, dias: 30 } })
    await waitFor(() => expect(result.current.carregando).toBe(false))

    rerender({ escopo: "ws1", dias: 7 })
    await waitFor(() => expect(svc.getObservabilityMetrics).toHaveBeenLastCalledWith(7, false, { workspace_id: "ws1" }))
    expect(svc.getRunsByDay).toHaveBeenLastCalledWith(7, expect.objectContaining({ workspace_id: "ws1" }))
    expect(svc.getExecutorMetrics).toHaveBeenLastCalledWith(7, false, { workspace_id: "ws1" })
    // Trocar só o período (mesmo escopo) não é 1ª carga: o dado fica na tela, não zera.
    expect(result.current.metrics).not.toBeNull()
  })

  it("falha de metrics na 1ª carga liga erroEspinha", async () => {
    respostasBoas()
    svc.getObservabilityMetrics.mockResolvedValue(falhou("Sem permissão"))
    const { result } = renderHook(({ escopo, dias }) => useDashboardDados(escopo, dias), { initialProps: { escopo: "ws1" as string | null, dias: 30 } })
    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(result.current.erroEspinha).toBe("Sem permissão")
    expect(result.current.metrics).toBeNull()
    expect(result.current.falhas.metrics).toBe(true)
  })

  it("falha de dias/runs vira falhas.* sem zerar o que já estava na tela", async () => {
    respostasBoas()
    const { result } = renderHook(({ escopo, dias }) => useDashboardDados(escopo, dias), { initialProps: { escopo: "ws1" as string | null, dias: 30 } })
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(result.current.dias).toHaveLength(1)

    // Recarrega com essas duas seções falhando: a espinha segue, os dados ficam.
    svc.getRunsByDay.mockResolvedValue(falhou())
    svc.getObservabilityRuns.mockResolvedValue(falhou())
    act(() => result.current.recarregar())
    await waitFor(() => expect(result.current.falhas.dias).toBe(true))

    expect(result.current.falhas.runs).toBe(true)
    expect(result.current.erroEspinha).toBeNull()
    // Sem zerar: o que já havia continua.
    expect(result.current.dias).toHaveLength(1)
    expect(result.current.runs).toHaveLength(1)
  })

  it("executores que falha vira [] e NÃO vira aviso", async () => {
    respostasBoas()
    svc.getExecutorMetrics.mockResolvedValue(falhou())
    const { result } = renderHook(({ escopo, dias }) => useDashboardDados(escopo, dias), { initialProps: { escopo: "ws1" as string | null, dias: 30 } })
    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(result.current.executores).toEqual([])
    expect(Object.keys(result.current.falhas)).not.toContain("executores")
    expect(result.current.erroEspinha).toBeNull()
  })

  it("resposta atrasada do escopo anterior é descartada (carimbo de sequência)", async () => {
    // ws1 responde DEPOIS de ws2: a tela tem de ficar com ws2.
    let soltarWs1: (v: unknown) => void = () => {}
    svc.getObservabilityMetrics.mockImplementation((_d: number, _f: boolean, filtros: { workspace_id?: string }) =>
      filtros.workspace_id === "ws1" ? new Promise(r => { soltarWs1 = r }) : Promise.resolve(ok(metrics(2))))
    svc.getRunsByDay.mockResolvedValue(ok({ days: [] }))
    svc.getObservabilityRuns.mockResolvedValue(ok({ total: 0, limit: 6, offset: 0, runs: [] }))
    svc.getExecutorMetrics.mockResolvedValue(ok({ executores: [] }))
    svc.getWorkflows.mockResolvedValue(ok([]))

    const { result, rerender } = renderHook(({ escopo, dias }) => useDashboardDados(escopo, dias), { initialProps: { escopo: "ws1" as string | null, dias: 30 } })
    rerender({ escopo: "ws2", dias: 30 })
    await waitFor(() => expect(result.current.metrics?.total_runs).toBe(2))

    await act(async () => { soltarWs1(ok(metrics(1))) })
    expect(result.current.metrics?.total_runs).toBe(2)
    expect(result.current.erroEspinha).toBeNull()
  })
})
