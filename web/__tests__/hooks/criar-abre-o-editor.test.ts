/**
 * Saving a new workflow opens it in the editor.
 *
 * POST /workflows answers `{ id, name }`, not the workflow. The hook read
 * `id_hash` from that answer, found nothing and stayed on /workflow/create:
 * no Executar (the editor buttons only show with an id in the route), and the
 * next save went down the create path again and hit the name already taken
 * (409). The other suites mocked the answer with `id_hash`, so none failed.
 *
 * Once the redirect really happens it has edges of its own: a save while the
 * route is still "create", a person who already left the screen, another
 * editor opened during the request, an answer with no id.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, act } from "@testing-library/react"

let nodes: unknown[] = []
vi.mock("@xyflow/react", () => ({
  useReactFlow: () => ({ getViewport: () => ({ x: 0, y: 0, zoom: 1 }) }),
  useStoreApi: () => ({ getState: () => ({ nodes, edges: [] }) }),
}))

// `vi.hoisted`: the `vi.mock` factories run before the module's `const`s.
const { replace, createWorkflow, levarConversaDoAssistente, toast } = vi.hoisted(() => ({
  replace: vi.fn(),
  createWorkflow: vi.fn(),
  levarConversaDoAssistente: vi.fn(async () => ({ data: { levada: true }, error: null })),
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn(), warning: vi.fn() },
}))
vi.mock("next/navigation", () => ({
  // /workflow/create: no id in the route.
  useParams: () => ({}),
  useRouter: () => ({ replace, push: vi.fn() }),
}))
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: { id_hash: "ws-1" } }),
}))
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { createWorkflow, updateWorkflowById: vi.fn(), levarConversaDoAssistente },
}))
vi.mock("@/utils/createToast", () => ({ createToast: toast }))

import { useSaveWorkflow } from "@/app/hooks/workflow/useSaveWorkflow"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import {
  receberConversa,
  registrarConversaDaCriacao,
} from "@/app/components/workflow/assistente/conversa-da-criacao"

const no = (id: string) => ({
  id,
  position: { x: 0, y: 0 },
  data: { name: "Buffer", alias: id, type: "spatial", properties: {} },
})

// The answer POST /workflows really gives (app/api/routers/workflows_router.py).
const CRIADO = { data: { id: "wf-novo", name: "Novo fluxo" }, error: null }

function montar() {
  const { result } = renderHook(() => useSaveWorkflow())
  return async () => { await act(async () => { await result.current.saveWorkflow() }) }
}

beforeEach(() => {
  vi.clearAllMocks()
  window.history.replaceState({}, "", "/workflow/create")
  // The create screen's assistant drawer has a conversation to hand over.
  receberConversa("wf-novo")
  registrarConversaDaCriacao([{ id: "t1", papel: "user", texto: "monte um buffer", blocos: [] }], false)
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
    createWorkflow.mockResolvedValue(CRIADO)

    await montar()()

    expect(createWorkflow).toHaveBeenCalledTimes(1)
    expect(replace).toHaveBeenCalledWith("/workflow/wf-novo")
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("saved")
  })

  it("leva junto a conversa do assistente que montou o workflow", async () => {
    createWorkflow.mockResolvedValue(CRIADO)

    await montar()()

    expect(levarConversaDoAssistente).toHaveBeenCalledWith("wf-novo")
    expect(receberConversa("wf-novo")).toHaveLength(1)
  })

  it("um save antes de o editor reabrir não tenta criar de novo", async () => {
    createWorkflow.mockResolvedValue(CRIADO)
    const salvar = montar()

    await salvar()
    // The route still says /workflow/create until /workflow/wf-novo mounts.
    await salvar()

    expect(createWorkflow).toHaveBeenCalledTimes(1)
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("se a criação é recusada, fica na tela de criação e diz que falhou", async () => {
    createWorkflow.mockResolvedValue({
      data: null,
      error: { message: "Já existe um workflow chamado 'Novo fluxo' neste workspace." },
    })

    await montar()()

    expect(replace).not.toHaveBeenCalled()
    expect(useWorkflowSaveStore.getState().saveStatus).toBe("error")
    expect(levarConversaDoAssistente).not.toHaveBeenCalled()
  })

  it("uma resposta sem id não vira um 'Salvo' mudo: avisa onde está o workflow", async () => {
    createWorkflow.mockResolvedValue({ data: { name: "Novo fluxo" }, error: null })

    await montar()()

    expect(replace).not.toHaveBeenCalled()
    expect(toast.warning).toHaveBeenCalledWith("Workflow criado", expect.stringContaining("Projetos"))
  })

  it("quem saiu da tela durante o pedido não é puxado de volta ao editor", async () => {
    createWorkflow.mockImplementation(async () => {
      window.history.pushState({}, "", "/projects")
      return CRIADO
    })

    await montar()()

    expect(createWorkflow).toHaveBeenCalledTimes(1)
    expect(replace).not.toHaveBeenCalled()
    expect(levarConversaDoAssistente).not.toHaveBeenCalled()
  })

  it("o que o agendamento não aplicou vira aviso, como numa edição", async () => {
    // Before, the create answer had no notices: a ScheduleTrigger the scheduler
    // refused (a cron with 6 fields, drawn by the assistant) was born unscheduled
    // with only "Salvo" on screen.
    const aviso = "Configuração de agendamento inválida: cron_expression deve ter 5 campos. O workflow foi salvo sem agendamento."
    createWorkflow.mockResolvedValue({
      data: { ...CRIADO.data, schedule_notices: [{ code: "invalid_schedule", severity: "warning", message: aviso }] },
      error: null,
    })

    await montar()()

    expect(toast.warning).toHaveBeenCalledWith("Agendamento não aplicado", aviso)
    expect(replace).toHaveBeenCalledWith("/workflow/wf-novo")
  })

  it("o aviso de agendamento chega mesmo a quem já saiu da tela", async () => {
    // It is about the workflow just created, not about the screen on view.
    createWorkflow.mockImplementation(async () => {
      window.history.pushState({}, "", "/projects")
      return {
        data: { ...CRIADO.data, schedule_notices: [{ code: "invalid_schedule", severity: "warning", message: "inválido" }] },
        error: null,
      }
    })

    await montar()()

    expect(toast.warning).toHaveBeenCalledWith("Agendamento não aplicado", "inválido")
    expect(replace).not.toHaveBeenCalled()
  })

  it("se outro workflow abriu durante o pedido, não mexe no editor dele", async () => {
    createWorkflow.mockImplementation(async () => {
      useWorkflowSaveStore.setState(s => ({ geracao: s.geracao + 1 }))
      return CRIADO
    })

    await montar()()

    expect(replace).not.toHaveBeenCalled()
    expect(useWorkflowSaveStore.getState().saveStatus).not.toBe("saved")
    // That editor's drawer has a conversation of its own.
    expect(levarConversaDoAssistente).not.toHaveBeenCalled()
  })
})
