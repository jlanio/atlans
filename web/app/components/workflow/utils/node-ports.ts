// web/app/components/workflow/utils/node-ports.ts
//
// A node's input ports — declared in the catalog or by the user.
//
// Most nodes declare their inputs in their own schema (`inputs`), and they are
// the same for every instance. A few (`dynamic_inputs`) leave the list to
// whoever builds the workflow, in the `ports` property — that is the case of
// the Python Script, where the names become the script's VARIABLES.
//
// This exists because the name that reaches the script comes from the edge's
// `to_key`, and the editor only fills `to_key` when the target node declares
// more than one port. Without declaring, two edges write to the same key and
// the second overwrites the first — the script receives ONE input and complains
// about an undefined variable, with nothing saying the other one was lost.
import { INodePortAPI, INodesAPI } from "@/service/types"

/**
 * Values accepted as a port name.
 *
 * Same rule as SubWorkflowPortsHelper: a healthy identifier. The name becomes a
 * variable inside the Python script, so a space or an accent would produce
 * invalid code — and the error would show up as a SyntaxError in the middle of
 * the user's script, far from the cause.
 */
export const NOME_DE_PORTA = /^[A-Za-z_][A-Za-z0-9_]*$/

/** Reads the `ports` property, tolerating a list, a JSON string, or absence. */
export function lerPortas(bruto: unknown): string[] {
  if (Array.isArray(bruto)) {
    return bruto.filter((x): x is string => typeof x === "string" && x.trim() !== "")
  }
  if (typeof bruto === "string" && bruto.trim()) {
    try {
      const parsed = JSON.parse(bruto)
      return Array.isArray(parsed)
        ? parsed.filter((x): x is string => typeof x === "string" && x.trim() !== "")
        : []
    } catch {
      return []
    }
  }
  return []
}

/**
 * Input connection points of ONE node instance.
 *
 * Regular node: the catalog's ports. Dynamic-input node: the ones the user
 * defined — and their absence returns an empty list, which is what keeps the
 * node with an anonymous connection point, exactly as before `ports` existed.
 */
export function portasDeEntrada(
  def: Pick<INodesAPI, "inputs" | "dynamic_inputs"> | undefined,
  properties: Record<string, unknown> | undefined,
): INodePortAPI[] {
  if (!def) return []
  if (!def.dynamic_inputs) return def.inputs ?? []
  // No duplicates: two connection points with the same id leave React Flow
  // not knowing which one the edge attaches to, and the second input would
  // overwrite the first in the script — which is exactly the defect ports exist
  // to solve. The field already marks the duplicate name in red; this is the
  // guarantee that the canvas does not enter an ambiguous state while it is
  // being fixed.
  return [...new Set(lerPortas(properties?.ports))].map(name => ({ name }))
}

/**
 * OUTPUT connection points of ONE node instance.
 *
 * Symmetric to `portasDeEntrada`: an `outputs_from_ports` node (SubWorkflowInput)
 * exposes as outputs the ports the user declared in `ports` — each port becomes
 * its own output handle, and the edge leaving it carries `from_key` = the port
 * name, so the next node receives only that key. The absence of ports returns
 * an empty list, which keeps the output point anonymous (spread mode) —
 * exactly the legacy behavior.
 */
export function portasDeSaida(
  def: Pick<INodesAPI, "outputs" | "outputs_from_ports" | "branches"> | undefined,
  properties: Record<string, unknown> | undefined,
): INodePortAPI[] {
  if (!def) return []
  if (def.outputs_from_ports) {
    return [...new Set(lerPortas(properties?.ports))].map(name => ({ name }))
  }
  // Branch node: the output points route execution, they do not carry a field.
  if (def.branches) return [{ name: "true" }, { name: "false" }]
  // Fields with their own connection point (`port`). None marked ⇒ anonymous
  // output point (spread mode) — the same rule as always.
  return (def.outputs ?? [])
    .filter(c => c.port)
    .map(c => ({ name: c.name, description: c.description }))
}

