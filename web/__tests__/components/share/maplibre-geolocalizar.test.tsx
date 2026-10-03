import { createRef } from "react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, cleanup, render } from "@testing-library/react"

/**
 * Location on the globe (Home only): MapLibre's GeolocateControl comes in
 * when `geolocalizar` is on, in FOLLOW mode, with the texts in pt-BR. And the
 * owner's rule: locating RULES the globe — the hero spin stops while we follow the
 * person, and the return to Brazil does not fire. The `/share` portal, which does not pass
 * `geolocalizar`, gets no control at all.
 *
 * jsdom does not draw MapLibre: the map is a double that keeps the camera and the
 * calls, and the GeolocateControl is a double that lets the test fire the
 * events the real one emits (`trackuserlocationstart/end`).
 */
vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))

type Listener = (e?: unknown) => void

const espiao = vi.hoisted(() => ({
  mapa: null as ReturnType<typeof createMap> | null,
  geo: null as null | {
    opcoes: Record<string, unknown>
    fire: (ev: string, e?: unknown) => void
    trigger: ReturnType<typeof vi.fn>
    /** The raw double, so the test can set the internal state the real code consults. */
    duble: {
      _watchState?: string
      _lastKnownPosition?: { coords: { latitude: number; longitude: number; accuracy: number } }
    }
  },
}))

// A function declaration: it is hoisted, so the vi.mock factory (which is also hoisted)
// can call it. A CLASS at the top would not be — hence the control double
// lives INSIDE the factory.
function createMap(opcoes: Record<string, unknown>) {
  const ouvintes: Record<string, Listener[]> = {}
  const inicial = opcoes.center as [number, number]
  let centro = { lng: inicial[0], lat: inicial[1] }
  let zoom = opcoes.zoom as number
  let moving = false
  const aplicar = (o: { center?: [number, number]; zoom?: number }) => {
    if (o.center) centro = { lng: o.center[0], lat: o.center[1] }
    if (o.zoom != null) zoom = o.zoom
  }
  const mapa = {
    _opcoes: opcoes,
    easeTo: vi.fn((o: { center?: [number, number]; zoom?: number }) => { moving = true; aplicar(o) }),
    jumpTo: vi.fn((o: { center?: [number, number]; zoom?: number }) => { moving = false; aplicar(o) }),
    stop: vi.fn(() => { moving = false }),
    isMoving: () => moving,
    getCenter: () => ({ ...centro }),
    getZoom: () => zoom,
    _terminarMovimento: () => { moving = false; mapa._disparar("moveend") },
    _disparar: (evento: string, e?: unknown) => [...(ouvintes[evento] ?? [])].forEach((f) => f(e)),
    on: (evento: string, f: Listener) => { (ouvintes[evento] ??= []).push(f) },
    once: (evento: string, f: Listener) => {
      const so = (e?: unknown) => { ouvintes[evento] = (ouvintes[evento] ?? []).filter((g) => g !== so); f(e) }
      ;(ouvintes[evento] ??= []).push(so)
    },
    off: (evento: string, f: Listener) => { ouvintes[evento] = (ouvintes[evento] ?? []).filter((g) => g !== f) },
    addControl: vi.fn(),
    removeControl: () => {}, setProjection: () => {},
    setStyle: () => {}, getStyle: () => ({ layers: [], sources: {} }),
    getSource: () => undefined, getLayer: () => undefined,
    addSource: () => {}, addLayer: () => {}, removeLayer: () => {}, removeSource: () => {},
    getPaintProperty: () => undefined, setPaintProperty: () => {},
    getLayoutProperty: () => undefined, setLayoutProperty: () => {},
    queryRenderedFeatures: () => [], getCanvas: () => ({ style: {} }),
    fitBounds: () => {}, flyTo: () => {}, remove: () => {},
  }
  return mapa
}

vi.mock("maplibre-gl", () => {
  class GeolocateDuble {
    opcoes: Record<string, unknown>
    _ouvintes: Record<string, Listener[]> = {}
    /** The real code consults these maplibre internals; the test sets them up. */
    _watchState?: string
    _lastKnownPosition?: { coords: { latitude: number; longitude: number; accuracy: number } }
    trigger = vi.fn()
    constructor(opcoes: Record<string, unknown>) {
      this.opcoes = opcoes
      espiao.geo = {
        opcoes,
        fire: (ev: string, e?: unknown) => (this._ouvintes[ev] ?? []).forEach((f) => f(e)),
        trigger: this.trigger,
        duble: this,
      }
    }
    on(ev: string, f: Listener) { (this._ouvintes[ev] ??= []).push(f) }
  }
  return {
    Map: class {
      constructor(opcoes: Record<string, unknown>) {
        const m = createMap(opcoes)
        espiao.mapa = m
        return m as unknown as object
      }
    },
    NavigationControl: class {},
    ScaleControl: class {},
    GeolocateControl: GeolocateDuble,
    AttributionControl: class {},
    Popup: class { setLngLat() { return this } setHTML() { return this } addTo() { return this } remove() {} },
    LngLatBounds: class { extend() { return this } isEmpty() { return true } },
    setWorkerUrl: () => {},
  }
})

