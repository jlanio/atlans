/**
 * Both consumers of the assistant stream release the reader when reading
 * ends — including when "Parar" (stop) cuts it off in the middle.
 *
 * `useAssistente` (Home) was born as a fork of `useAssistenteEditor` (the editor
 * drawer), and the copies of the read loop diverged: the Home's called
 * `leitor.cancel()` in the `finally` and documented that, without it, the connection stays
 * hanging until the server gives up on its own; the editor's did not call it. Now the
 * two read through the same piece, and this test runs against both.
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

/** The piece of the interface the two hooks have in common and this test uses. */
interface StreamConsumer {
  correndo: boolean
  enviar: (mensagem: string) => Promise<void>
  parar: () => void
}

const HOOKS: [string, () => StreamConsumer][] = [
  ["Home (useAssistente)", () => useAssistente({})],
  ["editor (useAssistenteEditor)", () => useAssistenteEditor("wf-1")],
]

let fakeFetch: ReturnType<typeof vi.fn>

beforeEach(() => {
  servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
  servico.estadoDoAssistente.mockResolvedValue({ success: true, data: ATIVO })
  fakeFetch = vi.fn()
  vi.stubGlobal("fetch", fakeFetch)
})
afterEach(() => { vi.unstubAllGlobals() })

describe.each(HOOKS)("o leitor do stream — %s", (_nome, usar) => {
  it("'Parar' no meio da leitura solta o leitor", async () => {
    const cancel = vi.fn(async () => {})
    fakeFetch.mockImplementation(async (_url: string, init: RequestInit) => ({
      ok: true,
      status: 200,
      body: {
        getReader: () => ({
          // A stream that never ends on its own: only the abort cuts the read off.
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
    fakeFetch.mockResolvedValue({
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
