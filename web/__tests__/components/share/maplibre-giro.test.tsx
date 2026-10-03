import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, cleanup, render } from "@testing-library/react"

/**
 * The globe's slow spin (the Home hero): half a degree per second westward, in
 * one-second steps chained on `moveend`; pauses after a gesture by the
 * person; nothing with `prefers-reduced-motion`; and, when turned off, the return to
 * `center`/`zoom` — Brazil — in 900 ms.
 *
 * jsdom does not draw MapLibre: the map is a double that keeps the camera and the
 * `easeTo`/`jumpTo`/`stop` calls, and ends a movement on command
 * (`_terminarMovimento`), like the real one's `moveend`.
 */
vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))

type Listener = (e?: unknown) => void

const espiao = vi.hoisted(() => ({ mapa: null as ReturnType<typeof createMap> | null }))

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
    easeTo: vi.fn((o: { center?: [number, number]; zoom?: number }) => { moving = true; aplicar(o) }),
    jumpTo: vi.fn((o: { center?: [number, number]; zoom?: number }) => { moving = false; aplicar(o) }),
    stop: vi.fn(() => { moving = false }),
    isMoving: () => moving,
    getCenter: () => ({ ...centro }),
    getZoom: () => zoom,
    /** The end of a movement, as the real map announces it. */
    _terminarMovimento: () => { moving = false; mapa._disparar("moveend") },
    _disparar: (evento: string, e?: unknown) => [...(ouvintes[evento] ?? [])].forEach((f) => f(e)),
    on: (evento: string, f: Listener) => { (ouvintes[evento] ??= []).push(f) },
    once: (evento: string, f: Listener) => {
      const so = (e?: unknown) => { ouvintes[evento] = (ouvintes[evento] ?? []).filter((g) => g !== so); f(e) }
      ;(ouvintes[evento] ??= []).push(so)
    },
    off: (evento: string, f: Listener) => { ouvintes[evento] = (ouvintes[evento] ?? []).filter((g) => g !== f) },
    addControl: () => {}, removeControl: () => {}, setProjection: () => {},
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

vi.mock("maplibre-gl", () => ({
  Map: class {
    constructor(opcoes: Record<string, unknown>) {
      const m = createMap(opcoes)
      espiao.mapa = m
      return m as unknown as object
    }
  },
  NavigationControl: class {},
  ScaleControl: class {},
  AttributionControl: class {},
  Popup: class { setLngLat() { return this } setHTML() { return this } addTo() { return this } remove() {} },
  LngLatBounds: class { extend() { return this } isEmpty() { return true } },
  setWorkerUrl: () => {},
}))

import MapLibreMap, {
  REVOLUTION_DURATION_MS, SPIN_STEP_MS, PAUSE_AFTER_GESTURE_MS, SPIN_SPEED_DEGREES_PER_S,
} from "@/app/components/share/MapLibreMap"

const BRASIL: [number, number] = [-52, -12]
const DEGREES_PER_STEP = SPIN_SPEED_DEGREES_PER_S * (SPIN_STEP_MS / 1000)

function montar(giroLento: boolean) {
  return render(<MapLibreMap layers={[]} basemapToggle={false} center={BRASIL} zoom={2.3} giroLento={giroLento} />)
}

beforeEach(() => { cleanup(); espiao.mapa = null; vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

describe("MapLibreMap — o giro lento do hero", () => {
  it("gira meio grau por segundo para oeste, um passo linear por vez, encadeado no moveend", () => {
    montar(true)
    const mapa = espiao.mapa!

    // O primeiro passo sai na montagem.
    expect(mapa.easeTo).toHaveBeenCalledTimes(1)
    const primeiro = mapa.easeTo.mock.calls[0][0] as { center: [number, number]; duration: number; easing: (n: number) => number; essential: boolean }
    expect(primeiro.center[0]).toBeCloseTo(BRASIL[0] - DEGREES_PER_STEP)
    expect(primeiro.center[1]).toBe(BRASIL[1])
    expect(primeiro.duration).toBe(SPIN_STEP_MS)
    expect(primeiro.easing(0.25)).toBe(0.25) // linear: velocidade constante
    expect(primeiro.essential).toBe(true)

    // The next one chains onto the end of the previous one, always westward.
    act(() => { mapa._terminarMovimento() })
    expect(mapa.easeTo).toHaveBeenCalledTimes(2)
    const segundo = mapa.easeTo.mock.calls[1][0] as { center: [number, number] }
    expect(segundo.center[0]).toBeCloseTo(BRASIL[0] - 2 * DEGREES_PER_STEP)
  })

  it("um gesto da pessoa pausa o giro, que retoma 2,5 s depois", () => {
    montar(true)
    const mapa = espiao.mapa!
    expect(mapa.easeTo).toHaveBeenCalledTimes(1)

    // The person grabs the globe: the step in flight finishes, and no other one goes out.
    act(() => { mapa._disparar("mousedown"); mapa._terminarMovimento() })
    act(() => { vi.advanceTimersByTime(PAUSE_AFTER_GESTURE_MS - 500) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(1)

    // Once the pause is over, the resume interval sets the globe spinning again.
    act(() => { vi.advanceTimersByTime(1000) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(2)
  })

  it("ao desligar, para o passo em voo e volta a center/zoom em 900 ms com easing suave", () => {
    const { rerender } = montar(true)
    const mapa = espiao.mapa!
    expect(mapa.easeTo).toHaveBeenCalledTimes(1)

    rerender(<MapLibreMap layers={[]} basemapToggle={false} center={BRASIL} zoom={2.3} giroLento={false} />)

    expect(mapa.stop).toHaveBeenCalled()
    expect(mapa.easeTo).toHaveBeenCalledTimes(2)
    const volta = mapa.easeTo.mock.calls[1][0] as { center: [number, number]; zoom: number; duration: number; easing: (n: number) => number }
    expect(volta.center).toEqual(BRASIL)
    expect(volta.zoom).toBe(2.3)
    expect(volta.duration).toBe(REVOLUTION_DURATION_MS)
    // ease-in-out: starts slowly, passes the halfway point at half time.
    expect(volta.easing(0.5)).toBeCloseTo(0.5)
    expect(volta.easing(0.25)).toBeLessThan(0.25)

    // And nothing spins anymore: finishing the return chains no step at all.
    act(() => { mapa._terminarMovimento() })
    act(() => { vi.advanceTimersByTime(5000) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(2)
  })

  it("sem giroLento a câmera não é tocada — o portal segue como sempre", () => {
    const { rerender } = montar(false)
    const mapa = espiao.mapa!
    act(() => { vi.advanceTimersByTime(5000) })
    rerender(<MapLibreMap layers={[]} basemapToggle={false} center={BRASIL} zoom={2.3} giroLento={false} />)

    expect(mapa.easeTo).not.toHaveBeenCalled()
    expect(mapa.jumpTo).not.toHaveBeenCalled()
  })

  it("com prefers-reduced-motion não gira, e a volta é um salto", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: true, addEventListener() {}, removeEventListener() {} }))
    const { rerender } = montar(true)
    const mapa = espiao.mapa!
    act(() => { vi.advanceTimersByTime(5000) })
    expect(mapa.easeTo).not.toHaveBeenCalled()

    rerender(<MapLibreMap layers={[]} basemapToggle={false} center={BRASIL} zoom={2.3} giroLento={false} />)
    expect(mapa.easeTo).not.toHaveBeenCalled()
    expect(mapa.jumpTo).toHaveBeenCalledWith({ center: BRASIL, zoom: 2.3 })
  })
})
