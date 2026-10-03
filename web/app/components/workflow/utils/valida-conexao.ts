// web/app/components/workflow/utils/valida-conexao.ts
//
// Connection validation AT THE GESTURE (A16) — derived from the catalog, with
// no second source of truth. Before, the canvas let any port be connected to
// any port and the error only showed up in the server's validation; now the
// forbidden line does not even stick (React Flow's `isValidConnection`) and
// `onConnect` explains why. The server remains the final judge: this layer
// only rejects what would CERTAINLY break, never what depends on runtime data.
import { Connection, Edge } from "@xyflow/react"
import { INodeOutputField, INodePortAPI } from "@/service/types"
import { limitadoAUmaAresta } from "./resolve-edge-keys"

export type RejectionReason =
  | "auto-conexao"
  | "duplicada"
  | "destino-de-uma-aresta"
  | "tipo-incompativel"

export const REJECTION_MESSAGE: Record<RejectionReason, string> = {
  "auto-conexao": "Um nó não pode ligar nele mesmo.",
  "duplicada": "Essa conexão já existe.",
  "destino-de-uma-aresta":
    "Este nó aceita uma única entrada enquanto não declara portas — declare 2+ portas para receber várias conexões.",
  "tipo-incompativel":
    "A saída escolhida não é uma camada — este nó espera um GeoDataFrame.",
}

/** Minimal node shape the validation needs to see. */
interface NodeToValidate {
  id: string
  data?: {
    name?: string
    branches?: boolean
    saidas?: INodeOutputField[]
    inputs?: INodePortAPI[]
  }
}

const SCALARS = new Set(["string", "number", "boolean", "list"])

/**
 * Data type that LEAVES through the source handle.
 *
 * - Branch (`branches`): the data passed on is the first field (`result`) — its
 *   type applies, and when in doubt `any`.
 * - Named handle: the type of the field with the same name.
 * - Anonymous handle: with a single field, its type; with several, the executor
 *   spreads them all — `any`.
 */
export function tipoEmitido(
  data: NodeToValidate["data"],
  sourceHandle?: string | null,
): string {
  const saidas = data?.saidas ?? []
  if (data?.branches) return saidas[0]?.type ?? "any"
  if (sourceHandle) {
    const campo = saidas.find(c => c.name === sourceHandle)
    if (campo) return campo.type ?? "any"
    return "any"
  }
  if (saidas.length === 1) return saidas[0].type ?? "any"
  return "any"
}

/** Data type the target handle ACCEPTS (`any` when not declared). */
export function tipoAceito(
  data: NodeToValidate["data"],
  targetHandle?: string | null,
): string {
  const inputs = data?.inputs ?? []
  if (targetHandle) {
    return inputs.find(p => p.name === targetHandle)?.type ?? "any"
  }
  // Anonymous handle: if ALL declared inputs require the same type, it applies
  // to the anonymous connection too (binary nodes with one port connected).
  const tipos = new Set(inputs.map(p => p.type).filter(Boolean))
  return tipos.size === 1 ? (inputs[0].type as string) : "any"
}

/**
 * Rejects a certainly wrong connection; `null` = allowed.
 *
 * The type rule is deliberately conservative: it only rejects a scalar
 * (string/number/boolean/list) going where the catalog requires a geodataframe —
 * the executor's `get_input_gdf` would fail with a TypeError. `object` and `any`
 * pass: DataInput emits `object`, which MAY be a layer (it depends on the
 * file), and vetoing it would break the product's most common workflow.
 */
export function validarConexao(
  conexao: Pick<Connection, "source" | "target" | "sourceHandle" | "targetHandle">,
  nodes: NodeToValidate[],
  edges: Pick<Edge, "source" | "target" | "sourceHandle" | "targetHandle">[],
): RejectionReason | null {
  if (conexao.source === conexao.target) return "auto-conexao"

  // React Flow uses `null` for an anonymous handle and the load returns
  // `undefined`; strict comparison would give a false negative (the lesson
  // recorded in the canvas).
  const sameHandle = (a?: string | null, b?: string | null) => (a ?? null) === (b ?? null)
  const repetida = edges.some(e =>
    e.source === conexao.source &&
    e.target === conexao.target &&
    sameHandle(e.sourceHandle, conexao.sourceHandle) &&
    sameHandle(e.targetHandle, conexao.targetHandle),
  )
  if (repetida) return "duplicada"

  const origem = nodes.find(n => n.id === conexao.source)
  const destino = nodes.find(n => n.id === conexao.target)

  const targetPortCount = (destino?.data?.inputs ?? []).length
  if (
    limitadoAUmaAresta(destino?.data?.name, targetPortCount) &&
    edges.some(e => e.target === conexao.target)
  ) {
    return "destino-de-uma-aresta"
  }

  const emitido = tipoEmitido(origem?.data, conexao.sourceHandle)
  const aceito = tipoAceito(destino?.data, conexao.targetHandle)
  if (aceito === "geodataframe" && SCALARS.has(emitido)) {
    return "tipo-incompativel"
  }

  return null
}
