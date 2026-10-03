import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"
import { ESTADO_PADRAO, type EstadoDoHistorico } from "@/app/components/observability/historico-url"

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getObservabilityRuns: vi.fn() },
}))

import { GisFlowService } from "@/service/GisFlowService"
import { TAMANHO_DA_PAGINA, useExecucoes } from "@/app/components/observability/use-execucoes"

const svc = GisFlowService as unknown as { getObservabilityRuns: ReturnType<typeof vi.fn> }

type Deferido<T> = { promise: Promise<T>; resolve: (v: T) => void }
function deferido<T>(): Deferido<T> {
  let resolve!: (v: T) => void
  const promise = new Promise<T>(r => { resolve = r })
  return { promise, resolve }
}

const pagina = (ids: string[], extra: Partial<{ total: number | null; has_more: boolean }> = {}) => ({
  success: true, status: 200,
  data: { total: extra.total ?? null, has_more: extra.has_more ?? false, limit: TAMANHO_DA_PAGINA, offset: 0, runs: ids.map(run_id => ({ run_id, status: "success" })) },
})

function estado(extra: Partial<EstadoDoHistorico> = {}): EstadoDoHistorico {
  return { ...ESTADO_PADRAO, ...extra }
}

beforeEach(() => { vi.resetAllMocks() })
afterEach(() => { vi.useRealTimers() })

describe("useExecucoes", () => {
  it("o chip Assistente vira workflow_origem, sem tocar no trigger_source", async () => {
    svc.getObservabilityRuns.mockResolvedValue(pagina(["a"]))
    const { result, rerender } = renderHook(
      ({ e }) => useExecucoes(e, { habilitado: true }),
      { initialProps: { e: estado({ assistente: true, origem: "manual" }) } },
    )
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(svc.getObservabilityRuns.mock.calls[0][0]).toMatchObject({
      workflow_origem: "assistente", trigger_source: "manual",
    })

    // Turning the chip off redoes the first page's list, without the slice.
    rerender({ e: estado({ assistente: false, origem: "manual" }) })
    await waitFor(() => expect(svc.getObservabilityRuns).toHaveBeenCalledTimes(2))
    const params = svc.getObservabilityRuns.mock.calls[1][0]
    expect(params.workflow_origem).toBeUndefined()
    expect(params.offset).toBe(0)
  })

  it("manda todos os filtros do estado, com date_from da janela e with_total só na primeira página", async () => {
    svc.getObservabilityRuns.mockResolvedValue(pagina(["a"], { total: 1, has_more: true }))
    const antes = Date.now()
    const { result } = renderHook(() => useExecucoes(
      estado({ periodo: 7, status: "failed", workspace: "ws1", workflow: "wf1", executor: "host1", origem: "schedule", q: "  timeout " }),
      { habilitado: true },
    ))
    await waitFor(() => expect(result.current.carregando).toBe(false))

    const params = svc.getObservabilityRuns.mock.calls[0][0]
    expect(params).toMatchObject({
      status: "failed", workspace_id: "ws1", workflow_id: "wf1", worker_host: "host1", trigger_source: "schedule", q: "timeout",
      limit: TAMANHO_DA_PAGINA, offset: 0, with_total: true,
    })
    const dateFrom = Date.parse(params.date_from)
    expect(antes - dateFrom).toBeGreaterThanOrEqual(7 * 24 * 3600 * 1000 - 1000)
    expect(antes - dateFrom).toBeLessThan(7 * 24 * 3600 * 1000 + 5000)
    expect(result.current.total).toBe(1)
    expect(result.current.hasMore).toBe(true)

    // Second page: accumulates, without with_total, offset advanced.
    svc.getObservabilityRuns.mockResolvedValue(pagina(["b"]))
    act(() => { result.current.carregarMais() })
    await waitFor(() => expect(result.current.runs.map(r => r.run_id)).toEqual(["a", "b"]))
    const segunda = svc.getObservabilityRuns.mock.calls[1][0]
    expect(segunda.offset).toBe(1)
    expect(segunda.with_total).toBeUndefined()
    // The first page's total stays.
    expect(result.current.total).toBe(1)
    expect(result.current.hasMore).toBe(false)
  })

  it("filtros ausentes não viajam", async () => {
    svc.getObservabilityRuns.mockResolvedValue(pagina([]))
    const { result } = renderHook(() => useExecucoes(estado(), { habilitado: true }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    const params = svc.getObservabilityRuns.mock.calls[0][0]
    expect(params.status).toBeUndefined()
    expect(params.workspace_id).toBeUndefined()
    expect(params.q).toBeUndefined()
    expect(params.date_from).toBeDefined()
  })

  it("não busca desabilitado", () => {
    renderHook(() => useExecucoes(estado(), { habilitado: false }))
    expect(svc.getObservabilityRuns).not.toHaveBeenCalled()
  })

  it("ignora a resposta velha quando o filtro muda antes de ela chegar", async () => {
    const lenta = deferido<ReturnType<typeof pagina>>()
    const rapida = deferido<ReturnType<typeof pagina>>()
    svc.getObservabilityRuns.mockReturnValueOnce(lenta.promise).mockReturnValueOnce(rapida.promise)

    const { result, rerender } = renderHook(
      ({ e }) => useExecucoes(e, { habilitado: true }),
      { initialProps: { e: estado() } },
    )
    rerender({ e: estado({ status: "failed" }) })
    expect(svc.getObservabilityRuns).toHaveBeenCalledTimes(2)

    await act(async () => { rapida.resolve(pagina(["nova"], { total: 1 })) })
    await waitFor(() => expect(result.current.runs.map(r => r.run_id)).toEqual(["nova"]))

    await act(async () => { lenta.resolve(pagina(["velha-1", "velha-2"], { total: 2 })) })
    // The slow one arrived later, but it was from the previous filter: nothing changes.
    expect(result.current.runs.map(r => r.run_id)).toEqual(["nova"])
    expect(result.current.total).toBe(1)
    expect(result.current.carregando).toBe(false)
  })

  it("trocar de visão ou abrir uma execução não refaz a lista", async () => {
    svc.getObservabilityRuns.mockResolvedValue(pagina(["a"]))
    const { result, rerender } = renderHook(
      ({ e }) => useExecucoes(e, { habilitado: true }),
      { initialProps: { e: estado() } },
    )
    await waitFor(() => expect(result.current.carregando).toBe(false))
    rerender({ e: estado({ visao: "workflows", execucao: "a" }) })
    expect(svc.getObservabilityRuns).toHaveBeenCalledTimes(1)
  })

  it("falha vira `falhou`, e recarregar limpa", async () => {
    svc.getObservabilityRuns.mockResolvedValueOnce({ success: false, status: 500, error: { name: "AxiosError", message: "boom" } })
    const { result } = renderHook(() => useExecucoes(estado(), { habilitado: true }))
    await waitFor(() => expect(result.current.falhou).toBe(true))
    expect(result.current.carregando).toBe(false)
    svc.getObservabilityRuns.mockResolvedValueOnce(pagina(["a"], { total: 1 }))
    act(() => { result.current.recarregar() })
    await waitFor(() => expect(result.current.falhou).toBe(false))
    expect(result.current.runs).toHaveLength(1)
  })
})
