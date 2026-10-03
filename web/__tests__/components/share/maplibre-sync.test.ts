import { describe, it, expect, vi } from "vitest"

/**
 * MapLibreMap's `_syncLayers` gained REMOVAL of absent layers (the Home
 * removes layers from the globe) and geomType inference (null would render nothing,
 * silently). jsdom does not do MapLibre layout — we mock the module and pass a
 * fake map that records the calls.
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
    // A real GeoJSONSource has setData; we return a wrapper with it.
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
        { id: "fill-water", source: "terceiros" },  // a layer from a style that is not ours
        { id: "line-old", source: "src-old" },       // our layer, now absent
      ],
      { "src-old": { type: "geojson" }, terceiros: { type: "vector" } },
    )
    _syncLayers(asMap(map), [], false) // empty list: everything of ours goes away
    expect(map._calls.removeLayer).toContain("line-old")
    expect(map._calls.removeSource).toContain("src-old")
    // The basemap does NOT disappear, even though "water" is not in the desired list.
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
    // `getStyle()` serializes ALL the layers and sources of the vector basemap; the
    // component passes the ids from the last sync precisely to avoid it.
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
    expect(map._calls.addLayer).toContain("fill-art:2") // polygon → fill layer
    // Known type: no filter — the layer draws whatever comes.
    expect(map._layer("fill-art:2")?.filter).toBeUndefined()
  })

  it("MVT sem tipo declarado: as três camadas, cada uma filtrada por geometria", () => {
    // A `circle` layer without a filter emits a circle PER VERTEX (including those of
    // a polygon) and a `fill` triangulates even a LineString — on the public portal that
    // turns into a cloud of dots over the field plot.
    const map = fakeMap([], {})
    const withoutType = camada({ id: "art:3", geomType: undefined, mvt: { workflowHash: "wf", layerKey: "k" } })
    _syncLayers(asMap(map), [withoutType], true)
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

    // It actually changed (the panel's eye) → writes only the visibility.
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
      camada({ id: "b", visible: false }), // hidden: out of the query
      camada({ id: "c", visible: true }),  // no layer on the map
    ])
    expect(ids).toEqual(["fill-a", "line-a"])
    // The point of the test: no `getStyle()` on the pointer path.
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
    const withPoint = camada({
      geojson: { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [10, 20] } }] },
    })
    expect(_estenderBounds(bounds, withPoint)).toBe(true)
    expect(extend).toHaveBeenCalled()

    extend.mockClear()
    expect(_estenderBounds(bounds, camada())).toBe(false) // no bbox and no features
  })
})
