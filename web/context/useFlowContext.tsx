import { Edge, Node, ReactFlowInstance } from "@xyflow/react";
import { createContext, PropsWithChildren, useContext, useState } from "react";
import { INodes } from "@/service/types";
import { ActionsType, TriggersType, ControlsType } from "../consts/WorkflowIcons";

export type INodeContext = Node<INodes<ActionsType | TriggersType | ControlsType | (string & {})>>

export type StatusWorkflow = "idle" | "queued" | "completed" | "running" | "failed" | "cancelled"

/** `unknown`: o run terminou e este nó começou, mas o evento de término dele
 *  nunca chegou. Todas as camadas do caminho executor→servidor→browser podem
 *  descartar evento (fila do executor, inbox do servidor, buffer do espectador,
 *  rate limit) e o socket pode cair sem aviso — então "não sei" é um desfecho
 *  REAL, e precisa de representação própria. Antes esse nó ficava em `started`
 *  para sempre, girando, sugerindo um trabalho que já tinha acabado. */
export type StatusNodeStatusWorkFlow = "idle" | "started" | "completed" | "failed" | "unknown"
export interface IStatusWorkflow {
  status: StatusWorkflow
  task_id?: string
  nodes: INodeStatusWorkFlow[]
  paramsSchema?: Record<string, { type: string; description?: string; default?: unknown; required?: boolean }>
}

export interface INodeStatusWorkFlow extends Node{
  id: string
  status: StatusNodeStatusWorkFlow
  error?: string
  duration?: number
  output_keys?: string[]
  /** Colunas de cada saída, vistas na última execução: {chave: [coluna, …]}.
   *  É o que permite sugerir nomes de coluna em vez de exigir que a pessoa
   *  execute o fluxo só para descobrir o que chega no próximo nó. */
  output_columns?: Record<string, string[]> | null
  branch_result?: boolean
  cache_hit?: boolean
  schema_drift?: { missing: string[]; extra: string[] }
}

// Campos dinâmicos (nodesAPI, credentials, pinnedNodes, nodesDrawerState,
// newlyAddedNodeId) foram migrados para useWorkflowCatalogStore (Zustand),
// eliminando re-renders em cascata quando esses campos mudam.
// O contexto agora guarda apenas refs imutáveis ao ReactFlow/DOM e o callback
// de reload. `setFlowContext` aqui só atualiza esses 3 campos — não é mais
// um setter genérico.
interface IFlowContext {
  reactFlowInstance: ReactFlowInstance<Node, Edge>
  flowRef: React.RefObject<HTMLDivElement | null>
  reloadWorkflow?: () => Promise<void>
  setFlowContext: (patch: Partial<Omit<IFlowContext, "setFlowContext">>) => void
}

const FlowContext = createContext<IFlowContext>({} as IFlowContext)

export const useFlowContext = () => useContext(FlowContext);

export const FlowContextProvider = ({ children }: PropsWithChildren) => {
  const [data, setData] = useState<Omit<IFlowContext, "setFlowContext">>({} as IFlowContext);

  const setFlowContext: IFlowContext["setFlowContext"] = (patch) => {
    setData(prev => ({ ...prev, ...patch }))
  }

  return (
    <FlowContext.Provider value={{ ...data, setFlowContext }}>
      {children}
    </FlowContext.Provider>
  )
};
