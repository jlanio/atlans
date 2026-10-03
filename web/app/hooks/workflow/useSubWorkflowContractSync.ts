"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useReactFlow, Edge } from "@xyflow/react"
import { INodeContext } from "@/context/useFlowContext"
import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkflowContract } from "@/service/types"
import { reancorarArestasDoNo } from "@/app/components/workflow/utils/node-ports"


const DEBOUNCE_MS = 300

/**
 * Syncs the dynamic ports (inputs/outputs) of SubWorkflow nodes with the
 * contract declared by the target workflow (SubWorkflowInput + SubWorkflowOutput).
 *
 * Why: the /nodes catalog has no way to predict the keys of each
 * sub-workflow. We render dynamic handles on the canvas by fetching the contract
 * by the workflowHash configured in each SubWorkflow node.
 *
 * Anti-loop strategy:
 *   - in-memory cache per hash (avoids re-fetching between re-renders)
 *   - comparison of current vs new ports before setNodes (avoids an
 *     unnecessary ReactFlow re-render)
 */
export function useSubWorkflowContractSync(nodes: INodeContext[]) {
  const { setNodes, setEdges } = useReactFlow<INodeContext, Edge>()
  const cacheRef = useRef<Map<string, IWorkflowContract | null>>(new Map())
  const inflightRef = useRef<Set<string>>(new Set())

  // Stable key for the dep array: re-runs only when hashes change
  // (add/remove of a SubWorkflow or an edit of workflowHash). Memoized because in
  // the hook body the scan ran on every canvas render — the canvas passes a
  // projection of `nodes` that ignores position changes.
  const subworkflowSignature = useMemo(() => nodes
    .filter((n) => (n.data as { name?: string })?.name === "SubWorkflow")
    .map((n) => `${n.id}:${((n.data?.properties ?? {}) as { workflowHash?: string }).workflowHash ?? ""}`)
    .join("|"), [nodes])

  // Debounce: an operator typing a hash character by character should not
  // fire one request per keystroke. Waits for 300ms of inactivity.
  const [debouncedSignature, setDebouncedSignature] = useState(subworkflowSignature)
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSignature(subworkflowSignature), DEBOUNCE_MS)
    return () => clearTimeout(t)
  }, [subworkflowSignature])

  useEffect(() => {
    const subworkflowNodes = nodes.filter(
      (n) => (n.data as { name?: string })?.name === "SubWorkflow",
    )
    if (subworkflowNodes.length === 0) return

    let cancelled = false

    const hashDoNo = (node: INodeContext) =>
      String(((node.data?.properties ?? {}) as Record<string, unknown>).workflowHash ?? "").trim()

    async function syncAll() {
      // Fetches the contracts in PARALLEL. Before, it was one `await` per node inside
      // the loop — a waterfall of N requests, each waiting for the previous one.
      // Collects the hashes not yet cached nor in flight, marks them in flight, and
      // resolves them all together; only then applies the ports per node, reading
      // the cache. Order across nodes does not matter (each applyPorts targets a
      // disjoint id and is idempotent).
      const toFetch = new Set<string>()
      for (const node of subworkflowNodes) {
        const hash = hashDoNo(node)
        if (hash && cacheRef.current.get(hash) === undefined && !inflightRef.current.has(hash)) {
          toFetch.add(hash)
        }
      }

      if (toFetch.size > 0) {
        await Promise.all(
          [...toFetch].map(async (hash) => {
            inflightRef.current.add(hash)
            try {
              const resp = await GisFlowService.getWorkflowContract(hash)
              cacheRef.current.set(hash, resp?.data ?? null)
            } catch {
              cacheRef.current.set(hash, null)
            } finally {
              inflightRef.current.delete(hash)
            }
          }),
        )
        if (cancelled) return
      }

      for (const node of subworkflowNodes) {
        const hash = hashDoNo(node)
        // No hash: clears dynamic ports. A hash in flight from a previous round
        // (not cached yet): `?? null` applies empty ports, as before.
        const contract = hash ? (cacheRef.current.get(hash) ?? null) : null
        const inputs = (contract?.inputs ?? []).map((p) => ({
          name: p.name,
          description: p.description ?? undefined,
        }))
        const outputs = (contract?.outputs ?? []).map((p) => ({
          name: p.name,
          description: p.description ?? undefined,
        }))
        applyPorts(node.id, inputs, outputs)
      }
    }

    function applyPorts(
      nodeId: string,
      inputs: { name: string; description?: string }[],
      outputs: { name: string; description?: string }[],
    ) {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id !== nodeId) return n
          const currentInputs = (n.data?.inputs ?? []) as { name: string }[]
          const currentOutputs = (n.data?.outputs ?? []) as { name: string }[]
          const sameInputs =
            currentInputs.length === inputs.length &&
            currentInputs.every((p, i) => p.name === inputs[i]?.name)
          const sameOutputs =
            currentOutputs.length === outputs.length &&
            currentOutputs.every((p, i) => p.name === outputs[i]?.name)
          if (sameInputs && sameOutputs) return n
          return {
            ...n,
            data: { ...n.data, inputs, outputs },
          }
        }),
      )

      // Re-anchors the edges whose handle was lost on load, now that the contract's
      // ports have arrived — fixes the "everything on the first input" collapse on
      // F5. The logic is pure (`reancorarArestasDoNo`) and idempotent: it returns
      // the SAME array when nothing changes, so as not to feed back into `useEdgesState`.
      setEdges((eds) =>
        reancorarArestasDoNo(
          eds,
          nodeId,
          inputs.map((p) => p.name),
          outputs.map((p) => p.name),
        ),
      )
    }

    syncAll()

    return () => {
      cancelled = true
    }
    // Re-runs only when the debounced signature changes — the operator stopped
    // typing for DEBOUNCE_MS.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSignature])
}
