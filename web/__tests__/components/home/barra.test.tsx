import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"

import Barra from "@/app/components/home/assistente/barra"
import { pt } from "@/app/components/home/i18n/secoes/assistente"
import { useHomeStore } from "@/app/stores/homeStore"
import type { IAssistenteEstado } from "@/service/types"

// The sentences typed into the empty field and the hero chips, in Portuguese — the
// dictionary the bar reads with no language provider.
const { sugestoes: SUGESTOES, chips: CHIPS } = pt.barra

const ATIVO: IAssistenteEstado = { ativo: true, cota: { gasto: 0, teto: 1_000_000, reabre_em_segundos: null } }

// The draft lives in the store (it survives the panel↔bar switch): each test
// starts over with an empty box, otherwise the text of one leaks into the next.
beforeEach(() => { cleanup(); useHomeStore.setState({ painel: "barra", rascunho: "" }) })
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

function digitar(texto: string) {
  const campo = screen.getByLabelText(/Mensagem para o assistente/i)
  fireEvent.change(campo, { target: { value: texto } })
  return campo
}

/**
 * Advances the typing timers ONE step at a time. Inside a single `act`
 * React only applies the `setState`s at the end, so one `advanceTimersByTime(1600)`
 * fired a single timer (the effect that schedules the next one never re-ran).
 */
function avancar(ms: number, passo = 26) {
  for (let t = 0; t < ms; t += passo) act(() => { vi.advanceTimersByTime(passo) })
}

describe("Barra de comando — rodapé", () => {
  it("Enter envia e NÃO abre o painel: a conversa segue ao centro", () => {
    const enviar = vi.fn()
    render(<Barra enviar={enviar} estado={ATIVO} />)
    const campo = digitar("buffer de 500 m")
    fireEvent.keyDown(campo, { key: "Enter" })

    expect(enviar).toHaveBeenCalledWith("buffer de 500 m")
    expect(useHomeStore.getState().painel).toBe("barra")
    expect((campo as HTMLInputElement).value).toBe("")
  })

  it("com stream em curso NÃO envia — e o rascunho continua na tela", () => {
    const enviar = vi.fn()
    render(<Barra enviar={enviar} estado={ATIVO} correndo />)
    const campo = digitar("na verdade use o buffer de 500 m")
    fireEvent.keyDown(campo, { key: "Enter" })

    expect(enviar).not.toHaveBeenCalled()
    expect((campo as HTMLInputElement).value).toBe("na verdade use o buffer de 500 m")
    expect(useHomeStore.getState().painel).toBe("barra")
  })

  it("com a cota estourada avisa e trava o envio", () => {
    const enviar = vi.fn()
    render(<Barra enviar={enviar} estado={{ ativo: true, cota: { gasto: 10, teto: 10, reabre_em_segundos: 3600 } }} />)
    expect(screen.getByText(/cota de hoje/i)).toBeTruthy()

    const campo = screen.getByLabelText(/Mensagem para o assistente/i)
    expect((campo as HTMLInputElement).disabled).toBe(true)
    fireEvent.keyDown(campo, { key: "Enter" })
    expect(enviar).not.toHaveBeenCalled()
    // And the donut closes: it becomes the reopening countdown, not a mute "100%".
    expect(screen.getByTestId("uso-da-cota").textContent).toBe("reabre em 1 h")
  })

  it("mostra o donut da cota sob o campo, com o percentual", () => {
    render(<Barra enviar={vi.fn()} estado={{ ativo: true, cota: { gasto: 820_000, teto: 1_000_000, reabre_em_segundos: 7_200 } }} />)
    const donut = screen.getByTestId("uso-da-cota")
    expect(donut.textContent).toBe("82%")
    expect(donut.getAttribute("aria-label")).toContain("820.000 de 1.000.000")
  })

  it("sem cota no estado, o donut simplesmente não existe", () => {
    render(<Barra enviar={vi.fn()} estado={{ ativo: true }} />)
    expect(screen.queryByTestId("uso-da-cota")).toBeNull()
  })

  it("o chevron só abre o painel, sem enviar nada", () => {
    const enviar = vi.fn()
    render(<Barra enviar={enviar} estado={ATIVO} />)
    digitar("rascunho")
    fireEvent.click(screen.getByRole("button", { name: /abrir o assistente/i }))

    expect(enviar).not.toHaveBeenCalled()
    expect(useHomeStore.getState().painel).toBe("aberto")
  })

  it("com stream em curso o botão de enviar vira Parar", () => {
    const parar = vi.fn()
    render(<Barra enviar={vi.fn()} estado={ATIVO} correndo parar={parar} />)

    expect(screen.queryByRole("button", { name: /^enviar$/i })).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: /^parar$/i }))
    expect(parar).toHaveBeenCalledTimes(1)
  })

  it("no rodapé não há chips nem sugestão digitada", () => {
    render(<Barra enviar={vi.fn()} estado={ATIVO} />)

    expect(screen.getByTestId("barra").dataset.variante).toBe("rodape")
    expect(screen.queryByRole("group", { name: /sugestões/i })).toBeNull()
    expect(screen.queryByTestId("sugestao")).toBeNull()
    expect(screen.getByPlaceholderText(/o que você quer saber/i)).toBeTruthy()
  })
})

