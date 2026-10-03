import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react"

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getPendingAcks: vi.fn() },
}))

import { GisFlowService } from "@/service/GisFlowService"
import { VisaoConfirmacoes, usePendingAcks, type PendingAcks } from "@/app/components/observability/visao-confirmacoes"

const svc = GisFlowService as unknown as { getPendingAcks: ReturnType<typeof vi.fn> }
const ok = <T,>(data: T) => ({ success: true, status: 200, data })

beforeEach(() => { vi.resetAllMocks() })
afterEach(cleanup)

function acks(extra: Partial<PendingAcks> = {}): PendingAcks {
  const itens = [
    { job_id: "job-a", executor_id: "exec-0001-xyz", elapsed_seconds: 22 },
    { job_id: "job-b", executor_id: "exec-0002-xyz", elapsed_seconds: 3 },
  ]
  return { itens, limiarSegundos: 15, carregando: false, atrasadas: itens.filter(i => i.elapsed_seconds >= 15), falhou: false, ...extra }
}

describe("VisaoConfirmacoes", () => {
  it("textos em português, sem jargão", () => {
    const onAbrir = vi.fn()
    render(<VisaoConfirmacoes acks={acks()} onAbrirExecucao={onAbrir} />)
    expect(screen.getByRole("heading", { name: "Confirmações pendentes" })).toBeInTheDocument()
    expect(screen.getByText("1 atrasada")).toBeInTheDocument()
    expect(screen.getByText("2 em espera")).toBeInTheDocument()
    expect(screen.getByText(/1 execução enviada há mais de 15 s sem confirmação/)).toBeInTheDocument()
    const secao = screen.getByRole("region", { name: "Confirmações pendentes" })
    expect(secao.textContent).not.toMatch(/overdue|ACK|job\(s\)|frame/i)
    fireEvent.click(screen.getByRole("button", { name: "Abrir execução job-a" }))
    expect(onAbrir).toHaveBeenCalledWith("job-a")
  })

  it("vazio e falha", () => {
    const { rerender } = render(<VisaoConfirmacoes acks={acks({ itens: [], atrasadas: [] })} onAbrirExecucao={() => {}} />)
    expect(screen.getByText(/Nenhuma execução esperando confirmação/)).toBeInTheDocument()
    rerender(<VisaoConfirmacoes acks={acks({ falhou: true })} onAbrirExecucao={() => {}} />)
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível consultar a fila de confirmações. Os itens abaixo são da última leitura que deu certo.")
  })
})

describe("usePendingAcks", () => {
  it("desabilitado não consulta; habilitado lê itens, limiar e atrasadas", async () => {
    const { result: off } = renderHook(() => usePendingAcks({ enabled: false }))
    expect(svc.getPendingAcks).not.toHaveBeenCalled()
    expect(off.current.carregando).toBe(false)

    svc.getPendingAcks.mockResolvedValue(ok({ count: 2, threshold_overdue_seconds: 20, items: [
      { job_id: "a", executor_id: "e", elapsed_seconds: 25 },
      { job_id: "b", executor_id: "e", elapsed_seconds: 5 },
    ] }))
    const { result } = renderHook(() => usePendingAcks({ enabled: true }))
    await waitFor(() => expect(result.current.carregando).toBe(false))
    expect(result.current.limiarSegundos).toBe(20)
    expect(result.current.itens).toHaveLength(2)
    expect(result.current.atrasadas.map(i => i.job_id)).toEqual(["a"])
    expect(result.current.falhou).toBe(false)
  })

  it("falha não vira fila vazia", async () => {
    svc.getPendingAcks.mockResolvedValue({ success: false, status: 500, error: { name: "AxiosError", message: "x" } })
    const { result } = renderHook(() => usePendingAcks({ enabled: true }))
    await waitFor(() => expect(result.current.falhou).toBe(true))
  })
})
