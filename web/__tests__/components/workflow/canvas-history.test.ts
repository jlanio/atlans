/**
 * Baseline of the undo/redo history on load (F10).
 *
 * Without a baseline snapshot after hydration, the history starts empty
 * (pointer=-1) and the first saveSnapshot is the POST-edit state; since undo()
 * guards `pointer <= 0`, the FIRST edge edit got stuck and was never undone.
 * captureBaseline() records the loaded state as pointer=0.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, act } from "@testing-library/react"

let _nodes: unknown[] = []
let _edges: unknown[] = []
vi.mock("@xyflow/react", () => ({
  useReactFlow: () => ({
    getNodes: () => _nodes,
    getEdges: () => _edges,
    setNodes: (n: unknown[]) => { _nodes = n },
    setEdges: (e: unknown[]) => { _edges = e },
  }),
}))

import { useCanvasHistory } from "@/app/hooks/workflow/useCanvasHistory"

beforeEach(() => { _nodes = []; _edges = [] })

describe("useCanvasHistory — baseline (F10)", () => {
  it("SEM baseline: a primeira edição não é desfazível (o bug)", () => {
    _nodes = [{ id: "a" }]
    const { result } = renderHook(() => useCanvasHistory())

    _edges = [{ id: "e1" }]                    // first edit changes the canvas
    act(() => result.current.saveSnapshot())    // saves the POST-edit state

    expect(result.current.canUndo).toBe(false)  // pointer=0 → undo is a no-op
  })

  it("COM baseline: a primeira edição é desfazível e volta ao estado carregado", () => {
    _nodes = [{ id: "a" }]
    _edges = []
    const { result } = renderHook(() => useCanvasHistory())

    act(() => result.current.captureBaseline())  // baseline = estado carregado
    expect(result.current.canUndo).toBe(false)   // baseline alone doesn't undo

    _edges = [{ id: "e1" }]                       // first edit
    act(() => result.current.saveSnapshot())
    expect(result.current.canUndo).toBe(true)

    act(() => result.current.undo())
    expect(_edges).toEqual([])                    // restaurou o canvas carregado
  })

  it("captureBaseline reinicia o histórico (não vaza entre workflows)", () => {
    _nodes = [{ id: "a" }]
    const { result } = renderHook(() => useCanvasHistory())
    _edges = [{ id: "e1" }]
    act(() => result.current.saveSnapshot())
    _edges = [{ id: "e2" }]
    act(() => result.current.saveSnapshot())
    expect(result.current.canUndo).toBe(true)

    // Novo workflow carregado → baseline reinicia: nada a desfazer antes dele.
    _nodes = [{ id: "b" }]
    _edges = [{ id: "novo" }]
    act(() => result.current.captureBaseline())
    expect(result.current.canUndo).toBe(false)
    expect(result.current.canRedo).toBe(false)
  })
})
