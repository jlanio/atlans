import { describe, it, expect } from "vitest"
import { buildTimeline, timelineToText, WF_COMPLETE } from "@/app/components/workflow/run-panel/timeline"
import { RunEvent, toRunEvent } from "@/app/stores/workflowExecutionStore"
import { INodeStatusWorkFlow } from "@/context/useFlowContext"

const T0 = 1_700_000_000_000

function lifecycle(node: string, status: string, atMs: number, extra: Partial<RunEvent> = {}): RunEvent {
  return {
    ts: T0 + atMs,
    node,
    seq: 0,
    kind: "lifecycle",
    level: status === "failed" ? "error" : "info",
    status,
    node_name: `Nó ${node}`,
    node_type: "action",
    raw: {},
    ...extra,
  }
}

/** A stdout event as the executor emits it today: the text lives ONLY in `lines`.
 *  `message` stopped repeating the same content — the duplication blew the
 *  event's 64 KB ceiling and the whole batch arrived with no output at all. */
function stdout(node: string, atMs: number, ...lines: string[]): RunEvent {
  return { seq: 0, ts: T0 + atMs, node, kind: "stdout", level: "info", status: "log", lines, raw: {} }
}

function canvasNode(id: string, status: INodeStatusWorkFlow["status"], extra: Partial<INodeStatusWorkFlow> = {}) {
  return { id, status, position: { x: 0, y: 0 }, data: { alias: `Nó ${id}` }, ...extra } as INodeStatusWorkFlow
}

