// web/app/components/workflow/utils/valida-conexao.ts
//
// Validação de conexão NO GESTO (A16) — derivada do catálogo, sem segunda
// fonte de verdade. Antes o canvas deixava ligar qualquer porta em qualquer
// porta e o erro só aparecia na validação do servidor; agora a linha proibida
// nem cola (`isValidConnection` do React Flow) e o `onConnect` explica o
// motivo. O servidor segue como juiz final: esta camada só recusa o que
// CERTAMENTE quebraria, nunca o que depende do dado em runtime.
import { Connection, Edge } from "@xyflow/react"
import { INodeOutputField, INodePortAPI } from "@/service/types"
import { limitadoAUmaAresta } from "./resolve-edge-keys"

export type MotivoDeRecusa =
  | "auto-conexao"
  | "duplicada"
  | "destino-de-uma-aresta"
  | "tipo-incompativel"

export const MENSAGEM_DE_RECUSA: Record<MotivoDeRecusa, string> = {
  "auto-conexao": "Um nó não pode ligar nele mesmo.",
  "duplicada": "Essa conexão já existe.",
  "destino-de-uma-aresta":
    "Este nó aceita uma única entrada enquanto não declara portas — declare 2+ portas para receber várias conexões.",
  "tipo-incompativel":
    "A saída escolhida não é uma camada — este nó espera um GeoDataFrame.",
}

/** Forma mínima de nó que a validação precisa enxergar. */
interface NoParaValidar {
  id: string
  data?: {
    name?: string
    branches?: boolean
    saidas?: INodeOutputField[]
    inputs?: INodePortAPI[]
  }
}

const ESCALARES = new Set(["string", "number", "boolean", "list"])

/**
 * Tipo de dado que SAI pelo handle de origem.
 *
 * - Ramo (`branches`): o dado repassado é o primeiro campo (`result`) — vale
 *   o tipo dele, e na dúvida `any`.
 * - Handle nomeado: o tipo do campo homônimo.
 * - Handle anônimo: com um campo só, o tipo dele; com vários, o executor
 *   espalha todos — `any`.
 */
export function tipoEmitido(
  data: NoParaValidar["data"],
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

/** Tipo de dado que o handle de destino ACEITA (`any` quando não declarado). */
export function tipoAceito(
  data: NoParaValidar["data"],
  targetHandle?: string | null,
): string {
  const inputs = data?.inputs ?? []
  if (targetHandle) {
    return inputs.find(p => p.name === targetHandle)?.type ?? "any"
  }
  // Handle anônimo: se TODAS as entradas declaradas exigem o mesmo tipo, ele
  // vale para a conexão anônima também (nós binários com uma porta ligada).
  const tipos = new Set(inputs.map(p => p.type).filter(Boolean))
  return tipos.size === 1 ? (inputs[0].type as string) : "any"
}

/**
 * Recusa uma conexão certamente errada; `null` = permitida.
 *
 * A regra de tipo é deliberadamente conservadora: só recusa escalar
 * (string/number/boolean/list) entrando onde o catálogo exige geodataframe —
 * o `get_input_gdf` do executor falharia com TypeError. `object` e `any`
 * passam: DataInput emite `object` que PODE ser uma camada (depende do
 * arquivo), e vetá-lo quebraria o fluxo mais comum do produto.
 */
export function validarConexao(
  conexao: Pick<Connection, "source" | "target" | "sourceHandle" | "targetHandle">,
  nodes: NoParaValidar[],
  edges: Pick<Edge, "source" | "target" | "sourceHandle" | "targetHandle">[],
): MotivoDeRecusa | null {
  if (conexao.source === conexao.target) return "auto-conexao"

  // O React Flow usa `null` para handle anônimo e o load devolve `undefined`;
  // comparação estrita daria falso negativo (a lição registrada no canvas).
  const mesmoHandle = (a?: string | null, b?: string | null) => (a ?? null) === (b ?? null)
  const repetida = edges.some(e =>
    e.source === conexao.source &&
    e.target === conexao.target &&
    mesmoHandle(e.sourceHandle, conexao.sourceHandle) &&
    mesmoHandle(e.targetHandle, conexao.targetHandle),
  )
  if (repetida) return "duplicada"

  const origem = nodes.find(n => n.id === conexao.source)
  const destino = nodes.find(n => n.id === conexao.target)

  const portasDoDestino = (destino?.data?.inputs ?? []).length
  if (
    limitadoAUmaAresta(destino?.data?.name, portasDoDestino) &&
    edges.some(e => e.target === conexao.target)
  ) {
    return "destino-de-uma-aresta"
  }

  const emitido = tipoEmitido(origem?.data, conexao.sourceHandle)
  const aceito = tipoAceito(destino?.data, conexao.targetHandle)
  if (aceito === "geodataframe" && ESCALARES.has(emitido)) {
    return "tipo-incompativel"
  }

  return null
}
