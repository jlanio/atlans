// web/app/components/workflow/utils/variaveis-de-saida.ts
//
// What applying a node's configuration does to the edges leaving it, when its
// outputs are the variables the person typed (`dynamic_output` + the
// `output_vars` property — the Python Script).
//
// An edge leaving such a node carries the variable's NAME in `from_key`, and
// at run the executor picks that key from the node's result. Renaming the
// variable in the form kept the edges on the old name: they stayed on the
// canvas, were saved and ran — and delivered nothing (the run panel's "entrada
// vazia"), far from the cause.
//
// Pure, and used in two places on purpose: the form warns BEFORE applying and
// the modal moves the edges ON applying, and both must agree on what changed.
import type { Edge, EdgeReplaceChange } from "@xyflow/react"
import { saidasDoNo } from "./node-ports"
import { sourceHandleDaChave } from "./resolve-edge-keys"

export interface MudancaDeSaidas {
  /** Exactly one name left and exactly one came in: a rename. */
  renomeada: { de: string; para: string } | null
  /** Names that leave with nothing taking their place — every name that left,
   *  when it is not a rename. */
  perdidas: string[]
}

const SEM_MUDANCA: MudancaDeSaidas = { renomeada: null, perdidas: [] }

/**
 * How the output names change when `propriedades` replaces the node's
 * properties.
 *
 * The names come from `saidasDoNo`, the same derivation the edge badge offers
 * as keys — including its fallback to the catalog when `output_vars` is empty.
 * Only `output_vars` counts: a node with `dynamic_output` and no such property
 * (ReadGeoJSON: the SHAPE of its data varies, its output is the catalog's) has
 * nothing a form edit could rename.
 */
export function mudancaDeSaidas(
  data: Parameters<typeof saidasDoNo>[0],
  propriedades: Record<string, unknown> | undefined,
): MudancaDeSaidas {
  if (!data?.dynamic_output || data.properties?.output_vars === propriedades?.output_vars) {
    return SEM_MUDANCA
  }
  const antes = saidasDoNo(data).map(s => s.name)
  const depois = saidasDoNo({ ...data, properties: propriedades }).map(s => s.name)
  const sairam = antes.filter(nome => !depois.includes(nome))
  const entraram = depois.filter(nome => !antes.includes(nome))
  // One for one is the only case where the intent is unambiguous. Two names
  // swapped at once could pair up either way, and guessing would send an edge
  // to the wrong variable — worse than leaving it where the warning points.
  if (sairam.length === 1 && entraram.length === 1) {
    return { renomeada: { de: sairam[0], para: entraram[0] }, perdidas: [] }
  }
  return { renomeada: null, perdidas: sairam }
}

/** The edges leaving `nodeId` that read one of `chaves`. Edges without
 *  `from_key` receive every output (the executor spreads the result) and are
 *  never among them. */
export function arestasQueLeem<E extends Edge>(edges: E[], nodeId: string, chaves: string[]): E[] {
  if (!chaves.length) return []
  return edges.filter(e => e.source === nodeId && chaves.includes(e.data?.from_key as string))
}

/**
 * The changes that move the edges reading `de` over to `para`.
 *
 * Changes, not a new edge list: emitted through React Flow they reach the
 * editor's `onEdgesChange`, which is what records an undo step — the same path
 * as choosing a key on the edge badge. The handle follows the badge's rule too
 * (`sourceHandleDaChave`): a rename is that choice made for every edge that read
 * the old name.
 */
export function trocasDaChaveRenomeada<E extends Edge>(
  edges: E[],
  nodeId: string,
  { de, para }: { de: string; para: string },
  saidas: ReadonlyArray<{ name?: string }> | undefined,
): EdgeReplaceChange<E>[] {
  const handle = sourceHandleDaChave(saidas, para)
  return arestasQueLeem(edges, nodeId, [de]).map(e => ({
    id: e.id,
    type: "replace",
    item: {
      ...e,
      sourceHandle: handle,
      data: { ...e.data, from_key: para },
    },
  }))
}
