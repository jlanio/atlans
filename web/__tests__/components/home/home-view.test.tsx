import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"

/**
 * A HomeView montada. jsdom não desenha o MapLibre nem faz layout, então o que
 * se confere aqui é o CONTRATO de estado: qual superfície aparece em cada
 * resposta do `/assistente/estado`, o atalho que alterna nos dois sentidos, a fila
 * de camadas do sidebar e o ciclo de vida das camadas na troca de conversa.
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
    default: React.forwardRef(function MapLibreFalso(p: { giroLento?: boolean }) {
      // `data-giro` expõe o que a HomeView pediu ao globo: girar no hero, parar depois.
      return React.createElement("div", { "data-testid": "maplibre", "data-giro": String(!!p.giroLento) })
    }),
  }
})

// A sessão é MUTÁVEL: a Home abre sem sessão, e é o status que decide a casca.
// Padrão "authenticated" — os testes de sempre não mudam.
const sessao = vi.hoisted(() => ({
  status: "authenticated" as "authenticated" | "unauthenticated" | "loading",
  data: { user: { id_hash: "u1" } } as Record<string, unknown> | null,
}))
vi.mock("next-auth/react", () => ({ useSession: () => ({ data: sessao.data, status: sessao.status }) }))
const nav = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }))
vi.mock("next/navigation", () => ({ useRouter: () => nav }))
// O modal de entrada tem teste próprio; aqui é um marcador que expõe o modo
// pedido e a frase de apoio, e dois botões: fechar sem entrar e "entrou".
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
import { IdiomaProvider, useIdioma } from "@/context/IdiomaContext"

// As frases e os chips do hero em português (o dicionário que a barra lê).
const { sugestoes: SUGESTOES, chips: CHIPS } = pt.barra

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
  // Chamar não é responder: a Home só sai do esqueleto de carregamento no
  // `.then` do useAssistente. Sem esperar a resposta ser aplicada, quem lê a
  // barra logo depois do montar() às vezes pega o esqueleto (runner lento).
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
    // O `motivo` vem em português e fala com quem administra ("defina
    // OPENROUTER_API_KEY"); fora do português vale o aviso do dicionário.
    servico.estadoDoAgente.mockResolvedValue({
      success: true, data: { ativo: false, motivo: "O assistente está desligado. Defina OPENROUTER_API_KEY." },
    })
    render(
      <IdiomaProvider inicial={{ idioma: "en", detectado: "en", escolhido: "en" }}>
        <HomeView />
      </IdiomaProvider>,
    )
    expect(await screen.findByText("The assistant isn’t available on this installation.")).toBeTruthy()
    expect(screen.queryByText(/OPENROUTER_API_KEY/)).toBeNull()
  })

  it("Ctrl+I recolhe E reabre com o cursor no campo, sem perder o rascunho", async () => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    await montar()
    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)

    // O keydown sai DO CAMPO — que é onde o cursor está quando alguém digita —
    // e sobe até o window. Disparado direto em `window`, o alvo do evento seria
    // a janela, e o teste passaria mesmo com o atalho ignorando o foco.
    act(() => {
      fireEvent.change(campo, { target: { value: "buffer de 500 m" } })
      campo.focus()
      fireEvent.keyDown(campo, { key: "i", ctrlKey: true })
    })
    expect(useHomeStore.getState().painel).toBe("barra")

    // Recolher DESMONTA o painel: o texto tem de reaparecer na barra.
    const naBarra = screen.getByLabelText(/Mensagem para o assistente/i) as HTMLInputElement
    expect(naBarra.value).toBe("buffer de 500 m")

    act(() => {
      naBarra.focus()
      fireEvent.keyDown(naBarra, { key: "i", ctrlKey: true })
    })
    expect(useHomeStore.getState().painel).toBe("aberto")
    // A barra ainda está saindo (fade) por um instante; o campo do painel é o textarea.
    await waitFor(() => expect(screen.queryByTestId("barra")).toBeNull())
    const deVolta = screen.getByLabelText(/Mensagem para o assistente/i) as HTMLTextAreaElement
    expect(deVolta.value).toBe("buffer de 500 m")
  })
})

describe("HomeView — o lang do <html>", () => {
  function TrocarPara({ idioma }: { idioma: "es" }) {
    const { escolher } = useIdioma()
    return <button onClick={() => escolher(idioma)}>trocar</button>
  }

  it("segue o idioma da Home e volta ao de antes quando ela sai", async () => {
    // O do <html> cobre o que o Radix porta para o <body>; o resto do app é
    // português, então sair da Home devolve o valor de antes.
    document.documentElement.lang = "pt-BR"
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    const { unmount } = render(
      <IdiomaProvider inicial={{ idioma: "en", detectado: "en", escolhido: null }}>
        <HomeView />
        <TrocarPara idioma="es" />
      </IdiomaProvider>,
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
    // O 1º quadro do SSE ensina o id da conversa: o `conversaId` vai de null a
    // um id sem que a conversa tenha mudado — e as camadas são dela. O anúncio
    // inteiro (id, título, nova) fica na store para a lista de Chats, que aqui
    // não está montada: é ela que insere a linha sem F5.
    const sse = [
      'event: conversa\ndata: {"conversa_id":"c9","titulo":"focos","nova":true}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(async (url: string) => {
      if (String(url).includes("/assistente/conversa")) {
        return { ok: true, body: corpoSSE(sse) }
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
    // O id anunciado pelo stream vale para UMA troca — a que ele mesmo causou.
    // Guardado para sempre, ele dizia "esta conversa nunca é outra", e voltar a
    // ela pelos Chats deixava no globo as camadas do chat anterior.
    const sse = [
      'event: conversa\ndata: {"conversa_id":"c9","nova":true}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(async (url: string) => {
      if (String(url).includes("/assistente/conversa")) return { ok: true, body: corpoSSE(sse) }
      return { ok: true, json: async () => ({ type: "FeatureCollection", features: [] }) }
    })

    await montar()
    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    await act(async () => { fireEvent.change(campo, { target: { value: "e agora?" } }) })
    await act(async () => { fireEvent.submit(campo.closest("form")!) })
    await waitFor(() => expect(useHomeStore.getState().conversaId).toBe("c9"))

    // Outro chat, e uma camada posta LÁ.
    await act(async () => { useHomeStore.getState().selecionarConversa("z") })
    await act(async () => { useHomeStore.getState().pedirCamada("a2", "Outra") })
    await screen.findByText("Outra")

    // De volta a c9 pelos Chats: é outra conversa, e o globo é da conversa.
    await act(async () => { useHomeStore.getState().selecionarConversa("c9") })
    await waitFor(() => expect(screen.queryByText("Outra")).toBeNull())
  })
})

describe("HomeView — o hero do primeiro acesso", () => {
  beforeEach(() => {
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    // Todo acesso começa na barra; o painel é sob demanda.
    useHomeStore.setState({ painel: "barra" })
  })

  function veu() { return document.querySelector(".home-veu")?.getAttribute("data-visivel") }
  function textoDoHero() { return document.querySelector(".home-hero-texto")?.getAttribute("data-visivel") ?? null }

  it("é o estado inicial: título, chips, barra grande e véu — sem painel nem pilha", async () => {
    await montar()

    expect(screen.getByRole("heading", { name: /menos ferramentas\. mais respostas/i })).toBeTruthy()
    expect(screen.getByRole("group", { name: /sugestões/i })).toBeTruthy()
    expect(screen.getByTestId("barra").dataset.variante).toBe("hero")
    expect(veu()).toBe("true")
    expect(screen.queryByLabelText("Assistente")).toBeNull()
    expect(screen.queryByTestId("pilha")).toBeNull()
    // O globo gira devagar enquanto o hero está na tela.
    expect(screen.getByTestId("maplibre").dataset.giro).toBe("true")
  })

  it("termina no PRIMEIRO TOKEN: a barra vai ao rodapé, o véu some e a troca aparece ao centro", async () => {
    const sse = [
      'event: conversa\ndata: {"conversa_id":"c1","nova":true}\n\n',
      'event: pensando\ndata: {"texto":"preciso do catálogo"}\n\n',
      'event: texto\ndata: {"texto":"Achei 1 284 focos."}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, body: corpoSSE(sse) })
    await montar()

    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    // Dois `act`: dentro de um só, o keyDown veria o render ANTERIOR ao change
    // (campo vazio → mandaria a sugestão da vez). No navegador são duas tarefas.
    await act(async () => { fireEvent.change(campo, { target: { value: "focos de calor em MT" } }) })
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })

    const pilha = await screen.findByTestId("pilha")
    expect(pilha.textContent).toContain("focos de calor em MT")
    expect(pilha.textContent).toContain("Achei 1 284 focos.")
    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")
    expect(veu()).toBe("false")
    // O giro para — e o mapa volta ao Brasil (o `center` do Globo).
    expect(screen.getByTestId("maplibre").dataset.giro).toBe("false")
    // O título fica no DOM até a transição acabar, já invisível.
    expect(textoDoHero()).toBe("false")
    // E o painel continua fechado: a conversa está ao centro.
    expect(useHomeStore.getState().painel).toBe("barra")
  })

  it("a resposta traz respostas rápidas; clicar uma manda a frase como a próxima mensagem", async () => {
    const comChips = [
      'event: conversa\ndata: {"conversa_id":"c1","nova":true}\n\n',
      'event: texto\ndata: {"texto":"Achei 1 284 focos."}\n\n',
      'event: respostas_rapidas\ndata: {"opcoes":["Só os últimos 7 dias","Cruzar com o CAR"]}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    const semChips = [
      'event: conversa\ndata: {"conversa_id":"c1","nova":false}\n\n',
      'event: texto\ndata: {"texto":"Cruzei: 37 sobreposições."}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    const fila = [comChips, semChips]
    const fetchFalso = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    fetchFalso.mockImplementation(async () => ({ ok: true, body: corpoSSE(fila.shift() ?? semChips) }))
    await montar()

    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    await act(async () => { fireEvent.change(campo, { target: { value: "focos de calor em MT" } }) })
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })

    const chip = await screen.findByRole("button", { name: "Cruzar com o CAR" })
    await act(async () => { fireEvent.click(chip) })

    // O segundo POST leva a frase do chip; e o turno novo tira os chips da tela.
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(2))
    const corpos = fetchFalso.mock.calls.map((c) => JSON.parse(String((c[1] as RequestInit).body)) as { mensagem: string })
    expect(corpos.map((b) => b.mensagem)).toEqual(["focos de calor em MT", "Cruzar com o CAR"])
    await screen.findByText(/37 sobreposições/)
    expect(screen.queryByRole("button", { name: "Cruzar com o CAR" })).toBeNull()
    expect(screen.queryByRole("group", { name: /respostas rápidas/i })).toBeNull()
  })

  it("enviar encerra o hero na hora — a faixa carrega antes do 1º token — e Esc interrompe", async () => {
    // Um stream que nunca entrega nada: fica no raciocínio até a pessoa desistir.
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: { getReader: () => ({ read: () => new Promise(() => {}), cancel: async () => {} }) },
    })
    await montar()

    const campo = await screen.findByLabelText(/Mensagem para o assistente/i)
    // Dois `act`: dentro de um só, o keyDown veria o render ANTERIOR ao change
    // (campo vazio → mandaria a sugestão da vez). No navegador são duas tarefas.
    await act(async () => { fireEvent.change(campo, { target: { value: "focos de calor em MT" } }) })
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })

    // O ENVIO já desce a barra: a faixa aparece com a pergunta e o indicador de
    // raciocínio, mesmo SEM nenhum token de texto ainda. É o conserto do bug do
    // dono — a barra não fica travada no centro durante o raciocínio/ferramentas.
    const pilha = await screen.findByTestId("pilha")
    expect(pilha.textContent).toContain("focos de calor em MT")
    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")
    expect(screen.queryByRole("group", { name: /sugestões/i })).toBeNull()

    await act(async () => { fireEvent.keyDown(campo, { key: "Escape" }) })

    await waitFor(() => expect(screen.getByTestId("pilha").textContent).toContain("Resposta interrompida."))
    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")
  })

  it("no rodapé, a barra mostra o PASSO da vez durante raciocínio e ferramentas — e o esconde na escrita", async () => {
    // Um corpo SSE que entrega os pedaços SOB DEMANDA: é o único jeito de
    // assertar o MEIO do stream (o corpoSSE de sempre entrega tudo de uma vez).
    const enc = new TextEncoder()
    let resolver: ((r: { done: boolean; value?: Uint8Array }) => void) | null = null
    const fila: { done: boolean; value?: Uint8Array }[] = []
    const empurrar = (texto: string | null) => {
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

    // Raciocínio: a barra já desceu e o passo diz "Pensando…".
    await act(async () => {
      empurrar('event: conversa\ndata: {"conversa_id":"c1","nova":true}\n\nevent: pensando\ndata: {"texto":"preciso do catálogo"}\n\n')
    })
    await waitFor(() => expect(screen.getByTestId("etapa-da-barra").textContent).toContain("Pensando"))
    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")

    // Ferramenta em curso: o passo troca para o RÓTULO dela, com o detalhe —
    // é o "indicar as etapas" que o dono pediu.
    await act(async () => {
      empurrar('event: ferramenta\ndata: {"id":"t1","nome":"get_authoring_guide","argumentos":{"topic":"edges"}}\n\n')
    })
    await waitFor(() => expect(screen.getByTestId("etapa-da-barra").textContent).toContain("Consultando o guia"))
    expect(screen.getByTestId("etapa-da-barra").textContent).toContain("edges")

    // Escrevendo: o passo some — a resposta já aparece na faixa.
    await act(async () => {
      empurrar('event: texto\ndata: {"texto":"Achei 1 284 focos."}\n\nevent: fim\ndata: {"ok":true}\n\n')
      empurrar(null)
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
    // O cursor foi para o campo do painel (o textarea): a barra, saindo, não o rouba.
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

    // E é o MESMO nó depois do prazo: um timer que sobrevivesse ao cancelamento
    // desmontaria e remontaria a barra — um piscar, com a entrada de novo.
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

    // O mesmo caminho do clique na lista de Artefatos do sidebar.
    await act(async () => { useHomeStore.getState().pedirCamada("a1", "Focos") })

    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")
    expect(veu()).toBe("false")
    expect(textoDoHero()).toBe("false")
    // O globo girando contra o enquadramento da camada nova era metade do bug.
    expect(screen.getByTestId("maplibre").dataset.giro).toBe("false")
  })
})

/** Um corpo de resposta que entrega o SSE em um pedaço só. */
function corpoSSE(texto: string) {
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
      if (String(url).includes("/assistente/conversa")) return { ok: true, body: corpoSSE(sse) }
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
  const fetchFalso = () => globalThis.fetch as unknown as ReturnType<typeof vi.fn>

  function semSessao() {
    sessao.status = "unauthenticated"
    sessao.data = null
  }
  function comSessao() {
    sessao.status = "authenticated"
    sessao.data = { user: { id_hash: "u1" } }
  }
  /** Monta anônimo e afirma o essencial: a barra está lá e NADA foi consultado. */
  async function montarAnonimo(props: React.ComponentProps<typeof HomeView> = {}) {
    semSessao()
    useHomeStore.setState({ painel: "barra" })
    const r = render(<HomeView {...props} />)
    await screen.findByLabelText(/Mensagem para o assistente/i)
    expect(servico.estadoDoAgente).not.toHaveBeenCalled()
    return r
  }
  async function digitarEEnviar(texto: string) {
    const campo = screen.getByLabelText(/Mensagem para o assistente/i) as HTMLInputElement
    await act(async () => { fireEvent.change(campo, { target: { value: texto } }) })
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })
    return campo
  }

  it("o hero inteiro, sem consultar o assistente e sem aviso; o modal fechado", async () => {
    await montarAnonimo()
    expect(screen.getByRole("heading", { name: /menos ferramentas\. mais respostas/i })).toBeTruthy()
    expect(screen.getByRole("group", { name: /sugestões/i })).toBeTruthy()
    expect(screen.getByTestId("barra").dataset.variante).toBe("hero")
    expect(screen.queryByText(/não foi possível falar/i)).toBeNull()
    expect(screen.queryByText(/não está disponível/i)).toBeNull()
    expect(modal().dataset.modo).toBe("")
  })

  it("digitar + Enter abre o modal com a mensagem pendente; o texto FICA na barra; nada vai ao servidor", async () => {
    await montarAnonimo()
    const campo = await digitarEEnviar("focos de calor em MT")
    expect(store().entrada).toBe("entrar")
    expect(store().envioPendente).toBe("focos de calor em MT")
    expect(campo.value).toBe("focos de calor em MT")
    expect(modal().dataset.modo).toBe("entrar")
    expect(modal().dataset.pendente).toBe("true")
    expect(fetchFalso()).not.toHaveBeenCalled()
  })

  it("um chip e o botão Enviar também pedem a entrada", async () => {
    await montarAnonimo()
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: CHIPS[0] })) })
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Enviar" })) })
    expect(store().envioPendente).toBe(CHIPS[0])
    expect(modal().dataset.modo).toBe("entrar")
    expect(fetchFalso()).not.toHaveBeenCalled()
  })

  it("Enter no campo vazio manda a sugestão da vez ao modal", async () => {
    await montarAnonimo()
    const campo = screen.getByLabelText(/Mensagem para o assistente/i)
    await act(async () => { fireEvent.keyDown(campo, { key: "Enter" }) })
    expect(SUGESTOES).toContain(store().envioPendente)
    expect(modal().dataset.modo).toBe("entrar")
  })

  it("fechar o modal sem entrar desiste do envio, mas o texto fica na barra", async () => {
    await montarAnonimo()
    const campo = await digitarEEnviar("focos de calor em MT")
    await act(async () => { fireEvent.click(screen.getByText("fechar-modal")) })
    expect(store().entrada).toBeNull()
    expect(store().envioPendente).toBeNull()
    expect(campo.value).toBe("focos de calor em MT")
    expect(modal().dataset.modo).toBe("")
  })

  it("o painel (Ctrl+I) abre para o anônimo com o convite, e o Enter dele também pede a entrada", async () => {
    await montarAnonimo()
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
    expect(fetchFalso()).not.toHaveBeenCalled()
  })

  it("o login deu certo: a mensagem pendente vai sozinha assim que o assistente responde", async () => {
    const r = await montarAnonimo()
    await digitarEEnviar("focos de calor em MT")
    expect(store().entrada).toBe("entrar")

    // O signIn (sem redirect) atualizou a sessão da aba; o modal avisa que entrou.
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    const sse = [
      'event: conversa\ndata: {"conversa_id":"c1","nova":true}\n\n',
      'event: texto\ndata: {"texto":"Achei 1 284 focos."}\n\n',
      'event: fim\ndata: {"ok":true}\n\n',
    ].join("")
    fetchFalso().mockResolvedValue({ ok: true, body: corpoSSE(sse) })
    await act(async () => { fireEvent.click(screen.getByText("entrou-modal")) })
    comSessao()
    r.rerender(<HomeView />)

    await waitFor(() => expect(fetchFalso()).toHaveBeenCalledTimes(1))
    const [url, init] = fetchFalso().mock.calls[0] as [string, RequestInit]
    expect(String(url)).toMatch(/\/assistente\/conversa$/)
    expect(JSON.parse(String(init.body)).mensagem).toBe("focos de calor em MT")
    expect(store().entrada).toBeNull()
    expect(store().envioPendente).toBeNull()
    expect(store().rascunho).toBe("")
    expect(servico.estadoDoAgente).toHaveBeenCalled()
    expect((await screen.findByTestId("pilha")).textContent).toContain("Achei 1 284 focos.")
  })

  it("com a cota estourada a mensagem fica na caixa, com o aviso — a regra da barra", async () => {
    const r = await montarAnonimo()
    const campo = await digitarEEnviar("focos de calor em MT")
    servico.estadoDoAgente.mockResolvedValue({
      success: true, data: { ativo: true, cota: { gasto: 10, teto: 10, reabre_em_segundos: 3600 } },
    })
    await act(async () => { fireEvent.click(screen.getByText("entrou-modal")) })
    comSessao()
    r.rerender(<HomeView />)

    await screen.findByText(/cota de hoje/i)
    expect(fetchFalso()).not.toHaveBeenCalled()
    expect(store().envioPendente).toBe("focos de calor em MT")
    expect(campo.value).toBe("focos de calor em MT")
  })

  it("?cadastro=1 abre o modal na chegada — e, logado, a query é ignorada", async () => {
    await montarAnonimo({ entrada: "cadastro" })
    expect(modal().dataset.modo).toBe("cadastro")

    cleanup()
    useHomeStore.setState({ entrada: null })
    comSessao()
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    render(<HomeView entrada="entrar" />)
    await waitFor(() => expect(servico.estadoDoAgente).toHaveBeenCalled())
    expect(modal().dataset.modo).toBe("")
  })

  it("os painéis do e-mail abrem COM sessão — é o link do e-mail chegando num navegador logado", async () => {
    // `entrar` e `cadastro` são ignorados com sessão (o teste acima). Estes
    // não: quem esqueceu a senha, ou ainda não verificou o e-mail, costuma ter
    // uma sessão velha aberta no mesmo navegador — com o portão de `anonimo`
    // valendo para todos, o link abria a Home e não fazia NADA.
    for (const modo of ["verificar", "recuperar", "redefinir"] as const) {
      cleanup()
      useHomeStore.setState({ entrada: null })
      comSessao()
      servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
      render(<HomeView entrada={modo} tokenDoLink="tok-abc" />)
      await waitFor(() => expect(modal().dataset.modo).toBe(modo))
      expect(modal().dataset.token).toBe("tok-abc")
    }
  })

  it("a sessão chegando NÃO fecha um painel do e-mail: o token é de uso único", async () => {
    const r = await montarAnonimo()
    await act(async () => { store().pedirEntrada("verificar") })
    expect(modal().dataset.modo).toBe("verificar")

    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    comSessao()
    r.rerender(<HomeView entrada="verificar" tokenDoLink="tok-abc" />)
    await waitFor(() => expect(servico.estadoDoAgente).toHaveBeenCalled())
    expect(store().entrada).toBe("verificar")
    expect(modal().dataset.modo).toBe("verificar")
  })

  it("com callbackUrl, entrar leva à página pedida — e o pendente não vai", async () => {
    const r = await montarAnonimo({ entrada: "entrar", callbackUrl: "/projects" })
    expect(modal().dataset.modo).toBe("entrar")
    await digitarEEnviar("focos de calor em MT")
    expect(store().envioPendente).toBe("focos de calor em MT")

    await act(async () => { fireEvent.click(screen.getByText("entrou-modal")) })
    expect(nav.push).toHaveBeenCalledWith("/projects")
    expect(nav.refresh).toHaveBeenCalled()
    expect(store().envioPendente).toBeNull()

    comSessao()
    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    r.rerender(<HomeView entrada="entrar" callbackUrl="/projects" />)
    await waitFor(() => expect(servico.estadoDoAgente).toHaveBeenCalled())
    expect(fetchFalso()).not.toHaveBeenCalled()
  })

  it("a sessão chegando noutra aba com o modal aberto o fecha e consulta o assistente", async () => {
    const r = await montarAnonimo()
    await act(async () => { store().pedirEntrada("entrar") })
    expect(modal().dataset.modo).toBe("entrar")

    servico.estadoDoAgente.mockResolvedValue({ success: true, data: ATIVO })
    comSessao()
    r.rerender(<HomeView />)
    await waitFor(() => expect(servico.estadoDoAgente).toHaveBeenCalledTimes(1))
    expect(store().entrada).toBeNull()
    expect(await screen.findByTestId("uso-da-cota")).toBeTruthy()
  })

  it("Ctrl+I com o foco dentro de um diálogo não alterna o painel por trás", async () => {
    await montarAnonimo()
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
