import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, render, screen, fireEvent } from "@testing-library/react"

/**
 * O basemap do MapLibreMap: com que basemap o mapa NASCE (`basemapInicial`), o
 * alternador do portal (Mapa ↔ Satélite, que remenda a fonte raster do estilo
 * montado à mão) e a rede de segurança do `style.load` — um `setStyle` que caia
 * em carga completa apaga sources e layers, e as camadas de dados têm de
 * voltar. A Home nasce em `hybrid` e não alterna.
 *
 * Os fundos são os da instalação (MAPA_*, web/lib/fundos-do-mapa.ts); aqui, um
 * satélite e um híbrido de exemplo. Sem eles (o padrão do código), ver
 * fundos-do-mapa.test.tsx.
 *
 * jsdom não desenha o MapLibre: o mapa é um dublê que registra as chamadas e
 * dispara `style.load` a cada `setStyle`, como o de verdade faz quando o diff
 * não se aplica e o estilo recarrega inteiro.
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
  /** Toda `new AttributionControl(...)` feita pelo componente. Deve ficar VAZIA. */
  atribuicoes: [] as Array<Record<string, unknown> | undefined>,
  /** O último HTML que o Popup recebeu — para conferir as cores do tema corrente. */
  popupHtml: undefined as string | undefined,
  /** A feature que `queryRenderedFeatures` devolve no clique (vazio por padrão). */
  feature: undefined as unknown,
}))

function criarMapa(opcoes: Record<string, unknown>) {
  const ouvintes: Record<string, Ouvinte[]> = {}
  /** `off(evento, f)` chega com a função ORIGINAL; guardamos o embrulho do `once`. */
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
    // Cópia: um `once` se desregistra durante o próprio laço.
    _disparar: (evento: string, e?: unknown) => [...(ouvintes[evento] ?? [])].forEach((f) => f(e)),
    on: (evento: string, f: Ouvinte) => { (ouvintes[evento] ??= []).push(f) },
    // `once` DESREGISTRA depois de disparar, como o de verdade. Não é detalhe:
    // o efeito de `[layers]` também escuta `style.load` uma vez, e um `once`
    // que ficasse pendurado re-sincronizaria as camadas eternamente — mascarando
    // exatamente o defeito que o `style.load` do componente conserta.
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
    // Como o de verdade quando o diff NÃO se aplica: o estilo recarrega
    // inteiro e termina em `style.load`.
    setStyle: (s: unknown, o?: unknown) => {
      chamadas.setStyle.push(s)
      chamadas.setStyleOpcoes.push(o)
      mapa._disparar("style.load")
    },
    getStyle: () => estilo,
    // Uma GeoJSONSource de verdade tem `setData` — o `_syncLayers` a usa para
    // atualizar camada que já existe.
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
    // O híbrido (imagem + vias e rótulos), e não o satélite puro: a esfera
    // ficaria sem um nome sequer.
    expect(estilo.sources.basemap.tiles[0]).toContain("hibrido.example.org")
    expect(estilo.sources.basemap.attribution).toContain("Híbrido de Teste")
    expect(estilo.layers[0]).toMatchObject({ id: "basemap", type: "raster" })
    // Nasce pronto: nenhum `setStyle` para chegar lá.
    expect(mapa._chamadas.setStyle).toEqual([])
  })

  it("o estado do alternador nasce no basemapInicial, sem setStyle redundante", () => {
    // O que este teste pega: um `useState("streets")` fixo com o construtor em
    // `basemapInicial` — o botão errado apareceria pressionado, e o efeito da
    // troca faria um `setStyle` logo na montagem.
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
    // O construtor do portal monta o estilo raster à mão: a fonte existe.
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
    // O defeito que este teste tranca: a carga completa apaga sources e layers,
    // e o efeito de `[layers]` não roda de novo (as camadas não mudaram). A
    // troca de basemap pede `diff: true`, mas o MapLibre recarrega tudo quando
    // o diff não se aplica — e sem a re-sincronização no `style.load`, isso
    // apagava as camadas de dados do mapa.
    render(<MapLibreMap layers={[camada()]} />)
    const mapa = espiao.mapa!
    mapa._disparar("style.load") // o estilo inicial carrega e as camadas entram
    expect(mapa._chamadas.addSource).toContain("src-art:1")

    // O estilo recarregado volta só com o basemap: as nossas `src-*` somem,
    // como na carga completa de verdade.
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
    // O handler de clique é registrado uma vez na montagem: se ele capturar o
    // `buildPopupHtml` do primeiro render, trocar o tema abre o popup com as
    // cores velhas (o container já vira pelo CSS, as células não). Lê-lo por ref
    // conserta — e é isto que o teste tranca.
    espiao.feature = { layer: { id: "fill-art:1" }, properties: { valor: "abc" } }
    const { rerender } = render(<MapLibreMap layers={[camada()]} isDark={false} />)
    const mapa = espiao.mapa!
    mapa._disparar("style.load") // sincroniza: fill-art:1 entra no mapa
    mapa._disparar("click", { point: { x: 1, y: 1 }, lngLat: { lng: 0, lat: 0 } })
    expect(espiao.popupHtml).toContain("#1a1a1a") // o texto do tema CLARO
    expect(espiao.popupHtml).not.toContain("#e5e5e5")

    rerender(<MapLibreMap layers={[camada()]} isDark />)
    mapa._disparar("click", { point: { x: 1, y: 1 }, lngLat: { lng: 0, lat: 0 } })
    expect(espiao.popupHtml).toContain("#e5e5e5") // agora o texto do tema ESCURO
  })
})

