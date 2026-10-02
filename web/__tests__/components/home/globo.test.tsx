import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

/**
 * O Globo é um invólucro fino do MapLibreMap. Mockamos o mapa (jsdom não faz
 * layout do MapLibre) e conferimos o CONTRATO: mapa em projeção globe sobre a
 * imagem híbrida da instalação como basemap ÚNICO — sem alternador, sem chave, sem
 * estado "sem basemap" —, chrome discreta, e um transformRequest que manda o
 * cookie de sessão nos tiles do agente e deixa o resto cru.
 */
const espiao = vi.hoisted(() => ({ props: null as Record<string, unknown> | null }))
vi.mock("@/app/components/share/MapLibreMap", async () => {
  const React = await import("react")
  return {
    default: React.forwardRef(function MapLibreMapDuble(p: Record<string, unknown>) {
      espiao.props = p
      return React.createElement("div", { "data-testid": "maplibre" })
    }),
  }
})

// O fuso do navegador é do TESTE, não da máquina que roda: sem isto o centro
// dependeria de onde o CI (ou quem roda local) está.
const fuso = vi.hoisted(() => ({ valor: null as string | null }))
vi.mock("@/app/components/home/mapa/regiao", async (original) => ({
  ...(await original<typeof import("@/app/components/home/mapa/regiao")>()),
  fusoDoNavegador: () => fuso.valor,
}))

import Globo from "@/app/components/home/globo"
import { IdiomaProvider } from "@/context/IdiomaContext"

beforeEach(() => { espiao.props = null; fuso.valor = null; cleanup() })

describe("Globo", () => {
  it("sempre monta o mapa: não existe mais estado sem basemap", () => {
    // O Dark Matter exigia chave e, sem ela, a página mostrava um aviso. O
    // híbrido da instalação não exige nada: a Home sempre tem mapa.
    render(<Globo />)
    expect(screen.getByTestId("maplibre")).toBeTruthy()
    expect(screen.queryByText(/mapa de fundo não está disponível/i)).toBeNull()
  })

  it("nasce na imagem híbrida da instalação, em globo, escuro, com os tiles do agente", () => {
    render(<Globo />)
    const p = espiao.props!
    expect(p.basemapInicial).toBe("hybrid")
    expect(p.projection).toBe("globe")
    expect(p.isDark).toBe(true)
    expect(p.tilesBaseUrl).toBe("/terra/assistente/tiles")
    // Nada de estilo remoto: o CARTO saiu inteiro.
    expect(p.styleUrl).toBeUndefined()
  })

  it("sem alternador: com um basemap só, não há para o que alternar", () => {
    render(<Globo />)
    expect(espiao.props!.basemapToggle).toBe(false)
  })

  it("liga a localização (só a Home): o botão de me-localizar do MapLibre", () => {
    // O `/share` não passa `geolocalizar`; a Home passa. É o que separa o mapa
    // que segue a pessoa do mapa público.
    render(<Globo />)
    expect(espiao.props!.geolocalizar).toBe(true)
  })

  it("repassa `aoLocalizar` ao mapa — a coordenada sobe do globo para a Home", () => {
    const aoLocalizar = vi.fn()
    render(<Globo aoLocalizar={aoLocalizar} />)
    expect(espiao.props!.aoLocalizar).toBe(aoLocalizar)
  })

  it("a chrome do mapa é discreta, e a atribuição NÃO é passada por nós", () => {
    // A fonte raster já declara o crédito dela. Passar um texto nosso por cima não
    // a substituía — o MapLibre concatena os dois com " | " e a tela mostrava
    // a mesma coisa duas vezes.
    render(<Globo />)
    const p = espiao.props!
    expect(p.controlesDiscretos).toBe(true)
    expect(p.attribution).toBeUndefined()
  })

  it("`girando` vira o giro lento do mapa; sem ele o globo fica parado", () => {
    render(<Globo girando />)
    expect(espiao.props!.giroLento).toBe(true)

    cleanup()
    render(<Globo />)
    expect(espiao.props!.giroLento).toBe(false)
    // Sem sinal de região, a volta do giro é para o centro neutro.
    expect(espiao.props!.center).toEqual([0, 20])
    expect(espiao.props!.zoom).toBe(2.3)
  })

  it("começa (e volta) na região do fuso do navegador", () => {
    fuso.valor = "Europe/Madrid"
    render(<Globo girando />)
    expect(espiao.props!.center).toEqual([-3.7, 40.4])
    expect(espiao.props!.zoom).toBe(2.3)
  })

  it("sem fuso útil (\"UTC\" dos modos de privacidade), o país da conexão decide", () => {
    fuso.valor = "UTC"
    render(<Globo pais="MX" />)
    const [lon, lat] = espiao.props!.center as [number, number]
    // O centro dos fusos do México — no México, longe do Brasil de antes.
    expect(lon).toBeLessThan(-90)
    expect(lat).toBeGreaterThan(14)
  })

  it("o centro fica estável entre renders (o giro não reinicia)", () => {
    fuso.valor = "America/New_York"
    const { rerender } = render(<Globo girando />)
    const primeiro = espiao.props!.center
    rerender(<Globo />)
    expect(espiao.props!.center).toBe(primeiro)
  })

  it("os textos do mapa seguem o idioma da Home (português sem provider)", () => {
    render(<Globo />)
    const pt = espiao.props!.textos as { controles: Record<string, string>; semAtributos: string }
    expect(pt.controles["NavigationControl.ZoomIn"]).toBe("Aproximar")
    expect(pt.semAtributos).toBe("Sem atributos")
    cleanup()

    render(
      <IdiomaProvider inicial={{ idioma: "en", detectado: "en", escolhido: null }}>
        <Globo />
      </IdiomaProvider>,
    )
    const en = espiao.props!.textos as { controles: Record<string, string>; campos: (n: number) => string }
    expect(en.controles["GeolocateControl.FindMyLocation"]).toBe("Show my location")
    expect(en.campos(1)).toBe("1 field")
    expect(en.campos(3)).toBe("3 fields")
  })

  it("o transformRequest manda o cookie nos tiles do agente e deixa o basemap cru", () => {
    render(<Globo />)
    const tr = espiao.props!.transformRequest as (u: string) => unknown
    expect(typeof tr).toBe("function")
    expect(tr("/terra/assistente/tiles/wf/l/1/2/3.pbf"))
      .toEqual({ url: "/terra/assistente/tiles/wf/l/1/2/3.pbf", credentials: "same-origin" })
    expect(tr("https://hibrido.example.org/3/1/2.jpg")).toBeUndefined()
  })
})
