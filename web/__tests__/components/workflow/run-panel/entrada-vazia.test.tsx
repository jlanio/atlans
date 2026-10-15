/**
 * An edge whose `from_key` the source no longer produces delivers nothing: the
 * node runs without that input and fails far from the cause ("Nenhum
 * GeoDataFrame encontrado") or finishes green with wrong data. The executor
 * now sends those edges with the node's completion event (`unresolved_edges`);
 * the panel has to show them where the person looks — the node's row and,
 * when it failed, its problem card.
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/app/components/workflow/run-panel/shared", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/components/workflow/run-panel/shared")>()),
  // Canvas focus and sub-workflow drill-down need the editor around them.
  useNodeFocus: () => ({ focusNode: () => {}, setHovered: () => {} }),
  useOpenSubworkflow: () => ({ abrir: () => {}, podeAbrir: () => false }),
}))
vi.mock("@/app/hooks/workflow/useConfigNodeParams", () => ({
  useConfigNodeParams: () => ({ setConfigNodeParam: () => {} }),
}))

import { buildTimeline } from "@/app/components/workflow/run-panel/timeline"
import ProblemsTab from "@/app/components/workflow/run-panel/problems-tab"
import { RunEvent, toRunEvent } from "@/app/stores/workflowExecutionStore"
import { INodeStatusWorkFlow } from "@/context/useFlowContext"

const canvas = [
  { id: "fonte", status: "completed", position: { x: 0, y: 0 }, data: { alias: "Script de origem" } },
  { id: "destino", status: "failed", position: { x: 0, y: 0 }, data: { alias: "Salvar GeoJSON" } },
] as unknown as INodeStatusWorkFlow[]

const SEM_DADO = [{ source: "fonte", from_key: "resultado", keys: ["areas", "total"] }]

function falhou(extra: Record<string, unknown>): RunEvent {
  return toRunEvent({
    node: "destino", status: "failed", kind: "lifecycle", level: "error", timestamp: 1_700_000_001,
    error: "Nenhum GeoDataFrame encontrado", extra,
  })
}

describe("conexão que não entregou dado", () => {
  it("o evento traz as arestas e a linha do nó ganha o nome da origem", () => {
    const ev = falhou({ unresolved_edges: SEM_DADO })
    expect(ev.unresolved_edges).toEqual(SEM_DADO)

    const linha = buildTimeline([ev], canvas).nodes.find(n => n.nodeId === "destino")!
    expect(linha.unresolvedEdges).toEqual([{ ...SEM_DADO[0], sourceName: "Script de origem" }])
  })

  it("dentro de um subfluxo, a origem é achada pelo id prefixado", () => {
    const filho = toRunEvent({
      node: "pai::destino", status: "completed", kind: "lifecycle", level: "warn", timestamp: 1_700_000_001,
      extra: { subworkflow_parent_node: "pai", unresolved_edges: [{ source: "fonte", from_key: "x", keys: [] }] },
    })
    const inicio = toRunEvent({
      node: "pai::fonte", status: "completed", timestamp: 1_700_000_000,
      extra: { subworkflow_parent_node: "pai", node_name: "Origem no filho" },
    })
    const linha = buildTimeline([inicio, filho], []).nodes.find(n => n.nodeId === "pai::destino")!
    expect(linha.unresolvedEdges?.[0].sourceName).toBe("Origem no filho")
  })

  it("sem o campo, nada muda", () => {
    const linha = buildTimeline([falhou({})], canvas).nodes.find(n => n.nodeId === "destino")!
    expect(linha.unresolvedEdges).toBeNull()
  })

  it("o cartão do problema aponta a entrada que faltou", () => {
    render(<ProblemsTab timeline={buildTimeline([falhou({ unresolved_edges: SEM_DADO })], canvas)} />)
    expect(screen.getByText("O nó rodou sem uma das entradas")).toBeInTheDocument()
    expect(screen.getByText(/"Script de origem" não produziu "resultado" \(produziu: areas, total\)/)).toBeInTheDocument()
  })
})
