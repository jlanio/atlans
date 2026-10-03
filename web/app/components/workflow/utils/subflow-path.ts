// web/app/components/workflow/utils/subflow-path.ts
//
// Address of a node that ran INSIDE a sub-workflow.
//
// The executor republishes the child's events on the parent's channel,
// prefixing the id with the SubWorkflow node that called it
// (`_SubWorkflowEventPublisher`, in flow/nodes/control/sub_workflow.py). In an
// A→B→C chain this accumulates: a node `X` inside C reaches A's canvas as
// `sA::sB::X`.
//
// The `subworkflow_parent_node` meta does NOT work for going down more than one
// level: each level OVERWRITES it when republishing, so it always points at
// the root canvas's SubWorkflow node. What carries the whole path is the id
// itself — and that is why deep navigation is resolved here, and not by
// reading the meta. Node ids are canvas UUIDs, so `::` never collides with the
// content.

export const SEPARATOR = "::"

/** Address segments: the SubWorkflow nodes traversed + the node itself. */
export function runNodeIdSegments(runNodeId: string): string[] {
  return runNodeId.split(SEPARATOR).filter(Boolean)
}

/**
 * Id of the node within the canvas where it actually lives.
 *
 * It is this id — and not the full address — that matches the sub-workflow's
 * definition loaded from the backend.
 */
export function idLocal(runNodeId: string): string {
  const segmentos = runNodeIdSegments(runNodeId)
  return segmentos[segmentos.length - 1] ?? runNodeId
}

/**
 * SubWorkflow nodes traversed to reach it. Empty for a node of the open
 * workflow itself — it is the "did this come from inside a sub-workflow?" test.
 */
export function callPath(runNodeId: string): string[] {
  return runNodeIdSegments(runNodeId).slice(0, -1)
}

/**
 * Is the node DIRECTLY inside the level described by `caminho`?
 *
 * Strict on purpose: a node of a deeper sub-workflow shares the prefix, but
 * does not belong to this canvas — painting it here would attribute to a node
 * of the open graph another node's state, with the same local id by coincidence.
 */
export function pertenceAoNivel(runNodeId: string, caminho: string[]): boolean {
  const chamada = callPath(runNodeId)
  return (
    chamada.length === caminho.length &&
    chamada.every((segmento, i) => segmento === caminho[i])
  )
}
