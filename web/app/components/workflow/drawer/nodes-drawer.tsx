import { INodeContext, useFlowContext } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { useMemo } from "react"
import { IconType } from "react-icons"
import { v4 as uuid } from "uuid"
import { Edge, useReactFlow, useStore } from "@xyflow/react"
import { NODE_ICONS } from "@/consts/WorkflowIcons"
import { useLinkNodeParams } from "@/app/hooks/workflow/useLinkNodeParams"
import { INodesAPI } from "@/service/types"
import { TbError404, TbSearch } from "react-icons/tb"
import { getTypeIcon } from "@/utils/getTypeIconsUtils"
import IconDrawer from "./components/icon-drawer"
import { getCandidateKeys, resolveFromKey, portaDeEntradaPadrao } from "../utils/resolve-edge-keys"
import { contratoDoNo } from "../utils/node-ports"
import { estiloDoTipo, nomeDoTipo } from "@/consts/NodeTypeStyles"
import { cn } from "@/lib/utils"

export interface INodesItemsDrawer extends INodesAPI<string> {
  icon: IconType
}

// A cor do tipo NÃO se decide aqui. `TYPE_STYLES` se declara "fonte única de
// verdade" e é o que pinta o card no canvas e o cabeçalho do modal; este arquivo
// mantinha duas tabelas próprias que discordavam dela em QUATRO dos seis tipos —
// trigger era azul aqui e violeta lá, ação âmbar aqui e azul-céu lá. Quem
// clicava num item âmbar recebia um nó azul no canvas.

interface NodesDrawerProps {
  aliasFilter: string
}

