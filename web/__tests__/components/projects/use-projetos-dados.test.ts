import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"
import type { IWorkflow, IWorkflowGroup } from "@/service/types"

// Only the service, the workspace and the toast are doubled: the hook is tested
// for real (parallelism, partial failure, sequencing, metrics poll).
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getWorkflows: vi.fn(),
    getWorkflowGroups: vi.fn(),
    getWorkflowMetricsList: vi.fn(),
  },
}))

// Mutable workspace: each test decides which one is current and whether the context is still
// resolving; `rerender` makes the hook see the switch.
const ws = vi.hoisted(() => ({ current: { id_hash: "ws1" } as { id_hash: string } | null, loading: false }))
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: ws.current, loading: ws.loading }),
}))

const toast = vi.hoisted(() => ({ error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn() }))
vi.mock("@/utils/createToast", () => ({ createToast: toast }))

import { GisFlowService } from "@/service/GisFlowService"
import { INTERVALO_DAS_METRICAS_MS, useProjetosDados } from "@/app/components/projects/use-projetos-dados"

const svc = GisFlowService as unknown as {
  getWorkflows: ReturnType<typeof vi.fn>
  getWorkflowGroups: ReturnType<typeof vi.fn>
  getWorkflowMetricsList: ReturnType<typeof vi.fn>
}

const ok = <T,>(data: T) => ({ success: true, status: 200, data })
const falhou = (message = "boom") => ({ success: false, status: 500, error: { name: "AxiosError", message } })

function wf(id: string, extra: Partial<IWorkflow> = {}): IWorkflow {
  return {
    id_hash: id, flag_ative: true, name: `Fluxo ${id}`, description: "", version: "1", priority: 0,
    definition: { nodes: [], edges: [] }, created_by_id: "u1", updated_by_id: "u1", ...extra,
  }
}

function grupo(id: string): IWorkflowGroup {
  return { id: 1, id_hash: id, name: `Grupo ${id}`, workflow_count: 0, created_at: "", updated_at: "" }
}

const metrica = (hash: string, total = 1) => ({ workflow_hash: hash, total_runs: total, last_status: "success" })

function respostasBoas(sufixo = "") {
  svc.getWorkflows.mockResolvedValue(ok([wf(`a${sufixo}`), wf(`b${sufixo}`)]))
  svc.getWorkflowGroups.mockResolvedValue(ok([grupo(`g${sufixo}`)]))
  svc.getWorkflowMetricsList.mockResolvedValue(ok({ period_days: 30, workflows: [metrica(`a${sufixo}`)] }))
}

beforeEach(() => {
  vi.resetAllMocks()
  ws.current = { id_hash: "ws1" }
  ws.loading = false
})
afterEach(() => {
  vi.useRealTimers()
})

