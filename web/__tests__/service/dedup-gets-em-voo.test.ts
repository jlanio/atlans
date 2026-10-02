import { describe, it, expect, vi, beforeEach } from "vitest"

// O serviço registra interceptors no import, então o mock do axios precisa
// tê-los; o resto é o mínimo que os helpers get/post/del usam.
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

/** Promise que o teste resolve na mão, para segurar a requisição "em voo". */
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

    // É para isto que a dedup existe: uma requisição só quando dois pontos da
    // tela pedem a mesma lista no mesmo instante.
    expect(get).toHaveBeenCalledTimes(1)
  })

  it("não serve a um leitor pós-escrita a resposta que já estava em voo", async () => {
    // Tick de auto-refresh já em voo quando o admin confirma a exclusão.
    const tick = pendente<{ data: unknown[] }>()
    get.mockReturnValueOnce(tick.promise)
    const emVoo = GisFlowService.getAgents()

    del.mockResolvedValueOnce({ data: {} })
    await GisFlowService.deleteAgent("exec-1")

    // O refetch disparado no sucesso do DELETE precisa ir à rede: reaproveitar
    // a promise anterior devolvia uma lista calculada ANTES da exclusão, e o
    // card excluído reaparecia por até 15s depois do toast "Executor excluído".
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
  // `unpinNodeOutput` e `removeAgentUser` montavam o `axios.delete` à mão em
  // vez de passar por `del()`. O efeito era sutil e exatamente o que a época
  // existe para impedir: como não incrementavam `epocaEscrita`, um GET já em
  // voo continuava elegível para coalescência, e o refetch do sucesso podia
  // receber uma resposta calculada ANTES da exclusão.

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
    // A troca por `del()` cru descartaria o corpo. Nenhum chamador o usa hoje,
    // mas o tipo é público e mudá-lo em silêncio é uma quebra de contrato.
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
