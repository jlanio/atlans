import { describe, it, expect } from "vitest"
import { Edge } from "@xyflow/react"
import { INodeContext } from "@/context/useFlowContext"
import { computeAutoLayout } from "@/app/components/workflow/utils/auto-layout"
import { NODE_MIN_HEIGHT, calcNodeHeight } from "@/app/components/workflow/utils/node-metrics"

/**
 * Auto-layout today is dagre (layered layout, LR). These tests lock the
 * properties the "reorganizar nós" (rearrange nodes) button needs to guarantee:
 * chains come out straight, a join centers between its branches, tall nodes
 * (many ports) don't overlap, crossings don't get worse, and the result is
 * stable (same graph → same positions, so a repeated click doesn't "dance").
 * The order within a layer comes from the graph's structure — dagre reorders to
 * reduce crossings, it doesn't preserve the order from the canvas layout.
 */

function node(id: string, y = 0, ports = 0): INodeContext {
  return {
    id,
    position: { x: 0, y },
    data: { outputs: Array.from({ length: ports }, (_, i) => ({ name: `p${i}` })) },
  } as unknown as INodeContext
}

function edge(source: string, target: string): Edge {
  return { id: `${source}-${target}`, source, target } as Edge
}

/** Vertical interval occupied by a node, with its real height. */
function span(pos: { y: number }, n: INodeContext) {
  const outputs = (n.data.outputs as unknown[] | undefined)?.length ?? 0
  return { top: pos.y, bottom: pos.y + calcNodeHeight(outputs) }
}

/** Inversions between two adjacent columns — a direct proxy for the number of crossings. */
function countCrossings(
  orderA: string[],
  orderB: string[],
  children: Map<string, string[]>,
): number {
  const indexB = new Map<string, number>()
  orderB.forEach((id, i) => indexB.set(id, i))

  const targets: number[] = []
  for (const id of orderA) {
    const rows = (children.get(id) ?? [])
      .map(t => indexB.get(t))
      .filter((v): v is number => v !== undefined)
      .sort((a, b) => a - b)
    targets.push(...rows)
  }

  let crossings = 0
  for (let i = 0; i < targets.length; i++) {
    for (let j = i + 1; j < targets.length; j++) {
      if (targets[i] > targets[j]) crossings++
    }
  }
  return crossings
}

/** Serializes the position map into a stable string, to compare two runs. */
function fingerprint(pos: Map<string, { x: number; y: number }>) {
  return [...pos.entries()]
    .map(([id, p]) => `${id}:${p.x},${p.y}`)
    .sort()
    .join("|")
}

