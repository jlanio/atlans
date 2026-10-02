import { Edge } from "@xyflow/react"
import { IEdgeDefinition } from "@/service/types"
import { INodePortAPI } from "@/service/types"

/**
 * Serialização das arestas do canvas — o par save/load precisa ser simétrico.
 *
 * Assimetria aqui não é só bug de persistência: o detect-dirty compara o
 * snapshot inicial com o payload atual usando a MESMA serialização, então
 * qualquer divergência faz o canvas acusar "não salvo" assim que abre.
 *
 * Regressão que originou este módulo: `condition` era gravado para qualquer
 * handle nomeado (`sourceHandle === "true"` com sourceHandle="output" → false),
 * o que apagava o id da porta. No load isso virava sourceHandle="false" — um
 * handle que não existe em nó não-condicional —, o React Flow não conseguia
 * ancorar a aresta e ela sumia do canvas. Só afetava nós com mais de uma porta
 * de saída; com uma só, o handle é anônimo e nada era gravado.
 */

/** Handles de roteamento de nó condicional — os únicos que viram `condition`. */
function isRoutingHandle(handle?: string | null): boolean {
  return handle === "true" || handle === "false"
}

/** Converte uma aresta do React Flow para o formato persistido. */
export function serializeEdge(edge: Edge): IEdgeDefinition {
  const { source, target, sourceHandle, targetHandle, data } = edge
  return {
    source,
    target,
    ...(sourceHandle ? { source_handle: sourceHandle } : {}),
    ...(isRoutingHandle(sourceHandle) ? { condition: sourceHandle === "true" } : {}),
    ...(data?.from_key ? { from_key: data.from_key as string } : {}),
    ...(targetHandle
      ? { to_key: targetHandle }
      : data?.to_key
        ? { to_key: data.to_key as string }
        : {}),
  }
}

/**
 * Handle de origem de uma aresta persistida.
 *
 * `outputsByNodeId` traz as portas declaradas por cada nó: sem elas não dá para
 * distinguir um ramo condicional legítimo de um `condition` espúrio gravado
 * pela versão antiga.
 */
export function resolveSourceHandle(
  edge: IEdgeDefinition,
  outputsByNodeId: Map<string, INodePortAPI[]>,
): string | undefined {
  const outputs = outputsByNodeId.get(edge.source) ?? []

  // 1. Formato atual: o handle persistido — desde que ainda seja um handle REAL
  //    do nó. Só há handle NOMEADO com 2+ saídas reais (default-type desenha um
  //    HandleSource por porta apenas nesse caso); true/false são os de
  //    roteamento. Um id fora disso — um campo sem `port` gravado por um
  //    picker que sincronizava o sourceHandle com QUALQUER candidato — não tem
  //    ponto de conexão: o React Flow não ancora a aresta e ela some do canvas.
  //    Ignorá-lo aqui devolve a linha ao canvas pela recuperação abaixo
  //    (from_key / anônimo), sem migrar o banco. `data.outputs` é a MESMA fonte
  //    que a renderização usa, e chega síncrona no load (catálogo ou `ports`).
  if (edge.source_handle) {
    const eNomeado = outputs.length > 1 && outputs.some(p => p.name === edge.source_handle)
    const eRoteamento = (edge.source_handle === "true" || edge.source_handle === "false")
      && outputs.some(p => p.name === "true" || p.name === "false")
    if (eNomeado || eRoteamento) return edge.source_handle
    // Handle fantasma: cai para os passos de recuperação.
  }

  // 2. Ramo de condicional — só se o nó REALMENTE tem portas true/false.
  //    Confiar em `condition` sem checar o nó ressuscitaria o bug ao contrário.
  const isRoutingNode = outputs.some(p => p.name === "true" || p.name === "false")
  if (isRoutingNode && edge.condition !== undefined) {
    return edge.condition ? "true" : "false"
  }

  // 3. Recuperação das arestas salvas antes da correção: o id da porta se
  //    perdeu, mas `from_key` guarda a mesma informação quando o handle era
  //    porta de dado. Devolve a aresta ao canvas sem migrar o banco.
  if (outputs.length > 1 && edge.from_key && outputs.some(p => p.name === edge.from_key)) {
    return edge.from_key
  }

  // 4. Handle anônimo (nó de saída única) — o React Flow ancora no primeiro.
  return undefined
}
