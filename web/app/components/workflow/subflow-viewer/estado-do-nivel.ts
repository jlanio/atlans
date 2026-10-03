// web/app/components/workflow/subflow-viewer/estado-do-nivel.ts
//
// Slice of the run's timeline corresponding to ONE sub-workflow level.
import { NodeRun, NodeRunStatus } from "../run-panel/timeline"
import { StatusNodeStatusWorkFlow } from "@/context/useFlowContext"
import { idLocal, pertenceAoNivel } from "../utils/subflow-path"
import { NodeState } from "./scope"

/**
 * The timeline speaks in four execution states; the node card speaks in the
 * canvas's. They are the same thing under different names, except at the edge:
 * "aguardando" (waiting) in the panel is "idle" on the canvas — a node drawn
 * without a ring, which is what you want for a node the run never reached.
 */
const NODE_CANVAS_STATUS: Record<NodeRunStatus, StatusNodeStatusWorkFlow> = {
  pending: "idle",
  running: "started",
  completed: "completed",
  failed: "failed",
  // Maps to itself: the sub-workflow node also needs to be able to say "I started
  // and don't know how I ended" — collapsing into "idle" would hide that it ran.
  unknown: "unknown",
}

export interface LevelSlice {
  /** State of each node of that level, by local id — ready for the scope. */
  estadoPorId: Map<string, NodeState>
  /**
   * Nodes that ran at this level but do not exist in the loaded graph.
   *
   * Happens when the sub-workflow was edited after the run: the graph shown is
   * the current one, the events are from back then. Counting them is what keeps
   * the screen from passing for complete when it is not — saying nothing here
   * would claim, by omission, that everything that ran is drawn.
   */
  semCorrespondencia: string[]
}

export function recortarNivel(
  nodes: NodeRun[],
  caminho: string[],
  graphIds: Set<string>,
): LevelSlice {
  const estadoPorId = new Map<string, NodeState>()
  const semCorrespondencia: string[] = []

  for (const node of nodes) {
    if (!pertenceAoNivel(node.nodeId, caminho)) continue

    const id = idLocal(node.nodeId)
    if (!graphIds.has(id)) {
      semCorrespondencia.push(node.name || id)
      continue
    }

    estadoPorId.set(id, {
      status: NODE_CANVAS_STATUS[node.status],
      error: node.problem?.message,
      duration: node.durationMs ?? undefined,
      cache_hit: node.cacheHit,
    })
  }

  return { estadoPorId, semCorrespondencia }
}
