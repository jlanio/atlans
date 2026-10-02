// web/app/components/workflow/utils/build-canvas.ts
//
// Montagem de um canvas a partir de uma `definition` persistida + o catálogo de
// nós.
//
// A definition guarda só o estado serializável do nó (id, name, properties,
// position); todo o schema — campos, portas, tipo, descrição — vem do catálogo
// `GET /nodes` no momento de abrir. Juntar os dois é o que transforma o JSON do
// banco em algo que o React Flow consegue desenhar.
//
// Puras de propósito: além do editor, o visualizador de sub-fluxo monta o canvas
// de OUTRO workflow (o filho) para pintar o que aconteceu lá dentro. Enquanto
// isto vivia dentro do componente, lendo `workflow`/`nodesAPI` do closure e
// chamando `setNodes`/`setEdges`, não havia como montar um segundo grafo sem
// duplicar a regra — e o `data` montado em dois lugares é exatamente o defeito
// que `contratoDoNo` existe para impedir.
import { Edge } from "@xyflow/react"
import { v4 as uuid } from "uuid"
import { INodeContext } from "@/context/useFlowContext"
import { CanvasDefinition, INodePortAPI, INodesAPI } from "@/service/types"
import { getTypeIcon } from "@/utils/getTypeIconsUtils"
import { contratoDoNo, handleDeEntrada } from "./node-ports"
import { resolveSourceHandle } from "./edge-persistence"

/**
 * Nós do canvas para uma definition.
 *
 * `properties` é reconstruído campo a campo a partir do catálogo — e não copiado
 * da definition — para que um campo novo no schema chegue ao nó já com o default
 * do backend, sem migração de dados.
 */
export function buildNodes(
  definition: CanvasDefinition | undefined,
  nodesAPI: INodesAPI[] | undefined,
): INodeContext[] {
  if (!definition?.nodes?.length || !nodesAPI?.length) return []

  return definition.nodes.map((node, indice) => {
    const nodeApiFound = nodesAPI.find(n => n.name === node.name)
    const properties = {} as Record<string, string>

    nodeApiFound?.properties.forEach(field => {
      properties[field.name] = (node.properties?.[field.name] ?? field.default) as string
    })

    return {
      id: node.id,
      data: {
        // Usa o alias customizado salvo pelo usuário; cai no padrão do schema se não houver
        alias: node.alias ?? nodeApiFound?.alias ?? "",
        description: nodeApiFound?.description ?? "",
        name: node.name,
        fields: nodeApiFound?.properties.map((prop) => ({
          name: prop.name,
          label: prop.label,
          default: prop.default,
          type: prop.type,
          description: prop.description ?? "",
          credential_types: prop.credential_types,
          drive_extensions: prop.drive_extensions,
          options: prop.options,
          visibleWhen: prop.visibleWhen,
          // Sem esta linha o marcador morria AQUI no primeiro reload: o nó
          // recém-arrastado sugeria colunas (o drawer copia o objeto inteiro do
          // catálogo) e o mesmo nó, salvo e recarregado, nunca mais — a
          // projeção descartava o campo e `sugerirColunas()` devolvia [] para
          // sempre. Era o "às vezes funciona" da sugestão de colunas.
          suggest_columns: prop.suggest_columns,
        })) ?? [],
        properties,
        type: nodeApiFound?.type ?? "trigger",
        ...contratoDoNo(nodeApiFound, properties),
      },
      type: getTypeIcon(node),
      position: node.position ?? { x: 0 + (180 * indice), y: 0 },
    } satisfies INodeContext
  })
}

/**
 * Arestas do canvas. Depende dos nós já montados: o handle de origem e o de
 * destino só podem ser resolvidos sabendo quais portas cada nó declara.
 */
export function buildEdges(
  definition: CanvasDefinition | undefined,
  nodes: INodeContext[],
): Edge[] {
  if (!definition?.edges?.length) return []

  const outputsByNodeId = new Map<string, INodePortAPI[]>(
    nodes.map(n => [n.id, (n.data?.outputs ?? []) as INodePortAPI[]]),
  )
  const inputsByNodeId = new Map<string, string[]>(
    nodes.map(n => [n.id, ((n.data?.inputs ?? []) as INodePortAPI[]).map(p => p.name)]),
  )

  return definition.edges.map(edge => ({
    id: uuid(),
    source: edge.source,
    target: edge.target,
    sourceHandle: resolveSourceHandle(edge, outputsByNodeId),
    targetHandle: handleDeEntrada(edge, inputsByNodeId),
    type: "custom",
    data: {
      ...(edge.from_key ? { from_key: edge.from_key } : {}),
      ...(edge.to_key ? { to_key: edge.to_key } : {}),
    },
  } satisfies Edge))
}

export type { CanvasDefinition } from "@/service/types"
