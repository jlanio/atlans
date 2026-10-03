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
    vi.advanceTimersByTime(300) // the detector is debounced at 300ms

    expect(save().isDirty([no("a", 1)], [], "wf")).toBe(true)
    expect(save().autocorrigirSnapshot([no("a", 1)], [], "wf")).toBe(true)
    expect(save().isDirty([no("a", 1)], [], "wf")).toBe(false)
    expect(save().saveStatus).toBe("idle")
  })

  it("NÃO absorve a primeira edição do usuário feita depois da janela", () => {
    // Regression this test locks down: with detect-dirty debounced, the first
    // comparison only happens when the user stops dragging. A single-use flag
    // swallowed the whole edit — no "Não salvo" (unsaved), with Ctrl+S turning
    // into a no-op and Run firing the old definition.
    save().initSnapshot([no("a")], [], "wf")
    vi.advanceTimersByTime(5_000)

    expect(save().autocorrigirSnapshot([no("a", 120)], [], "wf")).toBe(false)
    expect(save().isDirty([no("a", 120)], [], "wf")).toBe(true)
  })

  it("a autocorreção vale uma vez só por hidratação", () => {
    save().initSnapshot([no("a")], [], "wf")
    expect(save().autocorrigirSnapshot([no("a", 1)], [], "wf")).toBe(true)
    // Second difference, still within the 1s: it is already a user edit.
    expect(save().autocorrigirSnapshot([no("a", 2)], [], "wf")).toBe(false)
  })

  it("um save fecha a janela — edição pós-save nunca é absorvida", () => {
    // The "Salvo" label disappears 3s later and the status goes back to 'idle';
    // without closing the window in completeSave, an edit made at that instant
    // would be swallowed.
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
    // At rest: the chip starts showing "Salvo há N min" (saved N min ago) from lastSavedAt.
    expect(save().saveStatus).toBe("idle")
    expect(save().lastSavedAt).toBe(Date.parse("2026-09-05T14:32:00Z"))
  })

  it("falha vira 'error' com a mensagem — não 'unsaved'", () => {
    // The graph is still different from the snapshot, but what the user needs to
    // see is that the attempt failed, with the retry in the same place.
    save().startSaving()
    save().failSave("Sem permissão para editar este workflow")

    expect(save().saveStatus).toBe("error")
    expect(save().isSaving).toBe(false)
    expect(save().lastError).toBe("Sem permissão para editar este workflow")
  })

  it("flashSaved pisca 'Salvo' sem PUT e sem mexer em lastSavedAt", () => {
    // Ctrl+S with nothing to save: confirms everything is stored, but the "salvo
    // às" (saved at) is still that of the real save.
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
