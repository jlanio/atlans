import { Edge, Node, ReactFlowInstance } from "@xyflow/react";
import { createContext, PropsWithChildren, useContext, useState } from "react";
import { INodes } from "@/service/types";
import { ActionsType, TriggersType, ControlsType } from "../consts/WorkflowIcons";

export type INodeContext = Node<INodes<ActionsType | TriggersType | ControlsType | (string & {})>>

export type StatusWorkflow = "idle" | "queued" | "completed" | "running" | "failed" | "cancelled"

/** `unknown`: the run finished and this node started, but its completion event
 *  never arrived. Every layer on the executor→server→browser path can drop
 *  events (executor queue, server inbox, viewer buffer, rate limit) and the
 *  socket can drop without warning — so "I don't know" is a REAL outcome, and
 *  needs its own representation. Before, that node stayed in `started`
 *  forever, spinning, suggesting work that had already finished. */
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
  /** Columns of each output, as seen in the last run: {key: [column, …]}.
   *  This is what makes it possible to suggest column names instead of
   *  requiring the person to run the workflow just to find out what reaches
   *  the next node. */
  output_columns?: Record<string, string[]> | null
  branch_result?: boolean
  cache_hit?: boolean
  schema_drift?: { missing: string[]; extra: string[] }
}

// Dynamic fields (nodesAPI, credentials, pinnedNodes, nodesDrawerState,
// newlyAddedNodeId) were migrated to useWorkflowCatalogStore (Zustand),
// eliminating cascading re-renders when those fields change.
// The context now holds only immutable refs to ReactFlow/DOM and the reload
// callback. `setFlowContext` here only updates those 3 fields — it is no
// longer a generic setter.
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