const NodesDrawer = ({ aliasFilter }: NodesDrawerProps) => {
  const { flowRef, reactFlowInstance } = useFlowContext()
  const nodesAPI = useWorkflowCatalogStore(s => s.nodesAPI)
  const nodesDrawerState = useWorkflowCatalogStore(s => s.nodesDrawerState)
  const setNodesDrawerState = useWorkflowCatalogStore(s => s.setNodesDrawerState)
  const setNewlyAddedNodeId = useWorkflowCatalogStore(s => s.setNewlyAddedNodeId)
  const { addEdges, addNodes, getNode } = useReactFlow<INodeContext, Edge>()
  const { linkHandleIdParam, linkNodeIdParam, removeLinkNodeParam } = useLinkNodeParams()
  // A lista de nós do canvas só serve para duas perguntas pontuais: "está
  // vazio?" (aqui) e "onde está o nó de onde saiu o +?" (dentro do addNode, via
  // getNode). Assinar `useNodes()` refiltrava o catálogo inteiro a cada quadro
  // de arraste, com o drawer fechado e fora da tela.
  const canvasVazio = useStore(s => s.nodeLookup.size === 0)

  const drawerType = canvasVazio ? "trigger" : nodesDrawerState
  const hasTypeFilter = drawerType !== "closed" && drawerType !== "opened"

  // Derivado, e não estado + efeito: o cálculo é síncrono e o `setItems` só
  // servia para guardá-lo, ao custo de um segundo render do drawer inteiro.
  const items = useMemo<INodesItemsDrawer[]>(() => {
    const filtro = aliasFilter.toLowerCase()
    return (nodesAPI ?? [])
      .filter(item => item.alias.toLowerCase().includes(filtro))
      .filter(item => hasTypeFilter ? item.type === drawerType : true)
      .map(item => ({ ...item, icon: NODE_ICONS[item.name as string] ?? TbError404 })) as INodesItemsDrawer[]
  }, [nodesAPI, aliasFilter, hasTypeFilter, drawerType])

  function addNode(item: INodesItemsDrawer) {
    const viewPort = reactFlowInstance.getViewport()
    const clientWidth = flowRef.current?.clientWidth ?? 0
    const clientHeight = flowRef.current?.clientHeight ?? 0

    let position = {
      x: (clientWidth / 2) - viewPort.x - 80,
      y: (clientHeight / 2) - viewPort.y - 30,
    }

    const nodeFound = linkNodeIdParam ? getNode(linkNodeIdParam) : undefined
    if (nodeFound) {
      position = { x: nodeFound.position.x + 180, y: nodeFound.position.y }
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { icon, properties: fields, ...data } = item
    const properties = {} as Record<string, string>
    fields.forEach(field => {
      const isObject = typeof field.default === "object"
      properties[field.name] = isObject ? field.default as string : field.default as string ?? ""
    })

    const newNode: INodeContext = {
      id: uuid(),
      type: getTypeIcon(item),
      // O contrato vem DEPOIS do spread de `item`: num nó de entradas dinâmicas
      // a lista do catálogo é vazia e quem manda são as portas do usuário.
      data: { ...data, fields, properties, ...contratoDoNo(item, properties) },
      position,
    }

    addNodes(newNode)
    setNodesDrawerState("closed")
    setNewlyAddedNodeId(newNode.id)
    removeLinkNodeParam()

    if (nodeFound) {
      // Sem from_key o executor espalha TODAS as saídas do pai no filho
      // (inputs.update), ignorando a porta de onde o usuário puxou o "+".
      // Mesma regra do arrastar-e-soltar do canvas.
      //
      // `resolveFromKey` devolve undefined quando a escolha é ambígua. O canvas
      // resolvia isso abrindo um seletor; aqui a aresta nascia SEM chave —
      // silenciosamente, e justamente no caso que mais precisava de uma. Agora
      // os dois caminhos usam o primeiro candidato e o badge da aresta permite
      // trocar depois.
      const candidatos = getCandidateKeys(nodeFound.data)
      const from_key = resolveFromKey(linkHandleIdParam, candidatos) ?? candidatos[0]?.name
      // Destino multi-input (Join layerA/layerB): a aresta nasce na PRIMEIRA
      // porta declarada — sem `to_key`, `colunas-conhecidas` indexa pela chave
      // errada e a sugestão por porta fica vazia para sempre; e o executor cai
      // em `inputs[from_key]`. Mesma regra do arrastar-e-soltar
      // (`resolveToKey`), que aqui não tem handle escolhido para consultar.
      const to_key = portaDeEntradaPadrao(newNode.data.inputs)
      const newEdge: Edge = {
        id: uuid(),
        source: nodeFound.id,
        sourceHandle: linkHandleIdParam,
        target: newNode.id,
        // O handle nomeado existe sempre que há 2+ inputs declarados — ancorar
        // a linha nele mantém o visual e o dado (`to_key`) contando a mesma
        // história.
        ...(to_key ? { targetHandle: to_key } : {}),
        type: "custom",
        ...(from_key || to_key
          ? { data: { ...(from_key ? { from_key } : {}), ...(to_key ? { to_key } : {}) } }
          : {}),
      }
      addEdges(newEdge)
    }
  }

  // Determina se deve agrupar (sem filtro de tipo específico e com busca ou sem tipo selecionado)
  const shouldGroup = !hasTypeFilter && aliasFilter !== ""

  // Agrupa por tipo quando buscando sem categoria
  const grouped = shouldGroup
    ? items.reduce<Record<string, INodesItemsDrawer[]>>((acc, item) => {
        const key = item.type as string
        acc[key] = acc[key] ?? []
        acc[key].push(item)
        return acc
      }, {})
    : null

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted-foreground">
        <TbSearch className="h-8 w-8 opacity-30" />
        <p className="text-sm">Nenhum nó encontrado</p>
        {aliasFilter && (
          <p className="text-xs opacity-70">para &ldquo;{aliasFilter}&rdquo;</p>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1 py-2">
      {grouped ? (
        // Modo agrupado (busca global)
        Object.entries(grouped).map(([type, groupItems]) => (
          <div key={type} className="mb-1">
            <div className="flex items-center gap-2 px-4 py-1.5">
              <IconDrawer type={type} fontSize={12} className={estiloDoTipo(type).icon} />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                {nomeDoTipo(type)}
              </span>
              <div className="flex-1 border-t border-border/50" />
            </div>
            {groupItems.map(item => (
              <NodeCard key={item.name} item={item} onAdd={addNode} mostrarTipo={false} />
            ))}
          </div>
        ))
      ) : (
        // Modo plano (categoria selecionada ou canvas vazio)
        items.map(item => (
          <NodeCard key={item.name} item={item} onAdd={addNode} mostrarTipo={!hasTypeFilter} />
        ))
      )}
    </div>
  )
}

/**
 * Um nó do catálogo, pronto para entrar no canvas.
 *
 * O ladrilho do ícone repete `bg`/`icon` do tipo — as mesmas classes que o card
 * do canvas usa — para o item da lista PARECER o nó que ele cria. Antes era um
 * `bg-muted` neutro, e a única pista de tipo era a cor do ícone, que discordava
 * da do canvas.
 */
function NodeCard({ item, onAdd, mostrarTipo }: {
  item: INodesItemsDrawer
  onAdd: (item: INodesItemsDrawer) => void
  /** O selo de tipo só informa quando a lista mistura tipos. Sob um filtro de
   *  categoria todos são iguais, e repeti-lo em cada linha é ruído. */
  mostrarTipo: boolean
}) {
  const estilo = estiloDoTipo(item.type as string)

  return (
    <div
      onClick={() => onAdd(item)}
      className="flex gap-3 mx-2 px-3 py-2.5 cursor-pointer items-start rounded-lg hover:bg-accent transition-colors duration-150 group"
    >
      <div className={cn(
        "min-w-9 min-h-9 flex items-center justify-center rounded-lg shrink-0 border border-border/60 shadow-sm",
        "group-hover:border-border transition-colors duration-150",
        estilo.bg,
      )}>
        <item.icon fontSize={17} className={estilo.icon} />
      </div>
      <div className="flex flex-col gap-0.5 min-w-0 flex-1 pt-0.5">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-medium text-foreground truncate leading-tight">
            {item.alias}
          </h4>
          {/* Presença fixa, e não `hidden group-hover:inline-flex`: aparecer no
              hover mudava a largura disponível para o título, que é truncado —
              passar o mouse encolhia o nome do nó. */}
          {mostrarTipo && item.type && (
            <span className={cn(
              "text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0",
              estilo.bg, estilo.icon,
            )}>
              {nomeDoTipo(item.type as string)}
            </span>
          )}
        </div>
        <p className="text-[12px] text-muted-foreground leading-tight line-clamp-2">
          {item.description ?? "Sem descrição"}
        </p>
      </div>
    </div>
  )
}

export default NodesDrawer
