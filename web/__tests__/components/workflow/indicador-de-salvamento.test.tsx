/**
 * O chip de salvamento é o único feedback permanente de "isto está salvo?".
 *
 * A versão anterior sumia 3s depois do save e não mostrava nada em repouso;
 * o erro caía em "Não salvo" e a mensagem ia embora com o toast. Estes testes
 * trancam os estados que o usuário sentia falta: o repouso com "Salvo há N
 * min", a falha com retry no lugar, e a detecção que marca — e desmarca —
 * "Alterações não salvas".
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup, act, fireEvent } from "@testing-library/react"

let nodes: unknown[] = []
let edges: unknown[] = []
vi.mock("@xyflow/react", () => ({
  useNodes: () => nodes,
  useEdges: () => edges,
  useStoreApi: () => ({ getState: () => ({ nodes, edges }) }),
}))

const salvar = vi.fn()
vi.mock("@/app/hooks/workflow/useSaveWorkflow", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/app/hooks/workflow/useSaveWorkflow")>()
  return { ...real, useSaveWorkflow: () => ({ saveWorkflow: salvar }) }
})

import GlobalSaveIndicator from "@/app/components/workflow/global-save-indicator"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { montarPayloadDoGrafo } from "@/app/hooks/workflow/useSaveWorkflow"
import type { INodeContext } from "@/context/useFlowContext"

const MIN = 60_000
const AGORA = new Date(2026, 8, 5, 14, 32, 0).getTime()

const no = (id: string, x = 0) => ({
  id,
  position: { x, y: 0 },
  data: { name: "Buffer", alias: id, type: "spatial", properties: { distancia: "10" } },
})

const store = () => useWorkflowSaveStore.getState()

/** Baseline "hidratado": snapshot igual ao canvas atual, janela de autocorreção
 *  já fechada (o que se testa aqui é o que vem DEPOIS da hidratação). */
function hidratar(savedAt: number | null = AGORA - 5 * MIN) {
  const { nodesReq, edgesReq } = montarPayloadDoGrafo(nodes as INodeContext[], [])
  store().initSnapshot(nodesReq, edgesReq, "wf", savedAt)
  useWorkflowSaveStore.setState({ snapshotIniciadoEm: null })
}

beforeEach(() => {
  cleanup()
  salvar.mockReset()
  vi.useFakeTimers()
  vi.setSystemTime(AGORA)
  nodes = [no("a")]
  edges = []
  useWorkflowSaveStore.setState({
    isSaving: false,
    saveStatus: "idle",
    lastSavedSnapshot: null,
    lastSavedAt: null,
    lastError: null,
    workflowName: "wf",
    snapshotIniciadoEm: null,
  })
})

afterEach(() => {
  vi.useRealTimers()
})

describe("chip de salvamento — repouso", () => {
  it("mostra quando foi o último save, e não anuncia o relógio", () => {
    hidratar(AGORA - 5 * MIN)
    render(<GlobalSaveIndicator />)

    const chip = screen.getByRole("status")
    expect(chip).toHaveTextContent("Salvo há 5 min")
    expect(chip).toHaveAttribute("aria-live", "off")
    expect(chip).toHaveAttribute("data-save-status", "idle")
  })

  it("sem save conhecido (workflow novo) não afirma nada", () => {
    hidratar(null)
    render(<GlobalSaveIndicator />)
    expect(screen.queryByRole("status")).toBeNull()
  })

  it("o rótulo envelhece sozinho", () => {
    hidratar(AGORA - 30_000)
    render(<GlobalSaveIndicator />)
    expect(screen.getByRole("status")).toHaveTextContent("Salvo agora")

    act(() => { vi.advanceTimersByTime(60_000) })
    expect(screen.getByRole("status")).toHaveTextContent("Salvo há 1 min")
  })
})

describe("chip de salvamento — detecção de alterações", () => {
  it("edição marca 'Alterações não salvas'; desfazer limpa", () => {
    hidratar()
    const { rerender } = render(<GlobalSaveIndicator />)
    act(() => { vi.advanceTimersByTime(300) })
    expect(store().saveStatus).toBe("idle")

    nodes = [no("a", 120)]
    rerender(<GlobalSaveIndicator />)
    act(() => { vi.advanceTimersByTime(300) })
    expect(store().saveStatus).toBe("unsaved")
    expect(screen.getByRole("status")).toHaveTextContent("Alterações não salvas")
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite")

    // Ctrl+Z de volta ao estado salvo: o aviso não tem mais razão de existir.
    nodes = [no("a", 0)]
    rerender(<GlobalSaveIndicator />)
    act(() => { vi.advanceTimersByTime(300) })
    expect(store().saveStatus).toBe("idle")
    expect(screen.getByRole("status")).toHaveTextContent("Salvo há 5 min")
  })

  it("uma edição logo depois de 'Salvo' vira 'não salvo' (o rótulo verde não a esconde)", () => {
    hidratar()
    const { rerender } = render(<GlobalSaveIndicator />)
    useWorkflowSaveStore.setState({ saveStatus: "saved" })

    nodes = [no("a", 120)]
    rerender(<GlobalSaveIndicator />)
    act(() => { vi.advanceTimersByTime(300) })
    expect(store().saveStatus).toBe("unsaved")
  })
})

describe("chip de salvamento — falha", () => {
  it("mostra a falha com a mensagem e um 'Tentar novamente' que salva de novo", () => {
    hidratar()
    useWorkflowSaveStore.setState({ saveStatus: "error", lastError: "Sem permissão" })
    render(<GlobalSaveIndicator />)

    const chip = screen.getByRole("status")
    expect(chip).toHaveTextContent("Falha ao salvar")
    expect(chip).toHaveAttribute("title", "Sem permissão")

    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }))
    expect(salvar).toHaveBeenCalledTimes(1)
  })

  it("a remedição do canvas não rebaixa a falha a 'não salvo'", () => {
    // Depois de uma falha o grafo segue diferente do snapshot; qualquer troca de
    // identidade de `nodes` (o ReactFlow medindo) disparava o detector, que
    // trocava "Falha ao salvar" por "Não salvo" — e o retry sumia junto.
    hidratar()
    nodes = [no("a", 120)]
    useWorkflowSaveStore.setState({ saveStatus: "error", lastError: "500" })
    const { rerender } = render(<GlobalSaveIndicator />)

    nodes = [no("a", 121)]
    rerender(<GlobalSaveIndicator />)
    act(() => { vi.advanceTimersByTime(300) })

    expect(store().saveStatus).toBe("error")
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeTruthy()
  })

  it("um save em voo também não é rebaixado", () => {
    hidratar()
    nodes = [no("a", 120)]
    useWorkflowSaveStore.setState({ saveStatus: "saving", isSaving: true })
    render(<GlobalSaveIndicator />)
    act(() => { vi.advanceTimersByTime(300) })
    expect(store().saveStatus).toBe("saving")
    expect(screen.getByRole("status")).toHaveTextContent("Salvando…")
  })
})
