import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"

/**
 * O estado do hook do assistente: como uma falha de rede é distinguida de
 * "desligado", e o que acontece com o stream quando a Home some.
 */
const servico = vi.hoisted(() => ({ estadoDoAgente: vi.fn(), lerConversa: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

import { useAssistente } from "@/app/hooks/home/useAssistente"

const ATIVO = { ativo: true, cota: { gasto: 0, teto: 100, reabre_em_segundos: null } }

beforeEach(() => {
  servico.estadoDoAgente.mockReset()
  servico.lerConversa.mockReset()
  vi.stubGlobal("fetch", vi.fn())
})

describe("useAssistente — sem sessão", () => {
  it("anonimo: não consulta o /estado (viraria 401) e deixa a barra aparecer", async () => {
    const { result } = renderHook(() => useAssistente({ anonimo: true }))
    await waitFor(() => expect(result.current.consultando).toBe(false))
    expect(servico.estadoDoAgente).not.toHaveBeenCalled()
    expect(result.current.falhou).toBe(false)
    expect(result.current.estado).toBeNull()
  })

  it("a sessão chegando (login no modal ou noutra aba) consulta o estado sem remontar", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    const { result, rerender } = renderHook(({ anonimo }) => useAssistente({ anonimo }), { initialProps: { anonimo: true } })
    await waitFor(() => expect(result.current.consultando).toBe(false))
    expect(servico.estadoDoAgente).not.toHaveBeenCalled()

    rerender({ anonimo: false })
    await waitFor(() => expect(result.current.estado?.ativo).toBe(true))
    expect(servico.estadoDoAgente).toHaveBeenCalledTimes(1)
  })
})

describe("useAssistente — estado", () => {
  it("falha na consulta vira `falhou`, e não 'assistente desligado'", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: false, error: { message: "502" }, data: undefined })
    const { result } = renderHook(() => useAssistente({}))

    await waitFor(() => expect(result.current.consultando).toBe(false))
    expect(result.current.falhou).toBe(true)
    expect(result.current.estado).toBeNull()
  })

  it("reconsultar refaz a chamada e limpa a falha", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: false, data: undefined })
    const { result } = renderHook(() => useAssistente({}))
    await waitFor(() => expect(result.current.falhou).toBe(true))

    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    act(() => { result.current.reconsultar() })
    await waitFor(() => expect(result.current.falhou).toBe(false))
    expect(result.current.estado?.ativo).toBe(true)
  })

  it("desligado responde com sucesso: `falhou` continua falso", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: { ativo: false, motivo: "sem chave" } })
    const { result } = renderHook(() => useAssistente({}))

    await waitFor(() => expect(result.current.consultando).toBe(false))
    expect(result.current.falhou).toBe(false)
    expect(result.current.estado?.motivo).toBe("sem chave")
  })

  it("desmontar a Home aborta o stream em curso", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    let sinal: AbortSignal | undefined
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      async (_url: string, init: RequestInit) => {
        sinal = init.signal ?? undefined
        // Um stream que nunca termina sozinho — é o abort que o encerra.
        return { ok: true, body: { getReader: () => ({ read: () => new Promise(() => {}), cancel: async () => {} }) } }
      },
    )

    const { result, unmount } = renderHook(() => useAssistente({}))
    await waitFor(() => expect(result.current.consultando).toBe(false))
    act(() => { void result.current.enviar("oi") })
    await waitFor(() => expect(sinal).toBeDefined())
    expect(sinal!.aborted).toBe(false)

    unmount()
    expect(sinal!.aborted).toBe(true)
  })

  it("parar marca o turno como interrompido, em vez de deixá-lo com cara de pronto", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(async () => ({
      ok: true, body: { getReader: () => ({ read: () => new Promise(() => {}), cancel: async () => {} }) },
    }))

    const { result } = renderHook(() => useAssistente({}))
    await waitFor(() => expect(result.current.consultando).toBe(false))
    act(() => { void result.current.enviar("oi") })
    await waitFor(() => expect(result.current.correndo).toBe(true))

    act(() => { result.current.parar() })
    const ultimo = result.current.turnos[result.current.turnos.length - 1]
    expect(ultimo.blocos.some((b) => b.tipo === "erro" && /interrompida/i.test(b.erro.message))).toBe(true)
  })
})

