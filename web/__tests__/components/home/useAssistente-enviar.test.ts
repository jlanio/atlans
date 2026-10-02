import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act } from "@testing-library/react"

/**
 * O corpo dos POSTs que a Home manda ao assistente. O foco é a localização:
 * ela só viaja quando a pessoa COMPARTILHOU (o "+" liga, o × desliga) e há
 * posição — lida da store na hora do envio, nem prop nem ref. Sem ela, o corpo
 * é o de sempre. E a CONFIRMAÇÃO reenvia a mesma coordenada: a retomada do laço
 * não pode esquecer o "perto de mim" (o servidor não guarda a posição).
 * O fetch é dublê e a resposta sai cedo do consumidor (sem body).
 */
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    estadoDoAgente: vi.fn().mockResolvedValue({ success: true, data: undefined }),
    // O `conversaId` dispara o replay; devolve uma conversa vazia para o efeito.
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
  // `body: null` faz o consumidor sair na hora (não há stream a ler no teste).
  fetchMock.mockResolvedValue({ ok: true, body: null })
  vi.stubGlobal("fetch", fetchMock)
  useHomeStore.setState({ localizacao: null, compartilharLocalizacao: false })
})
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

/** O corpo JSON do primeiro POST do teste. */
function corpoDoPost(): Record<string, unknown> {
  const chamada = fetchMock.mock.calls[0]
  return JSON.parse((chamada[1] as { body: string }).body)
}

const LOC = { lat: -23.5505, lon: -46.6333, precisao_m: 18 }

describe("useAssistente — a localização no turno", () => {
  it("sem compartilhar, o corpo é o de sempre — sem o campo", async () => {
    // Posição conhecida (o botão do globo gravou), mas a pessoa NÃO pediu para
    // compartilhar: nada viaja.
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
    // Deixa o replay da conversa selecionada assentar (lerConversa dublê).
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
    // No stream, `rate_limited` é a cota DIÁRIA; se o 429 da rota usasse o
    // mesmo código, a tela em inglês diria "espere um instante" a quem só
    // volta amanhã (e vice-versa).
    fetchMock.mockResolvedValue({ ok: false, status: 429, json: async () => ({}) })
    const { result } = renderHook(() =>
      useAssistente({ conversaId: "c1", workspaceId: "w1", anonimo: true }),
    )
    await act(async () => {}) // o replay da conversa assenta antes (senão zera os turnos)
    await act(async () => { await result.current.enviar("oi") })
    const blocos = result.current.turnos.flatMap((t) => t.blocos)
    const erro = blocos.find((b) => b.tipo === "erro")
    expect(erro && erro.tipo === "erro" && erro.erro.code).toBe("muitas_requisicoes")
  })
})

describe("useAssistente — o idioma da tela no turno", () => {
  // O provider de idioma embrulha o hook como a Home real (o layout o monta).
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
    // `enviar` lê o idioma por ref (trocar não o recria): o efeito que mantém
    // a ref em dia é o que faz a troca valer antes de a página recarregar.
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
