import { describe, it, expect } from "vitest"
import { Edge } from "@xyflow/react"
import { buildFocusGraph, collectPath } from "@/app/components/workflow/utils/graph-traversal"

function edge(id: string, source: string, target: string): Edge {
  return { id, source, target } as Edge
}

/** Atalho: monta o grafo e coleta o caminho de uma vez. */
function pathOf(edges: Edge[], nodeId: string) {
  const { nodes, edges: touched } = collectPath(buildFocusGraph(edges), nodeId)
  return { nodes: [...nodes].sort(), edges: [...touched].sort() }
}

describe("collectPath", () => {

  it("pega ancestrais e descendentes, não os ramos vizinhos", () => {
    // a → b → c ; d → e  (componente separado)
    const edges = [edge("ab", "a", "b"), edge("bc", "b", "c"), edge("de", "d", "e")]

    const { nodes, edges: touched } = pathOf(edges, "b")

    expect(nodes).toEqual(["a", "b", "c"])
    expect(touched).toEqual(["ab", "bc"])
  })

  it("não duplica o nó de junção do diamante", () => {
    // a → {b, c} → d, focando em a: d é alcançado por dois caminhos.
    const edges = [
      edge("ab", "a", "b"), edge("ac", "a", "c"),
      edge("bd", "b", "d"), edge("cd", "c", "d"),
    ]

    const { nodes, edges: touched } = pathOf(edges, "a")

    expect(nodes).toEqual(["a", "b", "c", "d"])
    expect(touched).toEqual(["ab", "ac", "bd", "cd"])
  })

  it("termina em ciclo", () => {
    const edges = [edge("ab", "a", "b"), edge("ba", "b", "a")]

    const { nodes, edges: touched } = pathOf(edges, "a")

    expect(nodes).toEqual(["a", "b"])
    expect(touched).toEqual(["ab", "ba"])
  })

  it("devolve os dois ids em arestas paralelas (Conditional true/false → mesmo alvo)", () => {
    const edges = [edge("verdadeiro", "cond", "alvo"), edge("falso", "cond", "alvo")]

    const { edges: touched } = pathOf(edges, "alvo")

    expect(touched).toEqual(["falso", "verdadeiro"])
  })

  it("nó isolado devolve apenas ele mesmo", () => {
    const { nodes, edges: touched } = pathOf([edge("de", "d", "e")], "sozinho")

    expect(nodes).toEqual(["sozinho"])
    expect(touched).toEqual([])
  })

  it("segue um self-loop sem travar", () => {
    const { nodes, edges: touched } = pathOf([edge("aa", "a", "a")], "a")

    expect(nodes).toEqual(["a"])
    expect(touched).toEqual(["aa"])
  })

})
