// web/app/components/workflow/subflow-viewer/estado-do-nivel.ts
//
// Recorte da linha do tempo do run correspondente a UM nível de sub-fluxo.
import { NodeRun, NodeRunStatus } from "../run-panel/timeline"
import { StatusNodeStatusWorkFlow } from "@/context/useFlowContext"
import { idLocal, pertenceAoNivel } from "../utils/subflow-path"
import { EstadoDeNo } from "./scope"

/**
 * A linha do tempo fala em quatro estados de execução; o card do nó fala nos do
 * canvas. São a mesma coisa com nomes diferentes, exceto na ponta: "aguardando"
 * no painel é "idle" no canvas — nó desenhado sem anel, que é o que se quer para
 * um nó que o run nem chegou a alcançar.
 */
const ESTADO_NO_CANVAS: Record<NodeRunStatus, StatusNodeStatusWorkFlow> = {
  pending: "idle",
  running: "started",
  completed: "completed",
  failed: "failed",
  // Mapeia para si mesmo: o nó do sub-fluxo também precisa poder dizer "comecei
  // e não sei como terminei" — colapsar em "idle" esconderia que ele executou.
  unknown: "unknown",
}

export interface RecorteDoNivel {
  /** Estado de cada nó daquele nível, pelo id local — pronto para o escopo. */
  estadoPorId: Map<string, EstadoDeNo>
  /**
   * Nós que executaram no nível mas não existem no grafo carregado.
   *
   * Acontece quando o sub-fluxo foi editado depois do run: o grafo mostrado é o
   * atual, os eventos são os de então. Contá-los é o que impede a tela de passar
   * por completa quando não é — dizer nada aqui seria afirmar, por omissão, que
   * tudo o que rodou está desenhado.
   */
  semCorrespondencia: string[]
}

export function recortarNivel(
  nodes: NodeRun[],
  caminho: string[],
  idsDoGrafo: Set<string>,
): RecorteDoNivel {
  const estadoPorId = new Map<string, EstadoDeNo>()
  const semCorrespondencia: string[] = []

  for (const node of nodes) {
    if (!pertenceAoNivel(node.nodeId, caminho)) continue

    const id = idLocal(node.nodeId)
    if (!idsDoGrafo.has(id)) {
      semCorrespondencia.push(node.name || id)
      continue
    }

    estadoPorId.set(id, {
      status: ESTADO_NO_CANVAS[node.status],
      error: node.problem?.message,
      duration: node.durationMs ?? undefined,
      cache_hit: node.cacheHit,
    })
  }

  return { estadoPorId, semCorrespondencia }
}
