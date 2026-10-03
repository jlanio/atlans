import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"

/**
 * The mounted HomeView. jsdom does not draw MapLibre nor do layout, so what
 * is checked here is the state CONTRACT: which surface shows up for each
 * `/assistente/estado` response, the shortcut that toggles both ways, the sidebar's
 * layer queue and the layers' lifecycle when switching conversations.
 */
const servico = vi.hoisted(() => ({
  estadoDoAgente: vi.fn(),
  lerConversa: vi.fn(),
  camadaDoGlobo: vi.fn(),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))
vi.mock("@/context/WorkspaceContext", () => ({ useWorkspace: () => ({ current: { id_hash: "w1" } }) }))
vi.mock("@/app/hooks/useResizablePanel", () => ({
  useResizablePanel: () => ({ width: 420, isResizing: false, resizeHandleProps: {} }),
}))
vi.mock("@/hooks/use-mobile", () => ({ useIsMobile: () => false }))
vi.mock("@/app/components/share/MapLibreMap", async () => {
  const React = await import("react")
  return {
    default: React.forwardRef(function FakeMapLibre(p: { giroLento?: boolean }) {
      // `data-giro` exposes what the HomeView asked of the globe: spin in the hero, stop afterward.
      return React.createElement("div", { "data-testid": "maplibre", "data-giro": String(!!p.giroLento) })
    }),
  }
})

// The session is MUTABLE: the Home opens without a session, and it is the status that decides the shell.
// Default "authenticated" — the usual tests do not change.
const sessao = vi.hoisted(() => ({
  status: "authenticated" as "authenticated" | "unauthenticated" | "loading",
  data: { user: { id_hash: "u1" } } as Record<string, unknown> | null,
}))
vi.mock("next-auth/react", () => ({ useSession: () => ({ data: sessao.data, status: sessao.status }) }))
const nav = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }))
vi.mock("next/navigation", () => ({ useRouter: () => nav }))
// The sign-in modal has its own test; here it is a marker that exposes the requested
// mode and the supporting sentence, and two buttons: close without signing in and "entrou".
vi.mock("@/app/components/home/entrada/modal-de-entrada", () => ({
  default: (p: { modo: string | null; tokenDoLink?: string; comEnvioPendente?: boolean; onFechar: () => void; onEntrou: () => void }) => (
    <div data-testid="modal-de-entrada" data-modo={p.modo ?? ""} data-token={p.tokenDoLink ?? ""} data-pendente={String(!!p.comEnvioPendente)}>
      <button type="button" onClick={p.onFechar}>fechar-modal</button>
      <button type="button" onClick={p.onEntrou}>entrou-modal</button>
    </div>
  ),
}))

import HomeView, { SAIDA_MS } from "@/app/components/home"
import { pt } from "@/app/components/home/i18n/secoes/assistente"
import { useHomeStore } from "@/app/stores/homeStore"
import { LanguageProvider, useLanguage } from "@/context/IdiomaContext"

// The hero's sentences and chips in Portuguese (the dictionary the bar reads).
const { sugestoes: SUGGESTIONS, chips: CHIPS } = pt.barra

const ATIVO = { ativo: true, cota: { gasto: 0, teto: 1_000_000, reabre_em_segundos: null } }

beforeEach(() => {
  cleanup()
  servico.estadoDoAgente.mockReset()
  servico.lerConversa.mockReset()
  servico.camadaDoGlobo.mockReset()
  servico.lerConversa.mockResolvedValue({ success: true, data: { quadros: [] } })
  useHomeStore.setState({
    conversaId: null, painel: "aberto", pedidosDeCamada: [], anuncioDeConversa: null,
    decididos: {}, expirados: {}, rascunho: "", hidratado: false, entrada: null, envioPendente: null,
  })
  vi.stubGlobal("fetch", vi.fn())
  sessao.status = "authenticated"
  sessao.data = { user: { id_hash: "u1" } }
  nav.push.mockClear()
  nav.refresh.mockClear()
})

async function montar() {
  const r = render(<HomeView />)
  await waitFor(() => expect(servico.estadoDoAgente).toHaveBeenCalled())
  // Calling is not responding: the Home only leaves the loading skeleton in
  // useAssistente's `.then`. Without waiting for the response to be applied, whoever reads the
  // bar right after montar() sometimes catches the skeleton (slow runner).
  await act(async () => { await servico.estadoDoAgente.mock.results[0]?.value })
  return r
}