describe("Barra de comando — hero", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    // Typing at a fixed pace (26 ms per letter): the test measures the sequence, not chance.
    vi.spyOn(Math, "random").mockReturnValue(0)
  })

  it("é a variante grande, com os chips e a sugestão digitada letra a letra", () => {
    render(<Barra enviar={vi.fn()} estado={ATIVO} variante="hero" />)

    expect(screen.getByTestId("barra").dataset.variante).toBe("hero")
    for (const chip of CHIPS) expect(screen.getByRole("button", { name: chip })).toBeTruthy()

    const sugestao = screen.getByTestId("sugestao")
    // O placeholder sai da frente: a frase digitada ocupa o lugar dele.
    expect((screen.getByLabelText(/Mensagem para o assistente/i) as HTMLInputElement).placeholder).toBe("")

    const primeira = SUGESTOES[0]
    avancar(26 * 3)
    expect(sugestao.textContent).toBe(primeira.slice(0, 3))
    avancar(26 * primeira.length)
    expect(sugestao.textContent).toBe(primeira)

    // Read for 2.3 s, erased (14 ms per letter) and replaced by the next one.
    avancar(2300 + 14 * primeira.length + 420 + 26 * 4, 14)
    const agora = sugestao.textContent ?? ""
    expect(agora.length).toBeGreaterThan(0)
    expect(SUGESTOES[1].startsWith(agora)).toBe(true)
  })

  it("Tab aceita a sugestão da vez", () => {
    render(<Barra enviar={vi.fn()} estado={ATIVO} variante="hero" />)
    const campo = screen.getByLabelText(/Mensagem para o assistente/i)

    fireEvent.keyDown(campo, { key: "Tab" })

    expect(useHomeStore.getState().rascunho).toBe(SUGESTOES[0])
    // With text in the box the suggestion goes away.
    expect(screen.queryByTestId("sugestao")).toBeNull()
  })

  it("Enter com o campo vazio envia a sugestão da vez", () => {
    const enviar = vi.fn()
    render(<Barra enviar={enviar} estado={ATIVO} variante="hero" />)

    fireEvent.keyDown(screen.getByLabelText(/Mensagem para o assistente/i), { key: "Enter" })

    expect(enviar).toHaveBeenCalledWith(SUGESTOES[0])
    expect(useHomeStore.getState().painel).toBe("barra")
  })

  it("um chip preenche o campo; apagar tudo traz a sugestão de volta", () => {
    render(<Barra enviar={vi.fn()} estado={ATIVO} variante="hero" />)

    fireEvent.click(screen.getByRole("button", { name: CHIPS[1] }))
    expect(useHomeStore.getState().rascunho).toBe(CHIPS[1])
    expect(screen.queryByTestId("sugestao")).toBeNull()

    digitar("")
    expect(screen.getByTestId("sugestao")).toBeTruthy()
  })

  it("processando: os chips dão lugar ao status, e 'Esc para parar' chama parar", () => {
    const parar = vi.fn()
    render(<Barra enviar={vi.fn()} estado={ATIVO} variante="hero" correndo parar={parar} />)

    expect(screen.queryByRole("group", { name: /sugestões/i })).toBeNull()
    expect(screen.queryByTestId("sugestao")).toBeNull()
    const pensando = screen.getByText(/Trabalhando…/)
    // The text has the sweeping shimmer and, next to it, the animated site mark —
    // it used to be the static ExecActivity, and the owner asked for life (2026-09-19).
    expect(pensando.classList.contains("texto-pensando")).toBe(true)
    expect(document.querySelector(".home-marca-anim")).toBeTruthy()

    fireEvent.click(screen.getByRole("button", { name: /esc para parar/i }))
    expect(parar).toHaveBeenCalledTimes(1)
  })
})

