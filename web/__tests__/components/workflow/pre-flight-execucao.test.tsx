import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, cleanup, waitFor } from "@testing-library/react"

// Pré-voo do botão Executar: a política do workspace ativo diz se há para
// onde despachar. O aviso é informativo — o botão NUNCA depende dele, porque
// a leitura pode falhar ou estar defasada e o servidor é quem decide.

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getWorkspacePolicy: vi.fn(), cancelRun: vi.fn() },
}))
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: { id_hash: "ws-a", name: "A" } }),
}))
vi.mock("@/app/hooks/workflow/useExecuteWorkflow", () => ({
  useExecuteWorkflow: () => ({
    executeWorkflow: vi.fn(), isExecuting: false, debugMode: false, setDebugMode: vi.fn(),
  }),
}))
vi.mock("@/app/stores/workflowExecutionStore", () => ({
  useWorkflowExecutionStore: Object.assign(
    (sel: (s: { statusWorkflow: null }) => unknown) => sel({ statusWorkflow: null }),
    { getState: () => ({ resetExecution: vi.fn() }) },
  ),
}))
vi.mock("@/app/stores/workflowSaveStore", () => ({
  useWorkflowSaveStore: (sel: (s: { flagActive: boolean }) => unknown) => sel({ flagActive: true }),
}))
vi.mock("@/app/components/workflow/execute-params-dialog", () => ({ default: () => null }))

import { GisFlowService } from "@/service/GisFlowService"
import ExecuteWorkflow from "@/app/components/workflow/buttons/execute-workflow"
import { isolada, politica } from "../../fixtures/politica"

const getPolicy = vi.mocked(GisFlowService.getWorkspacePolicy)
/* eslint-disable @typescript-eslint/no-explicit-any */
function ok<T>(data: T) { return { status: 200, success: true, data } as any }

beforeEach(() => { cleanup(); vi.clearAllMocks() })

describe("pré-voo do Executar", () => {
  it("avisa quando a cadeia efetiva não tem ninguém online — e o botão continua habilitado", async () => {
    getPolicy.mockResolvedValue(ok(isolada({ available_primary: 0 })))
    render(<ExecuteWorkflow />)

    const aviso = await screen.findByRole("status")
    expect(aviso.textContent).toMatch(/vai falhar sem despacho/)
    expect(getPolicy).toHaveBeenCalledWith("ws-a")
    const executar = screen.getByRole("button", { name: /Executar/ })
    expect((executar as HTMLButtonElement).disabled).toBe(false)
  })

  it("cala quando há para onde despachar", async () => {
    getPolicy.mockResolvedValue(ok(politica()))
    render(<ExecuteWorkflow />)
    await waitFor(() => expect(getPolicy).toHaveBeenCalled())
    expect(screen.queryByRole("status")).toBeNull()
  })

  it("leitura falhando não vira aviso: não se afirma nada sobre a política", async () => {
    getPolicy.mockResolvedValue({ status: 500, success: false, error: { message: "boom" } } as any)
    render(<ExecuteWorkflow />)
    await waitFor(() => expect(getPolicy).toHaveBeenCalled())
    expect(screen.queryByRole("status")).toBeNull()
  })
})
