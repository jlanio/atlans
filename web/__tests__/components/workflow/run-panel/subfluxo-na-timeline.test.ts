/**
 * What happens inside a sub-workflow, seen from the parent workflow's panel.
 *
 * The child's nodes don't exist on the parent's canvas: the executor publishes
 * them with a prefixed id (`nóPai::nóFilho`) and marks `subworkflow_parent_node`
 * in `extra`. Nothing read that mark — the row showed up with the raw id, without
 * saying where it came from, and clicking it was a silent no-op (`focusNode`
 * doesn't find the id on the canvas).
 */
import { describe, it, expect } from "vitest"

import { buildTimeline } from "@/app/components/workflow/run-panel/timeline"
import { RunEvent, toRunEvent } from "@/app/stores/workflowExecutionStore"
import { INodeStatusWorkFlow } from "@/context/useFlowContext"

const T0 = 1_700_000_000_000

function doFilho(
  no: string,
  status: string,
  atMs: number,
  extra: Partial<RunEvent> = {},
): RunEvent {
  return {
    ts: T0 + atMs,
    node: `pai::${no}`,
    seq: 0,
    kind: "lifecycle",
    level: status === "failed" ? "error" : "info",
    status,
    node_name: `Nó ${no}`,
    node_type: "action",
    subworkflow_parent: "pai",
    raw: {},
    ...extra,
  }
}

const canvasPai = {
  id: "pai",
  status: "started",
  position: { x: 0, y: 0 },
  data: { alias: "Calcular área" },
} as unknown as INodeStatusWorkFlow

describe("toRunEvent", () => {
  it("lê subworkflow_parent_node do extra", () => {
    const ev = toRunEvent({
      node: "pai::c",
      status: "started",
      extra: { subworkflow_parent_node: "pai" },
    })
    expect(ev.subworkflow_parent).toBe("pai")
  })

  it("evento normal não vira sub-fluxo", () => {
    expect(toRunEvent({ node: "a", status: "started" }).subworkflow_parent).toBeNull()
  })
})

describe("buildTimeline com eventos de sub-fluxo", () => {
  it("amarra a linha ao nó SubWorkflow do canvas", () => {
    const t = buildTimeline([doFilho("c", "started", 100)], [canvasPai], T0)
    const linha = t.nodes.find(n => n.nodeId === "pai::c")!

    // Without this, focusing/highlighting/opening the configuration did nothing:
    // the child's id doesn't exist on the parent's canvas.
    expect(linha.canvasNodeId).toBe("pai")
    // The badge shows the node's ALIAS on the canvas, not the id — it's what the
    // person sees drawn on the screen.
    expect(linha.subFlow).toBe("Calcular área")
  })

  it("nó do próprio fluxo continua apontando para si mesmo", () => {
    const t = buildTimeline(
      [{ seq: 0, ts: T0, node: "pai", kind: "lifecycle", level: "info", status: "started", raw: {} }],
      [canvasPai],
      T0,
    )
    const linha = t.nodes.find(n => n.nodeId === "pai")!
    expect(linha.canvasNodeId).toBe("pai")
    expect(linha.subFlow).toBeNull()
  })

  it("cai no id do nó SubWorkflow quando ele não está no canvas", () => {
    // Happens when opening a historical run of a workflow that has changed since.
    const t = buildTimeline([doFilho("c", "started", 100)], [], T0)
    expect(t.nodes[0].subFlow).toBe("pai")
  })

  it("sem node_name, mostra o nome do nó filho e não o id prefixado", () => {
    const t = buildTimeline(
      [doFilho("c", "started", 100, { node_name: undefined })],
      [canvasPai],
      T0,
    )
    expect(t.nodes[0].name).toBe("c")
  })

  it("a falha dentro do filho vira um problema atribuído ao nó do canvas", () => {
    const t = buildTimeline(
      [
        doFilho("c", "started", 100),
        doFilho("c", "failed", 300, { message: "division by zero", duration_ms: 200 }),
      ],
      [canvasPai],
      T0,
    )
    expect(t.problems).toHaveLength(1)
    expect(t.problems[0].problem!.message).toBe("division by zero")
    expect(t.problems[0].canvasNodeId).toBe("pai")
    expect(t.problems[0].subFlow).toBe("Calcular área")
  })
})