describe("computeAutoLayout", () => {

  it("endireita uma cadeia linear — todos os nós no mesmo Y", () => {
    const nodes = [node("a", 300), node("b", 10), node("c", 900)]
    const edges = [edge("a", "b"), edge("b", "c")]

    const pos = computeAutoLayout(nodes, edges)

    expect(pos.get("a")!.y).toBe(pos.get("b")!.y)
    expect(pos.get("b")!.y).toBe(pos.get("c")!.y)
    // E em colunas estritamente crescentes.
    expect(pos.get("a")!.x).toBeLessThan(pos.get("b")!.x)
    expect(pos.get("b")!.x).toBeLessThan(pos.get("c")!.x)
  })

  it("centra o nó de junção entre os dois ramos do diamante", () => {
    const nodes = [node("a"), node("b", 0), node("c", 100), node("d", 50)]
    const edges = [edge("a", "b"), edge("a", "c"), edge("b", "d"), edge("c", "d")]

    const pos = computeAutoLayout(nodes, edges)
    const center = (id: string) => pos.get(id)!.y + NODE_MIN_HEIGHT / 2

    // D sits midway between B and C, and so does A (the parent of both branches).
    expect(center("d")).toBeCloseTo((center("b") + center("c")) / 2, 0)
    expect(center("a")).toBeCloseTo((center("b") + center("c")) / 2, 0)
    // And the three layers sit in increasing columns.
    expect(pos.get("a")!.x).toBeLessThan(pos.get("b")!.x)
    expect(pos.get("b")!.x).toBeLessThan(pos.get("d")!.x)
  })

  it("não sobrepõe um nó de 8 portas com o vizinho de baixo", () => {
    const nodes = [node("root"), node("tall", 0, 8), node("small", 100)]
    const edges = [edge("root", "tall"), edge("root", "small")]

    const pos = computeAutoLayout(nodes, edges)
    const byId = new Map(nodes.map(n => [n.id, n]))

    const spans = ["tall", "small"]
      .map(id => span(pos.get(id)!, byId.get(id)!))
      .sort((a, b) => a.top - b.top)

    expect(spans[0].bottom).toBeLessThanOrEqual(spans[1].top)
  })

  it("empilha irmãos sem sobreposição, na mesma coluna à frente do pai", () => {
    // dagre doesn't preserve the canvas's vertical order, but it keeps the
    // siblings in a clean stack (same column, no overlap) right after the parent.
    const nodes = [node("root"), node("um", 0), node("dois", 200), node("tres", 400)]
    const edges = [edge("root", "um"), edge("root", "dois"), edge("root", "tres")]

    const pos = computeAutoLayout(nodes, edges)
    const byId = new Map(nodes.map(n => [n.id, n]))
    const filhos = ["um", "dois", "tres"]

    // All in the same column, to the right of the parent.
    const colX = pos.get("um")!.x
    for (const id of filhos) expect(pos.get(id)!.x).toBe(colX)
    expect(colX).toBeGreaterThan(pos.get("root")!.x)

    // Stacked with no vertical overlap.
    const spans = filhos
      .map(id => span(pos.get(id)!, byId.get(id)!))
      .sort((a, b) => a.top - b.top)
    for (let i = 0; i < spans.length - 1; i++) {
      expect(spans[i].bottom).toBeLessThanOrEqual(spans[i + 1].top)
    }
  })

  it("termina em grafo cíclico sem raiz", () => {
    const nodes = [node("a"), node("b"), node("c")]
    const edges = [edge("a", "b"), edge("b", "c"), edge("c", "a")]

    const pos = computeAutoLayout(nodes, edges)

    expect(pos.size).toBe(3)
    // Each node gets its own column — no stacking in column 0.
    expect(new Set([...pos.values()].map(p => p.x)).size).toBe(3)
  })

  it("ignora self-loop e aresta órfã sem quebrar", () => {
    const nodes = [node("a"), node("b")]
    const edges = [edge("a", "a"), edge("a", "b"), edge("b", "fantasma")]

    const pos = computeAutoLayout(nodes, edges)

    expect(pos.size).toBe(2)
    expect(pos.get("a")!.x).toBeLessThan(pos.get("b")!.x)
  })

  it("nunca aumenta o número de cruzamentos", () => {
    // Ordem inicial deliberadamente cruzada: a→d e b→c.
    const nodes = [node("a", 0), node("b", 100), node("c", 0), node("d", 100)]
    const edges = [edge("a", "d"), edge("b", "c")]

    const children = new Map([["a", ["d"]], ["b", ["c"]], ["c", []], ["d", []]])
    const before = countCrossings(["a", "b"], ["c", "d"], children)

    const pos = computeAutoLayout(nodes, edges)
    const col1 = ["a", "b"].sort((x, y) => pos.get(x)!.y - pos.get(y)!.y)
    const col2 = ["c", "d"].sort((x, y) => pos.get(x)!.y - pos.get(y)!.y)

    expect(countCrossings(col1, col2, children)).toBeLessThanOrEqual(before)
  })

  it("é determinístico — mesmo grafo, mesmas posições a cada clique", () => {
    const nodes = [node("t"), node("wfs"), node("filtro"), node("caixa"), node("salvar")]
    const edges = [
      edge("t", "caixa"),
      edge("wfs", "filtro"),
      edge("filtro", "caixa"),
      edge("caixa", "salvar"),
    ]

    const a = fingerprint(computeAutoLayout(nodes, edges))
    const b = fingerprint(computeAutoLayout(nodes, edges))
    const c = fingerprint(computeAutoLayout(nodes, edges))

    expect(a).toBe(b)
    expect(b).toBe(c)
  })

  it("posiciona nós desconectados sem colidir", () => {
    const nodes = [node("ilha1", 0), node("ilha2", 50)]

    const pos = computeAutoLayout(nodes, [])

    expect(pos.get("ilha1")!.x).toBe(pos.get("ilha2")!.x)
    expect(Math.abs(pos.get("ilha1")!.y - pos.get("ilha2")!.y)).toBeGreaterThanOrEqual(NODE_MIN_HEIGHT)
  })

  it("devolve mapa vazio sem nós", () => {
    expect(computeAutoLayout([], []).size).toBe(0)
  })

})
