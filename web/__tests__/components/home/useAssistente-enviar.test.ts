import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act } from "@testing-library/react"

/**
 * The body of the POSTs the Home sends to the assistant. The focus is location:
 * it only travels when the person SHARED it (the "+" turns it on, the × turns it off) and there is a
 * position — read from the store at send time, neither prop nor ref. Without it, the body
 * is the usual one. And the CONFIRMATION resends the same coordinate: resuming the loop
 * must not forget the "near me" (the server does not keep the position).
 * The fetch is a double and the response exits the consumer early (no body).
 */
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    estadoDoAgente: vi.fn().mockResolvedValue({ success: true, data: undefined }),
    // The `conversaId` triggers the replay; returns an empty conversation for the effect.
    lerConversa: vi.fn().mockResolvedValue({ success: true, data: { quadros: [] } }),
  },
}))

import { useAssistente } from "@/app/hooks/home/useAssistente"
import { useHomeStore } from "@/app/stores/homeStore"
import * as React from "react"
import { IdiomaProvider, useIdioma } from "@/context/IdiomaContext"

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  // `body: null` makes the consumer exit right away (there is no stream to read in the test).
  fetchMock.mockResolvedValue({ ok: true, body: null })
  vi.stubGlobal("fetch", fetchMock)
  useHomeStore.setState({ localizacao: null, compartilharLocalizacao: false })
})
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

/** The JSON body of the test's first POST. */
function corpoDoPost(): Record<string, unknown> {
  const chamada = fetchMock.mock.calls[0]
  return JSON.parse((chamada[1] as { body: string }).body)
}

const LOC = { lat: -23.5505, lon: -46.6333, precisao_m: 18 }

describe("useAssistente — a localização no turno", () => {
  it("sem compartilhar, o corpo é o de sempre — sem o campo", async () => {
    // Known position (the globe's button recorded it), but the person did NOT ask to
    // share: nothing travels.
    useHomeStore.setState({ localizacao: LOC, compartilharLocalizacao: false })
    const { result } = renderHook(() =>
      useAssistente({ conversaId: "c1", workspaceId: "w1", anonimo: true }),
    )
    await act(async () => { await result.current.enviar("oi") })

    const corpo = corpoDoPost()
    expect(corpo).toEqual({ mensagem: "oi", conversa_id: "c1", workspace_id: "w1" })
    expect("localizacao" in corpo).toBe(false)
  })

  it("compartilhada, o corpo carrega { lat, lon, precisao_m }", async () => {
    useHomeStore.setState({ localizacao: LOC, compartilharLocalizacao: true })
    const { result } = renderHook(() =>
      useAssistente({ conversaId: "c1", workspaceId: "w1", anonimo: true }),
    )
    await act(async () => { await result.current.enviar("mapeie o risco perto de mim") })

    expect(corpoDoPost().localizacao).toEqual(LOC)
  })

  it("a CONFIRMAÇÃO reenvia a localização — a retomada continua sabendo o 'perto de mim'", async () => {
    useHomeStore.setState({ localizacao: LOC, compartilharLocalizacao: true })
    const { result } = renderHook(() =>
      useAssistente({ conversaId: "c1", workspaceId: "w1", anonimo: true }),
    )
    // Lets the selected conversation's replay settle (lerConversa double).
    await act(async () => {})

    await act(async () => { await result.current.confirmar("tu1", "tok", "confirmar") })

    const corpo = corpoDoPost()
    expect(corpo.token).toBe("tok")
    expect(corpo.decisao).toBe("confirmar")
    expect(corpo.localizacao).toEqual(LOC)
  })
})

describe("useAssistente — a recusa antes do stream", () => {
  it("o 429 da rota é `muitas_requisicoes`, não o `rate_limited` da cota diária", async () => {
    // In the stream, `rate_limited` is the DAILY quota; if the route's 429 used the
    // same code, the English screen would say "wait a moment" to someone who only
    // gets back tomorrow (and vice versa).
    fetchMock.mockResolvedValue({ ok: false, status: 429, json: async () => ({}) })
    const { result } = renderHook(() =>
      useAssistente({ conversaId: "c1", workspaceId: "w1", anonimo: true }),
    )
    await act(async () => {}) // the conversation replay settles first (otherwise it resets the turns)
    await act(async () => { await result.current.enviar("oi") })
    const blocos = result.current.turnos.flatMap((t) => t.blocos)
    const erro = blocos.find((b) => b.tipo === "erro")
    expect(erro && erro.tipo === "erro" && erro.erro.code).toBe("muitas_requisicoes")
  })
})

describe("useAssistente — o idioma da tela no turno", () => {
  // The language provider wraps the hook like the real Home (the layout mounts it).
  const comIdioma = (idioma: "pt-BR" | "en" | "es") =>
    function Embrulho({ children }: { children: React.ReactNode }) {
      return React.createElement(IdiomaProvider, { inicial: { idioma, detectado: idioma, escolhido: idioma }, children })
    }

  it("em inglês o turno leva `idioma: en` — o assistente responde nele", async () => {
    const { result } = renderHook(
      () => useAssistente({ conversaId: "c1", workspaceId: "w1", anonimo: true }),
      { wrapper: comIdioma("en") },
    )
    await act(async () => { await result.current.enviar("hi") })
    expect(corpoDoPost().idioma).toBe("en")
  })

  it("em português o corpo segue o de sempre — sem o campo", async () => {
    const { result } = renderHook(
      () => useAssistente({ conversaId: "c1", workspaceId: "w1", anonimo: true }),
      { wrapper: comIdioma("pt-BR") },
    )
    await act(async () => { await result.current.enviar("oi") })
    expect("idioma" in corpoDoPost()).toBe(false)
  })

  it("trocado nas Preferências, o próximo turno já vai no idioma novo — sem recarregar", async () => {
    // `enviar` reads the language through a ref (switching does not recreate it): the effect that keeps
    // the ref up to date is what makes the switch take effect before the page reloads.
    const { result } = renderHook(
      () => ({ agente: useAssistente({ conversaId: "c1", workspaceId: "w1", anonimo: true }), idioma: useIdioma() }),
      { wrapper: comIdioma("pt-BR") },
    )
    act(() => { result.current.idioma.escolher("en") })
    await act(async () => { await result.current.agente.enviar("hi") })
    expect(corpoDoPost().idioma).toBe("en")
  })

  it("a CONFIRMAÇÃO também leva o idioma — a retomada continua respondendo nele", async () => {
    const { result } = renderHook(
      () => useAssistente({ conversaId: "c1", workspaceId: "w1", anonimo: true }),
      { wrapper: comIdioma("es") },
    )
    await act(async () => { await result.current.confirmar("tu1", "tok", "confirmar") })
    expect(corpoDoPost().idioma).toBe("es")
  })
})
