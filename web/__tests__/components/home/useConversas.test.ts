import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"
import type { IConversaResumo } from "@/service/types"

/**
 * The hook for the "Recentes" (the Home's Chats list): the list mirrors the server
 * without F5 (the stream announcement), renaming moves up, and the reload preserves the
 * depth that "Ver mais" already loaded — the server ceiling is 100 and
 * SILENT (asking for more returns 100 without an error).
 */
const servico = vi.hoisted(() => ({
  listarConversas: vi.fn(), renomearConversa: vi.fn(), apagarConversa: vi.fn(),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

import { useConversas, comAnuncio } from "@/app/hooks/home/useConversas"

const linha = (id: string, extra: Partial<IConversaResumo> = {}): IConversaResumo => ({
  id, titulo: `Conversa ${id}`, workflow_id: null, tokens_total: 0,
  created_at: "2026-09-10T12:00:00Z", updated_at: "2026-09-10T12:00:00Z", ...extra,
})
const ok = (itens: IConversaResumo[], total: number) => ({ success: true, status: 200, data: { itens, total } })
const falhou = (status = 500, message = "Erro inesperado.") => ({ success: false, status, error: { message }, data: undefined })

/** A server with `n` conversations, c0 the most recent, paginated like the API (ceiling 100). */
function servidorCom(n: number) {
  const todas = Array.from({ length: n }, (_, i) => linha(`c${i}`))
  servico.listarConversas.mockImplementation(async (limit: number, offset = 0) =>
    ok(todas.slice(offset, offset + Math.min(limit, 100)), n),
  )
  return todas
}

/** The service calls as `[limit, offset]` (the 1st page omits the offset). */
const chamadas = () => servico.listarConversas.mock.calls.map((c) => [c[0], c[1] ?? 0])

beforeEach(() => {
  servico.listarConversas.mockReset()
  servico.renomearConversa.mockReset()
  servico.apagarConversa.mockReset()
})

async function montar() {
  const r = renderHook(() => useConversas())
  await waitFor(() => expect(r.result.current.carregando).toBe(false))
  return r
}

describe("comAnuncio — a lista que o servidor devolveria, sem ir buscar", () => {
  const lista = [linha("a"), linha("b"), linha("c")]
  const agora = "2026-09-19T07:00:00.000Z"

  it("a conversa que já está na lista sobe ao topo, sem duplicar, com o título do anúncio", () => {
    const r = comAnuncio(lista, { id: "c", titulo: "Novo título", nova: false }, agora)
    expect(r.inseriu).toBe(false)
    expect(r.lista.map((c) => c.id)).toEqual(["c", "a", "b"])
    expect(r.lista[0]).toMatchObject({ titulo: "Novo título", updated_at: agora, tokens_total: 0 })
  })

  it("sem título no anúncio, a existente sobe e mantém o título que tinha", () => {
    const r = comAnuncio(lista, { id: "b", nova: false }, agora)
    expect(r.lista.map((c) => c.id)).toEqual(["b", "a", "c"])
    expect(r.lista[0].titulo).toBe("Conversa b")
  })

  it("a conversa ausente com título entra no topo como linha nova", () => {
    const r = comAnuncio(lista, { id: "z", titulo: "Focos", nova: true }, agora)
    expect(r.inseriu).toBe(true)
    expect(r.lista.map((c) => c.id)).toEqual(["z", "a", "b", "c"])
    expect(r.lista[0]).toEqual({
      id: "z", titulo: "Focos", workflow_id: null, tokens_total: 0, created_at: agora, updated_at: agora,
    })
  })

  it("ausente e SEM título (a confirmação aceita só sabe o id) não inventa 'Sem título'", () => {
    const r = comAnuncio(lista, { id: "z", nova: false }, agora)
    expect(r.inseriu).toBe(false)
    expect(r.lista).toBe(lista)
  })

  it("é idempotente: o mesmo anúncio duas vezes não duplica", () => {
    const uma = comAnuncio(lista, { id: "z", titulo: "Focos", nova: true }, agora).lista
    const duas = comAnuncio(uma, { id: "z", titulo: "Focos", nova: true }, agora)
    expect(duas.inseriu).toBe(false)
    expect(duas.lista.map((c) => c.id)).toEqual(["z", "a", "b", "c"])
  })
})

describe("useConversas — o anúncio do stream", () => {
  it("a conversa nova entra no topo e o total sobe 1 — sem rede", async () => {
    servidorCom(2)
    const { result } = await montar()
    act(() => { result.current.anunciar({ id: "c9", titulo: "Focos em Rondônia", nova: true }) })
    expect(result.current.conversas.map((c) => c.id)).toEqual(["c9", "c0", "c1"])
    expect(result.current.conversas[0].titulo).toBe("Focos em Rondônia")
    expect(result.current.total).toBe(3)
    expect(servico.listarConversas).toHaveBeenCalledTimes(1)
  })

  it("a conversa existente sobe; o total não muda", async () => {
    servidorCom(3)
    const { result } = await montar()
    act(() => { result.current.anunciar({ id: "c2", titulo: "Conversa c2", nova: false }) })
    expect(result.current.conversas.map((c) => c.id)).toEqual(["c2", "c0", "c1"])
    expect(result.current.total).toBe(3)
  })

  it("um anúncio 'nova' de conversa que a carga já trouxe não soma ao total", async () => {
    servidorCom(2)
    const { result } = await montar()
    act(() => { result.current.anunciar({ id: "c1", titulo: "Conversa c1", nova: true }) })
    expect(result.current.conversas).toHaveLength(2)
    expect(result.current.total).toBe(2)
  })

  it("renomear troca o título E sobe a linha — o servidor carimba updated_at no PATCH", async () => {
    servidorCom(3)
    servico.renomearConversa.mockResolvedValue({ success: true, status: 200, data: {} })
    const { result } = await montar()
    let r: { ok: boolean } | undefined
    await act(async () => { r = await result.current.renomear("c2", "Renomeada") })
    expect(r?.ok).toBe(true)
    expect(result.current.conversas.map((c) => c.id)).toEqual(["c2", "c0", "c1"])
    expect(result.current.conversas[0].titulo).toBe("Renomeada")
  })

  it("apagar remove a linha e desconta o total", async () => {
    servidorCom(3)
    servico.apagarConversa.mockResolvedValue({ success: true, status: 204 })
    const { result } = await montar()
    await act(async () => { await result.current.apagar("c1") })
    expect(result.current.conversas.map((c) => c.id)).toEqual(["c0", "c2"])
    expect(result.current.total).toBe(2)
  })
})

describe("useConversas — a recarga preserva a profundidade", () => {
  /** 237 conversations: 3 pages (100, 100, 37) after two "Ver mais". */
  async function comTresPaginas() {
    servidorCom(237)
    const r = await montar()
    expect(r.result.current.conversas).toHaveLength(100)
    expect(chamadas()).toEqual([[100, 0]])
    await act(async () => { r.result.current.carregarMais() })
    await waitFor(() => expect(r.result.current.conversas).toHaveLength(200))
    await act(async () => { r.result.current.carregarMais() })
    await waitFor(() => expect(r.result.current.conversas).toHaveLength(237))
    servico.listarConversas.mockClear()
    return r
  }

  it("a 1ª carga custa um GET só", async () => {
    servidorCom(5)
    await montar()
    expect(chamadas()).toEqual([[100, 0]])
  })

  it("recarregar relê as três páginas (não só a primeira) e mantém as 237 linhas", async () => {
    // The defect: `recarregar` was always the 1st page and REPLACED the list —
    // after "Ver mais", "Tentar de novo" took the list back to 100.
    const { result } = await comTresPaginas()
    await act(async () => { result.current.recarregar() })
    await waitFor(() => expect(result.current.atualizando).toBe(false))
    expect(chamadas()).toEqual([[100, 0], [100, 100], [100, 200]])
    expect(result.current.conversas).toHaveLength(237)
    expect(result.current.total).toBe(237)
  })

  it("uma página ruim deixa a lista como estava, com o erro no rodapé", async () => {
    const { result } = await comTresPaginas()
    servico.listarConversas.mockImplementation(async (_limit: number, offset = 0) =>
      offset === 100 ? falhou(503) : ok([], 237),
    )
    await act(async () => { result.current.recarregar() })
    await waitFor(() => expect(result.current.atualizando).toBe(false))
    expect(result.current.conversas).toHaveLength(237)
    expect(result.current.erro).toBe("Não foi possível carregar as conversas.")
    expect(result.current.jaCarregou).toBe(true)
  })

  it("a resposta de uma recarga superada por outra é descartada", async () => {
    servidorCom(2)
    const { result } = await montar()
    let resolverVelha!: (r: unknown) => void
    servico.listarConversas.mockImplementationOnce(() => new Promise((r) => { resolverVelha = r }))
    act(() => { result.current.recarregar() })
    servidorCom(3)
    await act(async () => { result.current.recarregar() })
    await waitFor(() => expect(result.current.conversas).toHaveLength(3))
    await act(async () => { resolverVelha(ok([linha("velha")], 1)) })
    expect(result.current.conversas).toHaveLength(3)
  })

  it("'Tentar de novo' depois de um 'Ver mais' que falhou pede a PÁGINA, não a lista inteira", async () => {
    const { result } = await comTresPaginas()
    servico.listarConversas.mockResolvedValueOnce(falhou(503))
    await act(async () => { result.current.carregarMais() })
    await waitFor(() => expect(result.current.erro).toBe("Não foi possível carregar mais conversas."))
    servico.listarConversas.mockClear()
    servidorCom(300)
    await act(async () => { result.current.tentarDeNovo() })
    await waitFor(() => expect(result.current.conversas).toHaveLength(300))
    expect(chamadas()).toEqual([[100, 237]])
    expect(result.current.erro).toBeNull()
  })

  it("'Tentar de novo' depois de uma recarga que falhou refaz a recarga", async () => {
    servidorCom(2)
    const { result } = await montar()
    servico.listarConversas.mockResolvedValueOnce(falhou(503))
    await act(async () => { result.current.recarregar() })
    await waitFor(() => expect(result.current.erro).toBeTruthy())
    servico.listarConversas.mockClear()
    servidorCom(2)
    await act(async () => { result.current.tentarDeNovo() })
    await waitFor(() => expect(result.current.erro).toBeNull())
    expect(chamadas()).toEqual([[100, 0]])
  })
})
