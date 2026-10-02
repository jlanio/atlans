import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

/**
 * O "+" do compositor (a opção B') e o chip de localização.
 *
 * "Anexar arquivo" cai no MESMO caminho do arrasta-e-solta (useAnexos.receber),
 * agora com um lar descobrível; "Usar minha localização" aciona o controle do
 * globo. O chip é o espelho dos de anexo: à vista, com o ×, lendo a store.
 */
import { BotaoMais, ChipDeLocalizacao } from "@/app/components/home/assistente/mais"
import { useHomeStore } from "@/app/stores/homeStore"

beforeEach(() => { cleanup(); useHomeStore.setState({ localizacao: null, compartilharLocalizacao: false }) })
afterEach(() => vi.restoreAllMocks())

describe("BotaoMais — o \"+\" do compositor", () => {
  it("«Anexar arquivo» leva os arquivos escolhidos ao mesmo caminho do arraste", () => {
    const aoAnexar = vi.fn()
    render(<BotaoMais aoAnexar={aoAnexar} aoLocalizar={vi.fn()} />)
    const input = screen.getByTestId("entrada-de-arquivo") as HTMLInputElement
    const arquivo = new File(["x"], "municipios.shp")
    fireEvent.change(input, { target: { files: [arquivo] } })
    expect(aoAnexar).toHaveBeenCalledTimes(1)
    expect(aoAnexar.mock.calls[0][0][0].name).toBe("municipios.shp")
    // Zera para que reescolher o MESMO arquivo dispare o change de novo.
    expect(input.value).toBe("")
  })

  it("o item «Anexar arquivo» do menu abre o seletor (o click do input)", () => {
    // O caminho menu → seletor, e não só o change do input: sem isto o item
    // podia apontar para o nada e a suíte seguia verde.
    const click = vi.spyOn(HTMLInputElement.prototype, "click")
    render(<BotaoMais aoAnexar={vi.fn()} aoLocalizar={vi.fn()} />)
    fireEvent.keyDown(screen.getByRole("button", { name: /anexar/i }), { key: "Enter" })
    fireEvent.click(screen.getByRole("menuitem", { name: /Anexar arquivo/i }))
    expect(click).toHaveBeenCalledTimes(1)
  })

  it("«Usar minha localização» aciona o pedido de localização", () => {
    const aoLocalizar = vi.fn()
    render(<BotaoMais aoAnexar={vi.fn()} aoLocalizar={aoLocalizar} />)
    fireEvent.keyDown(screen.getByRole("button", { name: /localiza/i }), { key: "Enter" })
    fireEvent.click(screen.getByRole("menuitem", { name: /Usar minha localização/i }))
    expect(aoLocalizar).toHaveBeenCalledTimes(1)
  })
})

describe("ChipDeLocalizacao", () => {
  it("sem compartilhar ligado, não renderiza — mesmo com posição na store", () => {
    // O botão nativo do globo grava a posição (última conhecida), mas só o
    // gesto do "+" a põe na conversa.
    useHomeStore.setState({ localizacao: { lat: 1, lon: 2, precisao_m: 5 } })
    render(<ChipDeLocalizacao />)
    expect(screen.queryByTestId("chip-de-localizacao")).toBeNull()
  })

  it("mostra a coordenada e a precisão; o × desliga o compartilhar e PERSISTE", () => {
    useHomeStore.setState({
      compartilharLocalizacao: true,
      localizacao: { lat: -23.5505, lon: -46.6333, precisao_m: 18 },
    })
    render(<ChipDeLocalizacao />)
    const chip = screen.getByTestId("chip-de-localizacao")
    expect(chip.textContent).toContain("-23.5505, -46.6333")
    expect(chip.textContent).toContain("±18 m")

    fireEvent.click(screen.getByRole("button", { name: /Tirar a localização/i }))
    expect(useHomeStore.getState().compartilharLocalizacao).toBe(false)
    // A última posição fica (religar volta na hora) — o chip é que some.
    expect(useHomeStore.getState().localizacao).toEqual({ lat: -23.5505, lon: -46.6333, precisao_m: 18 })
    expect(screen.queryByTestId("chip-de-localizacao")).toBeNull()

    // O tick seguinte do modo seguir NÃO ressuscita o chip.
    useHomeStore.getState().definirLocalizacao({ lat: -23.56, lon: -46.64, precisao_m: 9 })
    expect(screen.queryByTestId("chip-de-localizacao")).toBeNull()
  })

  it("sem precisão (null), mostra só a coordenada", () => {
    useHomeStore.setState({ compartilharLocalizacao: true, localizacao: { lat: 1, lon: 2, precisao_m: null } })
    render(<ChipDeLocalizacao />)
    const chip = screen.getByTestId("chip-de-localizacao")
    expect(chip.textContent).toContain("1.0000, 2.0000")
    expect(chip.textContent).not.toContain("±")
  })
})
