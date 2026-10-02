import { describe, it, expect, vi } from "vitest"

/**
 * O `_syncLayers` do MapLibreMap ganhou a REMOÇÃO de camadas ausentes (a Home
 * tira camada do globo) e a inferência de geomType (null não renderia nada, em
 * silêncio). jsdom não faz layout do MapLibre — mockamos o módulo e passamos um
 * mapa falso que registra as chamadas.
 */
vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))
vi.mock("maplibre-gl", () => ({
  LngLatBounds: class { extend() { return this } },
  setWorkerUrl: () => {},
}))

import {
  _syncLayers, _sniffGeomType, _estenderBounds, _idsInterativos, _quandoEstiloPronto, _filtroGeom,
} from "@/app/components/share/MapLibreMap"
import type { MapLayer } from "@/app/components/share/MapLibreMap"

type Layer = { id: string; source?: string; filter?: unknown; paint?: Record<string, unknown> }
function fakeMap(layers: Layer[], sources: Record<string, unknown>) {
  const estilo = { layers: [...layers] as Layer[], sources: { ...sources } }
  const layout: Record<string, Record<string, unknown>> = {}
  const calls = {
    removeLayer: [] as string[], removeSource: [] as string[], addLayer: [] as string[],
    addSource: [] as string[], setPaint: [] as string[], setLayout: [] as string[], getStyle: 0,
  }
  const achar = (id: string) => estilo.layers.find((l) => l.id === id)
  return {
    _calls: calls,
    _layer: achar,
    getStyle: () => { calls.getStyle += 1; return estilo },
    // Uma GeoJSONSource real tem setData; devolvemos um wrapper com ela.
    getSource: (id: string) => (estilo.sources[id] ? { ...(estilo.sources[id] as object), setData: () => {} } : undefined),
    getLayer: achar,
    addSource: (id: string, def: unknown) => { estilo.sources[id] = def; calls.addSource.push(id) },
    addLayer: (def: Layer) => { estilo.layers.push({ ...def }); calls.addLayer.push(def.id) },
    removeLayer: (id: string) => { estilo.layers = estilo.layers.filter((l) => l.id !== id); calls.removeLayer.push(id) },
    removeSource: (id: string) => { delete estilo.sources[id]; calls.removeSource.push(id) },
    getPaintProperty: (id: string, prop: string) => achar(id)?.paint?.[prop],
    setPaintProperty: (id: string, prop: string, valor: unknown) => {
      const l = achar(id)
      if (l) l.paint = { ...(l.paint || {}), [prop]: valor }
      calls.setPaint.push(`${id}.${prop}`)
    },
    getLayoutProperty: (id: string, prop: string) => layout[id]?.[prop],
    setLayoutProperty: (id: string, prop: string, valor: unknown) => {
      layout[id] = { ...(layout[id] || {}), [prop]: valor }
      calls.setLayout.push(`${id}.${prop}`)
    },
    fitBounds: () => {},
  }
}

const camada = (over: Partial<MapLayer> = {}): MapLayer => ({
  id: "art:1", label: "Camada", color: "#f00", opacity: 0.6, visible: true,
  geojson: { type: "FeatureCollection", features: [] }, ...over,
})

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const asMap = (m: unknown) => m as any

describe("_syncLayers — remoção", () => {
  it("remove as camadas que sumiram, poupando o que não é nosso (o basemap)", () => {
    const map = fakeMap(
      [
        { id: "fill-water", source: "terceiros" },  // camada de um estilo que não é nosso
        { id: "line-old", source: "src-old" },       // nossa camada, agora ausente
      ],
      { "src-old": { type: "geojson" }, terceiros: { type: "vector" } },
    )
    _syncLayers(asMap(map), [], false) // lista vazia: tudo o que é nosso sai
    expect(map._calls.removeLayer).toContain("line-old")
    expect(map._calls.removeSource).toContain("src-old")
    // O basemap NÃO some, embora "water" não esteja na lista desejada.
    expect(map._calls.removeLayer).not.toContain("fill-water")
    expect(map._calls.removeSource).not.toContain("terceiros")
  })

  it("não remove uma camada ainda desejada", () => {
    const map = fakeMap(
      [{ id: "fill-art:1", source: "src-art:1" }],
      { "src-art:1": { type: "geojson" } },
    )
    _syncLayers(asMap(map), [camada({ id: "art:1", geomType: "Polygon" })], true)
    expect(map._calls.removeLayer).not.toContain("fill-art:1")
    expect(map._calls.removeSource).not.toContain("src-art:1")
  })

  it("com a lista anterior, fecha o delta sem serializar o estilo", () => {
    // `getStyle()` serializa TODAS as camadas e fontes do basemap vetorial; o
    // componente passa os ids da última sincronização justamente para evitá-lo.
    const map = fakeMap(
      [{ id: "fill-old", source: "src-old" }, { id: "line-old", source: "src-old" }],
      { "src-old": { type: "geojson" } },
    )
    _syncLayers(asMap(map), [], true, undefined, undefined, undefined, undefined, ["old"])
    expect(map._calls.removeLayer).toEqual(expect.arrayContaining(["fill-old", "line-old"]))
    expect(map._calls.removeSource).toContain("src-old")
    expect(map._calls.getStyle).toBe(0)
  })
})

