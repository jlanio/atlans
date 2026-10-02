/**
 * O que acontece dentro de um sub-fluxo, visto do painel do fluxo pai.
 *
 * Os nós do filho não existem no canvas do pai: o executor os publica com o id
 * prefixado (`nóPai::nóFilho`) e marca `subworkflow_parent_node` no `extra`.
 * Nada lia essa marca — a linha aparecia com o id cru, sem dizer de onde veio, e
 * clicar nela era um no-op silencioso (`focusNode` não acha o id no canvas).
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

    // Sem isto, focar/destacar/abrir configuração não fazia nada: o id do
    // filho não existe no canvas do pai.
    expect(linha.canvasNodeId).toBe("pai")
    // O selo mostra o ALIAS do nó no canvas, não o id — é o que a pessoa vê
    // desenhado na tela.
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
    // Acontece ao abrir um run histórico de um fluxo que mudou desde então.
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