/**
 * Where an edge's line attaches to the target node, when reloading the workflow.
 *
 * `to_key` is the DATA NAME for the executor; `targetHandle` is WHERE THE LINE
 * ATTACHES on screen. There is only a NAMED handle (`id={port.name}`) when the
 * node declares 2+ ports — `default-type` draws one `HandleTarget` per port only
 * in that case; with just ONE port, the handle is ANONYMOUS (no id). Returning
 * the name of a single port as `targetHandle` points the edge at an id that does
 * not exist on screen: React Flow does not draw it, it VANISHES from the canvas
 * while still executing (`to_key` survives in `data`, so the executor still
 * routes by the key), and with no line drawn the delete button is unreachable —
 * you cannot even redo the connection.
 *
 * That is why `> 1` mirrors the threshold of `resolveSourceHandle` and of the
 * rendering: with one port, the edge anchors on the anonymous handle (and
 * draws); with 2+, on the named handle that exists. `data.to_key` is preserved
 * in both cases.
 */
export function handleDeEntrada(
  edge: { target: string; to_key?: string },
  portasPorNo: Map<string, string[]>,
): string | undefined {
  const portas = portasPorNo.get(edge.target)
  return edge.to_key && portas && portas.length > 1 && portas.includes(edge.to_key)
    ? edge.to_key
    : undefined
}

/** Minimal edge shape the re-anchoring needs to see. */
interface ArestaComHandles {
  source: string
  target: string
  sourceHandle?: string | null
  targetHandle?: string | null
  data?: { from_key?: string; to_key?: string }
}

/**
 * Re-anchors, for ONE node, the edges whose handle was lost on load.
 *
 * `buildEdges` resolves the handle from `to_key`/`from_key` only if the node
 * already declares that port. The SubWorkflow (invoke) node receives its ports
 * from an ASYNCHRONOUS contract (~300 ms after hydration), so on the first mount
 * `handleDeEntrada`/`resolveSourceHandle` return `undefined` and React Flow
 * pins every edge to the first handle — the "everything on the first input"
 * collapse on F5. When the ports arrive, this function returns each edge to its
 * point: `data` preserved `to_key` (input) and `from_key` (output), and now
 * those names match a declared port.
 *
 * Returns the SAME array when nothing changes — an anti-loop protection for
 * callers inside an effect with `setEdges` (same rule as `reconciliarPortas`).
 */
export function reancorarArestasDoNo<E extends ArestaComHandles>(
  edges: E[],
  nodeId: string,
  inputs: string[],
  outputs: string[],
): E[] {
  const nomesEntrada = new Set(inputs)
  const nomesSaida = new Set(outputs)
  let mudou = false
  const proximos = edges.map(e => {
    let ne = e
    // `> 1` for the same reason as `handleDeEntrada`/`resolveSourceHandle`: with a
    // single port, the handle is anonymous (no id) — anchoring on its name would
    // point at a nonexistent id and the edge would vanish. With 2+, the named
    // handle exists.
    if (e.target === nodeId && !e.targetHandle && inputs.length > 1 && e.data?.to_key && nomesEntrada.has(e.data.to_key)) {
      ne = { ...ne, targetHandle: e.data.to_key }
    }
    if (e.source === nodeId && !e.sourceHandle && outputs.length > 1 && e.data?.from_key && nomesSaida.has(e.data.from_key)) {
      ne = { ...ne, sourceHandle: e.data.from_key }
    }
    if (ne !== e) mudou = true
    return ne
  })
  return mudou ? proximos : edges
}

/**
 * What the catalog declares about a node's contract, ready to go into the
 * instance's `data` on the canvas.
 *
 * Exists because `data` is built in TWO places — when opening a saved workflow
 * and when pasting/duplicating a node — each one field by field. A new field
 * forgotten in one of them produces a defect with a bizarre symptom: it works
 * on the freshly created node and disappears on page reload. It happened with
 * `dynamic_inputs` and again with `dynamic_output`; centralizing it here is
 * what prevents a third time.
 */
