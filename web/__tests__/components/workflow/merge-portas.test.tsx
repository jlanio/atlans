/**
 * Merge with declared input ports.
 *
 * Two parallel branches wired into a Merge both delivered `output`: the second
 * overwrote the first and "all" returned one branch, with nothing failing. The
 * Merge now declares input ports like the Python Script (`dynamic_inputs` +
 * `ports`): with two or more, each one is a connection point of its own and the
 * edge dropped on it carries its name as `to_key`. A Merge without ports keeps
 * its anonymous input, so saved workflows draw and run as before.
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

import PortsField from "@/app/components/workflow/nodes-configuration/fields/ports-field"
import { buildNodes } from "@/app/components/workflow/utils/build-canvas"
import { serializeEdge } from "@/app/components/workflow/utils/edge-persistence"
import { resolveToKey } from "@/app/components/workflow/utils/resolve-edge-keys"
import type { CanvasDefinition, INodesAPI, INodesPropertyAPI } from "@/service/types"

// What `GET /nodes` returns for the Merge (flow/nodes/control/merge.py).
const MERGE: INodesAPI = {
  name: "Merge", alias: "Mesclagem", description: "", type: "control",
  properties: [
    { name: "strategy", type: "select", default: "first", description: null },
    { name: "ports", type: "ports", default: [], description: null },
  ],
  dynamic_inputs: true,
  outputs: [{ name: "output", type: "any" }],
} as unknown as INodesAPI

const merge = (properties: Record<string, unknown>) => buildNodes(
  { nodes: [{ id: "m", name: "Merge", type: "control", properties, position: { x: 0, y: 0 } }] } as CanvasDefinition,
  [MERGE],
)[0]

describe("Merge no canvas", () => {
  it("sem portas, segue com a entrada anônima de sempre", () => {
    expect(merge({ strategy: "all" }).data.inputs).toEqual([])
  })

  it("com duas portas, cada uma é um ponto de conexão e vira o to_key da aresta", () => {
    const no = merge({ strategy: "all", ports: '["lotes","quadras"]' })
    expect(no.data.inputs?.map(p => p.name)).toEqual(["lotes", "quadras"])

    const toKey = resolveToKey("quadras", no.data.inputs)
    expect(toKey).toBe("quadras")
    const salva = serializeEdge({
      id: "e", source: "q", target: "m", sourceHandle: null, targetHandle: "quadras",
      data: { from_key: "output" },
    })
    expect(salva).toMatchObject({ from_key: "output", to_key: "quadras" })
  })
})

describe("campo de portas", () => {
  const campo = { name: "ports", label: "Portas de entrada", type: "ports", default: [] } as unknown as INodesPropertyAPI

  it("no Merge, não fala de variável nem de script", () => {
    render(<PortsField field={campo} values={{}} setNodeField={vi.fn()} />)
    expect(screen.getByText(/duas com o mesmo nome se sobrescrevem/)).toBeInTheDocument()
    expect(screen.queryByText(/variável/)).toBeNull()
  })

  it("no Merge, nome inválido não cita o script", () => {
    render(<PortsField field={campo} values={{ ports: '["lotes-1"]' }} setNodeField={vi.fn()} />)
    expect(screen.getByText("Só letras, números e _.")).toBeInTheDocument()
  })

  it("no Python Script, o nome segue sendo a variável do código", () => {
    render(<PortsField field={campo} values={{ ports: '["lotes-1"]' }} setNodeField={vi.fn()} nomeViraVariavel />)
    expect(screen.getByText(/o nome vira uma variável no script/)).toBeInTheDocument()
  })
})