import MapLibreMap, { SPIN_STEP_MS, TEXTOS_DO_MAPA_PT, type MapLibreMapHandle } from "@/app/components/share/MapLibreMap"
import { textosDe } from "@/app/components/home/i18n"

const BRASIL: [number, number] = [-52, -12]

beforeEach(() => { cleanup(); espiao.mapa = null; espiao.geo = null; vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

function montar(props: Record<string, unknown>) {
  return render(<MapLibreMap layers={[]} basemapToggle={false} center={BRASIL} zoom={2.3} {...props} />)
}

describe("MapLibreMap — a localização no globo", () => {
  it("com `geolocalizar`, adiciona o GeolocateControl no modo seguir", () => {
    montar({ geolocalizar: true })
    expect(espiao.geo).not.toBeNull()
    const o = espiao.geo!.opcoes
    expect(o.trackUserLocation).toBe(true)     // segue a pessoa
    expect(o.showAccuracyCircle).toBe(true)    // the accuracy circle
    expect((o.positionOptions as { enableHighAccuracy?: boolean }).enableHighAccuracy).toBe(true)
    // and it was in fact registered on the map (some control with the follow options)
    const registrado = espiao.mapa!.addControl.mock.calls
      .some((c) => (c[0] as { opcoes?: { trackUserLocation?: boolean } })?.opcoes?.trackUserLocation === true)
    expect(registrado).toBe(true)
  })

  it("os textos do controle são pt-BR", () => {
    montar({ geolocalizar: true })
    const locale = espiao.mapa!._opcoes.locale as Record<string, string>
    expect(locale["GeolocateControl.FindMyLocation"]).toBe("Mostrar a minha localização")
    expect(locale["GeolocateControl.LocationNotAvailable"]).toBe("Localização indisponível")
  })

  it("com `textos` (a Home em outro idioma), os controles nascem nele", () => {
    montar({ geolocalizar: true, textos: textosDe("es").casca.mapa })
    const locale = espiao.mapa!._opcoes.locale as Record<string, string>
    expect(locale["GeolocateControl.FindMyLocation"]).toBe("Mostrar mi ubicación")
    expect(locale["NavigationControl.ZoomIn"]).toBe("Acercar")
  })

  it("o português do portal e o da Home são o mesmo texto", () => {
    expect(textosDe("pt-BR").casca.mapa.controles).toEqual(TEXTOS_DO_MAPA_PT.controles)
    expect(textosDe("pt-BR").casca.mapa.semAtributos).toBe(TEXTOS_DO_MAPA_PT.semAtributos)
    expect(textosDe("pt-BR").casca.mapa.campos(2)).toBe(TEXTOS_DO_MAPA_PT.campos(2))
    expect(textosDe("pt-BR").casca.mapa.data).toEqual(TEXTOS_DO_MAPA_PT.data)
  })

  it("sem `geolocalizar` (o portal), NÃO adiciona controle de localização", () => {
    montar({})
    expect(espiao.geo).toBeNull()
  })

  it("localizar pausa o giro do hero; ao soltar o seguir, ele retoma", () => {
    montar({ geolocalizar: true, giroLento: true })
    const mapa = espiao.mapa!
    // The hero spin went out on mount.
    expect(mapa.easeTo).toHaveBeenCalledTimes(1)

    // A pessoa toca em localizar → o controle entra em modo seguir.
    act(() => { espiao.geo!.fire("trackuserlocationstart") })
    expect(mapa.stop).toHaveBeenCalled()          // corta o passo em voo

    // While following, the spin stays suspended: the resume interval moves nothing.
    act(() => { vi.advanceTimersByTime(SPIN_STEP_MS + 1000) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(1)

    // A pessoa solta o seguir (segundo toque) → o giro volta a andar.
    act(() => { espiao.geo!.fire("trackuserlocationend") })
    act(() => { vi.advanceTimersByTime(1000) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(2)
  })

  it("seguindo, desligar o hero NÃO volta ao Brasil (a pessoa ficaria para trás)", () => {
    const { rerender } = montar({ geolocalizar: true, giroLento: true })
    const mapa = espiao.mapa!
    act(() => { espiao.geo!.fire("trackuserlocationstart") })
    const antes = mapa.easeTo.mock.calls.length

    // The hero ends (the person sent something), but they are being followed.
    rerender(<MapLibreMap layers={[]} basemapToggle={false} center={BRASIL} zoom={2.3} geolocalizar giroLento={false} />)

    // No "return to Brazil": no easeTo/jumpTo to the Globo's center.
    expect(mapa.easeTo.mock.calls.length).toBe(antes)
    expect(mapa.jumpTo).not.toHaveBeenCalled()
  })

  it("o evento `geolocate` sobe a coordenada e a precisão por `aoLocalizar`", () => {
    const aoLocalizar = vi.fn()
    montar({ geolocalizar: true, aoLocalizar })
    act(() => {
      espiao.geo!.fire("geolocate", { coords: { latitude: -23.5505, longitude: -46.6333, accuracy: 18 } })
    })
    expect(aoLocalizar).toHaveBeenCalledWith({ lat: -23.5505, lon: -46.6333, precisao_m: 18 })
  })

  it("precisão não-finita vira `null` (±Infinity não é um raio real)", () => {
    const aoLocalizar = vi.fn()
    montar({ geolocalizar: true, aoLocalizar })
    act(() => {
      espiao.geo!.fire("geolocate", { coords: { latitude: 1, longitude: 2, accuracy: Infinity } })
    })
    expect(aoLocalizar).toHaveBeenCalledWith({ lat: 1, lon: 2, precisao_m: null })
  })

  it("o handle `localizar()` aciona o controle — a entrada do compositor", () => {
    const ref = createRef<MapLibreMapHandle>()
    render(<MapLibreMap ref={ref} layers={[]} basemapToggle={false} center={BRASIL} zoom={2.3} geolocalizar />)
    expect(espiao.geo!.trigger).not.toHaveBeenCalled()
    act(() => { ref.current!.localizar() })
    expect(espiao.geo!.trigger).toHaveBeenCalledTimes(1)
  })

  it("já seguindo, `localizar()` NÃO alterna: reemite a última posição sem tocar no trigger", () => {
    // `trigger()` in ACTIVE_LOCK/WAITING_ACTIVE TURNS OFF tracking — "Usar
    // minha localização" (use my location) must never turn it off. Reattaching after the × only re-emits.
    const ref = createRef<MapLibreMapHandle>()
    const aoLocalizar = vi.fn()
    render(<MapLibreMap ref={ref} layers={[]} basemapToggle={false} center={BRASIL} zoom={2.3} geolocalizar aoLocalizar={aoLocalizar} />)
    espiao.geo!.duble._watchState = "ACTIVE_LOCK"
    espiao.geo!.duble._lastKnownPosition = { coords: { latitude: -23.5, longitude: -46.6, accuracy: 12 } }

    act(() => { ref.current!.localizar() })

    expect(espiao.geo!.trigger).not.toHaveBeenCalled()
    expect(aoLocalizar).toHaveBeenCalledWith({ lat: -23.5, lon: -46.6, precisao_m: 12 })
  })

  it("permissão negada solta o giro — o hero não fica congelado para sempre", () => {
    // PERMISSION_DENIED drops the control to OFF WITHOUT `trackuserlocationend`;
    // without the error handler, geolocalizandoRef stayed stuck at true.
    const onError = vi.fn()
    montar({ geolocalizar: true, giroLento: true, aoErroDeLocalizacao: onError })
    const mapa = espiao.mapa!
    expect(mapa.easeTo).toHaveBeenCalledTimes(1) // the mount step

    act(() => { espiao.geo!.fire("trackuserlocationstart") })
    act(() => { espiao.geo!.fire("error", { code: 1 }) })
    expect(onError).toHaveBeenCalledWith(1)

    act(() => { vi.advanceTimersByTime(1000) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(2) // o giro voltou a andar
  })

  it("cair para o 2º plano (arrastar) NÃO devolve o giro: o watch segue vivo em zoom alto", () => {
    montar({ geolocalizar: true, giroLento: true })
    const mapa = espiao.mapa!
    act(() => { espiao.geo!.fire("trackuserlocationstart") })

    // maplibre also fires trackuserlocationend in the background state — with the
    // watch still active. Spinning here would sweep the screen over the person's home.
    espiao.geo!.duble._watchState = "BACKGROUND"
    act(() => { espiao.geo!.fire("trackuserlocationend") })
    act(() => { vi.advanceTimersByTime(1500) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(1) // suspenso

    // Only a real OFF releases it.
    espiao.geo!.duble._watchState = "OFF"
    act(() => { espiao.geo!.fire("trackuserlocationend") })
    act(() => { vi.advanceTimersByTime(1000) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(2)
  })

  it("sem movimento NOSSO em voo, o início do seguir não dá stop()", () => {
    // Stopping ANY movement killed the control's own framing on
    // re-click from the background state (fitBounds runs before the event).
    montar({ geolocalizar: true }) // no spin: nothing of ours flying
    act(() => { espiao.geo!.fire("trackuserlocationstart") })
    expect(espiao.mapa!.stop).not.toHaveBeenCalled()
  })
})