describe("HomeView — o assistente e o /assistente/estado", () => {
  it("falha transitória: mantém uma superfície com 'Tentar de novo' (não some com tudo)", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: false, error: { message: "502" } })
    await montar()

    const botao = await screen.findByRole("button", { name: /tentar de novo/i })
    expect(screen.getByText(/não foi possível falar com o assistente/i)).toBeTruthy()

    // O retry refaz a consulta — e desta vez o assistente responde.
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    await act(async () => { fireEvent.click(botao) })
    expect(await screen.findByLabelText(/Mensagem para o assistente/i)).toBeTruthy()
  })

  it("desligado na instalação: diz o motivo do servidor, e não um erro de rede", async () => {
    servico.estadoDoAgente.mockResolvedValue({
      success: true, data: { ativo: false, motivo: "O assistente está desligado nesta instalação." },
    })
    await montar()

    expect(await screen.findByText(/desligado nesta instalação/i)).toBeTruthy()
    expect(screen.queryByRole("button", { name: /tentar de novo/i })).toBeNull()
  })

  it("desligado, em inglês: o aviso do idioma — o motivo do servidor é para quem administra", async () => {
    // The `motivo` comes in Portuguese and speaks to whoever administers ("defina
    // OPENROUTER_API_KEY"); outside Portuguese the dictionary's warning applies.
    servico.estadoDoAgente.mockResolvedValue({
      success: true, data: { ativo: false, motivo: "O assistente está desligado. Defina OPENROUTER_API_KEY." },
    })
    render(
      <LanguageProvider inicial={{ idioma: "en", detectado: "en", escolhido: "en" }}>
        <HomeView />
      </LanguageProvider>,
    )
    expect(await screen.findByText("The assistant isn’t available on this installation.")).toBeTruthy()
    expect(screen.queryByText(/OPENROUTER_API_KEY/)).toBeNull()
  })

  it("Ctrl+I recolhe E reabre com o cursor no campo, sem perder o rascunho", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    await montar()
    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)

    // The keydown comes FROM THE FIELD — which is where the cursor is when someone types —
    // and bubbles up to window. Fired directly on `window`, the event target would be
    // the window, and the test would pass even with the shortcut ignoring focus.
    act(() => {
      fireEvent.change(campo, { target: { value: "buffer de 500 m" } })
      campo.focus()
      fireEvent.keyDown(campo, { key: "i", ctrlKey: true })
    })
    expect(useHomeStore.getState().painel).toBe("barra")

    // Collapsing UNMOUNTS the panel: the text has to reappear in the bar.
    const barInput = screen.getByLabelText(/Mensagem para o assistente/i) as HTMLInputElement
    expect(barInput.value).toBe("buffer de 500 m")

    act(() => {
      barInput.focus()
      fireEvent.keyDown(barInput, { key: "i", ctrlKey: true })
    })
    expect(useHomeStore.getState().painel).toBe("aberto")
    // The bar is still leaving (fade) for an instant; the panel's field is the textarea.
    await waitFor(() => expect(screen.queryByTestId("barra")).toBeNull())
    const deVolta = screen.getByLabelText(/Mensagem para o assistente/i) as HTMLTextAreaElement
    expect(deVolta.value).toBe("buffer de 500 m")
  })
})

describe("HomeView — o lang do <html>", () => {
  function TrocarPara({ idioma }: { idioma: "es" }) {
    const { escolher } = useLanguage()
    return <button onClick={() => escolher(idioma)}>trocar</button>
  }

  it("segue o idioma da Home e volta ao de antes quando ela sai", async () => {
    // The one on <html> covers what Radix portals to <body>; the rest of the app is
    // Portuguese, so leaving the Home restores the previous value.
    document.documentElement.lang = "pt-BR"
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    const { unmount } = render(
      <LanguageProvider inicial={{ idioma: "en", detectado: "en", escolhido: null }}>
        <HomeView />
        <TrocarPara idioma="es" />
      </LanguageProvider>,
    )
    await waitFor(() => expect(servico.estadoDoAgente).toHaveBeenCalled())
    expect(document.documentElement.lang).toBe("en")

    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "trocar" })) })
    expect(document.documentElement.lang).toBe("es")

    unmount()
    expect(document.documentElement.lang).toBe("pt-BR")
  })

  it("em português, o português de sempre", async () => {
    document.documentElement.lang = "pt-BR"
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    const { unmount } = await montar()
    expect(document.documentElement.lang).toBe("pt-BR")
    unmount()
    expect(document.documentElement.lang).toBe("pt-BR")
  })
})

