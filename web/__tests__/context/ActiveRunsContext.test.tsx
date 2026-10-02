import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, render, screen, waitFor } from "@testing-library/react"

// Só o serviço e os contextos vizinhos são dublados: o provider faz o poll de
// verdade e o consumidor mostra o que o contexto expõe.
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getWorkflows: vi.fn(),
    getObservabilityRuns: vi.fn(),
    getRunDetail: vi.fn(),
  },
}))

vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: { id_hash: "ws1" } }),
}))

// Estável entre renders: `addNotification` entra nas dependências do efeito
// do provider, e uma função nova a cada render reiniciaria o poll.
const addNotification = vi.hoisted(() => vi.fn())
vi.mock("@/context/NotificationsContext", () => ({
  useNotifications: () => ({ addNotification }),
}))

import { GisFlowService } from "@/service/GisFlowService"
import { ActiveRunsProvider, useActiveRuns } from "@/context/ActiveRunsContext"

const svc = GisFlowService as unknown as {
  getWorkflows: ReturnType<typeof vi.fn>
  getObservabilityRuns: ReturnType<typeof vi.fn>
  getRunDetail: ReturnType<typeof vi.fn>
}

const ok = <T,>(data: T) => ({ success: true, status: 200, data })

function Consumidor() {
  const { runningRuns, runningHashes, runningCount } = useActiveRuns()
  return (
    <pre data-testid="saida">
      {JSON.stringify({ runningRuns, hashes: [...runningHashes].sort(), runningCount })}
    </pre>
  )
}

function lerSaida() {
  return JSON.parse(screen.getByTestId("saida").textContent ?? "{}") as {
    runningRuns: { runId: string; workflowHash: string; name: string; startedAt: string | null; triggerSource: string | null; executorName: string | null }[]
    hashes: string[]
    runningCount: number
  }
}

beforeEach(() => {
  vi.resetAllMocks()
  svc.getWorkflows.mockResolvedValue(ok([
    { id_hash: "wf-a", name: "Consolidação de outorgas" },
    { id_hash: "wf-b", name: "Mapa de risco" },
  ]))
})
afterEach(() => {
  vi.useRealTimers()
})

describe("ActiveRunsProvider", () => {
  it("cada run vivo carrega started_at, trigger_source e executor_name do /observability/runs", async () => {
    svc.getObservabilityRuns.mockResolvedValue(ok({
      runs: [
        {
          run_id: "run-1", workflow_hash: "wf-a", status: "running",
          started_at: "2026-09-07T11:56:00", trigger_source: "schedule", executor_name: "geo-01",
        },
        // Ainda na fila: sem início, sem executor.
        { run_id: "run-2", workflow_hash: "wf-b", status: "pending", started_at: null, trigger_source: "manual", executor_name: null },
      ],
    }))
    render(<ActiveRunsProvider><Consumidor /></ActiveRunsProvider>)

    await waitFor(() => expect(lerSaida().runningCount).toBe(2))
    const { runningRuns, hashes } = lerSaida()
    expect(svc.getObservabilityRuns).toHaveBeenCalledWith({ status: "running", limit: 200 })
    expect(hashes).toEqual(["wf-a", "wf-b"])
    expect(runningRuns).toEqual([
      {
        runId: "run-1", workflowHash: "wf-a", name: "Consolidação de outorgas",
        startedAt: "2026-09-07T11:56:00", triggerSource: "schedule", executorName: "geo-01",
      },
      { runId: "run-2", workflowHash: "wf-b", name: "Mapa de risco", startedAt: null, triggerSource: "manual", executorName: null },
    ])
    // O nome vem da listagem: o endpoint só o dá a admin.
    expect(runningRuns.map(r => r.name)).not.toContain("Workflow")
  })

  it("campos ausentes na resposta viram nulo, e não `undefined` — o contrato do RunningRun é `string | null`", async () => {
    svc.getObservabilityRuns.mockResolvedValue(ok({ runs: [{ run_id: "run-3", workflow_hash: "wf-a", status: "running" }] }))
    render(<ActiveRunsProvider><Consumidor /></ActiveRunsProvider>)
    await waitFor(() => expect(lerSaida().runningCount).toBe(1))
    // O JSON preserva `null` e apaga `undefined`: as três chaves têm de existir.
    expect(lerSaida().runningRuns[0]).toEqual({
      runId: "run-3", workflowHash: "wf-a", name: "Consolidação de outorgas",
      startedAt: null, triggerSource: null, executorName: null,
    })
  })

  it("run de workflow que o workspace não conhece fica de fora (escopo por workspace, como antes)", async () => {
    svc.getObservabilityRuns.mockResolvedValue(ok({
      runs: [
        { run_id: "run-1", workflow_hash: "wf-a", status: "running", started_at: null },
        { run_id: "run-9", workflow_hash: "wf-de-outro-ws", status: "running", started_at: null },
      ],
    }))
    render(<ActiveRunsProvider><Consumidor /></ActiveRunsProvider>)
    await waitFor(() => expect(lerSaida().runningCount).toBe(1))
    expect(lerSaida().hashes).toEqual(["wf-a"])
    // O hash desconhecido fez a lista de nomes ser recarregada uma vez (workflow recém-criado?), sem loop.
    expect(svc.getWorkflows).toHaveBeenCalledTimes(2)
  })

  it("um run que some do conjunto vivo é notificado com o status final, e o contexto esvazia", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    svc.getObservabilityRuns.mockResolvedValue(ok({
      runs: [{ run_id: "run-1", workflow_hash: "wf-a", status: "running", started_at: "2026-09-07T11:56:00" }],
    }))
    svc.getRunDetail.mockResolvedValue(ok({ run_id: "run-1", status: "failed" }))
    render(<ActiveRunsProvider><Consumidor /></ActiveRunsProvider>)
    await waitFor(() => expect(lerSaida().runningCount).toBe(1))

    svc.getObservabilityRuns.mockResolvedValue(ok({ runs: [] }))
    // Com run vivo a cadência é de 10 s.
    await act(async () => { await vi.advanceTimersByTimeAsync(10_100) })
    await waitFor(() => expect(lerSaida().runningCount).toBe(0))
    expect(lerSaida().runningRuns).toEqual([])
    await waitFor(() => expect(addNotification).toHaveBeenCalledWith({
      type: "error", title: "Workflow falhou", message: "Consolidação de outorgas",
    }))
  })
})
