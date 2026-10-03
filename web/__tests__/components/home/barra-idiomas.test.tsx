import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

/**
 * The assistant bar in Spanish and English: labels, hero chips and the
 * sent message. Portuguese is still covered by barra.test.tsx, untouched.
 */
import Barra from "@/app/components/home/assistente/barra"
import { useHomeStore } from "@/app/stores/homeStore"
import { IdiomaProvider } from "@/context/IdiomaContext"
import { textosDe } from "@/app/components/home/i18n"
import type { Idioma } from "@/lib/idioma"
import type { IAssistenteEstado } from "@/service/types"

const ATIVO: IAssistenteEstado = { ativo: true, cota: { gasto: 0, teto: 1_000_000, reabre_em_segundos: null } }

beforeEach(() => { cleanup(); useHomeStore.setState({ painel: "barra", rascunho: "", anexos: [] }) })

const montar = (idioma: Idioma, props: Partial<React.ComponentProps<typeof Barra>> = {}) =>
  render(
    <IdiomaProvider inicial={{ idioma, detectado: idioma, escolhido: idioma }}>
      <Barra enviar={() => {}} estado={ATIVO} {...props} />
    </IdiomaProvider>,
  )

describe("Barra — espanhol", () => {
  it("rótulos e botões em espanhol", () => {
    montar("es")
    expect(screen.getByLabelText("Mensaje para el asistente")).toBeTruthy()
    expect(screen.getByRole("button", { name: "Abrir el asistente" })).toBeTruthy()
    expect(screen.getByRole("button", { name: "Enviar" })).toBeTruthy()
  })

  it("no hero, os chips são os do espanhol — e clicar preenche com o texto em espanhol", () => {
    montar("es", { variante: "hero" })
    const chips = textosDe("es").assistente.barra.chips
    for (const chip of chips) expect(screen.getByRole("button", { name: chip })).toBeTruthy()
    fireEvent.click(screen.getByRole("button", { name: chips[1] }))
    expect(useHomeStore.getState().rascunho).toBe(chips[1])
  })
})

describe("Barra — inglês", () => {
  it("com stream em curso, o placeholder e o parar falam inglês", () => {
    montar("en", { correndo: true, parar: () => {} })
    const campo = screen.getByLabelText("Message to the assistant") as HTMLInputElement
    expect(campo.placeholder).toBe("The assistant is responding…")
    expect(screen.getByRole("button", { name: "Stop" })).toBeTruthy()
  })

  it("a cota estourada avisa em inglês", () => {
    montar("en", { estado: { ativo: true, cota: { gasto: 10, teto: 10, reabre_em_segundos: 3600 } } })
    expect(screen.getByText(/You’ve used today’s quota/)).toBeTruthy()
  })
})

describe("Barra — o que vai ao assistente, em inglês", () => {
  const campo = () => screen.getByLabelText("Message to the assistant")

  it("a referência aos anexos prontos vai no idioma da pessoa (ela a vê na bolha)", () => {
    const enviar = vi.fn()
    useHomeStore.setState({ anexos: [{ id: "a1", nome: "municipios.shp", bytes: 10, estado: "pronto" }] })
    montar("en", { enviar })
    fireEvent.change(campo(), { target: { value: "list the columns" } })
    fireEvent.keyDown(campo(), { key: "Enter" })
    const en = textosDe("en").assistente.anexos
    expect(enviar).toHaveBeenCalledWith(`list the columns\n\n${en.referencia("municipios.shp")}`)
  })

  it("no hero, com o campo vazio, vai a sugestão digitada da vez — em inglês", () => {
    const enviar = vi.fn()
    montar("en", { enviar, variante: "hero" })
    fireEvent.keyDown(campo(), { key: "Enter" })
    expect(enviar).toHaveBeenCalledTimes(1)
    expect(textosDe("en").assistente.barra.sugestoes).toContain(enviar.mock.calls[0][0])
  })
})
