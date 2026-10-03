/**
 * The map backgrounds come from the install (MAPA_*), and the code only ships the streets.
 *
 * Before, satellite and hybrid were Google's imagery, hard-coded: every
 * install used it, with no key and under Google's terms, without choosing. Now the
 * root layout reads MAPA_{RUAS,SATELITE,HIBRIDO}_{URL,CREDITO} from the web
 * server's environment, and without satellite the portal does not offer the switcher.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import {
  conjuntoDoFundo, DEFAULT_BASEMAPS, lerFundosDoAmbiente, RUAS_PADRAO,
} from "@/lib/fundos-do-mapa"
import { MapBasemapsProvider } from "@/app/components/share/fundos-do-mapa"

vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))
const built = vi.hoisted(() => ({ estilo: null as unknown }))
vi.mock("maplibre-gl", () => {
  class Mapa {
    constructor(opcoes: { style: unknown }) { built.estilo = opcoes.style }
    on() {} once() {} off() {} addControl() {} removeControl() {} remove() {}
    getStyle() { return built.estilo }
    isStyleLoaded() { return false }
    getCanvas() { return { style: {} } }
    setProjection() {}
  }
  class Controle {}
  return {
    Map: Mapa, NavigationControl: Controle, ScaleControl: Controle, GeolocateControl: Controle,
    AttributionControl: Controle, Popup: class { setLngLat() { return this } setHTML() { return this } addTo() { return this } remove() {} },
    LngLatBounds: class { extend() { return this } isEmpty() { return true } },
    setWorkerUrl: () => {},
  }
})

import MapLibreMap from "@/app/components/share/MapLibreMap"

afterEach(cleanup)

type Estilo = { sources: { basemap: { tiles: string[]; attribution: string } } }

describe("lerFundosDoAmbiente", () => {
  it("sem variável nenhuma, só as ruas do OpenStreetMap", () => {
    expect(lerFundosDoAmbiente({})).toEqual(DEFAULT_BASEMAPS)
    expect(DEFAULT_BASEMAPS.ruas).toBe(RUAS_PADRAO)
    expect(RUAS_PADRAO.url).toContain("tile.openstreetmap.org")
  })

  it("lê os três fundos e os créditos", () => {
    const fundos = lerFundosDoAmbiente({
      MAPA_RUAS_URL: " https://ruas.example.org/{z}/{x}/{y}.png ", MAPA_RUAS_CREDITO: "© Ruas",
      MAPA_SATELITE_URL: "https://sat.example.org/{z}/{x}/{y}.jpg", MAPA_SATELITE_CREDITO: "© Sat",
      MAPA_HIBRIDO_URL: "https://hib.example.org/{z}/{x}/{y}.jpg",
    })
    expect(fundos).toEqual({
      ruas: { url: "https://ruas.example.org/{z}/{x}/{y}.png", credito: "© Ruas" },
      satelite: { url: "https://sat.example.org/{z}/{x}/{y}.jpg", credito: "© Sat" },
      hibrido: { url: "https://hib.example.org/{z}/{x}/{y}.jpg", credito: "" },
    })
  })

  it("uma URL que não é template de tiles é ignorada (e as ruas voltam ao padrão)", () => {
    const erro = vi.spyOn(console, "error").mockImplementation(() => {})
    expect(lerFundosDoAmbiente({ MAPA_RUAS_URL: "https://ruas.example.org/tiles", MAPA_SATELITE_URL: "javascript:alert(1)//{z}{x}{y}" }))
      .toEqual(DEFAULT_BASEMAPS)
    expect(erro).toHaveBeenCalledTimes(2)
    erro.mockRestore()
  })
})

describe("conjuntoDoFundo", () => {
  const sat = { url: "https://sat.example.org/{z}/{x}/{y}.jpg", credito: "© Sat <b>" }
  it("o híbrido cai no satélite, e o satélite nas ruas, sem configuração", () => {
    expect(conjuntoDoFundo(DEFAULT_BASEMAPS, "hybrid").tiles).toEqual([RUAS_PADRAO.url])
    expect(conjuntoDoFundo(DEFAULT_BASEMAPS, "satellite").tiles).toEqual([RUAS_PADRAO.url])
    expect(conjuntoDoFundo({ ...DEFAULT_BASEMAPS, satelite: sat }, "hybrid").tiles).toEqual([sat.url])
  })

  it("o crédito vai escapado: o MapLibre o desenha como HTML", () => {
    expect(conjuntoDoFundo({ ...DEFAULT_BASEMAPS, satelite: sat }, "satellite").attribution).toBe("© Sat &lt;b&gt;")
  })
})

describe("o mapa sem satélite configurado", () => {
  it("o portal não oferece o alternador: os dois lados seriam o mesmo mapa", () => {
    render(<MapLibreMap layers={[]} />)
    expect(screen.queryByRole("button", { name: "Satélite" })).toBeNull()
    expect((built.estilo as Estilo).sources.basemap.tiles[0]).toContain("tile.openstreetmap.org")
  })

  it("a Home (híbrido) nasce nas ruas", () => {
    render(<MapLibreMap layers={[]} basemapInicial="hybrid" basemapToggle={false} />)
    expect((built.estilo as Estilo).sources.basemap.tiles[0]).toContain("tile.openstreetmap.org")
  })

  it("com o satélite da instalação no contexto, o alternador volta", () => {
    render(
      <MapBasemapsProvider fundos={{ ...DEFAULT_BASEMAPS, satelite: { url: "https://sat.example.org/{z}/{x}/{y}.jpg", credito: "© Sat" } }}>
        <MapLibreMap layers={[]} />
      </MapBasemapsProvider>,
    )
    expect(screen.getByRole("button", { name: "Satélite" })).toBeTruthy()
  })
})