export function contratoDoNo(
  def: Pick<INodesAPI, "inputs" | "outputs" | "dynamic_inputs" | "dynamic_output" | "outputs_from_ports" | "branches"> | undefined,
  properties: Record<string, unknown> | undefined,
) {
  return {
    inputs: portasDeEntrada(def, properties),
    outputs: portasDeSaida(def, properties),
    dynamic_inputs: def?.dynamic_inputs,
    dynamic_output: def?.dynamic_output,
    outputs_from_ports: def?.outputs_from_ports,
    branches: def?.branches,
    saidas: def?.outputs,
  }
}

/**
 * Output fields of ONE node instance.
 *
 * Most declare them in the catalog (`saidas`, the node's typed `outputs`). The
 * Python Script declares `dynamic_output` and the real outputs are in
 * `output_vars` — the panel always showed "result", the catalog name, even
 * after the person had renamed the variables. And the edge badge offered that
 * same "result" as a key, which the executor does not find.
 *
 * The derivation requires `output_vars`: nodes like ReadGeoJSON also declare
 * `dynamic_output` — in the sense that the data's SHAPE varies — but do not
 * have the property, and for them the catalog applies.
 */
export function saidasDoNo(
  data: {
    dynamic_output?: boolean
    outputs_from_ports?: boolean
    saidas?: { name: string; type?: string; description?: string }[]
    properties?: Record<string, unknown>
  } | undefined,
): { name: string; type?: string; description?: string }[] {
  const bruto = data?.properties?.output_vars
  if (data?.dynamic_output && typeof bruto === "string") {
    const nomes = bruto.split(",").map(v => v.trim()).filter(Boolean)
    if (nomes.length) {
      return [...new Set(nomes)].map(name => ({
        name,
        description: "Variável definida em 'Variável de saída'",
      }))
    }
  }
  // SubWorkflowInput: the outputs ARE the ports declared by the user — the
  // catalog declares [] on purpose. Without this branch, the key picker and
  // the edge badge had no candidates and the edge was born without from_key.
  if (data?.outputs_from_ports) {
    return [...new Set(lerPortas(data?.properties?.ports))].map(name => ({ name }))
  }
  return data?.saidas ?? []
}

/** Minimal node shape the reconciliation needs to see. */
interface NoComPortas {
  data?: {
    dynamic_inputs?: boolean
    outputs_from_ports?: boolean
    properties?: Record<string, unknown>
    inputs?: { name: string }[]
    outputs?: { name: string }[]
  }
}

/** Do the current ports already match the declared list? (by name and order) */
function mesmasPortas(atuais: { name: string }[] | undefined, nomes: string[]): boolean {
  const lista = atuais ?? []
  return lista.length === nomes.length && lista.every((p, i) => p.name === nomes[i])
}

/**
 * Brings `data.inputs`/`data.outputs` back in line with what the `ports`
 * property says, on dynamic-port nodes — `dynamic_inputs` populates the inputs
 * (Python Script, SubWorkflowOutput) and `outputs_from_ports` populates the
 * outputs (SubWorkflowInput). Returns the SAME array when nothing changed.
 *
 * Referential identity is part of the contract, not a detail: the caller is an
 * effect that depends on the nodes' state, and returning a new array on every
 * pass would make it feed itself endlessly.
 */
export function reconciliarPortas<T extends NoComPortas>(nos: T[]): T[] {
  let mudou = false
  const proximos = nos.map(n => {
    const d = n.data
    if (!d?.dynamic_inputs && !d?.outputs_from_ports) return n

    const portas = [...new Set(lerPortas(d.properties?.ports))]
    let proximo = n

    if (d.dynamic_inputs && !mesmasPortas(d.inputs, portas)) {
      proximo = { ...proximo, data: { ...proximo.data, inputs: portas.map(name => ({ name })) } }
    }
    if (d.outputs_from_ports && !mesmasPortas(proximo.data?.outputs, portas)) {
      proximo = { ...proximo, data: { ...proximo.data, outputs: portas.map(name => ({ name })) } }
    }

    if (proximo !== n) mudou = true
    return proximo
  })
  return mudou ? proximos : nos
}
