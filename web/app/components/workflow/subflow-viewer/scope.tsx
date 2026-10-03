"use client"
import { createContext, PropsWithChildren, useContext, useMemo } from "react"
import { INodeStatusWorkFlow } from "@/context/useFlowContext"

/** What a node's card needs to know about its execution. */
export type EstadoDeNo = Pick<
  INodeStatusWorkFlow,
  "status" | "error" | "duration" | "cache_hit"
>

/**
 * "This node is being drawn in the sub-workflow viewer, not in the editor."
 *
 * Separate from the execution state on purpose. Whoever reads only this — the
 * node's toolbar, the "+" button for creating a connection — needs a boolean that
 * NEVER changes while the viewer is open. If they read the same context as the
 * state, they would re-render along with it: eight times per second during a live
 * run, for every node, for a constant piece of information.
 */
const SubflowReadOnlyContext = createContext(false)

/** State of each node of the open sub-workflow, indexed by LOCAL id. */
const SubflowStatusContext = createContext<Map<string, EstadoDeNo> | null>(null)

/** true when drawn inside the viewer. Stable for as long as it lasts. */
export function useSubflowReadOnly(): boolean {
  return useContext(SubflowReadOnlyContext)
}

/**
 * Execution state of the sub-workflow's nodes, or `null` outside the viewer.
 *
 * Exists because the source of the state changes with the context. On the editor
 * canvas it is `statusWorkflow.nodes`, which `useExecuteWorkflow` seeds from the
 * canvas's own nodes and then only updates by id — nodes inside a sub-workflow
 * never get in there, because their id arrives prefixed and matches none. What
 * knows those nodes is the panel's timeline, which creates a row for each
 * prefixed id that shows up in the events.
 *
 * The scope delivers the state already resolved, instead of a prefix for the card
 * to apply: that way the card has ONE read point, and the rule of which source
 * applies in which context lives in a single place.
 */
export function useSubflowStatus(): Map<string, EstadoDeNo> | null {
  return useContext(SubflowStatusContext)
}

export function SubflowScope({
  estadoPorId,
  children,
}: PropsWithChildren<{ estadoPorId: Map<string, EstadoDeNo> }>) {
  // The boolean's provider sits outside, with a literal value: its context is
  // never invalidated, so its consumers do not follow the state.
  const status = useMemo(() => estadoPorId, [estadoPorId])
  return (
    <SubflowReadOnlyContext.Provider value={true}>
      <SubflowStatusContext.Provider value={status}>
        {children}
      </SubflowStatusContext.Provider>
    </SubflowReadOnlyContext.Provider>
  )
}