describe("useAssistente — o desfecho de uma confirmação", () => {
  /** Um hook já com conversa carregada — `confirmar` precisa do id no ref. */
  async function comConversa(onConversa?: (info: { id: string; titulo?: string; nova: boolean }) => void) {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    servico.lerConversa.mockResolvedValue({ success: true, data: { quadros: [] } })
    const { result } = renderHook(() => useAssistente({ conversaId: "c1", onConversa }))
    await waitFor(() => expect(result.current.consultando).toBe(false))
    await waitFor(() => expect(result.current.carregandoReplay).toBe(false))
    return result
  }

  it("'Parar' no meio do stream NÃO destrava o cartão: a chave já foi consumida", async () => {
    // O servidor aceitou a decisão (a resposta virou stream) e só então o
    // aborto cortou a leitura. Ler isso como "não valeu" reabria um cartão que
    // não pode mais ser decidido — o clique seguinte bateria num 409.
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      async (_url: string, init: RequestInit) => ({
        ok: true,
        status: 200,
        body: {
          getReader: () => ({
            read: () => new Promise((_resolver, rejeitar) => {
              init.signal?.addEventListener("abort", () => rejeitar(new DOMException("Aborted", "AbortError")))
            }),
            cancel: async () => {},
          }),
        },
      }),
    )

    const result = await comConversa()
    let decisao!: Promise<string>
    act(() => { decisao = result.current.confirmar("tu1", "TOK", "confirmar") })
    await waitFor(() => expect(result.current.correndo).toBe(true))

    act(() => { result.current.parar() })
    await expect(decisao).resolves.toBe("valeu")
  })

  it("409 vira 'expirada' (travado, com explicação), e não 'falhou' — e não anuncia nada", async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false, status: 409, json: async () => ({ message: "A confirmação expirou ou já foi decidida." }),
    })
    const onConversa = vi.fn()
    const result = await comConversa(onConversa)

    let desfecho: string | undefined
    await act(async () => { desfecho = await result.current.confirmar("tu1", "TOK", "confirmar") })
    expect(desfecho).toBe("expirada")
    // Sem stream não há carimbo de `updated_at` no servidor: a lista não sobe.
    expect(onConversa).not.toHaveBeenCalled()
  })

  it("a decisão aceita anuncia a conversa (só o id) — a lista de Chats a sobe", async () => {
    // O 2º SSE não emite `conversa`, mas o servidor carimba `updated_at` ao
    // fechá-lo: sem o anúncio a linha só subia na mensagem seguinte.
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true, status: 200,
      body: { getReader: () => ({ read: async () => ({ done: true, value: undefined }), cancel: async () => {} }) },
    })
    const onConversa = vi.fn()
    const result = await comConversa(onConversa)

    await act(async () => { await result.current.confirmar("tu1", "TOK", "confirmar") })
    expect(onConversa).toHaveBeenCalledWith({ id: "c1", nova: false })
  })

  it("queda de rede vira 'falhou' — aí sim a ação precisa de outra chance", async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new TypeError("Failed to fetch"))
    const result = await comConversa()

    let desfecho: string | undefined
    await act(async () => { desfecho = await result.current.confirmar("tu1", "TOK", "confirmar") })
    expect(desfecho).toBe("falhou")
  })
})

describe("useAssistente — a cota durante o turno", () => {
  it("o quadro `cota` sobe o gasto DURANTE o turno; o fim do stream relê o estado", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    let soltar!: () => void
    const ultimaLeitura = new Promise<{ done: true; value?: undefined }>((r) => { soltar = () => r({ done: true }) })
    const bytes = new TextEncoder().encode('event: cota\ndata: {"gasto":40,"teto":100}\n\n')
    let lidas = 0
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: {
        getReader: () => ({
          read: () => (lidas++ === 0 ? Promise.resolve({ done: false, value: bytes }) : ultimaLeitura),
          cancel: async () => {},
        }),
      },
    })
    const { result } = renderHook(() => useAssistente({}))
    await waitFor(() => expect(result.current.consultando).toBe(false))

    act(() => { void result.current.enviar("quanto gastei?") })

    // Com o stream ainda aberto, o gasto já é o do quadro — sem GET nenhum.
    await waitFor(() => expect(result.current.estado?.cota?.gasto).toBe(40))
    expect(result.current.correndo).toBe(true)
    expect(servico.estadoDoAgente).toHaveBeenCalledTimes(1)
    expect(result.current.turnos.at(-1)?.blocos).toEqual([])

    // O stream fecha: a releitura traz o gasto e o PRAZO do servidor.
    servico.estadoDoAgente.mockResolvedValue({
      success: true, data: { ativo: true, cota: { gasto: 45, teto: 100, reabre_em_segundos: 60 } },
    })
    act(() => { soltar() })
    await waitFor(() => expect(result.current.correndo).toBe(false))
    await waitFor(() => expect(result.current.estado?.cota?.gasto).toBe(45))
    expect(result.current.estado?.cota?.reabre_em_segundos).toBe(60)
    expect(servico.estadoDoAgente).toHaveBeenCalledTimes(2)
  })
})
