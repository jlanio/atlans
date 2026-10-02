/**
 * A hidratação das portas dinâmicas dos nós SubWorkflow: o laço buscava um
 * contrato por vez (`for...of await`), um waterfall de N requisições. Passa a
 * coletar os hashes não cacheados e resolvê-los em `Promise.all` — o que se
 * testa aqui é que as buscas partem JUNTAS, antes de qualquer uma resolver.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"

const setNodes = vi.fn()
const setEdges = vi.fn()
vi.mock("@xyflow/react", () => ({
  useReactFlow: () => ({ setNodes, setEdges }),
}))
// `applyPorts` chama `reancorarArestasDoNo` dentro de `setEdges` (um mock que
// não executa o updater) — não roda no teste, mas o import precisa resolver.
vi.mock("@/app/components/workflow/utils/node-ports", () => ({
  reancorarArestasDoNo: (eds: unknown) => eds,
}))
const getContract = vi.fn()
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getWorkflowContract: (...a: unknown[]) => getContract(...a) },
}))

import { useSubWorkflowContractSync } from "@/app/hooks/workflow/useSubWorkflowContractSync"
import type { INodeContext } from "@/context/useFlowContext"

/** Promise segurada na mão, para provar que as buscas partem antes de resolver. */
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

    // O waterfall (`for...of await`) só chamaria a 2a DEPOIS de a 1a resolver;
    // como nenhuma resolveu, ficaria em 1. O `Promise.all` chama as duas de uma vez.
    await waitFor(() => expect(getContract).toHaveBeenCalledTimes(2))
    expect(getContract.mock.calls.map((c) => c[0])).toEqual(["h1", "h2"])

    p1.resolver({ data: null }); p2.resolver({ data: null })
  })
})