describe("HomeView — camadas", () => {
  beforeEach(() => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    servico.camadaDoGlobo.mockImplementation(async (id: string) => ({
      success: true,
      data: { artifact_id: id, nome: `Camada ${id}`, tipo: "geojson", available: true, download_url: "u" },
    }))
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true, json: async () => ({ type: "FeatureCollection", features: [] }),
    })
  })

  it("drena a fila de 'exibir no globo' e consome só o que despachou", async () => {
    await montar()
    await act(async () => { useHomeStore.getState().pedirCamada("a1", "Focos") })

    expect(await screen.findByText("Focos")).toBeTruthy()
    expect(useHomeStore.getState().pedidosDeCamada).toHaveLength(0)
  })

  it("trocar de conversa tira do globo as camadas da conversa anterior", async () => {
    await montar()
    await act(async () => { useHomeStore.getState().pedirCamada("a1", "Focos") })
    await screen.findByText("Focos")

    await act(async () => { useHomeStore.getState().selecionarConversa("outra") })
    await waitFor(() => expect(screen.queryByText("Focos")).toBeNull())
  })

  it("a conversa NOVA que ganha id no stream mantém as camadas que ela mesma pôs — e anuncia a lista", async () => {
    // The 1st SSE frame teaches the conversation id: `conversaId` goes from null to
    // an id without the conversation having changed — and the layers belong to it. The whole
    // announcement (id, title, new) stays in the store for the Chats list, which is not
    // mounted here: it is the one that inserts the row without F5.
    const sse = [
      'event: conversa\ndata: {"conversa_id":"c9","titulo":"focos","nova":true}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(async (url: string) => {
      if (String(url).includes("/assistente/conversa")) {
        return { ok: true, body: sseBody(sse) }
      }
      return { ok: true, json: async () => ({ type: "FeatureCollection", features: [] }) }
    })

    await montar()
    await act(async () => { useHomeStore.getState().pedirCamada("a1", "Focos") })
    await screen.findByText("Focos")

    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    await act(async () => {
      fireEvent.change(campo, { target: { value: "e agora?" } })
      fireEvent.submit(campo.closest("form")!)
    })

    expect(useHomeStore.getState().conversaId).toBe("c9")
    expect(useHomeStore.getState().anuncioDeConversa).toMatchObject({ id: "c9", titulo: "focos", nova: true })
    expect(screen.getByText("Focos")).toBeTruthy()
  })

  it("reabrir pelos Chats a conversa que o stream nomeou também troca o escopo", async () => {
    // The id announced by the stream applies to ONE switch — the one it caused itself.
    // Kept forever, it said "this conversation is never another one", and going back to
    // it through Chats left the previous chat's layers on the globe.
    const sse = [
      'event: conversa\ndata: {"conversa_id":"c9","nova":true}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(async (url: string) => {
      if (String(url).includes("/assistente/conversa")) return { ok: true, body: sseBody(sse) }
      return { ok: true, json: async () => ({ type: "FeatureCollection", features: [] }) }
    })

    await montar()
    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    await act(async () => { fireEvent.change(campo, { target: { value: "e agora?" } }) })
    await act(async () => { fireEvent.submit(campo.closest("form")!) })
    await waitFor(() => expect(useHomeStore.getState().conversaId).toBe("c9"))

    // Another chat, and a layer put THERE.
    await act(async () => { useHomeStore.getState().selecionarConversa("z") })
    await act(async () => { useHomeStore.getState().pedirCamada("a2", "Outra") })
    await screen.findByText("Outra")

    // Back to c9 through Chats: it is another conversation, and the globe belongs to the conversation.
    await act(async () => { useHomeStore.getState().selecionarConversa("c9") })
    await waitFor(() => expect(screen.queryByText("Outra")).toBeNull())
  })
})

