/**
 * Os dois consumidores do stream do assistente soltam o leitor quando a leitura
 * acaba — inclusive quando o "Parar" a corta no meio.
 *
 * `useAssistente` (Home) nasceu como fork de `useAssistenteEditor` (gaveta do
 * editor), e as cópias do laço de leitura divergiram: a da Home chamava
 * `leitor.cancel()` no `finally` e documentava que, sem isso, a conexão fica
 * pendurada até o servidor desistir sozinho; a do editor não chamava. Agora as
 * duas leem pela mesma peça, e este teste roda contra as duas.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"

const servico = vi.hoisted(() => ({
  estadoDoAgente: vi.fn(),
  estadoDoAssistente: vi.fn(),
  lerConversa: vi.fn(),
  esquecerConversaDoAssistente: vi.fn(),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

import { useAssistente } from "@/app/hooks/home/useAssistente"
import { useAssistenteEditor } from "@/app/hooks/workflow/useAssistenteEditor"

const ATIVO = { ativo: true, motivo: null, cota: null }

/** O pedaço da interface que os dois hooks têm em comum e este teste usa. */
interface ConsumidorDoStream {
  correndo: boolean
  enviar: (mensagem: string) => Promise<void>
  parar: () => void
}

const HOOKS: [string, () => ConsumidorDoStream][] = [
  ["Home (useAssistente)", () => useAssistente({})],
  ["editor (useAssistenteEditor)", () => useAssistenteEditor("wf-1")],
]

let fetchFalso: ReturnType<typeof vi.fn>

beforeEach(() => {
  servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
  servico.estadoDoAssistente.mockResolvedValue({ success: true, data: ATIVO })
  fetchFalso = vi.fn()
  vi.stubGlobal("fetch", fetchFalso)
})
afterEach(() => { vi.unstubAllGlobals() })

describe.each(HOOKS)("o leitor do stream — %s", (_nome, usar) => {
  it("'Parar' no meio da leitura solta o leitor", async () => {
    const cancel = vi.fn(async () => {})
    fetchFalso.mockImplementation(async (_url: string, init: RequestInit) => ({
      ok: true,
      status: 200,
      body: {
        getReader: () => ({
          // Um stream que nunca termina sozinho: só o abort corta a leitura.
          read: () => new Promise((_resolver, rejeitar) => {
            init.signal?.addEventListener("abort", () => rejeitar(new DOMException("Aborted", "AbortError")))
          }),
          cancel,
        }),
      },
    }))

    const { result } = renderHook(usar)
    act(() => { void result.current.enviar("oi") })
    await waitFor(() => expect(result.current.correndo).toBe(true))

    act(() => { result.current.parar() })
    await waitFor(() => expect(cancel).toHaveBeenCalled())
  })

  it("o stream que termina também solta o leitor", async () => {
    const cancel = vi.fn(async () => {})
    const bytes = new TextEncoder().encode('event: texto\ndata: {"texto":"oi"}\n\n')
    let lidas = 0
    fetchFalso.mockResolvedValue({
      ok: true,
      status: 200,
      body: {
        getReader: () => ({
          read: async () => (lidas++ === 0 ? { done: false, value: bytes } : { done: true, value: undefined }),
          cancel,
        }),
      },
    })

    const { result } = renderHook(usar)
    await act(async () => { await result.current.enviar("oi") })

    expect(cancel).toHaveBeenCalled()
    expect(result.current.correndo).toBe(false)
  })
})
