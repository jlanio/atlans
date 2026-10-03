import { describe, it, expect } from "vitest"
import { Edge } from "@xyflow/react"
import { classifyZoom } from "@/app/hooks/workflow/useZoomLod"
import { computeLaneOffsets } from "@/app/components/workflow/utils/edge-bundling"
import { buildFocusCss, escapeId } from "@/app/components/workflow/utils/focus-css"

describe("classifyZoom", () => {

  it("desce e sobe os degraus nos limiares", () => {
    expect(classifyZoom(0.30, "mid")).toBe("far")
    expect(classifyZoom(0.60, "mid")).toBe("mid")
    expect(classifyZoom(0.85, "mid")).toBe("near")
  })

  it("segura o degrau na zona de histerese", () => {
    // Entered `far` below 0.42; it has to go above 0.50 to leave.
    expect(classifyZoom(0.45, "far")).toBe("far")
    // Entered `near` above 0.80; it has to drop below 0.72 to leave.
    expect(classifyZoom(0.75, "near")).toBe("near")
  })

  it("pula degrau quando o zoom salta", () => {
    expect(classifyZoom(0.90, "far")).toBe("near")
    expect(classifyZoom(0.30, "near")).toBe("far")
  })

})

describe("computeLaneOffsets", () => {

  const edge = (id: string, source: string, target: string) =>
    ({ id, source, target }) as Edge

  it("não desloca arestas sem par concorrente", () => {
    const offsets = computeLaneOffsets([edge("e1", "a", "b"), edge("e2", "b", "c")])
    expect(offsets.size).toBe(0)
  })

  it("distribui faixas simétricas entre arestas do mesmo par", () => {
    const offsets = computeLaneOffsets([
      edge("verdadeiro", "cond", "alvo"),
      edge("falso", "cond", "alvo"),
    ], 20)

    expect([...offsets.values()].sort((a, b) => a - b)).toEqual([-10, 10])
  })

  it("mantém o do meio centrado com três arestas", () => {
    const offsets = computeLaneOffsets([
      edge("a", "x", "y"), edge("b", "x", "y"), edge("c", "x", "y"),
    ], 20)

    expect(offsets.get("b")).toBe(0)
    expect(offsets.get("a")).toBe(-20)
    expect(offsets.get("c")).toBe(20)
  })

  it("não agrupa o sentido inverso com o de ida", () => {
    const offsets = computeLaneOffsets([edge("ida", "a", "b"), edge("volta", "b", "a")])
    expect(offsets.size).toBe(0)
  })

})

describe("buildFocusCss", () => {

  it("devolve vazio sem âncora", () => {
    expect(buildFocusCss(new Set(["a"]), new Set(), null)).toBe("")
  })

  it("marca nós, arestas e o portal dos rótulos", () => {
    const css = buildFocusCss(new Set(["n1"]), new Set(["e1"]), "n1")

    expect(css).toContain('.react-flow__node[data-id="n1"]')
    expect(css).toContain('.react-flow__edge[data-id="e1"]')
    expect(css).toContain('[data-edge-id="e1"]')
    expect(css).toContain("--rf-focus-dim:1")
    expect(css).toContain("outline-color:var(--primary)")
  })

  it("preserva hífens de UUID e neutraliza o que quebraria a folha", () => {
    expect(escapeId("3f2a-9b1c-44de")).toBe("3f2a-9b1c-44de")
    expect(escapeId('a"b')).toBe('a\\"b')
    expect(escapeId("a</style>b")).toBe("a/styleb")
  })

})
