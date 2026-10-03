/**
 * Hydration of the SubWorkflow nodes' dynamic ports: the loop fetched one
 * contract at a time (`for...of await`), a waterfall of N requests. It now
 * collects the uncached hashes and resolves them with `Promise.all` — what's
 * tested here is that the fetches start TOGETHER, before any of them resolves.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"

const setNodes = vi.fn()
const setEdges = vi.fn()
vi.mock("@xyflow/react", () => ({
  useReactFlow: () => ({ setNodes, setEdges }),
}))
// `applyPorts` calls `reancorarArestasDoNo` inside `setEdges` (a mock that
// doesn't run the updater) — it doesn't run in the test, but the import has to resolve.
vi.mock("@/app/components/workflow/utils/node-ports", () => ({
  reancorarArestasDoNo: (eds: unknown) => eds,
}))
const getContract = vi.fn()
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getWorkflowContract: (...a: unknown[]) => getContract(...a) },
}))

import { useSubWorkflowContractSync } from "@/app/hooks/workflow/useSubWorkflowContractSync"
import type { INodeContext } from "@/context/useFlowContext"

/** A promise held by hand, to prove the fetches start before resolving. */
function pendente<T>() {
  let resolver!: (v: T) => void
  const promise = new Promise<T>((res) => { resolver = res })
  return { promise, resolver }
}

const subwf = (id: string, hash: string) =>
  ({ id, data: { name: "SubWorkflow", properties: { workflowHash: hash } } }) as unknown as INodeContext

beforeEach(() => { setNodes.mockReset(); setEdges.mockReset(); getContract.mockReset() })

describe("useSubWorkflowContractSync — busca os contratos em paralelo", () => {
  it("dois hashes disparam as DUAS buscas antes de qualquer uma resolver", async () => {
    const p1 = pendente<{ data: unknown }>()
    const p2 = pendente<{ data: unknown }>()
    getContract.mockReturnValueOnce(p1.promise).mockReturnValueOnce(p2.promise)

    renderHook(() => useSubWorkflowContractSync([subwf("n1", "h1"), subwf("n2", "h2")]))

    // The waterfall (`for...of await`) would only call the 2nd AFTER the 1st
    // resolved; since none resolved, it'd stay at 1. `Promise.all` calls both at once.
    await waitFor(() => expect(getContract).toHaveBeenCalledTimes(2))
    expect(getContract.mock.calls.map((c) => c[0])).toEqual(["h1", "h2"])

    p1.resolver({ data: null }); p2.resolver({ data: null })
  })
})
