import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"
import { ESTADO_PADRAO, type EstadoDoHistorico } from "@/app/components/observability/historico-url"

// Only the service is doubled: the hook is tested for real (cache, sequence, poll).
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getObservabilityMetrics: vi.fn(),
    getRunsByDay: vi.fn(),
    getExecutorMetrics: vi.fn(),
    getWorkflowMetricsList: vi.fn(),
  },
}))

import { GisFlowService } from "@/service/GisFlowService"
import { chavesDeCache, useHistoricoDados } from "@/app/components/observability/use-historico-dados"

const svc = GisFlowService as unknown as {
  getObservabilityMetrics: ReturnType<typeof vi.fn>
  getRunsByDay: ReturnType<typeof vi.fn>
  getExecutorMetrics: ReturnType<typeof vi.fn>
  getWorkflowMetricsList: ReturnType<typeof vi.fn>
}

const ok = <T,>(data: T) => ({ success: true, status: 200, data })
const falhou = () => ({ success: false, status: 500, error: { name: "AxiosError", message: "boom" } })

function metricas(total: number) {
  return { total_runs: total, period_days: 30 } as unknown as Parameters<typeof ok>[0]
}

function respostasBoas(total = 10) {
  svc.getObservabilityMetrics.mockResolvedValue(ok(metricas(total)))
  svc.getRunsByDay.mockResolvedValue(ok({ days: [{ day: "2026-09-06", total, success: total, failed: 0, running: 0 }] }))
  svc.getExecutorMetrics.mockResolvedValue(ok({ executores: [{ agent_host: "h1" }] }))
  svc.getWorkflowMetricsList.mockResolvedValue(ok({ period_days: 30, workflows: [{ workflow_hash: "wf" }] }))
}

function estado(extra: Partial<EstadoDoHistorico> = {}): EstadoDoHistorico {
  return { ...ESTADO_PADRAO, ...extra }
}

beforeEach(() => {
  vi.resetAllMocks()
})
afterEach(() => {
  vi.useRealTimers()
})