describe("buildTimeline", () => {
  it("colapsa started + completed numa única linha por nó", () => {
    const timeline = buildTimeline(
      [lifecycle("a", "started", 0), lifecycle("a", "completed", 500, { duration_ms: 480 })],
      [],
      T0,
    )
    expect(timeline.nodes).toHaveLength(1)
    expect(timeline.nodes[0].status).toBe("completed")
    expect(timeline.nodes[0].durationMs).toBe(480)
    expect(timeline.nodes[0].startOffsetMs).toBe(0)
  })

  it("calcula offsets relativos ao início do run, não à hora local", () => {
    const timeline = buildTimeline(
      [lifecycle("a", "started", 0), lifecycle("b", "started", 1500)],
      [],
      T0,
    )
    const b = timeline.nodes.find(n => n.nodeId === "b")!
    expect(b.startOffsetMs).toBe(1500)
  })

  it("mantém os offsets corretos quando o começo da lista foi descartado", () => {
    // The store pins `runStartedTs` on the arrival of the first event precisely
    // for this case: deriving it from events[0] would shift everything after rotation.
    const rotated = [lifecycle("b", "started", 4000), lifecycle("b", "completed", 4200, { duration_ms: 200 })]
    const timeline = buildTimeline(rotated, [], T0)
    expect(timeline.nodes[0].startOffsetMs).toBe(4000)
  })

  it("inclui nós do canvas que ainda não executaram", () => {
    const timeline = buildTimeline(
      [lifecycle("a", "started", 0)],
      [canvasNode("a", "started"), canvasNode("b", "idle")],
      T0,
    )
    expect(timeline.counts.total).toBe(2)
    expect(timeline.nodes.find(n => n.nodeId === "b")!.status).toBe("pending")
  })

  it("confia no canvas quando os eventos do nó foram descartados", () => {
    // Scenario of the run that prints a lot: the `completed` of 'a' dropped off the
    // list, but the canvas accumulated the state. Without reconciliation, 'a'
    // would show up again as "aguardando" (waiting) — contradicting the graph itself.
    const timeline = buildTimeline(
      [stdout("b", 900, "linha")],
      [canvasNode("a", "completed", { duration: 320, output_keys: ["out"] }), canvasNode("b", "started")],
      T0,
    )
    const a = timeline.nodes.find(n => n.nodeId === "a")!
    expect(a.status).toBe("completed")
    expect(a.durationMs).toBe(320)
    expect(a.outputKeys).toEqual(["out"])
    expect(timeline.counts.done).toBe(1)
  })

  it("agrupa prints por nó preservando a ordem", () => {
    const timeline = buildTimeline(
      [
        lifecycle("a", "started", 0),
        stdout("a", 100, "primeira"),
        stdout("a", 200, "segunda"),
        lifecycle("b", "started", 300),
        stdout("b", 400, "de outro nó"),
      ],
      [],
      T0,
    )
    const a = timeline.nodes.find(n => n.nodeId === "a")!
    expect(a.prints.map(p => p.text)).toEqual(["primeira", "segunda"])
    expect(a.prints[1].offsetMs).toBe(200)
    expect(timeline.nodes.find(n => n.nodeId === "b")!.prints).toHaveLength(1)
    expect(timeline.totalPrints).toBe(3)
  })

  it("desdobra o stdout agregado: uma linha de painel por item de `lines`", () => {
    // The executor stopped emitting one event per print() — it aggregates in
    // ~200ms windows. Without unfolding, three prints became ONE row with \n in the middle.
    const timeline = buildTimeline(
      [
        lifecycle("a", "started", 0),
        stdout("a", 100, "um", "dois", "três"),
      ],
      [],
      T0,
    )
    const a = timeline.nodes.find(n => n.nodeId === "a")!
    expect(a.prints.map(p => p.text)).toEqual(["um", "dois", "três"])
    expect(timeline.totalPrints).toBe(3)
  })

  it("`lines` é a única fonte da saída — `message` não vira print", () => {
    // Single source: with both keys, the same text traveled DUPLICATED in the
    // event and the 200-line batch went over the 64 KB ceiling, arriving here
    // stripped down to the control fields. If `message` fed prints again, a
    // mixed-schema event would duplicate the whole output in the "Nós" tab.
    const timeline = buildTimeline(
      [{
        seq: 0, ts: T0 + 100, node: "a", kind: "stdout", level: "info", status: "log",
        lines: ["uma linha"], message: "uma linha", raw: {},
      }],
      [],
      T0,
    )
    expect(timeline.nodes[0].prints.map(p => p.text)).toEqual(["uma linha"])
  })

  it("expõe falha com traceback, categoria e retryable", () => {
    const timeline = buildTimeline(
      [
        lifecycle("a", "started", 0),
        lifecycle("a", "failed", 80, {
          duration_ms: 80,
          message: "coluna 'lat' não encontrada",
          traceback: "Traceback...",
          error_category: "user",
          retryable: false,
        }),
      ],
      [],
      T0,
    )
    expect(timeline.problems).toHaveLength(1)
    expect(timeline.problems[0].problem).toMatchObject({
      message: "coluna 'lat' não encontrada",
      category: "user",
      retryable: false,
      traceback: "Traceback...",
    })
  })

  it("identifica o nó mais lento", () => {
    const timeline = buildTimeline(
      [
        lifecycle("a", "completed", 100, { duration_ms: 100 }),
        lifecycle("b", "completed", 5000, { duration_ms: 4100 }),
        lifecycle("c", "completed", 5200, { duration_ms: 200 }),
      ],
      [],
      T0,
    )
    expect(timeline.slowest?.nodeId).toBe("b")
  })

  it("fecha o run com status, duração e taxonomia do workflow", () => {
    const timeline = buildTimeline(
      [
        lifecycle("a", "completed", 100, { duration_ms: 100 }),
        {
          ...lifecycle(WF_COMPLETE, "failed", 200, { duration_ms: 200 }),
          message: "Executor desconectou",
          error_category: "transient",
          retryable: true,
        },
      ],
      [],
      T0,
    )
    expect(timeline.workflow.status).toBe("failed")
    expect(timeline.workflow.durationMs).toBe(200)
    expect(timeline.workflow.category).toBe("transient")
    // The synthetic end-of-run node doesn't become a row in the list.
    expect(timeline.nodes.every(n => n.nodeId !== WF_COMPLETE)).toBe(true)
  })

  it("não zera a duração vinda do canvas quando o evento não a traz", () => {
    const timeline = buildTimeline(
      [lifecycle("a", "completed", 400)],
      [canvasNode("a", "completed", { duration: 390 })],
      T0,
    )
    expect(timeline.nodes[0].durationMs).toBe(390)
  })

  it("timelineToText inclui prints e erro de cada nó", () => {
    const timeline = buildTimeline(
      [
        lifecycle("a", "started", 0),
        stdout("a", 50, "processando"),
        lifecycle("a", "failed", 90, { duration_ms: 90, message: "boom", error_category: "user" }),
      ],
      [],
      T0,
    )
    const text = timelineToText(timeline, "run-123")
    expect(text).toContain("run-123")
    expect(text).toContain("processando")
    expect(text).toContain("boom")
    expect(text).toContain("categoria: user")
  })
})

describe("toRunEvent", () => {
  it("converte o timestamp do backend (segundos) para epoch ms", () => {
    const event = toRunEvent({ node: "a", status: "started", kind: "lifecycle", level: "info", timestamp: 1_700_000_000.5 })
    expect(event.ts).toBe(1_700_000_000_500)
  })

  it("deriva kind/level de eventos antigos ainda no histórico do Redis", () => {
    expect(toRunEvent({ node: "a", status: "log", extra: { message: "x" } }).kind).toBe("stdout")
    expect(toRunEvent({ node: "a", status: "debug" }).kind).toBe("debug")
    const failed = toRunEvent({ node: "a", status: "failed", error: "boom" })
    expect(failed.kind).toBe("lifecycle")
    expect(failed.level).toBe("error")
    expect(failed.message).toBe("boom")
  })
})
