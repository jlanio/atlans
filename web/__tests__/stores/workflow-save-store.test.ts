import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import type { INodesDefinition } from "@/service/types"

const no = (id: string, x = 0): INodesDefinition =>
  ({ id, name: "Postgres", alias: id, type: "default", properties: {}, position: { x, y: 0 } } as INodesDefinition)

const save = () => useWorkflowSaveStore.getState()

describe("workflowSaveStore — janela de autocorreção do snapshot", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    useWorkflowSaveStore.setState({
      isSaving: false,
      saveStatus: "idle",
      lastSavedSnapshot: null,
      workflowName: "wf",
      snapshotIniciadoEm: null,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("absorve a remedição do ReactFlow logo depois da hidratação", () => {
    save().initSnapshot([no("a")], [], "wf")
    vi.advanceTimersByTime(300) // o detector é debounced em 300ms

    expect(save().isDirty([no("a", 1)], [], "wf")).toBe(true)
    expect(save().autocorrigirSnapshot([no("a", 1)], [], "wf")).toBe(true)
    expect(save().isDirty([no("a", 1)], [], "wf")).toBe(false)
    expect(save().saveStatus).toBe("idle")
  })

  it("NÃO absorve a primeira edição do usuário feita depois da janela", () => {
    // Regressão que este teste tranca: com o detect-dirty debounced, a primeira
    // comparação só acontece quando o usuário para de arrastar. Uma flag de uso
    // único engolia a edição inteira — sem "Não salvo", com Ctrl+S virando
    // no-op e o Executar disparando a definição antiga.
    save().initSnapshot([no("a")], [], "wf")
    vi.advanceTimersByTime(5_000)

    expect(save().autocorrigirSnapshot([no("a", 120)], [], "wf")).toBe(false)
    expect(save().isDirty([no("a", 120)], [], "wf")).toBe(true)
  })

  it("a autocorreção vale uma vez só por hidratação", () => {
    save().initSnapshot([no("a")], [], "wf")
    expect(save().autocorrigirSnapshot([no("a", 1)], [], "wf")).toBe(true)
    // Segunda diferença, ainda dentro do 1s: já é edição do usuário.
    expect(save().autocorrigirSnapshot([no("a", 2)], [], "wf")).toBe(false)
  })

  it("um save fecha a janela — edição pós-save nunca é absorvida", () => {
    // O rótulo "Salvo" some 3s depois e o status volta a 'idle'; sem fechar a
    // janela no completeSave, uma edição feita nesse instante seria engolida.
    save().initSnapshot([no("a")], [], "wf")
    save().completeSave(JSON.stringify({ name: "wf", nodes: [no("a")], edges: [] }))
    expect(save().snapshotIniciadoEm).toBeNull()

    useWorkflowSaveStore.setState({ saveStatus: "idle" })
    expect(save().autocorrigirSnapshot([no("a", 50)], [], "wf")).toBe(false)
  })

  it("não autocorrige enquanto um save está em curso", () => {
    save().initSnapshot([no("a")], [], "wf")
    save().startSaving()
    expect(save().autocorrigirSnapshot([no("a", 1)], [], "wf")).toBe(false)
  })
})

describe("workflowSaveStore — estados do feedback de salvamento", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date("2026-09-05T14:32:00Z"))
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

  it("save concluído carimba lastSavedAt, limpa o erro e volta ao repouso em 3s", () => {
    useWorkflowSaveStore.setState({ saveStatus: "error", lastError: "500" })
    save().completeSave("{}")

    expect(save().saveStatus).toBe("saved")
    expect(save().lastSavedAt).toBe(Date.parse("2026-09-05T14:32:00Z"))
    expect(save().lastError).toBeNull()

    vi.advanceTimersByTime(3_000)
    // Repouso: o chip passa a mostrar "Salvo há N min" a partir de lastSavedAt.
    expect(save().saveStatus).toBe("idle")
    expect(save().lastSavedAt).toBe(Date.parse("2026-09-05T14:32:00Z"))
  })

  it("falha vira 'error' com a mensagem — não 'unsaved'", () => {
    // O grafo continua diferente do snapshot, mas o que o usuário precisa ver é
    // que a tentativa falhou, com o retry no mesmo lugar.
    save().startSaving()
    save().failSave("Sem permissão para editar este workflow")

    expect(save().saveStatus).toBe("error")
    expect(save().isSaving).toBe(false)
    expect(save().lastError).toBe("Sem permissão para editar este workflow")
  })

  it("flashSaved pisca 'Salvo' sem PUT e sem mexer em lastSavedAt", () => {
    // Ctrl+S sem nada a salvar: confirma que está tudo gravado, mas o "salvo
    // às" continua sendo o do save de verdade.
    useWorkflowSaveStore.setState({ lastSavedAt: 1_000 })
    save().flashSaved()

    expect(save().saveStatus).toBe("saved")
    expect(save().lastSavedAt).toBe(1_000)

    vi.advanceTimersByTime(3_000)
    expect(save().saveStatus).toBe("idle")
  })

  it("uma edição dentro dos 3s do rótulo não é apagada pelo timer", () => {
    save().completeSave("{}")
    useWorkflowSaveStore.setState({ saveStatus: "unsaved" })
    vi.advanceTimersByTime(3_000)
    expect(save().saveStatus).toBe("unsaved")
  })

  it("initSnapshot na hidratação traz o updated_at do servidor; sem ele, preserva o atual", () => {
    save().initSnapshot([], [], "wf", 123_456)
    expect(save().lastSavedAt).toBe(123_456)

    save().initSnapshot([], [], "wf")
    expect(save().lastSavedAt).toBe(123_456)
  })
})

describe("workflowSaveStore — viewport salvo", () => {
  beforeEach(() => {
    useWorkflowSaveStore.setState({ lastSavedViewport: null })
  })

  it("completeSave guarda o viewport gravado; sem ele, preserva o anterior", () => {
    save().completeSave("{}", { x: -10, y: 20, zoom: 1.5 })
    expect(save().lastSavedViewport).toEqual({ x: -10, y: 20, zoom: 1.5 })

    save().completeSave("{}")
    expect(save().lastSavedViewport).toEqual({ x: -10, y: 20, zoom: 1.5 })
  })

  it("initSnapshot traz o viewport que veio na definition", () => {
    save().initSnapshot([], [], "wf", null, { x: 1, y: 2, zoom: 0.8 })
    expect(save().lastSavedViewport).toEqual({ x: 1, y: 2, zoom: 0.8 })

    save().initSnapshot([], [], "wf")
    expect(save().lastSavedViewport).toEqual({ x: 1, y: 2, zoom: 0.8 })
  })
})
