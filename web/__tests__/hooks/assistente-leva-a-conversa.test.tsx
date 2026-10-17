/**
 * The assistant's conversation follows the workflow it built.
 *
 * The first save of a new workflow reopens the editor on /workflow/<id> —
 * another page, so the drawer mounts again and the hook's turns stayed behind:
 * the person who built the workflow talking to the assistant saw the
 * conversation vanish right after saving. The turns on screen go along through
 * `conversa-da-criacao.ts`; the server's transcript through
 * `POST /assistente/editor/conversa/levar`.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"

const servico = vi.hoisted(() => ({
  estadoDoAssistente: vi.fn(async () => ({ data: { ativo: true, motivo: null, cota: null }, error: null })),
  esquecerConversaDoAssistente: vi.fn(async () => ({ data: undefined, error: null })),
  levarConversaDoAssistente: vi.fn(async () => ({ data: { levada: true }, error: null })),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

import { useAssistenteEditor } from "@/app/hooks/workflow/useAssistenteEditor"
import { levarConversaDaCriacao, receberConversa } from "@/app/components/workflow/assistente/conversa-da-criacao"

// Effects run twice on mount, as in development: the second run must not undo
// what the first one took. The option, not a <StrictMode> wrapper: wrapped, React
// 19 ran the effects here only once.
const estrito = { reactStrictMode: true }

const quadro = (evento: string, dados: unknown) => `event: ${evento}\ndata: ${JSON.stringify(dados)}\n\n`

function respostaSSE(corpo: string) {
  const bytes = new TextEncoder().encode(corpo)
  return new Response(new ReadableStream({ start(c) { c.enqueue(bytes); c.close() } }), {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  })
}

/** A turn that answers and ends. */
const respondeEAcaba = () => vi.fn(async () => respostaSSE(
  quadro("texto", { texto: "Montei o buffer." }) + quadro("fim", { transcrito: [], ok: true }),
))

/** A turn that is still running until someone aborts it. */
const naoAcaba = () => vi.fn((_url: string, init: RequestInit) => new Promise<Response>((_, rejeita) => {
  init.signal?.addEventListener("abort", () => rejeita(new DOMException("parou", "AbortError")))
}))

/** The create screen's drawer, after one exchange. */
async function telaDeCriarQueConversou() {
  vi.stubGlobal("fetch", respondeEAcaba())
  const criacao = renderHook(() => useAssistenteEditor(), estrito)
  await act(async () => { await criacao.result.current.enviar("monte um buffer") })
  await waitFor(() => expect(criacao.result.current.correndo).toBe(false))
  return criacao
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.unstubAllGlobals()
  // Whatever an earlier test handed over and nobody took.
  receberConversa("wf-novo")
})

describe("a conversa da tela de criar vai para o workflow criado", () => {
  it("o editor do workflow novo abre com a conversa, e o servidor leva a dele", async () => {
    const criacao = await telaDeCriarQueConversou()
    const naTela = criacao.result.current.turnos
    expect(naTela).toHaveLength(2)

    levarConversaDaCriacao("wf-novo")
    criacao.unmount()
    const editor = renderHook(() => useAssistenteEditor("wf-novo"), estrito)

    expect(editor.result.current.turnos).toEqual(naTela)
    expect(servico.levarConversaDoAssistente).toHaveBeenCalledWith("wf-novo")
  })

  it("vai uma vez só: o próximo editor desse workflow começa do zero", async () => {
    const criacao = await telaDeCriarQueConversou()
    levarConversaDaCriacao("wf-novo")
    criacao.unmount()
    renderHook(() => useAssistenteEditor("wf-novo")).unmount()

    const depois = renderHook(() => useAssistenteEditor("wf-novo"))

    expect(depois.result.current.turnos).toEqual([])
  })

  it("um turno ainda correndo não vai: a conversa na tela seria uma que o assistente não lembra", async () => {
    vi.stubGlobal("fetch", naoAcaba())
    const criacao = renderHook(() => useAssistenteEditor())
    act(() => { void criacao.result.current.enviar("monte um buffer") })
    await waitFor(() => expect(criacao.result.current.correndo).toBe(true))

    levarConversaDaCriacao("wf-novo")
    criacao.unmount()
    const editor = renderHook(() => useAssistenteEditor("wf-novo"))

    expect(editor.result.current.turnos).toEqual([])
    expect(servico.levarConversaDoAssistente).not.toHaveBeenCalled()
  })

  it("sem conversa, nada vai ao servidor", () => {
    const criacao = renderHook(() => useAssistenteEditor())

    levarConversaDaCriacao("wf-novo")
    criacao.unmount()

    expect(servico.levarConversaDoAssistente).not.toHaveBeenCalled()
  })

  it("trocar de workflow continua trocando de conversa — também para a tela de criar", async () => {
    const criacao = await telaDeCriarQueConversou()
    levarConversaDaCriacao("wf-novo")
    criacao.unmount()
    const editor = renderHook(({ id }: { id?: string }) => useAssistenteEditor(id), {
      initialProps: { id: "wf-novo" as string | undefined },
    })
    expect(editor.result.current.turnos).toHaveLength(2)

    editor.rerender({ id: "wf-outro" })
    expect(editor.result.current.turnos).toEqual([])

    vi.stubGlobal("fetch", respondeEAcaba())
    await act(async () => { await editor.result.current.enviar("oi") })
    expect(editor.result.current.turnos).toHaveLength(2)
    editor.rerender({ id: undefined })
    expect(editor.result.current.turnos).toEqual([])
  })
})
