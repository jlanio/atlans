/**
 * ReactFlow needs to be told when a node's connection points change.
 *
 * It MEASURES the handles once and keeps positions and ids in an internal
 * registry. A handle added to an already-rendered node is drawn by React but
 * doesn't enter that registry — and the symptom doesn't look like a state bug:
 * the point appears on the screen and simply doesn't accept connections. That's
 * how the Python Script ports came out inert.
 *
 * What's tested: WHEN the re-measurement is requested. Requesting too little
 * leaves the point inert; requesting on every render (or every frame of a drag)
 * is expensive for nothing.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"

const updateNodeInternals = vi.fn()
vi.mock("@xyflow/react", () => ({
  useUpdateNodeInternals: () => updateNodeInternals,
}))

import { useHandleRegistrySync } from "@/app/hooks/workflow/useHandleRegistrySync"
import { INodeContext } from "@/context/useFlowContext"

const no = (
  id: string,
  inputs: string[] = [],
  outputs: string[] = [],
  position = { x: 0, y: 0 },
) => ({
  id,
  position,
  data: { inputs: inputs.map(name => ({ name })), outputs: outputs.map(name => ({ name })) },
}) as unknown as INodeContext

beforeEach(() => updateNodeInternals.mockClear())

describe("pede remedição quando os handles mudam", () => {
  it("ao ganhar portas", () => {
    const { rerender } = renderHook(({ nodes }) => useHandleRegistrySync(nodes), {
      initialProps: { nodes: [no("n1")] },
    })
    updateNodeInternals.mockClear()

    rerender({ nodes: [no("n1", ["a", "b"])] })
    expect(updateNodeInternals).toHaveBeenCalledWith(["n1"])
  })

  it("ao perder portas", () => {
    const { rerender } = renderHook(({ nodes }) => useHandleRegistrySync(nodes), {
      initialProps: { nodes: [no("n1", ["a", "b"])] },
    })
    updateNodeInternals.mockClear()

    rerender({ nodes: [no("n1", ["a"])] })
    expect(updateNodeInternals).toHaveBeenCalled()
  })

  it("ao renomear uma porta", () => {
    const { rerender } = renderHook(({ nodes }) => useHandleRegistrySync(nodes), {
      initialProps: { nodes: [no("n1", ["velho"])] },
    })
    updateNodeInternals.mockClear()

    rerender({ nodes: [no("n1", ["novo"])] })
    expect(updateNodeInternals).toHaveBeenCalled()
  })

  it("também para portas de SAÍDA", () => {
    // The sub-workflows' contract touches both lists, and had the same defect.
    const { rerender } = renderHook(({ nodes }) => useHandleRegistrySync(nodes), {
      initialProps: { nodes: [no("n1", [], ["a"])] },
    })
    updateNodeInternals.mockClear()

    rerender({ nodes: [no("n1", [], ["a", "b"])] })
    expect(updateNodeInternals).toHaveBeenCalled()
  })
})

describe("não pede remedição à toa", () => {
  it("arrastar o nó não dispara", () => {
    // `nodes` changes on every frame of a drag. Re-measuring all of them there
    // would be expensive and there'd be no new handle to find.
    const { rerender } = renderHook(({ nodes }) => useHandleRegistrySync(nodes), {
      initialProps: { nodes: [no("n1", ["a"], [], { x: 0, y: 0 })] },
    })
    updateNodeInternals.mockClear()

    rerender({ nodes: [no("n1", ["a"], [], { x: 120, y: 40 })] })
    rerender({ nodes: [no("n1", ["a"], [], { x: 240, y: 80 })] })
    expect(updateNodeInternals).not.toHaveBeenCalled()
  })

  it("re-render sem mudança nenhuma não dispara", () => {
    const nodes = [no("n1", ["a"])]
    const { rerender } = renderHook(({ nodes }) => useHandleRegistrySync(nodes), {
      initialProps: { nodes },
    })
    updateNodeInternals.mockClear()

    rerender({ nodes })
    expect(updateNodeInternals).not.toHaveBeenCalled()
  })

  it("canvas vazio não dispara", () => {
    renderHook(() => useHandleRegistrySync([]))
    expect(updateNodeInternals).not.toHaveBeenCalled()
  })
})