describe("HomeView — o hero do primeiro acesso", () => {
  beforeEach(() => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    // Every visit starts at the bar; the panel is on demand.
    useHomeStore.setState({ painel: "barra" })
  })

  function veu() { return document.querySelector(".home-veu")?.getAttribute("data-visivel") }
  function heroText() { return document.querySelector(".home-hero-texto")?.getAttribute("data-visivel") ?? null }

  it("é o estado inicial: título, chips, barra grande e véu — sem painel nem pilha", async () => {
    await montar()

    expect(screen.getByRole("heading", { name: /menos ferramentas\. mais respostas/i })).toBeTruthy()
    expect(screen.getByRole("group", { name: /sugestões/i })).toBeTruthy()
    expect(screen.getByTestId("barra").dataset.variante).toBe("hero")
    expect(veu()).toBe("true")
    expect(screen.queryByLabelText("Assistente")).toBeNull()
    expect(screen.queryByTestId("pilha")).toBeNull()
    // The globe spins slowly while the hero is on screen.
    expect(screen.getByTestId("maplibre").dataset.giro).toBe("true")
  })

  it("termina no PRIMEIRO TOKEN: a barra vai ao rodapé, o véu some e a troca aparece ao centro", async () => {
    const sse = [
      'event: conversa\ndata: {"conversa_id":"c1","nova":true}\n\n',
      'event: pensando\ndata: {"texto":"preciso do catálogo"}\n\n',
      'event: texto\ndata: {"texto":"Achei 1 284 focos."}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, body: sseBody(sse) })
    await montar()

    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    // Two `act`s: inside a single one, the keyDown would see the render BEFORE the change
    // (empty field → it would send the current suggestion). In the browser they are two tasks.
    await act(async () => { fireEvent.change(campo, { target: { value: "focos de calor em MT" } }) })
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })

    const pilha = await screen.findByTestId("pilha")
    expect(pilha.textContent).toContain("focos de calor em MT")
    expect(pilha.textContent).toContain("Achei 1 284 focos.")
    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")
    expect(veu()).toBe("false")
    // The spin stops — and the map goes back to Brazil (the Globo's `center`).
    expect(screen.getByTestId("maplibre").dataset.giro).toBe("false")
    // The title stays in the DOM until the transition ends, already invisible.
    expect(heroText()).toBe("false")
    // And the panel stays closed: the conversation is in the center.
    expect(useHomeStore.getState().painel).toBe("barra")
  })

  it("a resposta traz respostas rápidas; clicar uma manda a frase como a próxima mensagem", async () => {
    const withChips = [
      'event: conversa\ndata: {"conversa_id":"c1","nova":true}\n\n',
      'event: texto\ndata: {"texto":"Achei 1 284 focos."}\n\n',
      'event: respostas_rapidas\ndata: {"opcoes":["Só os últimos 7 dias","Cruzar com o CAR"]}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    const withoutChips = [
      'event: conversa\ndata: {"conversa_id":"c1","nova":false}\n\n',
      'event: texto\ndata: {"texto":"Cruzei: 37 sobreposições."}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    const fila = [withChips, withoutChips]
    const fakeFetch = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    fakeFetch.mockImplementation(async () => ({ ok: true, body: sseBody(fila.shift() ?? withoutChips) }))
    await montar()

    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    await act(async () => { fireEvent.change(campo, { target: { value: "focos de calor em MT" } }) })
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })

    const chip = await screen.findByRole("button", { name: "Cruzar com o CAR" })
    await act(async () => { fireEvent.click(chip) })

    // The second POST carries the chip's sentence; and the new turn takes the chips off the screen.
    await waitFor(() => expect(fakeFetch).toHaveBeenCalledTimes(2))
    const bodies = fakeFetch.mock.calls.map((c) => JSON.parse(String((c[1] as RequestInit).body)) as { mensagem: string })
    expect(bodies.map((b) => b.mensagem)).toEqual(["focos de calor em MT", "Cruzar com o CAR"])
    await screen.findByText(/37 sobreposições/)
    expect(screen.queryByRole("button", { name: "Cruzar com o CAR" })).toBeNull()
    expect(screen.queryByRole("group", { name: /respostas rápidas/i })).toBeNull()
  })

  it("enviar encerra o hero na hora — a faixa carrega antes do 1º token — e Esc interrompe", async () => {
    // A stream that never delivers anything: it stays in reasoning until the person gives up.
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: { getReader: () => ({ read: () => new Promise(() => {}), cancel: async () => {} }) },
    })
    await montar()

    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    // Two `act`s: inside a single one, the keyDown would see the render BEFORE the change
    // (empty field → it would send the current suggestion). In the browser they are two tasks.
    await act(async () => { fireEvent.change(campo, { target: { value: "focos de calor em MT" } }) })
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })

    // SUBMITTING already moves the bar down: the strip shows up with the question and the reasoning
    // indicator, even WITHOUT any text token yet. This is the fix for the owner's
    // bug — the bar does not stay stuck in the center during reasoning/tools.
    const pilha = await screen.findByTestId("pilha")
    expect(pilha.textContent).toContain("focos de calor em MT")
    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")
    expect(screen.queryByRole("group", { name: /sugestões/i })).toBeNull()

    await act(async () => { fireEvent.keyDown(campo, { key: "Escape" }) })

    await waitFor(() => expect(screen.getByTestId("pilha").textContent).toContain("Resposta interrompida."))
    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")
  })

  it("no rodapé, a barra mostra o PASSO da vez durante raciocínio e ferramentas — e o esconde na escrita", async () => {
    // An SSE body that delivers the chunks ON DEMAND: it is the only way to
    // assert the MIDDLE of the stream (the usual corpoSSE delivers everything at once).
    const enc = new TextEncoder()
    let resolver: ((r: { done: boolean; value?: Uint8Array }) => void) | null = null
    const fila: { done: boolean; value?: Uint8Array }[] = []
    const pushChunk = (texto: string | null) => {
      const item = texto === null ? { done: true, value: undefined } : { done: false, value: enc.encode(texto) }
      if (resolver) { const r = resolver; resolver = null; r(item) } else fila.push(item)
    }
    const body = {
      getReader: () => ({
        read: () => (fila.length
          ? Promise.resolve(fila.shift()!)
          : new Promise<{ done: boolean; value?: Uint8Array }>((res) => { resolver = res })),
        cancel: async () => {},
      }),
    }
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, body })
    await montar()

    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    await act(async () => { fireEvent.change(campo, { target: { value: "focos de calor em MT" } }) })
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })

    // Reasoning: the bar has already moved down and the step says "Pensando…".
    await act(async () => {
      pushChunk('event: conversa\ndata: {"conversa_id":"c1","nova":true}\n\nevent: pensando\ndata: {"texto":"preciso do catálogo"}\n\n')
    })
    await waitFor(() => expect(screen.getByTestId("etapa-da-barra").textContent).toContain("Pensando"))
    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")

    // Tool in progress: the step switches to its LABEL, with the detail —
    // it is the "show the stages" the owner asked for.
    await act(async () => {
      pushChunk('event: ferramenta\ndata: {"id":"t1","nome":"get_authoring_guide","argumentos":{"topic":"edges"}}\n\n')
    })
    await waitFor(() => expect(screen.getByTestId("etapa-da-barra").textContent).toContain("Consultando o guia"))
    expect(screen.getByTestId("etapa-da-barra").textContent).toContain("edges")

    // Writing: the step goes away — the answer already shows up in the strip.
    await act(async () => {
      pushChunk('event: texto\ndata: {"texto":"Achei 1 284 focos."}\n\nevent: fim\ndata: {"ok":true}\n\n')
      pushChunk(null)
    })
    await waitFor(() => expect(screen.queryByTestId("etapa-da-barra")).toBeNull())
    expect(screen.getByTestId("pilha").textContent).toContain("Achei 1 284 focos.")
  })

  it("abrir o painel segura a barra saindo, sem roubar o foco; depois ela some", async () => {
    await montar()
    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    act(() => { campo.focus(); fireEvent.keyDown(campo, { key: "i", ctrlKey: true }) })

    expect(useHomeStore.getState().painel).toBe("aberto")
    expect(screen.getByLabelText("Assistente")).toBeTruthy()
    expect(screen.getByTestId("barra").dataset.saindo).toBe("true")
    // The cursor went to the panel's field (the textarea): the bar, on its way out, does not steal it.
    expect(document.activeElement?.tagName).toBe("TEXTAREA")

    await waitFor(() => expect(screen.queryByTestId("barra")).toBeNull())
    expect(document.activeElement?.tagName).toBe("TEXTAREA")
  })

  it("recolher durante a saída cancela: a barra fica, sem 'saindo'", async () => {
    await montar()
    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    act(() => { campo.focus(); fireEvent.keyDown(campo, { key: "i", ctrlKey: true }) })
    expect(screen.getByTestId("barra").dataset.saindo).toBe("true")

    act(() => { fireEvent.keyDown(window, { key: "i", ctrlKey: true }) })
    expect(useHomeStore.getState().painel).toBe("barra")
    const barra = screen.getByTestId("barra")
    expect(barra.dataset.saindo).toBe("false")

    // And it is the SAME node after the timeout: a timer that survived the cancellation
    // would unmount and remount the bar — a flicker, with the entrance again.
    await act(async () => { await new Promise((r) => setTimeout(r, SAIDA_MS + 50)) })
    expect(screen.getByTestId("barra")).toBe(barra)
    expect(screen.queryByLabelText("Assistente")).toBeNull()
  })

  it("sem movimento a barra some no tick seguinte", async () => {
    const original = window.matchMedia
    window.matchMedia = ((q: string) => ({
      matches: q.includes("prefers-reduced-motion"), media: q, onchange: null,
      addEventListener: () => {}, removeEventListener: () => {},
      addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia
    try {
      await montar()
      const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
      act(() => { campo.focus(); fireEvent.keyDown(campo, { key: "i", ctrlKey: true }) })
      await act(async () => { await new Promise((r) => setTimeout(r, 0)) })
      expect(screen.queryByTestId("barra")).toBeNull()
    } finally {
      window.matchMedia = original
    }
  })

  it("abrir o painel (Ctrl+I) durante o hero também o encerra", async () => {
    await montar()
    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)

    act(() => {
      campo.focus()
      fireEvent.keyDown(campo, { key: "i", ctrlKey: true })
    })

    expect(useHomeStore.getState().painel).toBe("aberto")
    expect(veu()).toBe("false")
    expect(screen.getByLabelText("Assistente")).toBeTruthy()
  })

  it("carregar um artefato no globo encerra o hero: a barra desce ao rodapé e o globo para", async () => {
    servico.camadaDoGlobo.mockImplementation(async (id: string) => ({
      success: true,
      data: { artifact_id: id, nome: `Camada ${id}`, tipo: "geojson", available: true, download_url: "u" },
    }))
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true, json: async () => ({ type: "FeatureCollection", features: [] }),
    })
    await montar()
    expect(screen.getByTestId("barra").dataset.variante).toBe("hero")

    // The same path as clicking in the sidebar's Artifacts list.
    await act(async () => { useHomeStore.getState().pedirCamada("a1", "Focos") })

    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")
    expect(veu()).toBe("false")
    expect(heroText()).toBe("false")
    // The globe spinning against the new layer's framing was half the bug.
    expect(screen.getByTestId("maplibre").dataset.giro).toBe("false")
  })
})

