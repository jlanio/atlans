"use client"

import { useEffect, useMemo } from "react"
import { useUpdateNodeInternals } from "@xyflow/react"

import { INodeContext } from "@/context/useFlowContext"

/** Signature of a node's connection points: which ones exist, and in what order. */
function assinaturaDeHandles(n: INodeContext): string {
  const portas = (lista: unknown) =>
    ((lista ?? []) as { name: string }[]).map(p => p.name).join(",")
  return `${n.id}:${portas(n.data?.inputs)}>${portas(n.data?.outputs)}`
}

/**
 * Tells React Flow when a node's connection points change.
 *
 * React Flow MEASURES each node's handles once and keeps positions and ids in
 * an internal registry. Handles added to an already rendered node are drawn by
 * React, but do not enter that registry — and the result is the symptom that
 * does not look like a state bug: the points appear on screen and simply do
 * not accept connections. `updateNodeInternals` forces a re-measure.
 *
 * It applies to ANY source of dynamic ports, not only Script Python's: the
 * sub-workflow contract (`useSubWorkflowContractSync`) changes the same fields
 * and had the same defect, it is just that nobody had run into it. The rule is
 * a single one — the set of handles changed, re-measure — so it lives in a
 * single place.
 *
 * It runs AFTER `data.inputs` has already changed: the dependency is the
 * handles' signature, not the ports'. Measuring before React has put the
 * elements in the DOM would read the node the old way, and the effect would
 * not run again.
 */
export function useHandleRegistrySync(nodes: INodeContext[]) {
  const updateNodeInternals = useUpdateNodeInternals()

  // In the hook body, the scan happened on every canvas render — including per
  // drag frame, and on theme or save-status changes. The canvas hands over a
  // projection that only changes identity when a node enters, leaves or has its
  // `data` replaced, and that is what gives the useMemo here its value.
  const assinatura = useMemo(() => nodes.map(assinaturaDeHandles).join("|"), [nodes])

  useEffect(() => {
    if (!nodes.length) return
    updateNodeInternals(nodes.map(n => n.id))
    // Only the signature: dragging a node changes `nodes` and changes no handle,
    // and re-measuring everything on every frame of a drag would be costly for nothing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assinatura])
}