describe("useHistoricoDados", () => {
  it("quatro chamadas em paralelo, recortadas por período e filtros, com o fuso no runs-by-day", async () => {
    respostasBoas()
    const { result } = renderHook(() => useHistoricoDados(estado({ periodo: 7, workspace: "ws1", workflow: "wf1" }), { habilitado: true, intervaloDoAgoraMs: 0 }))
    expect(result.current.carregando).toBe(true)
    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(svc.getObservabilityMetrics).toHaveBeenCalledWith(7, false, { workspace_id: "ws1", workflow_id: "wf1" })
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
    expect(svc.getRunsByDay).toHaveBeenCalledWith(7, { workspace_id: "ws1", workflow_id: "wf1", tz })
    // The fleet and the workflow list aren't sliced by workflow.
    expect(svc.getExecutorMetrics).toHaveBeenCalledWith(7, false, { workspace_id: "ws1" })
    expect(svc.getWorkflowMetricsList).toHaveBeenCalledWith(7, false, { workspace_id: "ws1" })

    expect(result.current.metrics?.total_runs).toBe(10)
    expect(result.current.dias).toHaveLength(1)
    expect(result.current.executores).toHaveLength(1)
    expect(result.current.workflows).toHaveLength(1)
    expect(result.current.periodoDosDados).toBe(7)
    expect(result.current.falhas).toEqual({})
  })

  it("não busca enquanto desabilitado (sessão ainda não resolvida)", async () => {
    respostasBoas()
    const { result, rerender } = renderHook(
      ({ habilitado }) => useHistoricoDados(estado(), { habilitado, intervaloDoAgoraMs: 0 }),
      { initialProps: { habilitado: false } },
    )
    expect(svc.getObservabilityMetrics).not.toHaveBeenCalled()
    rerender({ habilitado: true })
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(svc.getObservabilityMetrics).toHaveBeenCalledTimes(1)
  })

  it("voltar a um período dentro de 60 s vem do cache, sem rede; recarregar fura o cache e manda force", async () => {
    respostasBoas()
    const { result, rerender } = renderHook(
      ({ periodo }: { periodo: 7 | 30 | 90 }) => useHistoricoDados(estado({ periodo }), { habilitado: true, intervaloDoAgoraMs: 0 }),
      { initialProps: { periodo: 30 as 7 | 30 | 90 } },
    )
    await waitFor(() => expect(result.current.carregando).toBe(false))
    rerender({ periodo: 7 })
    await waitFor(() => expect(result.current.periodoDosDados).toBe(7))
    expect(svc.getObservabilityMetrics).toHaveBeenCalledTimes(2)

    rerender({ periodo: 30 })
    await waitFor(() => expect(result.current.periodoDosDados).toBe(30))
    // Cache hit: no new call, and no skeleton.
    expect(svc.getObservabilityMetrics).toHaveBeenCalledTimes(2)
    expect(result.current.carregando).toBe(false)

    act(() => result.current.recarregar())
    await waitFor(() => expect(svc.getObservabilityMetrics).toHaveBeenCalledTimes(3))
    expect(svc.getObservabilityMetrics).toHaveBeenLastCalledWith(30, true, { workspace_id: undefined, workflow_id: undefined })
    expect(svc.getExecutorMetrics).toHaveBeenLastCalledWith(30, true, { workspace_id: undefined })
    expect(svc.getWorkflowMetricsList).toHaveBeenLastCalledWith(30, true, { workspace_id: undefined })
    await waitFor(() => expect(result.current.carregando).toBe(false))
  })

  it("trocar só o workflow reaproveita executores e workflows do cache", async () => {
    respostasBoas()
    const { result, rerender } = renderHook(
      ({ workflow }: { workflow: string | null }) => useHistoricoDados(estado({ workspace: "ws1", workflow }), { habilitado: true, intervaloDoAgoraMs: 0 }),
      { initialProps: { workflow: null as string | null } },
    )
    await waitFor(() => expect(result.current.carregando).toBe(false))
    rerender({ workflow: "wf9" })
    await waitFor(() => expect(svc.getObservabilityMetrics).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(svc.getRunsByDay).toHaveBeenCalledTimes(2)
    expect(svc.getExecutorMetrics).toHaveBeenCalledTimes(1)
    expect(svc.getWorkflowMetricsList).toHaveBeenCalledTimes(1)
  })

  it("resposta velha não sobrescreve a nova (carimbo de sequência)", async () => {
    // Period 30 answers AFTER 7: the screen has to stay with 7.
    let soltar30: (v: unknown) => void = () => {}
    svc.getObservabilityMetrics.mockImplementation((days: number) =>
      days === 30 ? new Promise(r => { soltar30 = r }) : Promise.resolve(ok(metricas(7))),
    )
    svc.getRunsByDay.mockResolvedValue(ok({ days: [] }))
    svc.getExecutorMetrics.mockResolvedValue(ok({ executores: [] }))
    svc.getWorkflowMetricsList.mockResolvedValue(ok({ period_days: 30, workflows: [] }))

    const { result, rerender } = renderHook(
      ({ periodo }: { periodo: 7 | 30 | 90 }) => useHistoricoDados(estado({ periodo }), { habilitado: true, intervaloDoAgoraMs: 0 }),
      { initialProps: { periodo: 30 as 7 | 30 | 90 } },
    )
    rerender({ periodo: 7 })
    await waitFor(() => expect(result.current.metrics?.total_runs).toBe(7))
    await act(async () => { soltar30(ok(metricas(30))) })
    expect(result.current.metrics?.total_runs).toBe(7)
    expect(result.current.periodoDosDados).toBe(7)
    expect(result.current.carregando).toBe(false)
  })

  it("falha parcial vira aviso na parte afetada e mantém o que já havia", async () => {
    respostasBoas(10)
    const { result, rerender } = renderHook(
      ({ periodo }: { periodo: 7 | 30 | 90 }) => useHistoricoDados(estado({ periodo }), { habilitado: true, intervaloDoAgoraMs: 0 }),
      { initialProps: { periodo: 30 as 7 | 30 | 90 } },
    )
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(result.current.executores).toHaveLength(1)

    svc.getExecutorMetrics.mockResolvedValue(falhou())
    svc.getObservabilityMetrics.mockResolvedValue(ok(metricas(99)))
    rerender({ periodo: 7 })
    // Waits for the new DATA, not `carregando`: right after the rerender the
    // effect hasn't started the load yet, and the previous state's
    // `carregando=false` would pass too early (the test was flaky with the
    // whole suite running).
    await waitFor(() => expect(result.current.metrics?.total_runs).toBe(99))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    // Each part arrives and is stored on its own: the executors' failure can
    // land one tick after the metrics.
    await waitFor(() => expect(result.current.falhas.executores).toBe("Não foi possível carregar os executores."))
    expect(result.current.falhas.metrics).toBeUndefined()
    // The previous list stays on screen — better than an empty table.
    expect(result.current.executores).toHaveLength(1)

    // And the part that failed was NOT memoized: going back to 7 redoes only it.
    svc.getExecutorMetrics.mockResolvedValue(ok({ executores: [{ agent_host: "h2" }] }))
    rerender({ periodo: 30 })
    await waitFor(() => expect(result.current.periodoDosDados).toBe(30))
    rerender({ periodo: 7 })
    await waitFor(() => expect(result.current.falhas.executores).toBeUndefined())
    await waitFor(() => expect(result.current.executores[0]?.agent_host).toBe("h2"))
    expect(svc.getExecutorMetrics).toHaveBeenCalledTimes(3)
    expect(svc.getObservabilityMetrics).toHaveBeenCalledTimes(2)
  })

  it("poll da faixa Agora: só as métricas, sem ligar carregando, e só com a aba visível", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    respostasBoas(1)
    const { result } = renderHook(() => useHistoricoDados(estado(), { habilitado: true, intervaloDoAgoraMs: 1_000 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(svc.getObservabilityMetrics).toHaveBeenCalledTimes(1)

    svc.getObservabilityMetrics.mockResolvedValue(ok(metricas(2)))
    await act(async () => { await vi.advanceTimersByTimeAsync(1_050) })
    await waitFor(() => expect(result.current.metrics?.total_runs).toBe(2))
    expect(svc.getObservabilityMetrics).toHaveBeenCalledTimes(2)
    expect(svc.getObservabilityMetrics).toHaveBeenLastCalledWith(30, false, { workspace_id: undefined, workflow_id: undefined })
    expect(svc.getRunsByDay).toHaveBeenCalledTimes(1)
    expect(result.current.carregando).toBe(false)

    // Hidden tab: no tick.
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "hidden" })
    await act(async () => { await vi.advanceTimersByTimeAsync(2_100) })
    expect(svc.getObservabilityMetrics).toHaveBeenCalledTimes(2)
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" })
  })

  it("chaves de cache: métricas e dias por (período, workspace, workflow); frota e workflows só por workspace", () => {
    const c = chavesDeCache({ periodo: 7, workspace: "ws", workflow: "wf" }, "America/Sao_Paulo")
    expect(c.metrics).toBe("metrics|7|ws|wf")
    expect(c.dias).toBe("dias|7|ws|wf|America/Sao_Paulo")
    expect(c.executores).toBe("executores|7|ws")
    expect(c.workflows).toBe("workflows|7|ws")
  })
})
