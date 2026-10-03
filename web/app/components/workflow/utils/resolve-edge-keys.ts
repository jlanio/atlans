import { INodePortAPI, INodeOutputField } from "@/service/types"
import { saidasDoNo } from "./node-ports"

/**
 * Rules for resolving an edge's keys.
 *
 * They live here because two screens create connections — dragging from a
 * handle (`handleConnectNodes` on the canvas) and the handle's "+" button,
 * which opens the drawer and creates the edge along with the node. The second
 * one was born without `from_key`, and in the executor that falls into
 * `inputs.update(parent_outputs)`: the child node receives ALL of the parent's
 * outputs spread out, instead of the port the user picked.
 */

/**
 * A node's `from_key` candidates: the instance's output fields.
 *
 * `saidasDoNo` resolves the source: the catalog's fields (`saidas`) or, in the
 * Python Script, the `output_vars` variables — offering the catalog's "result"
 * created an edge with a `from_key` the executor does not find in the result.
 * Branches (`true`/`false`) never show up: they route execution and are not
 * fields.
 */
export function getCandidateKeys(nodeData?: {
  saidas?: INodeOutputField[]
  dynamic_output?: boolean
  properties?: Record<string, unknown>
}): INodePortAPI[] {
  const candidates: INodePortAPI[] = []
  const seen = new Set<string>()
  for (const field of saidasDoNo(nodeData)) {
    if (!field?.name || seen.has(field.name)) continue
    seen.add(field.name)
    candidates.push(field)
  }
  return candidates
}

/**
 * `from_key` of a connection whose source handle is already known.
 *
 * Returns `undefined` when the choice is ambiguous — in that case the caller
 * should open the picker instead of guessing.
 */
export function resolveFromKey(
  sourceHandle: string | null | undefined,
  candidateKeys: INodePortAPI[],
): string | undefined {
  // A handle that is a data port: it is the key itself.
  if (sourceHandle && candidateKeys.some(f => f.name === sourceHandle)) {
    return sourceHandle
  }
  // Single candidate: nothing to choose.
  if (candidateKeys.length === 1) {
    return candidateKeys[0]?.name
  }
  return undefined
}


/**
 * `to_key` of a connection whose target handle is already known.
 *
 * Only fills it when the target declares MULTIPLE named inputs (e.g.
 * OverlapPercentage/AttributeJoin layerA/layerB) — with a single input, the
 * executor resolves it alone and writing `to_key` would be noise. Without
 * filling it, the executor falls into `inputs[from_key]` instead of
 * `inputs[to_key]` and maps the input ports wrong — and the PER-PORT column
 * suggestion (`colunas-conhecidas` indexes by `to_key || from_key`) is empty.
 *
 * Pure and here, not on the canvas: the handle's "+" button also creates an
 * edge (drawer) and it was born without `to_key` — the same story as the
 * `from_key` this file exists to prevent.
 */
export function resolveToKey(
  targetHandle: string | null | undefined,
  declaredInputs: unknown,
): string | undefined {
  if (!targetHandle) return undefined
  const inputs = (declaredInputs ?? []) as INodePortAPI[]
  if (inputs.length > 1 && inputs.some(p => p.name === targetHandle)) {
    return targetHandle
  }
  return undefined
}

/**
 * Default input port for an edge created WITHOUT an explicit target choice —
 * the "+" button creates node and edge at once, without anyone dropping the
 * line on a handle.
 *
 * Same rule as `resolveToKey`: there is only something to choose when the
 * target declares more than one port; then the first one applies, just as
 * `from_key` already falls to `candidatos[0]` in the same flow — and the edge
 * badge lets you change it later.
 */
export function portaDeEntradaPadrao(declaredInputs: unknown): string | undefined {
  const inputs = (declaredInputs ?? []) as INodePortAPI[]
  return inputs.length > 1 ? inputs[0]?.name : undefined
}

/**
 * `sourceHandle` an edge should carry when choosing key `nome` at the source,
 * keeping the `sourceHandle === from_key` invariant of multi-output nodes
 * without pointing the line at a handle that does not exist.
 *
 * There is only a NAMED handle when the node draws 2+ REAL outputs (`outputs`) —
 * see `default-type` / `default-trigger-icon`, which render one `HandleSource`
 * per `outputs[].name` only in that case, and an ANONYMOUS handle otherwise.
 * A field without `port` does NOT become a handle: syncing `sourceHandle` with a
 * field that has no connection point (which `getCandidateKeys` also offers in
 * the picker) pointed the edge at a nonexistent handle, and React Flow stopped
 * drawing it — the edge "vanished". Mirrors the rule of `resolveSourceHandle`
 * (edge-persistence): a real port only with `outputs.length > 1 && nome ∈ outputs`.
 *
 *   • single output (0/1 output)          → `null`      (anonymous handle; also
 *                                            clears an already saved ghost handle)
 *   • multi-output and `nome` is a port   → `nome`
 *   • multi-output and `nome` is no port  → `undefined` (leaves the handle as is)
 */
export function sourceHandleDaChave(
  outputs: ReadonlyArray<{ name?: string }> | undefined,
  nome: string,
): string | null | undefined {
  const saidas = outputs ?? []
  if (saidas.length <= 1) return null
  return saidas.some((o) => o?.name === nome) ? nome : undefined
}

/**
 * A node that accepts only ONE incoming edge — which depends on what it declares.
 *
 * `SubWorkflowOutput` defines the sub-workflow's return value. With no declared
 * ports it has an anonymous connection point: two edges spread both dicts into
 * the same keys and the last one wins, so the contract announces one output and
 * delivers another depending on the order of the edges. From TWO ports on, each
 * edge lands in its own key — the editor fills `to_key` with the port name —
 * and the contention ceases to exist: then multiple connections are the goal,
 * not the problem.
 *
 * A single port is not enough: `resolveToKey` only fills `to_key` when the
 * target declares MORE THAN ONE, so with one the edges would compete for the
 * key again.
 *
 * `SubWorkflowInput` was blocked for symmetry and did not need to be: each edge
 * leaving it spreads the input dict into its own target, with no contention.
 */
export function limitadoAUmaAresta(
  nodeName: string | undefined,
  declaredPorts: number,
): boolean {
  return nodeName !== undefined && SINGLE_EDGE_NODES.has(nodeName) && declaredPorts < 2
}

/**
 * The nodes that accept only one edge when no ports are declared. The image map
 * is included for the same reason as SubWorkflowOutput: with an anonymous
 * connection point, two connected layers would spread both dicts into the same
 * key (`output`), the last would win and the map would come out with a single
 * layer — without the node being able to notice the loss. From two ports on,
 * each layer arrives under its own port's name.
 */
const SINGLE_EDGE_NODES: ReadonlySet<string> = new Set(["SubWorkflowOutput", "CartaImagem"])