describe("_syncLayers — inferência de tipo", () => {
  it("infere o tipo do primeiro feature quando geomType falta", () => {
    const map = fakeMap([], {})
    const poly = camada({
      id: "art:2",
      geomType: undefined,
      geojson: {
        type: "FeatureCollection",
        features: [{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] } }],
      },
    })
    _syncLayers(asMap(map), [poly], true)
    expect(map._calls.addSource).toContain("src-art:2")
    expect(map._calls.addLayer).toContain("fill-art:2") // polígono → camada fill
    // Tipo conhecido: nada de filtro — a camada desenha tudo o que vier.
    expect(map._layer("fill-art:2")?.filter).toBeUndefined()
  })

  it("MVT sem tipo declarado: as três camadas, cada uma filtrada por geometria", () => {
    // Um layer `circle` sem filtro emite um círculo POR VÉRTICE (inclusive os de
    // um polígono) e um `fill` triangula até LineString — no portal público isso
    // vira uma nuvem de bolinhas sobre o talhão.
    const map = fakeMap([], {})
    const semTipo = camada({ id: "art:3", geomType: undefined, mvt: { workflowHash: "wf", layerKey: "k" } })
    _syncLayers(asMap(map), [semTipo], true)
    expect(map._layer("fill-art:3")?.filter).toEqual(_filtroGeom("Polygon"))
    expect(map._layer("line-art:3")?.filter).toEqual(_filtroGeom("Polygon", "LineString"))
    expect(map._layer("circle-art:3")?.filter).toEqual(_filtroGeom("Point"))
  })

  it("_filtroGeom aceita as variantes Multi*", () => {
    expect(_filtroGeom("Polygon")).toEqual(["in", ["geometry-type"], ["literal", ["Polygon", "MultiPolygon"]]])
  })
})

describe("_syncLayers — escrita de paint/layout", () => {
  it("não reescreve o que não mudou", () => {
    const map = fakeMap([], {})
    const poly = camada({ id: "art:4", geomType: "Polygon" })
    _syncLayers(asMap(map), [poly], true)
    map._calls.setPaint.length = 0
    map._calls.setLayout.length = 0

    _syncLayers(asMap(map), [poly], true, undefined, undefined, undefined, undefined, ["art:4"])
    expect(map._calls.setPaint).toEqual([])
    expect(map._calls.setLayout).toEqual([])

    // Mudou de fato (o olho do painel) → escreve só a visibilidade.
    _syncLayers(asMap(map), [{ ...poly, visible: false }], true, undefined, undefined, undefined, undefined, ["art:4"])
    expect(map._calls.setLayout).toEqual(["fill-art:4.visibility", "line-art:4.visibility"])
    expect(map._calls.setPaint).toEqual([])
  })
})

describe("_idsInterativos", () => {
  it("lista só as camadas visíveis que existem no mapa", () => {
    const map = fakeMap(
      [{ id: "fill-a", source: "src-a" }, { id: "line-a", source: "src-a" }, { id: "circle-b", source: "src-b" }],
      {},
    )
    const ids = _idsInterativos(asMap(map), [
      camada({ id: "a", visible: true }),
      camada({ id: "b", visible: false }), // oculta: fora da consulta
      camada({ id: "c", visible: true }),  // sem camada no mapa
    ])
    expect(ids).toEqual(["fill-a", "line-a"])
    // O ponto do teste: nada de `getStyle()` no caminho do ponteiro.
    expect(map._calls.getStyle).toBe(0)
  })
})

describe("_quandoEstiloPronto", () => {
  it("sincroniza na hora quando o estilo já carregou", () => {
    const sync = vi.fn()
    const once = vi.fn()
    const limpar = _quandoEstiloPronto(asMap({ once, off: vi.fn() }), true, sync)
    expect(sync).toHaveBeenCalledTimes(1)
    expect(once).not.toHaveBeenCalled()
    expect(limpar).toBeUndefined()
  })

  it("espera o próximo style.load — não o `load`, que dispara uma vez só", () => {
    const sync = vi.fn()
    const once = vi.fn()
    const off = vi.fn()
    const limpar = _quandoEstiloPronto(asMap({ once, off }), false, sync)
    expect(sync).not.toHaveBeenCalled()
    expect(once).toHaveBeenCalledWith("style.load", sync)
    limpar?.()
    expect(off).toHaveBeenCalledWith("style.load", sync)
  })
})

describe("_sniffGeomType / _estenderBounds", () => {
  it("_sniffGeomType lê o primeiro feature com geometria", () => {
    expect(_sniffGeomType({ type: "FeatureCollection", features: [] })).toBe("")
    expect(_sniffGeomType({
      type: "FeatureCollection",
      features: [{ type: "Feature", properties: {}, geometry: { type: "MultiPolygon", coordinates: [] } }],
    })).toBe("MultiPolygon")
  })

  it("_estenderBounds usa a bbox quando há, senão as coordenadas", () => {
    const extend = vi.fn()
    const bounds = asMap({ extend })
    expect(_estenderBounds(bounds, camada({ bbox: [0, 0, 1, 1] }))).toBe(true)
    expect(extend).toHaveBeenCalledTimes(2) // sudoeste + nordeste

    extend.mockClear()
    const comPonto = camada({
      geojson: { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [10, 20] } }] },
    })
    expect(_estenderBounds(bounds, comPonto)).toBe(true)
    expect(extend).toHaveBeenCalled()

    extend.mockClear()
    expect(_estenderBounds(bounds, camada())).toBe(false) // sem bbox e sem features
  })
})
