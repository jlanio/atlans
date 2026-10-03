import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

/**
 * The composer's "+" (option B') and the location chip.
 *
 * "Anexar arquivo" (attach file) goes down the SAME path as drag-and-drop (useAnexos.receber),
 * now with a discoverable home; "Usar minha localização" (use my location) triggers the globe's
 * control. The chip mirrors the attachment ones: in view, with the ×, reading the store.
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
    // Resets so that re-choosing the SAME file fires the change again.
    expect(input.value).toBe("")
  })

  it("o item «Anexar arquivo» do menu abre o seletor (o click do input)", () => {
    // The menu → picker path, and not just the input's change: without this the item
    // could point to nothing and the suite would stay green.
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
    // The globe's native button records the position (last known), but only the
    // "+" gesture puts it into the conversation.
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
    // The last position stays (turning it back on returns instantly) — it is the chip that goes away.
    expect(useHomeStore.getState().localizacao).toEqual({ lat: -23.5505, lon: -46.6333, precisao_m: 18 })
    expect(screen.queryByTestId("chip-de-localizacao")).toBeNull()

    // The next tick of follow mode does NOT bring the chip back.
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
