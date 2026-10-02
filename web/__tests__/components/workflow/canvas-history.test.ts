/**
 * Baseline do histórico de undo/redo no load (F10).
 *
 * Sem um snapshot de baseline após a hidratação, o histórico começa vazio
 * (pointer=-1) e o primeiro saveSnapshot é o estado PÓS-edição; como undo()
 * guarda `pointer <= 0`, a PRIMEIRA edição de aresta ficava presa e nunca era
 * desfeita. captureBaseline() grava o estado carregado como pointer=0.
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

    _edges = [{ id: "e1" }]                    // primeira edição muda o canvas
    act(() => result.current.saveSnapshot())    // salva o estado PÓS-edição

    expect(result.current.canUndo).toBe(false)  // pointer=0 → undo é no-op
  })

  it("COM baseline: a primeira edição é desfazível e volta ao estado carregado", () => {
    _nodes = [{ id: "a" }]
    _edges = []
    const { result } = renderHook(() => useCanvasHistory())

    act(() => result.current.captureBaseline())  // baseline = estado carregado
    expect(result.current.canUndo).toBe(false)   // baseline sozinho não desfaz

    _edges = [{ id: "e1" }]                       // primeira edição
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
