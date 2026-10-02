import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, cleanup, render } from "@testing-library/react"

/**
 * O giro lento do globo (o hero da Home): meio grau por segundo para oeste, em
 * passos de um segundo encadeados no `moveend`; pausa depois de um gesto da
 * pessoa; nada com `prefers-reduced-motion`; e, ao desligar, a volta a
 * `center`/`zoom` — o Brasil — em 900 ms.
 *
 * jsdom não desenha o MapLibre: o mapa é um dublê que guarda a câmera e as
 * chamadas de `easeTo`/`jumpTo`/`stop`, e termina um movimento sob comando
 * (`_terminarMovimento`), como o `moveend` do de verdade.
 */
vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))

type Ouvinte = (e?: unknown) => void

const espiao = vi.hoisted(() => ({ mapa: null as ReturnType<typeof criarMapa> | null }))

function criarMapa(opcoes: Record<string, unknown>) {
  const ouvintes: Record<string, Ouvinte[]> = {}
  const inicial = opcoes.center as [number, number]
  let centro = { lng: inicial[0], lat: inicial[1] }
  let zoom = opcoes.zoom as number
  let movendo = false
  const aplicar = (o: { center?: [number, number]; zoom?: number }) => {
    if (o.center) centro = { lng: o.center[0], lat: o.center[1] }
    if (o.zoom != null) zoom = o.zoom
  }
  const mapa = {
    easeTo: vi.fn((o: { center?: [number, number]; zoom?: number }) => { movendo = true; aplicar(o) }),
    jumpTo: vi.fn((o: { center?: [number, number]; zoom?: number }) => { movendo = false; aplicar(o) }),
    stop: vi.fn(() => { movendo = false }),
    isMoving: () => movendo,
    getCenter: () => ({ ...centro }),
    getZoom: () => zoom,
    /** O fim de um movimento, como o mapa de verdade anuncia. */
    _terminarMovimento: () => { movendo = false; mapa._disparar("moveend") },
    _disparar: (evento: string, e?: unknown) => [...(ouvintes[evento] ?? [])].forEach((f) => f(e)),
    on: (evento: string, f: Ouvinte) => { (ouvintes[evento] ??= []).push(f) },
    once: (evento: string, f: Ouvinte) => {
      const so = (e?: unknown) => { ouvintes[evento] = (ouvintes[evento] ?? []).filter((g) => g !== so); f(e) }
      ;(ouvintes[evento] ??= []).push(so)
    },
    off: (evento: string, f: Ouvinte) => { ouvintes[evento] = (ouvintes[evento] ?? []).filter((g) => g !== f) },
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
      const m = criarMapa(opcoes)
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
  DURACAO_DA_VOLTA_MS, PASSO_DO_GIRO_MS, PAUSA_APOS_GESTO_MS, VELOCIDADE_DO_GIRO_GRAUS_POR_S,
} from "@/app/components/share/MapLibreMap"

const BRASIL: [number, number] = [-52, -12]
const GRAUS_POR_PASSO = VELOCIDADE_DO_GIRO_GRAUS_POR_S * (PASSO_DO_GIRO_MS / 1000)

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
    expect(primeiro.center[0]).toBeCloseTo(BRASIL[0] - GRAUS_POR_PASSO)
    expect(primeiro.center[1]).toBe(BRASIL[1])
    expect(primeiro.duration).toBe(PASSO_DO_GIRO_MS)
    expect(primeiro.easing(0.25)).toBe(0.25) // linear: velocidade constante
    expect(primeiro.essential).toBe(true)

    // O seguinte encadeia no fim do anterior, sempre para oeste.
    act(() => { mapa._terminarMovimento() })
    expect(mapa.easeTo).toHaveBeenCalledTimes(2)
    const segundo = mapa.easeTo.mock.calls[1][0] as { center: [number, number] }
    expect(segundo.center[0]).toBeCloseTo(BRASIL[0] - 2 * GRAUS_POR_PASSO)
  })

  it("um gesto da pessoa pausa o giro, que retoma 2,5 s depois", () => {
    montar(true)
    const mapa = espiao.mapa!
    expect(mapa.easeTo).toHaveBeenCalledTimes(1)

    // Ela pega o globo: o passo em voo termina, e nenhum outro sai.
    act(() => { mapa._disparar("mousedown"); mapa._terminarMovimento() })
    act(() => { vi.advanceTimersByTime(PAUSA_APOS_GESTO_MS - 500) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(1)

    // Passada a pausa, o intervalo de retomada põe o globo a girar de novo.
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
    expect(volta.duration).toBe(DURACAO_DA_VOLTA_MS)
    // ease-in-out: começa devagar, passa pela metade na metade.
    expect(volta.easing(0.5)).toBeCloseTo(0.5)
    expect(volta.easing(0.25)).toBeLessThan(0.25)

    // E nada mais gira: terminar a volta não encadeia passo nenhum.
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