/** A response body that delivers the SSE in a single chunk. */
function sseBody(texto: string) {
  const bytes = new TextEncoder().encode(texto)
  let entregue = false
  return {
    getReader: () => ({
      read: async () => {
        if (entregue) return { done: true, value: undefined }
        entregue = true
        return { done: false, value: bytes }
      },
      cancel: async () => {},
    }),
  }
}

describe("HomeView — a cota acompanha a conversa", () => {
  it("o donut sobe ao fim do turno, sem F5: o estado é relido quando o stream fecha", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    const sse = 'event: texto\ndata: {"texto":"oi"}\n\nevent: fim\ndata: {"ok":true}\n\n'
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(async (url: string) => {
      if (String(url).includes("/assistente/conversa")) return { ok: true, body: sseBody(sse) }
      return { ok: true, json: async () => ({}) }
    })
    await montar()
    expect((await screen.findByTestId("uso-da-cota")).textContent).toBe("0%")

    // O servidor cobrou durante o turno: a releitura traz o gasto novo.
    servico.estadoDoAgente.mockResolvedValue({
      success: true, data: { ativo: true, cota: { gasto: 300_000, teto: 1_000_000, reabre_em_segundos: 3_600 } },
    })
    const campo = (await screen.findAllByLabelText(/Mensagem/i))[0]
    await act(async () => {
      fireEvent.change(campo, { target: { value: "quanto gastei?" } })
      fireEvent.submit(campo.closest("form")!)
    })

    await waitFor(() => expect(screen.getByTestId("uso-da-cota").textContent).toBe("30%"))
    expect(servico.estadoDoAgente).toHaveBeenCalledTimes(2)
  })
})