describe("useProjetosDados", () => {
  it("três chamadas em paralelo, por workspace, com janela de 30 dias e sem force", async () => {
    respostasBoas()
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    expect(result.current.carregando).toBe(true)
    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(svc.getWorkflows).toHaveBeenCalledWith("ws1", { incluirDoAssistente: true })
    expect(svc.getWorkflowGroups).toHaveBeenCalledWith("ws1")
    expect(svc.getWorkflowMetricsList).toHaveBeenCalledWith(30, false, { workspace_id: "ws1" })
    // They start together: all have already been called when the first one responds.
    expect(svc.getWorkflows).toHaveBeenCalledTimes(1)
    expect(svc.getWorkflowGroups).toHaveBeenCalledTimes(1)
    expect(svc.getWorkflowMetricsList).toHaveBeenCalledTimes(1)

    expect(result.current.workflows.map(w => w.id_hash)).toEqual(["a", "b"])
    expect(result.current.grupos.map(g => g.id_hash)).toEqual(["g"])
    expect(result.current.metricas?.get("a")?.total_runs).toBe(1)
    expect(result.current.metricas?.has("b")).toBe(false)
    expect(result.current.erro).toBeNull()
    expect(result.current.metricasIndisponiveis).toBe(false)
    expect(result.current.atualizadoEm).not.toBeNull()
    expect(result.current.atualizando).toBe(false)
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("espera o context resolver o workspace antes de buscar", async () => {
    respostasBoas()
    ws.loading = true
    const { result, rerender } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    expect(svc.getWorkflows).not.toHaveBeenCalled()
    expect(result.current.carregando).toBe(true)

    ws.loading = false
    rerender()
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(svc.getWorkflows).toHaveBeenCalledTimes(1)
  })

  it("só as métricas falharam: a lista sai completa, sem erro, com o aviso discreto", async () => {
    respostasBoas()
    svc.getWorkflowMetricsList.mockResolvedValue(falhou())
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(result.current.workflows).toHaveLength(2)
    expect(result.current.grupos).toHaveLength(1)
    expect(result.current.metricas).toBeNull()
    expect(result.current.metricasIndisponiveis).toBe(true)
    expect(result.current.erro).toBeNull()
    expect(result.current.atualizadoEm).not.toBeNull()
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("um `throw` inesperado nas métricas não derruba a tela (allSettled)", async () => {
    respostasBoas()
    svc.getWorkflowMetricsList.mockRejectedValue(new Error("rede"))
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(result.current.workflows).toHaveLength(2)
    expect(result.current.metricasIndisponiveis).toBe(true)
    expect(result.current.erro).toBeNull()
  })

  it("a listagem falhou na 1ª carga: estado de erro com a mensagem e o carregando desliga, sem toast", async () => {
    respostasBoas()
    svc.getWorkflows.mockResolvedValue(falhou("Sem permissão"))
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(result.current.erro).toBe("Sem permissão")
    expect(result.current.workflows).toEqual([])
    expect(result.current.atualizadoEm).toBeNull()
    // With no accepted load, the error card takes over the screen and already announces the failure
    // (role="alert"): the toast would make the screen reader read the same failure twice.
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("recarga que falha com a lista na tela: a lista fica e o toast avisa", async () => {
    respostasBoas()
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    const carimbo = result.current.atualizadoEm

    svc.getWorkflows.mockResolvedValue(falhou("caiu"))
    await act(async () => { result.current.recarregar() })
    await waitFor(() => expect(result.current.atualizando).toBe(false))
    expect(result.current.workflows.map(w => w.id_hash)).toEqual(["a", "b"])
    expect(result.current.atualizadoEm).toBe(carimbo)
    expect(toast.error).toHaveBeenCalledTimes(1)
    expect(toast.error).toHaveBeenCalledWith("Erro ao carregar projetos", "caiu")
  })

  it("1ª carga falhou: o tick das métricas não carimba a tela (o cartão de erro fica)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    respostasBoas()
    svc.getWorkflows.mockResolvedValue(falhou("boom"))
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 1_000 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(result.current.atualizadoEm).toBeNull()

    // The tick's stamp removed the card (`erro && atualizadoEm == null`), and the
    // screen started saying "first use" for a shelf that never even loaded.
    await act(async () => { await vi.advanceTimersByTimeAsync(1_050) })
    expect(result.current.atualizadoEm).toBeNull()
    expect(result.current.erro).toBe("boom")
    expect(svc.getWorkflowMetricsList).toHaveBeenCalledTimes(1)
  })

  it("os grupos falharam: também é erro (são obrigatórios), com a mensagem padrão quando não há texto", async () => {
    respostasBoas()
    svc.getWorkflowGroups.mockResolvedValue({ success: false, status: 500, error: { name: "AxiosError" } })
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(result.current.erro).toBe("Não foi possível carregar os projetos.")
  })

  it("recarregar: fura o cache das métricas com force, gira o botão e não mostra skeleton", async () => {
    respostasBoas()
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    const carimboAnterior = result.current.atualizadoEm

    // The reload stays pending to observe `atualizando` on with the list still on screen.
    let soltar: (v: unknown) => void = () => {}
    svc.getWorkflowMetricsList.mockImplementation(() => new Promise(r => { soltar = r }))
    act(() => result.current.recarregar({ force: true }))
    await waitFor(() => expect(result.current.atualizando).toBe(true))
    expect(result.current.carregando).toBe(false)
    expect(result.current.workflows).toHaveLength(2)
    expect(svc.getWorkflowMetricsList).toHaveBeenLastCalledWith(30, true, { workspace_id: "ws1" })

    await act(async () => { soltar(ok({ period_days: 30, workflows: [metrica("a", 9)] })) })
    await waitFor(() => expect(result.current.atualizando).toBe(false))
    expect(result.current.metricas?.get("a")?.total_runs).toBe(9)
    expect(result.current.atualizadoEm).toBeGreaterThanOrEqual(carimboAnterior!)
    // Without `force`, the call goes out without bypassing the cache.
    act(() => result.current.recarregar())
    await waitFor(() => expect(svc.getWorkflowMetricsList).toHaveBeenLastCalledWith(30, false, { workspace_id: "ws1" }))
  })

  it("resposta atrasada do workspace anterior é descartada (carimbo de sequência)", async () => {
    // ws1 responds AFTER ws2: the screen has to stay with ws2.
    let soltarWs1: (v: unknown) => void = () => {}
    svc.getWorkflows.mockImplementation((id: string) =>
      id === "ws1" ? new Promise(r => { soltarWs1 = r }) : Promise.resolve(ok([wf("z")])),
    )
    svc.getWorkflowGroups.mockResolvedValue(ok([]))
    svc.getWorkflowMetricsList.mockResolvedValue(ok({ period_days: 30, workflows: [] }))

    const { result, rerender } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    ws.current = { id_hash: "ws2" }
    rerender()
    await waitFor(() => expect(result.current.workflows.map(w => w.id_hash)).toEqual(["z"]))
    expect(result.current.carregando).toBe(false)

    await act(async () => { soltarWs1(ok([wf("velho")])) })
    expect(result.current.workflows.map(w => w.id_hash)).toEqual(["z"])
    expect(result.current.erro).toBeNull()
  })

  it("trocar de workspace mostra skeleton de novo (é outra estante), e recarregar o mesmo não", async () => {
    respostasBoas()
    const { result, rerender } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))

    let soltar: (v: unknown) => void = () => {}
    svc.getWorkflows.mockImplementation(() => new Promise(r => { soltar = r }))
    ws.current = { id_hash: "ws2" }
    rerender()
    await waitFor(() => expect(result.current.carregando).toBe(true))
    expect(result.current.atualizando).toBe(false)
    await act(async () => { soltar(ok([wf("n")])) })
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(result.current.workflows.map(w => w.id_hash)).toEqual(["n"])
  })

  it("sem workspace: listagem sem recorte, métricas não são pedidas e a coluna fica vazia, sem aviso", async () => {
    ws.current = null
    svc.getWorkflows.mockResolvedValue(ok([wf("solto")]))
    svc.getWorkflowGroups.mockResolvedValue(ok([]))
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(svc.getWorkflows).toHaveBeenCalledWith(undefined, { incluirDoAssistente: true })
    expect(svc.getWorkflowMetricsList).not.toHaveBeenCalled()
    expect(result.current.metricas?.size).toBe(0)
    expect(result.current.metricasIndisponiveis).toBe(false)
  })

  it("métricas se atualizam sozinhas no intervalo, só elas, com a aba visível; falha no tick mantém o que havia", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    respostasBoas()
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 1_000 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(svc.getWorkflowMetricsList).toHaveBeenCalledTimes(1)

    svc.getWorkflowMetricsList.mockResolvedValue(ok({ period_days: 30, workflows: [metrica("a", 5)] }))
    await act(async () => { await vi.advanceTimersByTimeAsync(1_050) })
    await waitFor(() => expect(result.current.metricas?.get("a")?.total_runs).toBe(5))
    expect(svc.getWorkflowMetricsList).toHaveBeenCalledTimes(2)
    expect(svc.getWorkflowMetricsList).toHaveBeenLastCalledWith(30, false, { workspace_id: "ws1" })
    // The listing does not change on its own; and no skeleton or spinning button.
    expect(svc.getWorkflows).toHaveBeenCalledTimes(1)
    expect(result.current.carregando).toBe(false)
    expect(result.current.atualizando).toBe(false)

    // A tick that fails: the previous data stays, without becoming "indisponível".
    svc.getWorkflowMetricsList.mockResolvedValue(falhou())
    await act(async () => { await vi.advanceTimersByTimeAsync(1_050) })
    expect(svc.getWorkflowMetricsList).toHaveBeenCalledTimes(3)
    expect(result.current.metricas?.get("a")?.total_runs).toBe(5)
    expect(result.current.metricasIndisponiveis).toBe(false)

    // Hidden tab: no tick.
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "hidden" })
    await act(async () => { await vi.advanceTimersByTimeAsync(2_100) })
    expect(svc.getWorkflowMetricsList).toHaveBeenCalledTimes(3)
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" })
  })

  it("o intervalo padrão é de 60 s", () => {
    expect(INTERVALO_DAS_METRICAS_MS).toBe(60_000)
  })

  it("definirWorkflows/definirGrupos aceitam função para a atualização otimista do index", async () => {
    respostasBoas()
    const { result } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))

    act(() => result.current.definirWorkflows(prev => prev.map(w => w.id_hash === "a" ? { ...w, flag_ative: false } : w)))
    expect(result.current.workflows.find(w => w.id_hash === "a")?.flag_ative).toBe(false)
    act(() => result.current.definirGrupos(prev => [...prev, grupo("g2")]))
    expect(result.current.grupos.map(g => g.id_hash)).toEqual(["g", "g2"])
    // None of this goes to the network.
    expect(svc.getWorkflows).toHaveBeenCalledTimes(1)
  })

  it("`recarregar` é estável entre renders (desce para o botão Atualizar)", async () => {
    respostasBoas()
    const { result, rerender } = renderHook(() => useProjetosDados({ intervaloDasMetricasMs: 0 }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    const antes = result.current.recarregar
    rerender()
    expect(result.current.recarregar).toBe(antes)
  })
})
