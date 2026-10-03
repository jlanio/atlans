/**
 * What the viewer paints at a sub-workflow level.
 *
 * The source is the panel's timeline — not `statusWorkflow.nodes`, which only
 * knows the editor canvas's nodes because it's seeded from them and afterwards
 * only updated by id (useExecuteWorkflow). The child's node ids arrive prefixed
 * and never match any of them.
 */
import { describe, it, expect } from "vitest"

import { recortarNivel } from "@/app/components/workflow/subflow-viewer/estado-do-nivel"
import { NodeRun } from "@/app/components/workflow/run-panel/timeline"

function linha(nodeId: string, over: Partial<NodeRun> = {}): NodeRun {
  return {
    nodeId,
    canvasNodeId: "sA",
    subFlow: "Sub-fluxo",
    name: `Nó ${nodeId}`,
    type: "action",
    status: "completed",
    startOffsetMs: 0,
    startedAt: null,
    durationMs: 120,
    outputKeys: [],
    cacheHit: false,
    schemaDrift: null,
    debug: null,
    prints: [],
    problem: null,
    order: 0,
    ...over,
  }
}

describe("recortarNivel", () => {
  it("indexa pelo id local, que é o que existe no grafo do filho", () => {
    const { estadoPorId } = recortarNivel(
      [linha("sA::X")],
      ["sA"],
      new Set(["X"]),
    )
    expect(estadoPorId.get("X")?.status).toBe("completed")
  })

  it("traduz 'aguardando' para o estado sem anel do canvas", () => {
    const { estadoPorId } = recortarNivel(
      [linha("sA::X", { status: "pending" })],
      ["sA"],
      new Set(["X"]),
    )
    expect(estadoPorId.get("X")?.status).toBe("idle")
  })

  it("'executando' vira o estado que o canvas anima", () => {
    const { estadoPorId } = recortarNivel(
      [linha("sA::X", { status: "running" })],
      ["sA"],
      new Set(["X"]),
    )
    expect(estadoPorId.get("X")?.status).toBe("started")
  })

  it("carrega a mensagem da falha para o tooltip do nó", () => {
    const { estadoPorId } = recortarNivel(
      [linha("sA::X", {
        status: "failed",
        problem: { message: "division by zero" },
      })],
      ["sA"],
      new Set(["X"]),
    )
    expect(estadoPorId.get("X")).toMatchObject({
      status: "failed",
      error: "division by zero",
    })
  })

  it("ignora os nós do fluxo pai e os de níveis mais profundos", () => {
    const { estadoPorId } = recortarNivel(
      [linha("X"), linha("sA::sB::X"), linha("sA::Y")],
      ["sA"],
      new Set(["X", "Y"]),
    )
    // "X" exists in the open graph, but the two rows with that local id are from
    // OTHER levels: painting them here would assign another node's state to this one.
    expect(estadoPorId.has("X")).toBe(false)
    expect(estadoPorId.has("Y")).toBe(true)
  })

  it("conta quem executou e não está mais no grafo", () => {
    // The graph comes in the sub-workflow's CURRENT version; in a historical run
    // the node may have been deleted since. Silencing that would make the screen pass as complete.
    const { estadoPorId, semCorrespondencia } = recortarNivel(
      [linha("sA::X"), linha("sA::sumiu", { name: "Buffer" })],
      ["sA"],
      new Set(["X"]),
    )
    expect(estadoPorId.size).toBe(1)
    expect(semCorrespondencia).toEqual(["Buffer"])
  })
})
