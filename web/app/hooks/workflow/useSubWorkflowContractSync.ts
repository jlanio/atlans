"use client"

import { useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react"
import type { Edge } from "@xyflow/react"
import { INodeContext } from "@/context/useFlowContext"
import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkflowContract } from "@/service/types"
import { reancorarArestasDoNo } from "@/app/components/workflow/utils/node-ports"


const DEBOUNCE_MS = 300

/** The port names on one side of a node, in order. */
const nomesDasPortas = (portas: unknown) =>
  ((portas ?? []) as { name: string }[]).map((p) => p.name).join(",")

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
 *
 * The setters are the canvas STATE's (`useNodesState`/`useEdgesState`), not
 * React Flow's. The ports are derived from the child, not edited, and through
 * React Flow they became changes, which the editor records as undo steps:
 * opening a workflow left a step nobody took (re-anchoring the edges), and
 * putting the ports back after an undo would record one that throws the redo
 * away — after an assistant drawing, Ctrl+Z would land on the drawing without
 * ports, get them back as a new step, and never get past it.
 */
export function useSubWorkflowContractSync(
  nodes: INodeContext[],
  setNodes: Dispatch<SetStateAction<INodeContext[]>>,
  setEdges: Dispatch<SetStateAction<Edge[]>>,
) {
  const cacheRef = useRef<Map<string, IWorkflowContract | null>>(new Map())
  // The request for each hash still on its way. A later round waits for it:
  // "not cached yet" is not "no contract" — read as such, it gave the node empty
  // ports, and the round that would have applied the answer had been cancelled.
  const inflightRef = useRef<Map<string, Promise<void>>>(new Map())

  // Stable key for the dep array: changes when a SubWorkflow enters or leaves,
  // when its workflowHash is edited — and when its ports change. Restoring a
  // version, an assistant drawing and undoing back to the canvas as it opened
  // rebuild the nodes from a definition, which carries no ports; keyed on the
  // hashes alone, nothing ran again, and the node stayed portless for the rest
  // of the session with its edges collapsed onto one point. Memoized because in
  // the hook body the scan ran on every canvas render — the canvas passes a
  // projection of `nodes` that ignores position changes.
  const subworkflowSignature = useMemo(() => nodes
    .filter((n) => (n.data as { name?: string })?.name === "SubWorkflow")
    .map((n) => `${n.id}:${((n.data?.properties ?? {}) as { workflowHash?: string }).workflowHash ?? ""}`
      + `:${nomesDasPortas(n.data?.inputs)}>${nomesDasPortas(n.data?.outputs)}`)
    .join("|"), [nodes])

  // Debounce: an operator typing a hash character by character should not
  // fire one request per keystroke. Waits for 300ms of inactivity.
  //
  // It counts rounds instead of holding the signature: ports applied and lost
  // again within the window bring the signature back to the previous round's,
  // a state holding that string would not change, and the round would not run.
  // Applying the ports changes the signature too, which costs one more round —
  // it finds them in place and changes nothing.
  const [rodada, setRodada] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setRodada((r) => r + 1), DEBOUNCE_MS)
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
      // Fetches the contracts in PARALLEL: every request starts before any is
      // awaited. Before, it was one `await` per node inside the loop — a
      // waterfall of N requests, each waiting for the previous one. Each node
      // then waits for ITS contract only — one a previous round left on its way
      // included — so one slow child does not hold back the other SubWorkflows'
      // ports. Order across nodes does not matter (each applyPorts targets a
      // disjoint id and is idempotent).
      await Promise.all(subworkflowNodes.map(async (node) => {
        const hash = hashDoNo(node)
        if (hash && cacheRef.current.get(hash) === undefined) {
          await (inflightRef.current.get(hash) ?? buscarContrato(hash))
          if (cancelled) return
        }
        // No hash: clears dynamic ports. Any other hash is cached by now.
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
      }))
    }

    function buscarContrato(hash: string): Promise<void> {
      const busca = (async () => {
        try {
          const resp = await GisFlowService.getWorkflowContract(hash)
          cacheRef.current.set(hash, resp?.data ?? null)
        } catch {
          cacheRef.current.set(hash, null)
        } finally {
          inflightRef.current.delete(hash)
        }
      })()
      inflightRef.current.set(hash, busca)
      return busca
    }

    function applyPorts(
      nodeId: string,
      inputs: { name: string; description?: string }[],
      outputs: { name: string; description?: string }[],
    ) {
      setNodes((nds) => {
        let mudou = false
        const proximos = nds.map((n) => {
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
          mudou = true
          return {
            ...n,
            data: { ...n.data, inputs, outputs },
          }
        })
        // The SAME array when nothing changed: this is the canvas state itself,
        // and a new one would re-render the whole editor for nothing.
        return mudou ? proximos : nds
      })

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
    // Re-runs only once the signature has settled — the operator stopped typing
    // for DEBOUNCE_MS.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rodada])
}
