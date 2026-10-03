import { describe, it, expect, vi, beforeEach } from "vitest"

// The service registers interceptors on import, so the axios mock needs to
// have them; the rest is the minimum the get/post/del helpers use.
const { get, post, del } = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), del: vi.fn(),
}))
vi.mock("axios", () => ({
  default: {
    get, post, delete: del, put: vi.fn(), patch: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

import { GisFlowService } from "@/service/GisFlowService"

/** A promise the test resolves by hand, to hold the request "in flight". */
function pendente<T>() {
  let resolver!: (v: T) => void
  const promise = new Promise<T>(res => { resolver = res })
  return { promise, resolver }
}

beforeEach(() => { get.mockReset(); post.mockReset(); del.mockReset() })

describe("dedup de GETs em voo", () => {
  it("coalesce dois leitores simultâneos da mesma URL", async () => {
    const p = pendente<{ data: unknown[] }>()
    get.mockReturnValue(p.promise)

    const a = GisFlowService.getAgents()
    const b = GisFlowService.getAgents()
    p.resolver({ data: [] })
    await Promise.all([a, b])

    // This is what dedup exists for: a single request when two spots on the
    // screen ask for the same list at the same instant.
    expect(get).toHaveBeenCalledTimes(1)
  })

  it("não serve a um leitor pós-escrita a resposta que já estava em voo", async () => {
    // An auto-refresh tick already in flight when the admin confirms the deletion.
    const tick = pendente<{ data: unknown[] }>()
    get.mockReturnValueOnce(tick.promise)
    const emVoo = GisFlowService.getAgents()

    del.mockResolvedValueOnce({ data: {} })
    await GisFlowService.deleteAgent("exec-1")

    // The refetch fired on the DELETE's success needs to go to the network:
    // reusing the previous promise returned a list computed BEFORE the deletion,
    // and the deleted card reappeared for up to 15s after the "Executor excluído"
    // (executor deleted) toast.
    const depois = pendente<{ data: unknown[] }>()
    get.mockReturnValueOnce(depois.promise)
    const releitura = GisFlowService.getAgents()

    expect(get).toHaveBeenCalledTimes(2)

    tick.resolver({ data: [{ id_hash: "exec-1" }] })
    depois.resolver({ data: [] })
    const [antes, agora] = await Promise.all([emVoo, releitura])
    expect(antes.data).toHaveLength(1)
    expect(agora.data).toHaveLength(0)
  })

  it("um GET disparado DURANTE a escrita também não é reaproveitado depois dela", async () => {
    const escrita = pendente<{ data: unknown }>()
    post.mockReturnValueOnce(escrita.promise)
    const mutacao = GisFlowService.duplicateWorkflowById("wf-1")

    const durante = pendente<{ data: unknown[] }>()
    get.mockReturnValueOnce(durante.promise)
    GisFlowService.getWorkflows("ws-1")

    escrita.resolver({ data: { id_hash: "wf-2" } })
    await mutacao

    const depois = pendente<{ data: unknown[] }>()
    get.mockReturnValueOnce(depois.promise)
    GisFlowService.getWorkflows("ws-1")

    expect(get).toHaveBeenCalledTimes(2)
    durante.resolver({ data: [] })
    depois.resolver({ data: [] })
  })
})

describe("mutações que burlavam a época de escrita", () => {
  // `unpinNodeOutput` and `removeAgentUser` built `axios.delete` by hand
  // instead of going through `del()`. The effect was subtle and exactly what
  // the epoch exists to prevent: since they didn't increment `epocaEscrita`, a
  // GET already in flight stayed eligible for coalescing, and the success
  // refetch could receive a response computed BEFORE the deletion.

  it("unpinNodeOutput invalida GETs em voo", async () => {
    const tick = pendente<{ data: unknown[] }>()
    get.mockReturnValueOnce(tick.promise)
    GisFlowService.getAgents()

    del.mockResolvedValueOnce({ data: { unpinned: "n1", total_pinned: 0 } })
    await GisFlowService.unpinNodeOutput("wf-1", "n1")

    const depois = pendente<{ data: unknown[] }>()
    get.mockReturnValueOnce(depois.promise)
    GisFlowService.getAgents()

    expect(get).toHaveBeenCalledTimes(2)
    tick.resolver({ data: [] }); depois.resolver({ data: [] })
  })

  it("unpinNodeOutput continua devolvendo o payload tipado", async () => {
    // Swapping for a raw `del()` would discard the body. No caller uses it
    // today, but the type is public and changing it silently is a contract break.
    del.mockResolvedValueOnce({ data: { unpinned: "n1", total_pinned: 2 } })
    const res = await GisFlowService.unpinNodeOutput("wf-1", "n1")
    expect(res.data).toEqual({ unpinned: "n1", total_pinned: 2 })
  })

  it("unpinNodeOutput devolve erro em vez de lançar", async () => {
    del.mockRejectedValueOnce({ response: { status: 403, data: { detail: "sem permissão" } } })
    const res = await GisFlowService.unpinNodeOutput("wf-1", "n1")
    expect(res.error?.message).toBe("sem permissão")
  })

  it("removeAgentUser invalida GETs em voo", async () => {
    const tick = pendente<{ data: unknown[] }>()
    get.mockReturnValueOnce(tick.promise)
    GisFlowService.getAgents()

    del.mockResolvedValueOnce({ data: {} })
    await GisFlowService.removeAgentUser("exec-1", "user-1")

    const depois = pendente<{ data: unknown[] }>()
    get.mockReturnValueOnce(depois.promise)
    GisFlowService.getAgents()

    expect(get).toHaveBeenCalledTimes(2)
    tick.resolver({ data: [] }); depois.resolver({ data: [] })
  })

  it("removeAgentUser devolve erro em vez de lançar", async () => {
    del.mockRejectedValueOnce({ response: { status: 500, data: { detail: "boom" } } })
    const res = await GisFlowService.removeAgentUser("exec-1", "user-1")
    expect(res.error?.message).toBe("boom")
  })
})