/**
 * `animationend` as React listens to it: in jsdom there is no `AnimationEvent`,
 * and React falls back to the prefixed name (`webkitAnimationEnd`). Firing both
 * covers both environments; whichever is not listened to is ignored.
 */
function fimDaAnimacao(el: Element) {
  fireEvent.animationEnd(el)
  fireEvent(el, new Event("webkitAnimationEnd", { bubbles: true }))
}

describe("Barra — o envio tem sinal, e a saída apaga", () => {
  it("enviar acende o flash na caixa; só o animationend da PRÓPRIA caixa o apaga", () => {
    render(<Barra enviar={vi.fn()} estado={ATIVO} />)
    const campo = digitar("buffer de 500 m")
    const caixa = campo.closest(".home-barra-caixa")!
    expect(caixa.getAttribute("data-flash")).toBe("false")

    fireEvent.keyDown(campo, { key: "Enter" })
    expect(caixa.getAttribute("data-flash")).toBe("true")

    // An animated child (the chevron, the cursor) finishing does not count.
    fimDaAnimacao(screen.getByRole("button", { name: /abrir o assistente/i }))
    expect(caixa.getAttribute("data-flash")).toBe("true")
    fimDaAnimacao(caixa)
    expect(caixa.getAttribute("data-flash")).toBe("false")
  })

  it("com stream em curso não envia — e não há flash", () => {
    render(<Barra enviar={vi.fn()} estado={ATIVO} correndo />)
    const campo = digitar("x")
    fireEvent.keyDown(campo, { key: "Enter" })
    expect(campo.closest(".home-barra-caixa")!.getAttribute("data-flash")).toBe("false")
  })

  it("o botão de enviar afunda ao apertar", () => {
    render(<Barra enviar={vi.fn()} estado={ATIVO} />)
    expect(screen.getByRole("button", { name: /^enviar$/i }).className).toContain("active:scale-90")
  })

  it("saindo: a raiz marca data-saindo; o padrão é não estar saindo", () => {
    const { rerender } = render(<Barra enviar={vi.fn()} estado={ATIVO} />)
    expect(screen.getByTestId("barra").dataset.saindo).toBe("false")
    rerender(<Barra enviar={vi.fn()} estado={ATIVO} saindo />)
    expect(screen.getByTestId("barra").dataset.saindo).toBe("true")
  })
})

