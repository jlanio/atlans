"use client"

import { useEffect, useMemo } from "react"
import { useReactFlow, Edge } from "@xyflow/react"

import { INodeContext } from "@/context/useFlowContext"
import { lerPortas, reconciliarPortas } from "@/app/components/workflow/utils/node-ports"

/**
 * Keeps `data.inputs`/`data.outputs` in sync with the `ports` property of
 * dynamic-port nodes — the INPUTS of Script Python / SubWorkflowOutput
 * (`dynamic_inputs`) and the OUTPUTS of SubWorkflowInput (`outputs_from_ports`).
 *
 * Without this the feature would only work after reloading the page: what builds
 * the connection points from `ports` is `loadNodes` (when opening the workflow)
 * and `addNode` (when creating the node), but the config panel's "Aplicar"
 * (apply) writes `data.properties` and does NOT recompute
 * `data.inputs`/`data.outputs`. The person would define the ports, apply, and the
 * node would still have one anonymous point.
 *
 * An effect, and not a patch in `saveNodeConfig`, because `properties` changes
 * through several paths — apply, undo, redo, pasting a node. Covering only one of
 * them would leave the others with the canvas describing a node that is no
 * longer that one.
 *
 * Mirrors `useSubWorkflowContractSync`, including the loop protection: the
 * reconciliation returns the same array when nothing changed, and that is what
 * keeps the effect from feeding itself on every render.
 */
export function useDynamicPortsSync(nodes: INodeContext[]) {
  const { setNodes } = useReactFlow<INodeContext, Edge>()

  // Stable signature for the dep array: it only re-runs when the ports of some
  // dynamic node change, not on every node move on the canvas. Memoized because
  // in the hook body the scan ran on every canvas render — the canvas passes a
  // projection of `nodes` that ignores position changes.
  const assinatura = useMemo(() => nodes
    .filter(n => {
      const d = n.data as { dynamic_inputs?: boolean; outputs_from_ports?: boolean }
      return d?.dynamic_inputs || d?.outputs_from_ports
    })
    .map(n => `${n.id}:${lerPortas((n.data?.properties as Record<string, unknown>)?.ports).join(",")}`)
    .join("|"), [nodes])

  useEffect(() => {
    if (!assinatura) return
    setNodes(reconciliarPortas)
  }, [assinatura, setNodes])
}