describe("HomeView — sem sessão: a Home abre, e o primeiro envio pede a entrada", () => {
  const store = () => useHomeStore.getState()
  const modal = () => screen.getByTestId("modal-de-entrada")
  const fakeFetch = () => globalThis.fetch as unknown as ReturnType<typeof vi.fn>

  function withoutSession() {
    sessao.status = "unauthenticated"
    sessao.data = null
  }
  function withSession() {
    sessao.status = "authenticated"
    sessao.data = { user: { id_hash: "u1" } }
  }
  /** Mounts anonymously and asserts the essentials: the bar is there and NOTHING was queried. */
  async function mountAnonymous(props: React.ComponentProps<typeof HomeView> = {}) {
    withoutSession()
    useHomeStore.setState({ painel: "barra" })
    const r = render(<HomeView {...props} />)
    await screen.findByLabelText(/Mensagem para o assistente/i)
    expect(servico.estadoDoAgente).not.toHaveBeenCalled()
    return r
  }
  async function typeAndSend(texto: string) {
    const campo = screen.getByLabelText(/Mensagem para o assistente/i) as HTMLInputElement
    await act(async () => { fireEvent.change(campo, { target: { value: texto } }) })
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })
    return campo
  }

  it("o hero inteiro, sem consultar o assistente e sem aviso; o modal fechado", async () => {
    await mountAnonymous()
    expect(screen.getByRole("heading", { name: /menos ferramentas\. mais respostas/i })).toBeTruthy()
    expect(screen.getByRole("group", { name: /sugestões/i })).toBeTruthy()
    expect(screen.getByTestId("barra").dataset.variante).toBe("hero")
    expect(screen.queryByText(/não foi possível falar/i)).toBeNull()
    expect(screen.queryByText(/não está disponível/i)).toBeNull()
    expect(modal().dataset.modo).toBe("")
  })

  it("digitar + Enter abre o modal com a mensagem pendente; o texto FICA na barra; nada vai ao servidor", async () => {
    await mountAnonymous()
    const campo = await typeAndSend("focos de calor em MT")
    expect(store().entrada).toBe("entrar")
    expect(store().envioPendente).toBe("focos de calor em MT")
    expect(campo.value).toBe("focos de calor em MT")
    expect(modal().dataset.modo).toBe("entrar")
    expect(modal().dataset.pendente).toBe("true")
    expect(fakeFetch()).not.toHaveBeenCalled()
  })

  it("um chip e o botão Enviar também pedem a entrada", async () => {
    await mountAnonymous()
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: CHIPS[0] })) })
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Enviar" })) })
    expect(store().envioPendente).toBe(CHIPS[0])
    expect(modal().dataset.modo).toBe("entrar")
    expect(fakeFetch()).not.toHaveBeenCalled()
  })

  it("Enter no campo vazio manda a sugestão da vez ao modal", async () => {
    await mountAnonymous()
    const campo = screen.getByLabelText(/Mensagem para o assistente/i)
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })
    expect(SUGGESTIONS).toContain(store().envioPendente)
    expect(modal().dataset.modo).toBe("entrar")
  })

  it("fechar o modal sem entrar desiste do envio, mas o texto fica na barra", async () => {
    await mountAnonymous()
    const campo = await typeAndSend("focos de calor em MT")
    await act(async () => { fireEvent.click(screen.getByText("fechar-modal")) })
    expect(store().entrada).toBeNull()
    expect(store().envioPendente).toBeNull()
    expect(campo.value).toBe("focos de calor em MT")
    expect(modal().dataset.modo).toBe("")
  })

  it("o painel (Ctrl+I) abre para o anônimo com o convite, e o Enter dele também pede a entrada", async () => {
    await mountAnonymous()
    const campo = screen.getByLabelText(/Mensagem para o assistente/i)
    act(() => { campo.focus(); fireEvent.keyDown(campo, { key: "i", ctrlKey: true }) })
    await waitFor(() => expect(screen.queryByTestId("barra")).toBeNull())
    const painel = screen.getByLabelText("Assistente")
    expect(painel.textContent).toContain("O que você quer saber?")

    const textarea = screen.getByLabelText(/Mensagem para o assistente/i)
    await act(async () => { fireEvent.change(textarea, { target: { value: "cruze o CAR" } }) })
    await act(async () => { fireEvent.keyDown(textarea, { key: "Enter" }) })
    expect(store().entrada).toBe("entrar")
    expect(store().envioPendente).toBe("cruze o CAR")
    expect(fakeFetch()).not.toHaveBeenCalled()
  })

  it("o login deu certo: a mensagem pendente vai sozinha assim que o assistente responde", async () => {
    const r = await mountAnonymous()
    await typeAndSend("focos de calor em MT")
    expect(store().entrada).toBe("entrar")

    // The signIn (no redirect) updated the tab's session; the modal reports that it signed in.
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    const sse = [
      'event: conversa\ndata: {"conversa_id":"c1","nova":true}\n\n',
      'event: texto\ndata: {"texto":"Achei 1 284 focos."}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    fakeFetch().mockResolvedValue({ ok: true, body: sseBody(sse) })
    await act(async () => { fireEvent.click(screen.getByText("entrou-modal")) })
    withSession()
    r.rerender(<HomeView />)

    await waitFor(() => expect(fakeFetch()).toHaveBeenCalledTimes(1))
    const [url, init] = fakeFetch().mock.calls[0] as [string, RequestInit]
    expect(String(url)).toMatch(/\/assistente\/conversa$/)
    expect(JSON.parse(String(init.body)).mensagem).toBe("focos de calor em MT")
    expect(store().entrada).toBeNull()
    expect(store().envioPendente).toBeNull()
    expect(store().rascunho).toBe("")
    expect(servico.estadoDoAgente).toHaveBeenCalled()
    expect((await screen.findByTestId("pilha")).textContent).toContain("Achei 1 284 focos.")
  })

  it("com a cota estourada a mensagem fica na caixa, com o aviso — a regra da barra", async () => {
    const r = await mountAnonymous()
    const campo = await typeAndSend("focos de calor em MT")
    servico.estadoDoAgente.mockResolvedValue({
      success: true, data: { ativo: true, cota: { gasto: 10, teto: 10, reabre_em_segundos: 3600 } },
    })
    await act(async () => { fireEvent.click(screen.getByText("entrou-modal")) })
    withSession()
    r.rerender(<HomeView />)

    await screen.findByText(/cota de hoje/i)
    expect(fakeFetch()).not.toHaveBeenCalled()
    expect(store().envioPendente).toBe("focos de calor em MT")
    expect(campo.value).toBe("focos de calor em MT")
  })

  it("?cadastro=1 abre o modal na chegada — e, logado, a query é ignorada", async () => {
    await mountAnonymous({ entrada: "cadastro" })
    expect(modal().dataset.modo).toBe("cadastro")

    cleanup()
    useHomeStore.setState({ entrada: null })
    withSession()
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    render(<HomeView entrada="entrar" />)
    await waitFor(() => expect(servico.estadoDoAgente).toHaveBeenCalled())
    expect(modal().dataset.modo).toBe("")
  })

  it("os painéis do e-mail abrem COM sessão — é o link do e-mail chegando num navegador logado", async () => {
    // `entrar` and `cadastro` are ignored with a session (the test above). These
    // are not: someone who forgot their password, or has not verified their email yet, often has
    // an old session open in the same browser — with the `anonimo` gate
    // applying to everyone, the link opened the Home and did NOTHING.
    for (const modo of ["verificar", "recuperar", "redefinir"] as const) {
      cleanup()
      useHomeStore.setState({ entrada: null })
      withSession()
      servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
      render(<HomeView entrada={modo} tokenDoLink="tok-abc" />)
      await waitFor(() => expect(modal().dataset.modo).toBe(modo))
      expect(modal().dataset.token).toBe("tok-abc")
    }
  })

  it("a sessão chegando NÃO fecha um painel do e-mail: o token é de uso único", async () => {
    const r = await mountAnonymous()
    await act(async () => { store().pedirEntrada("verificar") })
    expect(modal().dataset.modo).toBe("verificar")

    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    withSession()
    r.rerender(<HomeView entrada="verificar" tokenDoLink="tok-abc" />)
    await waitFor(() => expect(servico.estadoDoAgente).toHaveBeenCalled())
    expect(store().entrada).toBe("verificar")
    expect(modal().dataset.modo).toBe("verificar")
  })

  it("com callbackUrl, entrar leva à página pedida — e o pendente não vai", async () => {
    const r = await mountAnonymous({ entrada: "entrar", callbackUrl: "/projects" })
    expect(modal().dataset.modo).toBe("entrar")
    await typeAndSend("focos de calor em MT")
    expect(store().envioPendente).toBe("focos de calor em MT")

    await act(async () => { fireEvent.click(screen.getByText("entrou-modal")) })
    expect(nav.push).toHaveBeenCalledWith("/projects")
    expect(nav.refresh).toHaveBeenCalled()
    expect(store().envioPendente).toBeNull()

    withSession()
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    r.rerender(<HomeView entrada="entrar" callbackUrl="/projects" />)
    await waitFor(() => expect(servico.estadoDoAgente).toHaveBeenCalled())
    expect(fakeFetch()).not.toHaveBeenCalled()
  })

  it("a sessão chegando noutra aba com o modal aberto o fecha e consulta o assistente", async () => {
    const r = await mountAnonymous()
    await act(async () => { store().pedirEntrada("entrar") })
    expect(modal().dataset.modo).toBe("entrar")

    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    withSession()
    r.rerender(<HomeView />)
    await waitFor(() => expect(servico.estadoDoAgente).toHaveBeenCalledTimes(1))
    expect(store().entrada).toBeNull()
    expect(await screen.findByTestId("uso-da-cota")).toBeTruthy()
  })

  it("Ctrl+I com o foco dentro de um diálogo não alterna o painel por trás", async () => {
    await mountAnonymous()
    const dialogo = document.createElement("div")
    dialogo.setAttribute("role", "dialog")
    const campo = document.createElement("input")
    dialogo.appendChild(campo)
    document.body.appendChild(dialogo)
    try {
      act(() => { campo.focus(); fireEvent.keyDown(campo, { key: "i", ctrlKey: true }) })
      expect(store().painel).toBe("barra")
    } finally {
      dialogo.remove()
    }
  })

  it("a sessão vencida conta como anônima: nada é consultado com o token velho", async () => {
    sessao.status = "authenticated"
    sessao.data = { user: { id_hash: "u1" }, error: "RefreshTokenExpired" }
    useHomeStore.setState({ painel: "barra" })
    render(<HomeView />)
    await screen.findByLabelText(/Mensagem para o assistente/i)
    expect(servico.estadoDoAgente).not.toHaveBeenCalled()
    expect(screen.queryByText(/não foi possível falar/i)).toBeNull()
  })
})