describe("popup — no idioma dos textos que recebe (a Home traduzida)", () => {
  it("em inglês: a contagem de campos, os números e as datas saem em inglês", () => {
    // O português é o padrão (o portal /share): um popup que ignorasse os
    // textos recebidos continuaria "3 campos", "1.234,5" e "31/01/2026" na
    // Home em inglês — e nenhum outro teste veria.
    espiao.feature = {
      layer: { id: "fill-art:1" },
      properties: { nome: "Lote 7", area: 1234.5, prazo: "2026-01-31", vistoria: "2026-01-02T15:04:05Z" },
    }
    render(<MapLibreMap layers={[camada()]} textos={en.mapa} />)
    const mapa = espiao.mapa!
    mapa._disparar("style.load")
    mapa._disparar("click", { point: { x: 1, y: 1 }, lngLat: { lng: 0, lat: 0 } })
    const html = espiao.popupHtml ?? ""
    expect(html).toContain("3 fields") // o nome vira cabeçalho; sobram três
    expect(html).toContain("1,234.5")
    expect(html).toContain("01/31/2026")
    expect(html).toMatch(/\d{2}\/\d{2}\/2026 \d{1,2}:\d{2}:\d{2} (AM|PM)/)
  })
})

describe("atribuição — nada de texto nosso por cima", () => {
  it("NUNCA passa `customAttribution`, em nenhum dos dois mapas", () => {
    // O defeito que isto tranca: o MapLibre CONCATENA `customAttribution` com a
    // atribuição que a fonte declara, separados por " | ". Com um texto nosso, a
    // Home mostrava a mesma coisa duas vezes. Quem declara é a fonte.
    for (const props of [{}, { basemapInicial: "hybrid" as const, basemapToggle: false, controlesDiscretos: true }]) {
      cleanup()
      espiao.atribuicoes = []
      render(<MapLibreMap layers={[]} {...props} />)
      const opcoes = espiao.mapa!._opcoes.attributionControl as Record<string, unknown> | undefined
      expect(opcoes?.customAttribution).toBeUndefined()
      // Nem por um controle montado à mão.
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
    // Escopado ao container: um seletor solto vazaria para o outro mapa da tela.
    for (const linha of css.split("\n").filter((l) => l.includes("maplibregl-"))) {
      expect(linha).toContain("#map-x")
    }
  })

  it("no escuro o ícone é invertido; no claro, não", () => {
    // Os ícones do MapLibre são SVG com a cor ASSADA no data URI (cinza escuro):
    // sobre o vidro escuro da Home sumiriam. `invert` é o único caminho.
    expect(_cssDoMapa("#map-x", true, true)).toContain("filter: invert(1)")
    expect(_cssDoMapa("#map-x", false, true)).not.toContain("invert(1)")
  })

  it("discreto abaixa o contraste, não apaga: o ícone tem piso e sobe no hover", () => {
    const css = _cssDoMapa("#map-x", true, true)
    expect(css).toMatch(/\.maplibregl-ctrl-icon \{ opacity: 0\.65/)
    expect(css).toContain("opacity: 1")
    // Sem hover (toque) o piso sobe — senão a chrome fica fraca e sem remédio.
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
