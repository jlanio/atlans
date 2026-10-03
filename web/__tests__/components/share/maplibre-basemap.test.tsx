import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, render, screen, fireEvent } from "@testing-library/react"

/**
 * MapLibreMap's basemap: which basemap the map is BORN with (`basemapInicial`), the
 * portal's switcher (Mapa ↔ Satélite, which patches the raster source of the hand-built
 * style) and the `style.load` safety net — a `setStyle` that ends up
 * in a full load wipes sources and layers, and the data layers have to
 * come back. The Home is born in `hybrid` and does not switch.
 *
 * The backgrounds are the install's (MAPA_*, web/lib/fundos-do-mapa.ts); here, a
 * sample satellite and hybrid. Without them (the code's default), see
 * fundos-do-mapa.test.tsx.
 *
 * jsdom does not draw MapLibre: the map is a double that records the calls and
 * fires `style.load` on every `setStyle`, as the real one does when the diff
 * does not apply and the style reloads entirely.
 */
vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))

const fundosDeTeste = vi.hoisted(() => ({
  ruas: { url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png", credito: "© OpenStreetMap contributors" },
  satelite: { url: "https://satelite.example.org/{z}/{x}/{y}.jpg", credito: "© Satélite de Teste" },
  hibrido: { url: "https://hibrido.example.org/{z}/{x}/{y}.jpg", credito: "© Híbrido de Teste" },
}))
vi.mock("@/app/components/share/fundos-do-mapa", () => ({ useFundosDoMapa: () => fundosDeTeste }))

type Ouvinte = (e?: unknown) => void

const espiao = vi.hoisted(() => ({
  mapa: null as ReturnType<typeof criarMapa> | null,
  /** Every `new AttributionControl(...)` made by the component. Must stay EMPTY. */
  atribuicoes: [] as Array<Record<string, unknown> | undefined>,
  /** The last HTML the Popup received — to check the current theme's colors. */
  popupHtml: undefined as string | undefined,
  /** The feature `queryRenderedFeatures` returns on click (empty by default). */
  feature: undefined as unknown,
}))

function criarMapa(opcoes: Record<string, unknown>) {
  const ouvintes: Record<string, Ouvinte[]> = {}
  /** `off(evento, f)` arrives with the ORIGINAL function; we keep the `once` wrapper. */
  const registrados = new Map<Ouvinte, Ouvinte>()
  const estilo = {
    layers: [] as Array<Record<string, unknown>>,
    sources: (opcoes.style as { sources?: Record<string, unknown> })?.sources ?? {},
  }
  const chamadas = {
    setStyle: [] as unknown[],
    setStyleOpcoes: [] as unknown[],
    addSource: [] as string[],
    addLayer: [] as string[],
    addControl: [] as unknown[],
    removeControl: [] as unknown[],
    setProjection: [] as unknown[],
  }
  const mapa = {
    _opcoes: opcoes,
    _chamadas: chamadas,
    _estilo: estilo,
    // Copy: a `once` unregisters itself during the loop itself.
    _disparar: (evento: string, e?: unknown) => [...(ouvintes[evento] ?? [])].forEach((f) => f(e)),
    on: (evento: string, f: Ouvinte) => { (ouvintes[evento] ??= []).push(f) },
    // `once` UNREGISTERS after firing, like the real one. It is not a detail:
    // the `[layers]` effect also listens to `style.load` once, and a `once`
    // left hanging would re-sync the layers forever — masking
    // exactly the defect the component's `style.load` fixes.
    once: (evento: string, f: Ouvinte) => {
      const so = (e?: unknown) => {
        ouvintes[evento] = (ouvintes[evento] ?? []).filter((g) => g !== so)
        f(e)
      }
      ;(ouvintes[evento] ??= []).push(so)
      registrados.set(f, so)
    },
    off: (evento: string, f: Ouvinte) => {
      const alvo = registrados.get(f) ?? f
      ouvintes[evento] = (ouvintes[evento] ?? []).filter((g) => g !== alvo)
    },
    addControl: (c: unknown) => { chamadas.addControl.push(c) },
    removeControl: (c: unknown) => { chamadas.removeControl.push(c) },
    setProjection: (p: unknown) => { chamadas.setProjection.push(p) },
    // Like the real one when the diff does NOT apply: the style reloads
    // entirely and ends in `style.load`.
    setStyle: (s: unknown, o?: unknown) => {
      chamadas.setStyle.push(s)
      chamadas.setStyleOpcoes.push(o)
      mapa._disparar("style.load")
    },
    getStyle: () => estilo,
    // A real GeoJSONSource has `setData` — `_syncLayers` uses it to
    // update a layer that already exists.
    getSource: (id: string) => {
      const def = (estilo.sources as Record<string, unknown>)[id]
      return def ? { ...(def as object), setData: () => {} } : undefined
    },
    getLayer: (id: string) => estilo.layers.find((l) => l.id === id),
    addSource: (id: string, def: unknown) => { (estilo.sources as Record<string, unknown>)[id] = def; chamadas.addSource.push(id) },
    addLayer: (def: Record<string, unknown>) => { estilo.layers.push({ ...def }); chamadas.addLayer.push(String(def.id)) },
    removeLayer: (id: string) => { estilo.layers = estilo.layers.filter((l) => l.id !== id) },
    removeSource: (id: string) => { delete (estilo.sources as Record<string, unknown>)[id] },
    getPaintProperty: () => undefined,
    setPaintProperty: () => {},
    getLayoutProperty: () => undefined,
    setLayoutProperty: () => {},
    queryRenderedFeatures: () => (espiao.feature ? [espiao.feature] : []),
    getCanvas: () => ({ style: {} }),
    fitBounds: () => {},
    flyTo: () => {},
    remove: () => {},
  }
  return mapa
}

vi.mock("maplibre-gl", () => ({
  Map: class {
    constructor(opcoes: Record<string, unknown>) {
      const m = criarMapa(opcoes)
      espiao.mapa = m
      return m as unknown as object
    }
  },
  NavigationControl: class {},
  ScaleControl: class {},
  AttributionControl: class {
    constructor(public opcoes?: Record<string, unknown>) { espiao.atribuicoes.push(opcoes) }
  },
  Popup: class { setLngLat() { return this } setHTML(html: string) { espiao.popupHtml = html; return this } addTo() { return this } remove() {} },
  LngLatBounds: class { extend() { return this } isEmpty() { return true } },
  setWorkerUrl: () => {},
}))

import MapLibreMap, { _cssDoMapa, type MapLayer } from "@/app/components/share/MapLibreMap"
import { en } from "@/app/components/home/i18n/secoes/casca"

const camada = (over: Partial<MapLayer> = {}): MapLayer => ({
  id: "art:1", label: "Camada", color: "#f00", opacity: 0.6, visible: true, geomType: "Polygon",
  geojson: { type: "FeatureCollection", features: [] }, ...over,
})

beforeEach(() => { espiao.mapa = null; espiao.atribuicoes = []; espiao.popupHtml = undefined; espiao.feature = undefined; cleanup() })

describe("alternador de basemap — rótulos e acessibilidade", () => {
  it("oferece Mapa e Satélite, os dois lados do portal", () => {
    render(<MapLibreMap layers={[]} />)
    expect(screen.getByRole("button", { name: "Mapa" })).toBeTruthy()
    expect(screen.getByRole("button", { name: "Satélite" })).toBeTruthy()
  })

  it("o lado ativo é anunciado por aria-pressed, e ele muda no clique", () => {
    render(<MapLibreMap layers={[]} />)
    const mapa = screen.getByRole("button", { name: "Mapa" })
    const satelite = screen.getByRole("button", { name: "Satélite" })
    expect(mapa.getAttribute("aria-pressed")).toBe("true")
    expect(satelite.getAttribute("aria-pressed")).toBe("false")

    fireEvent.click(satelite)
    expect(mapa.getAttribute("aria-pressed")).toBe("false")
    expect(satelite.getAttribute("aria-pressed")).toBe("true")
  })

  it("`basemapToggle={false}` não desenha alternador nenhum", () => {
    render(<MapLibreMap layers={[]} basemapToggle={false} />)
    expect(screen.queryByRole("button", { name: "Mapa" })).toBeNull()
  })
})

describe("`basemapInicial` — o basemap com que o mapa nasce", () => {
  type EstiloRaster = {
    version: number
    sources: { basemap: { type: string; tiles: string[]; attribution: string } }
    layers: Array<{ id: string; type: string }>
  }

  it("padrão streets: o construtor recebe as tiles do OSM (o portal, intacto)", () => {
    render(<MapLibreMap layers={[]} />)
    const estilo = espiao.mapa!._opcoes.style as EstiloRaster
    expect(estilo.sources.basemap.tiles[0]).toContain("openstreetmap")
    expect(estilo.sources.basemap.attribution).toContain("OpenStreetMap")
  })

  it("hybrid (a Home): o construtor recebe o híbrido da instalação, e não há setStyle na montagem", () => {
    render(<MapLibreMap layers={[]} basemapInicial="hybrid" basemapToggle={false} />)
    const mapa = espiao.mapa!
    const estilo = mapa._opcoes.style as EstiloRaster
    expect(estilo.version).toBe(8)
    expect(estilo.sources.basemap.type).toBe("raster")
    // The hybrid (imagery + roads and labels), and not plain satellite: the sphere
    // would be left without a single name.
    expect(estilo.sources.basemap.tiles[0]).toContain("hibrido.example.org")
    expect(estilo.sources.basemap.attribution).toContain("Híbrido de Teste")
    expect(estilo.layers[0]).toMatchObject({ id: "basemap", type: "raster" })
    // Born ready: no `setStyle` to get there.
    expect(mapa._chamadas.setStyle).toEqual([])
  })

  it("o estado do alternador nasce no basemapInicial, sem setStyle redundante", () => {
    // What this test catches: a fixed `useState("streets")` with the constructor on
    // `basemapInicial` — the wrong button would show as pressed, and the switch
    // effect would do a `setStyle` right on mount.
    render(<MapLibreMap layers={[]} basemapInicial="satellite" />)
    expect(screen.getByRole("button", { name: "Satélite" }).getAttribute("aria-pressed")).toBe("true")
    expect(screen.getByRole("button", { name: "Mapa" }).getAttribute("aria-pressed")).toBe("false")
    expect(espiao.mapa!._chamadas.setStyle).toEqual([])
  })
})

describe("alternador de basemap — o portal remenda a fonte", () => {
  it("troca as tiles de `sources.basemap` em vez de trocar o estilo", () => {
    render(<MapLibreMap layers={[]} />)
    const mapa = espiao.mapa!
    // The portal's constructor builds the raster style by hand: the source exists.
    expect((mapa._estilo.sources as Record<string, { tiles: string[] }>).basemap).toBeTruthy()

    fireEvent.click(screen.getByRole("button", { name: "Satélite" }))
    const fonte = (mapa._estilo.sources as Record<string, { tiles: string[]; attribution: string }>).basemap
    expect(fonte.tiles[0]).toContain("satelite.example.org")
    expect(fonte.attribution).toContain("Satélite de Teste")
    // Remendo com diff, e o estilo continua sendo o MESMO objeto.
    expect(mapa._chamadas.setStyle[0]).toBe(mapa._estilo)
    expect(mapa._chamadas.setStyleOpcoes[0]).toEqual({ diff: true })
  })

  it("não faz `setStyle` na montagem — o mapa já nasce em `streets`", () => {
    render(<MapLibreMap layers={[]} />)
    expect(espiao.mapa!._chamadas.setStyle).toEqual([])
  })
})

describe("`style.load` — a rede de segurança quando o estilo recarrega inteiro", () => {
  it("a projeção globo é re-aplicada na recarga", () => {
    render(<MapLibreMap layers={[]} projection="globe" />)
    const mapa = espiao.mapa!
    mapa._chamadas.setProjection.length = 0

    fireEvent.click(screen.getByRole("button", { name: "Satélite" }))
    expect(mapa._chamadas.setProjection).toEqual([{ type: "globe" }])
  })

  it("as camadas de dados VOLTAM quando um setStyle recarrega o estilo", () => {
    // The defect this test locks: the full load wipes sources and layers,
    // and the `[layers]` effect does not run again (the layers did not change). The
    // basemap switch asks for `diff: true`, but MapLibre reloads everything when
    // the diff does not apply — and without the re-sync on `style.load`, that
    // wiped the data layers off the map.
    render(<MapLibreMap layers={[camada()]} />)
    const mapa = espiao.mapa!
    mapa._disparar("style.load") // o estilo inicial carrega e as camadas entram
    expect(mapa._chamadas.addSource).toContain("src-art:1")

    // The reloaded style comes back with only the basemap: our `src-*` disappear,
    // as in a real full load.
    mapa._estilo.layers = []
    mapa._estilo.sources = { basemap: (mapa._estilo.sources as Record<string, unknown>).basemap }
    mapa._chamadas.addSource.length = 0
    mapa._chamadas.addLayer.length = 0

    fireEvent.click(screen.getByRole("button", { name: "Satélite" }))
    expect(mapa._chamadas.addSource).toContain("src-art:1")
    expect(mapa._chamadas.addLayer).toContain("fill-art:1")
  })
})

describe("popup — o clique lê o buildPopupHtml corrente ao trocar de tema", () => {
  it("depois de trocar `isDark`, o popup sai nas cores do tema NOVO, não do 1º render", () => {
    // The click handler is registered once on mount: if it captures the
    // first render's `buildPopupHtml`, switching the theme opens the popup with the
    // old colors (the container switches through CSS, the cells do not). Reading it through a ref
    // fixes it — and that is what the test locks.
    espiao.feature = { layer: { id: "fill-art:1" }, properties: { valor: "abc" } }
    const { rerender } = render(<MapLibreMap layers={[camada()]} isDark={false} />)
    const mapa = espiao.mapa!
    mapa._disparar("style.load") // sincroniza: fill-art:1 entra no mapa
    mapa._disparar("click", { point: { x: 1, y: 1 }, lngLat: { lng: 0, lat: 0 } })
    expect(espiao.popupHtml).toContain("#1a1a1a") // the LIGHT theme's text
    expect(espiao.popupHtml).not.toContain("#e5e5e5")

    rerender(<MapLibreMap layers={[camada()]} isDark />)
    mapa._disparar("click", { point: { x: 1, y: 1 }, lngLat: { lng: 0, lat: 0 } })
    expect(espiao.popupHtml).toContain("#e5e5e5") // now the DARK theme's text
  })
})

describe("popup — no idioma dos textos que recebe (a Home traduzida)", () => {
  it("em inglês: a contagem de campos, os números e as datas saem em inglês", () => {
    // Portuguese is the default (the /share portal): a popup that ignored the
    // texts it received would keep showing "3 campos", "1.234,5" and "31/01/2026" on the
    // Home in English — and no other test would see it.
    espiao.feature = {
      layer: { id: "fill-art:1" },
      properties: { nome: "Lote 7", area: 1234.5, prazo: "2026-01-31", vistoria: "2026-01-02T15:04:05Z" },
    }
    render(<MapLibreMap layers={[camada()]} textos={en.mapa} />)
    const mapa = espiao.mapa!
    mapa._disparar("style.load")
    mapa._disparar("click", { point: { x: 1, y: 1 }, lngLat: { lng: 0, lat: 0 } })
    const html = espiao.popupHtml ?? ""
    expect(html).toContain("3 fields") // the name becomes the header; three remain
    expect(html).toContain("1,234.5")
    expect(html).toContain("01/31/2026")
    expect(html).toMatch(/\d{2}\/\d{2}\/2026 \d{1,2}:\d{2}:\d{2} (AM|PM)/)
  })
})

describe("atribuição — nada de texto nosso por cima", () => {
  it("NUNCA passa `customAttribution`, em nenhum dos dois mapas", () => {
    // The defect this locks: MapLibre CONCATENATES `customAttribution` with the
    // attribution the source declares, separated by " | ". With a text of ours, the
    // Home showed the same thing twice. The source is what declares it.
    for (const props of [{}, { basemapInicial: "hybrid" as const, basemapToggle: false, controlesDiscretos: true }]) {
      cleanup()
      espiao.atribuicoes = []
      render(<MapLibreMap layers={[]} {...props} />)
      const opcoes = espiao.mapa!._opcoes.attributionControl as Record<string, unknown> | undefined
      expect(opcoes?.customAttribution).toBeUndefined()
      // Not through a hand-built control either.
      expect(espiao.atribuicoes).toEqual([])
    }
  })

  it("o portal fica no controle padrão; a Home o recolhe a um \u201c\u24d8\u201d", () => {
    render(<MapLibreMap layers={[]} />)
    expect(espiao.mapa!._opcoes.attributionControl).toBeUndefined()
    cleanup()

    render(<MapLibreMap layers={[]} basemapInicial="hybrid" basemapToggle={false} controlesDiscretos />)
    expect(espiao.mapa!._opcoes.attributionControl).toEqual({ compact: true })
  })

  it("trocar de basemap não mexe em controle nenhum — a fonte é quem fala", () => {
    render(<MapLibreMap layers={[]} controlesDiscretos />)
    const mapa = espiao.mapa!
    fireEvent.click(screen.getByRole("button", { name: "Satélite" }))
    fireEvent.click(screen.getByRole("button", { name: "Mapa" }))
    expect(mapa._chamadas.removeControl).toEqual([])
    expect(espiao.atribuicoes).toEqual([])
  })
})

describe("_cssDoMapa", () => {
  it("o portal recebe SÓ o CSS do popup — zero regra de chrome", () => {
    const css = _cssDoMapa("#map-x", false, false)
    expect(css).toContain("maplibregl-popup-content")
    expect(css).not.toContain("maplibregl-ctrl-group")
    expect(css).not.toContain("maplibregl-ctrl-scale")
    expect(css).not.toContain("maplibregl-ctrl-attrib")
  })

  it("discreto veste zoom, bússola, escala e o \u201c\u24d8\u201d, sem perder o popup", () => {
    const css = _cssDoMapa("#map-x", true, true)
    expect(css).toContain("maplibregl-popup-content")
    for (const alvo of ["maplibregl-ctrl-group", "maplibregl-ctrl-scale", "maplibregl-ctrl-attrib"]) {
      expect(css).toContain(alvo)
    }
    // Scoped to the container: a loose selector would leak to the other map on the screen.
    for (const linha of css.split("\n").filter((l) => l.includes("maplibregl-"))) {
      expect(linha).toContain("#map-x")
    }
  })

  it("no escuro o ícone é invertido; no claro, não", () => {
    // MapLibre's icons are SVG with the color BAKED into the data URI (dark gray):
    // over the Home's dark glass they would vanish. `invert` is the only way.
    expect(_cssDoMapa("#map-x", true, true)).toContain("filter: invert(1)")
    expect(_cssDoMapa("#map-x", false, true)).not.toContain("invert(1)")
  })

  it("discreto abaixa o contraste, não apaga: o ícone tem piso e sobe no hover", () => {
    const css = _cssDoMapa("#map-x", true, true)
    expect(css).toMatch(/\.maplibregl-ctrl-icon \{ opacity: 0\.65/)
    expect(css).toContain("opacity: 1")
    // Without hover (touch) the floor goes up — otherwise the chrome stays faint with no remedy.
    expect(css).toContain("@media (hover: none)")
  })
})

describe("o CSS injetado", () => {
  it("é o do `_cssDoMapa`, escopado ao id daquele mapa", () => {
    const { container } = render(<MapLibreMap layers={[]} isDark controlesDiscretos />)
    const id = container.querySelector("[id^=map-]")!.id
    const tag = document.getElementById(`atlans-mapa-style-${id.replace("map-", "")}`)
    expect(tag?.textContent).toBe(_cssDoMapa(`#${id}`, true, true))
  })

  it("sai do documento quando o mapa é desmontado", () => {
    const { container, unmount } = render(<MapLibreMap layers={[]} />)
    const id = container.querySelector("[id^=map-]")!.id.replace("map-", "")
    expect(document.getElementById(`atlans-mapa-style-${id}`)).toBeTruthy()
    unmount()
    expect(document.getElementById(`atlans-mapa-style-${id}`)).toBeNull()
  })
})
