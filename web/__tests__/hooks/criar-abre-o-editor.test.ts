/**
 * Saving a new workflow opens it in the editor.
 *
 * POST /workflows answers `{ id, name }`, not the workflow. The hook read
 * `id_hash` from that answer, found nothing and stayed on /workflow/create:
 * no Executar (the editor buttons only show with an id in the route), and the
 * next save went down the create path again and hit the name already taken
 * (409). The other suites mocked the answer with `id_hash`, so none failed.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, act } from "@testing-library/react"

let nodes: unknown[] = []
vi.mock("@xyflow/react", () => ({
  useReactFlow: () => ({ getViewport: () => ({ x: 0, y: 0, zoom: 1 }) }),
  useStoreApi: () => ({ getState: () => ({ nodes, edges: [] }) }),
}))

// `vi.hoisted`: the `vi.mock` factories run before the module's `const`s.
const { replace, createWorkflow } = vi.hoisted(() => ({ replace: vi.fn(), createWorkflow: vi.fn() }))
vi.mock("next/navigation", () => ({
  // /workflow/create: no id in the route.
  useParams: () => ({}),
  useRouter: () => ({ replace, push: vi.fn() }),
}))
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: { id_hash: "ws-1" } }),
}))
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { createWorkflow, updateWorkflowById: vi.fn() },
}))
vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn(), warning: vi.fn() },
}))

import { useSaveWorkflow } from "@/app/hooks/workflow/useSaveWorkflow"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"

const no = (id: string) => ({
  id,
  position: { x: 0, y: 0 },
  data: { name: "Buffer", alias: id, type: "spatial", properties: {} },
})

async function salvar() {
  const { result } = renderHook(() => useSaveWorkflow())
  await act(async () => { await result.current.saveWorkflow() })
}

beforeEach(() => {
  replace.mockClear()
  createWorkflow.mockReset()
  nodes = [no("a")]
  useWorkflowSaveStore.setState({
    isSaving: false,
    saveStatus: "idle",
    workflowName: "Novo fluxo",
    lastError: null,
  })
})

describe("salvar um workflow novo", () => {
  it("abre no editor o workflow criado, pelo id da resposta", async () => {
    // The answer POST /workflows really gives (app/api/routers/workflows_router.py).
    createWorkflow.mockResolvedValue({ data: { id: "wf-novo", name: "Novo fluxo" }, error: null })

    await salvar()

    expect(createWorkflow).toHaveBeenCalledTimes(1)
    expect(replace).toHaveBeenCalledWith("/workflow/wf-novo")
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("saved")
  })

  it("se a criação é recusada, fica na tela de criação e diz que falhou", async () => {
    createWorkflow.mockResolvedValue({
      data: null,
      error: { message: "Já existe um workflow chamado 'Novo fluxo' neste workspace." },
    })

    await salvar()

    expect(replace).not.toHaveBeenCalled()
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("error")
  })
})
