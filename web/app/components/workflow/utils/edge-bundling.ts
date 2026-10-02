import { Edge } from "@xyflow/react"

/**
 * Separa em faixas as arestas que ligam o mesmo par de nós.
 *
 * Caso concreto: um `Conditional` com `true` e `false` apontando para o mesmo
 * alvo desenha duas linhas quase coladas, com os badges de label empilhados no
 * mesmo ponto. O offset entra como `centerX` do `getSmoothStepPath`: num layout
 * da esquerda para a direita é ali que fica o trecho vertical do degrau — e,
 * junto com ele, o rótulo. Deslocar `centerY` moveria só o rótulo, para fora da
 * própria linha.
 *
 * O resultado NÃO é guardado em `edge.data`: isso exigiria um `setEdges` a cada
 * mudança de topologia, e o detector de alterações de `useSaveWorkflow` veria
 * um array novo e marcaria o workflow como "não salvo" sem edição do usuário.
 */

/** Distância entre faixas vizinhas, em pixels de flow-space. */
const LANE_PX = 22

export function computeLaneOffsets(edges: Edge[], lanePx = LANE_PX): Map<string, number> {
  // Agrupamento em dois níveis (origem → destino → arestas) em vez de uma chave
  // concatenada: dispensa escolher um separador que os ids não possam conter.
  const groups = new Map<string, Map<string, string[]>>()

  for (const edge of edges) {
    let byTarget = groups.get(edge.source)
    if (!byTarget) {
      byTarget = new Map()
      groups.set(edge.source, byTarget)
    }

    const group = byTarget.get(edge.target)
    if (group) group.push(edge.id)
    else byTarget.set(edge.target, [edge.id])
  }

  const offsets = new Map<string, number>()
  for (const byTarget of groups.values()) {
    for (const group of byTarget.values()) {
      // Grupo unitário é o caso majoritário — sai sem offset e sem ordenar.
      if (group.length === 1) continue

      // Ordem por id: arbitrária, mas estável entre renders (ids são uuid).
      group.sort()
      group.forEach((id, i) => {
        offsets.set(id, (i - (group.length - 1) / 2) * lanePx)
      })
    }
  }

  return offsets
}

// Memo por identidade do array: sem ele, cada uma das E arestas recalcularia
// o agrupamento inteiro no próprio render — O(E²) por frame.
//
// WeakMap, e não um par de variáveis de módulo: o visualizador de sub-fluxo
// monta um SEGUNDO React Flow com o mesmo componente de aresta, e com o par de
// variáveis os dois canvas se invalidavam mutuamente — cada aresta do editor
// jogava fora o cache preenchido pelas do filho e vice-versa, devolvendo o
// O(E²) que este memo existe para evitar. Cada array guarda o próprio resultado
// e a entrada é liberada sozinha quando o array é descartado.
const cache = new WeakMap<Edge[], Map<string, number>>()

export function getLaneOffset(edges: Edge[], edgeId: string): number {
  let offsets = cache.get(edges)
  if (!offsets) {
    offsets = computeLaneOffsets(edges)
    cache.set(edges, offsets)
  }
  return offsets.get(edgeId) ?? 0
}
