/**
 * "When I save, I want to reopen at the same zoom and position."
 *
 * Pan/zoom isn't an edit — it doesn't mark "não salvo" (unsaved) — but it's
 * part of what gets saved. An explicit save (button, Ctrl+S) writes the viewport
 * even with the graph untouched; the silent save from Run doesn't PUT because of it.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, act } from "@testing-library/react"
import type { Viewport } from "@xyflow/react"

let viewport: Viewport = { x: 0, y: 0, zoom: 1 }
let nodes: unknown[] = []
let edges: unknown[] = []
vi.mock("@xyflow/react", () => ({
  useReactFlow: () => ({ getViewport: () => viewport }),
  useStoreApi: () => ({ getState: () => ({ nodes, edges }) }),
}))

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "wf-1" }),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}))
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: { id_hash: "ws-1" } }),
}))

// `vi.hoisted`: the `vi.mock` factory is hoisted to the top of the file and runs
// before any `const` here — referencing `put` directly gave
// "Cannot access 'put' before initialization" depending on the import order.
const { put } = vi.hoisted(() => ({
  put: vi.fn<(id: string, body: unknown) => Promise<{ success: boolean; data: { id_hash: string }; error: null }>>(
    async () => ({ success: true, data: { id_hash: "wf-1" }, error: null }),
  ),
}))
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { updateWorkflowById: put, createWorkflow: vi.fn() },
}))
vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn(), warning: vi.fn() },
}))

import { useSaveWorkflow, buildGraphPayload } from "@/app/hooks/workflow/useSaveWorkflow"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { createToast } from "@/utils/createToast"
import type { INodeContext } from "@/context/useFlowContext"

const no = (id: string, x = 0) => ({
  id,
  position: { x, y: 0 },
  data: { name: "Buffer", alias: id, type: "spatial", properties: {} },
})

const store = () => useWorkflowSaveStore.getState()
const lastPutPayload = () =>
  put.mock.calls[0][1] as { definition: { viewport: Viewport } }

beforeEach(() => {
  put.mockClear()
  vi.mocked(createToast.warning).mockClear()
  nodes = [no("a")]
  edges = []
  viewport = { x: 0, y: 0, zoom: 1 }
  useWorkflowSaveStore.setState({
    isSaving: false,
    saveStatus: "idle",
    workflowName: "wf",
    lastSavedAt: null,
    lastError: null,
  })
  // Hydrated: graph equal to the saved one, known saved viewport, self-correction
  // window closed.
  const { nodesReq, edgesReq } = buildGraphPayload(nodes as INodeContext[], [])
  store().initSnapshot(nodesReq, edgesReq, "wf", 1_000, { x: 0, y: 0, zoom: 1 })
  useWorkflowSaveStore.setState({ snapshotIniciadoEm: null })
})

describe("save explícito com o grafo intacto", () => {
  it("grava o viewport quando ele mudou", async () => {
    viewport = { x: -240, y: 80, zoom: 1.5 }
    const { result } = renderHook(() => useSaveWorkflow())

    await act(async () => { await result.current.saveWorkflow() })

    expect(put).toHaveBeenCalledTimes(1)
    expect(lastPutPayload().definition.viewport).toEqual({ x: -240, y: 80, zoom: 1.5 })
    expect(store().lastSavedViewport).toEqual({ x: -240, y: 80, zoom: 1.5 })
    expect(store().saveStatus).toBe("saved")
  })

  it("sem mudança nenhuma não faz PUT — só confirma 'Salvo'", async () => {
    const { result } = renderHook(() => useSaveWorkflow())
    await act(async () => { await result.current.saveWorkflow() })

    expect(put).not.toHaveBeenCalled()
    expect(store().saveStatus).toBe("saved")
  })

  it("ruído de ponto flutuante do zoom não vira PUT", async () => {
    viewport = { x: 0.2, y: -0.3, zoom: 1.0004 }
    const { result } = renderHook(() => useSaveWorkflow())
    await act(async () => { await result.current.saveWorkflow() })
    expect(put).not.toHaveBeenCalled()
  })
})

describe("save silencioso (antes de executar)", () => {
  it("não persegue o viewport nem pisca 'Salvo'", async () => {
    viewport = { x: -240, y: 80, zoom: 1.5 }
    const { result } = renderHook(() => useSaveWorkflow())
    await act(async () => { await result.current.saveWorkflow({ silent: true }) })

    expect(put).not.toHaveBeenCalled()
    expect(store().saveStatus).toBe("idle")
  })
})

describe("save com o grafo alterado", () => {
  it("o viewport do momento vai junto, como sempre foi", async () => {
    nodes = [no("a", 300)]
    viewport = { x: 10, y: 10, zoom: 0.75 }
    const { result } = renderHook(() => useSaveWorkflow())
    await act(async () => { await result.current.saveWorkflow() })

    expect(put).toHaveBeenCalledTimes(1)
    expect(lastPutPayload().definition.viewport).toEqual({ x: 10, y: 10, zoom: 0.75 })
    expect(store().lastSavedViewport).toEqual({ x: 10, y: 10, zoom: 0.75 })
  })
})

describe("avisos de agendamento (schedule_notices)", () => {
  it("mostra um toast âmbar quando o backend diz que o agendamento não foi aplicado", async () => {
    nodes = [no("a", 300)] // graph changed → there will be a PUT
    put.mockResolvedValueOnce({
      success: true,
      data: {
        id_hash: "wf-1",
        schedule_notices: [
          { code: "workflow_inactive", severity: "warning", message: "O workflow está inativo..." },
        ],
      },
      error: null,
    } as never)
    const { result } = renderHook(() => useSaveWorkflow())

    await act(async () => { await result.current.saveWorkflow() })

    expect(put).toHaveBeenCalledTimes(1)
    // It saved (the chip says "Salvo") but the toast warns about the caveat.
    expect(store().saveStatus).toBe("saved")
    expect(createToast.warning).toHaveBeenCalledWith("Agendamento não aplicado", "O workflow está inativo...")
  })

  it("save normal (sem avisos) não dispara toast de aviso", async () => {
    nodes = [no("a", 300)]
    const { result } = renderHook(() => useSaveWorkflow())
    await act(async () => { await result.current.saveWorkflow() })

    expect(put).toHaveBeenCalledTimes(1)
    expect(createToast.warning).not.toHaveBeenCalled()
  })
})
