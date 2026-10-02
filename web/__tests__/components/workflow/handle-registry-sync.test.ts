/**
 * O ReactFlow precisa ser avisado quando os pontos de conexão de um nó mudam.
 *
 * Ele MEDE os handles uma vez e guarda posições e ids num registro interno.
 * Handle acrescentado a um nó já renderizado é desenhado pelo React mas não
 * entra nesse registro — e o sintoma não parece bug de estado: o ponto aparece
 * na tela e simplesmente não aceita conexão. Foi assim que as portas do Script
 * Python surgiram inertes.
 *
 * O que se testa: QUANDO a remedição é pedida. Pedir de menos deixa o ponto
 * inerte; pedir a cada render (ou a cada quadro de um arrasto) custa caro à toa.
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
    // O contrato dos sub-fluxos mexe nas duas listas, e tinha o mesmo defeito.
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
    // `nodes` muda a cada quadro de um arrasto. Remedir todos ali custaria caro
    // e não haveria handle novo para encontrar.
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