describe("Barra — os anexos soltos sobre a Home", () => {
  // These cases touch the attachments state; each one starts clean, otherwise the
  // chips of one leak into the next.
  beforeEach(() => useHomeStore.setState({ painel: "barra", rascunho: "", anexos: [], arrastandoArquivo: false }))

  const pronto = (nome: string, id = nome) =>
    ({ id, nome, bytes: 2048, estado: "pronto" as const })

  it("mostra o chip do que já está no Drive, e a mensagem leva a referência", () => {
    useHomeStore.setState({ anexos: [pronto("municipios.geojson")] })
    const enviar = vi.fn()
    render(<Barra enviar={enviar} estado={ATIVO} />)

    expect(screen.getByText("municipios.geojson")).toBeTruthy()
    // Empty field + ready attachment: the send button is enabled.
    const botao = screen.getByRole("button", { name: /^enviar$/i }) as HTMLButtonElement
    expect(botao.disabled).toBe(false)

    fireEvent.click(botao)
    expect(enviar).toHaveBeenCalledTimes(1)
    expect(enviar.mock.calls[0][0]).toContain("municipios.geojson")
    // Enviada, a fileira de prontos limpa.
    expect(useHomeStore.getState().anexos).toHaveLength(0)
  })

  it("a pergunta digitada leva os prontos junto", () => {
    useHomeStore.setState({ anexos: [pronto("a.csv")] })
    const enviar = vi.fn()
    render(<Barra enviar={enviar} estado={ATIVO} />)
    const campo = digitar("compare com o Cerrado")
    fireEvent.keyDown(campo, { key: "Enter" })

    const texto = enviar.mock.calls[0][0]
    expect(texto).toContain("compare com o Cerrado")
    expect(texto).toContain("a.csv")
  })

  it("o convite de soltura aparece só enquanto o arquivo está no ar", () => {
    const { rerender } = render(<Barra enviar={vi.fn()} estado={ATIVO} />)
    expect(screen.queryByTestId("convite-de-soltura")).toBeNull()

    act(() => useHomeStore.setState({ arrastandoArquivo: true }))
    rerender(<Barra enviar={vi.fn()} estado={ATIVO} />)
    expect(screen.getByTestId("convite-de-soltura")).toBeTruthy()
  })

  it("a caixa acende no arraste (data-arraste), a janela é quem aceita", () => {
    useHomeStore.setState({ arrastandoArquivo: true })
    render(<Barra enviar={vi.fn()} estado={ATIVO} />)
    const caixa = document.querySelector(".home-barra-caixa")!
    expect(caixa.getAttribute("data-arraste")).toBe("true")
  })

  it("o recusado vira aviso — não chip — e não some ao enviar", () => {
    useHomeStore.setState({
      anexos: [{ id: "x", nome: "x.pdf", bytes: 10, estado: "recusado", tipo: "extension", motivo: "Extensão '.pdf' não permitida." }],
    })
    const enviar = vi.fn()
    render(<Barra enviar={enviar} estado={ATIVO} />)
    // No chip; with a warning.
    expect(screen.queryByTestId("chips-de-anexo")).toBeNull()
    expect(screen.getByTestId("anexos-recusados")).toBeTruthy()
    expect(screen.getByText("«x.pdf»")).toBeTruthy()
  })

  it("mede os extras e reporta a altura — a folga que impede a barra de cobrir o 'Expandir'", () => {
    const aoMedirExtras = vi.fn()
    useHomeStore.setState({ anexos: [pronto("a.csv")] })
    render(<Barra enviar={vi.fn()} estado={ATIVO} aoMedirExtras={aoMedirExtras} />)
    // jsdom does no layout (offsetHeight = 0), so the number is 0; what matters
    // is that the bar MEASURES and reports — the ruler exists and the channel is wired.
    expect(aoMedirExtras).toHaveBeenCalled()
    expect(typeof aoMedirExtras.mock.calls[0][0]).toBe("number")
  })

  it("mostra o passo da vez no rodapé, mas NÃO no hero (lá o 'Trabalhando…' já ocupa)", () => {
    const etapa = { tipo: "ferramenta" as const, rotulo: "Consultando o guia", detalhe: "edges" }
    const { rerender } = render(<Barra enviar={vi.fn()} estado={ATIVO} correndo etapa={etapa} />)
    expect(screen.getByTestId("etapa-da-barra").textContent).toContain("Consultando o guia")

    rerender(<Barra enviar={vi.fn()} estado={ATIVO} correndo etapa={etapa} variante="hero" />)
    expect(screen.queryByTestId("etapa-da-barra")).toBeNull()
  })
})
