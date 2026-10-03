import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

/**
 * The Globo is a thin wrapper around MapLibreMap. We mock the map (jsdom does no
 * MapLibre layout) and check the CONTRACT: map in globe projection over the
 * install's hybrid imagery as the ONLY basemap — no switcher, no key, no
 * "no basemap" state —, discreet chrome, and a transformRequest that sends the
 * session cookie on the agent's tiles and leaves the rest raw.
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

// The browser time zone is the TEST's, not the running machine's: without this the center
// would depend on where CI (or whoever runs it locally) is.
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
    // Dark Matter required a key and, without it, the page showed a warning. The
    // install's hybrid requires nothing: the Home always has a map.
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
    // `/share` does not pass `geolocalizar`; the Home does. That is what separates the map
    // that follows the person from the public map.
    render(<Globo />)
    expect(espiao.props!.geolocalizar).toBe(true)
  })

  it("repassa `aoLocalizar` ao mapa — a coordenada sobe do globo para a Home", () => {
    const aoLocalizar = vi.fn()
    render(<Globo aoLocalizar={aoLocalizar} />)
    expect(espiao.props!.aoLocalizar).toBe(aoLocalizar)
  })

  it("a chrome do mapa é discreta, e a atribuição NÃO é passada por nós", () => {
    // The raster source already declares its own credit. Passing our own text on top did not
    // replace it — MapLibre concatenates the two with " | " and the screen showed
    // the same thing twice.
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
    // With no region signal, the spin returns to the neutral center.
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
    // The center of Mexico's time zones — in Mexico, far from the Brazil of before.
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
