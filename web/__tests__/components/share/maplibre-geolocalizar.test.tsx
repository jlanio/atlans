import { createRef } from "react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, cleanup, render } from "@testing-library/react"

/**
 * A localização no globo (só a Home): o GeolocateControl do MapLibre entra
 * quando `geolocalizar` liga, no modo SEGUIR, com os textos em pt-BR. E a regra
 * do dono: localizar MANDA no globo — o giro do hero para enquanto seguimos a
 * pessoa, e a volta ao Brasil não dispara. O portal `/share`, que não passa
 * `geolocalizar`, não ganha controle nenhum.
 *
 * jsdom não desenha o MapLibre: o mapa é um dublê que guarda a câmera e as
 * chamadas, e o GeolocateControl é um dublê que deixa o teste disparar os
 * eventos que o de verdade emite (`trackuserlocationstart/end`).
 */
vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))

type Ouvinte = (e?: unknown) => void

const espiao = vi.hoisted(() => ({
  mapa: null as ReturnType<typeof criarMapa> | null,
  geo: null as null | {
    opcoes: Record<string, unknown>
    fire: (ev: string, e?: unknown) => void
    trigger: ReturnType<typeof vi.fn>
    /** O dublê cru, para o teste pôr o estado interno que o código real consulta. */
    duble: {
      _watchState?: string
      _lastKnownPosition?: { coords: { latitude: number; longitude: number; accuracy: number } }
    }
  },
}))

// Declaração de função: é içada, então o factory do vi.mock (que também é içado)
// consegue chamá-la. Uma CLASSE no topo não seria — daí o dublê do controle
// mora DENTRO do factory.
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
    _opcoes: opcoes,
    easeTo: vi.fn((o: { center?: [number, number]; zoom?: number }) => { movendo = true; aplicar(o) }),
    jumpTo: vi.fn((o: { center?: [number, number]; zoom?: number }) => { movendo = false; aplicar(o) }),
    stop: vi.fn(() => { movendo = false }),
    isMoving: () => movendo,
    getCenter: () => ({ ...centro }),
    getZoom: () => zoom,
    _terminarMovimento: () => { movendo = false; mapa._disparar("moveend") },
    _disparar: (evento: string, e?: unknown) => [...(ouvintes[evento] ?? [])].forEach((f) => f(e)),
    on: (evento: string, f: Ouvinte) => { (ouvintes[evento] ??= []).push(f) },
    once: (evento: string, f: Ouvinte) => {
      const so = (e?: unknown) => { ouvintes[evento] = (ouvintes[evento] ?? []).filter((g) => g !== so); f(e) }
      ;(ouvintes[evento] ??= []).push(so)
    },
    off: (evento: string, f: Ouvinte) => { ouvintes[evento] = (ouvintes[evento] ?? []).filter((g) => g !== f) },
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
    _ouvintes: Record<string, Ouvinte[]> = {}
    /** O código real consulta estes internos do maplibre; o teste os arma. */
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
    on(ev: string, f: Ouvinte) { (this._ouvintes[ev] ??= []).push(f) }
  }
  return {
    Map: class {
      constructor(opcoes: Record<string, unknown>) {
        const m = criarMapa(opcoes)
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

import MapLibreMap, { PASSO_DO_GIRO_MS, TEXTOS_DO_MAPA_PT, type MapLibreMapHandle } from "@/app/components/share/MapLibreMap"
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
    expect(o.showAccuracyCircle).toBe(true)    // o círculo de precisão
    expect((o.positionOptions as { enableHighAccuracy?: boolean }).enableHighAccuracy).toBe(true)
    // e ele foi de fato registrado no mapa (algum control com as opções de seguir)
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
    // O giro do hero saiu na montagem.
    expect(mapa.easeTo).toHaveBeenCalledTimes(1)

    // A pessoa toca em localizar → o controle entra em modo seguir.
    act(() => { espiao.geo!.fire("trackuserlocationstart") })
    expect(mapa.stop).toHaveBeenCalled()          // corta o passo em voo

    // Enquanto segue, o giro fica suspenso: o intervalo de retomada não move nada.
    act(() => { vi.advanceTimersByTime(PASSO_DO_GIRO_MS + 1000) })
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

    // O hero termina (a pessoa enviou algo), mas ela está sendo seguida.
    rerender(<MapLibreMap layers={[]} basemapToggle={false} center={BRASIL} zoom={2.3} geolocalizar giroLento={false} />)

    // Nenhuma "volta ao Brasil": nada de easeTo/jumpTo para o centro do Globo.
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
    // `trigger()` em ACTIVE_LOCK/WAITING_ACTIVE DESLIGA o rastreio — o "Usar
    // minha localização" jamais pode desligar. Reanexar depois do × só reemite.
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
    // PERMISSION_DENIED derruba o controle para OFF SEM `trackuserlocationend`;
    // sem o handler de erro, geolocalizandoRef ficava preso em true.
    const aoErro = vi.fn()
    montar({ geolocalizar: true, giroLento: true, aoErroDeLocalizacao: aoErro })
    const mapa = espiao.mapa!
    expect(mapa.easeTo).toHaveBeenCalledTimes(1) // o passo da montagem

    act(() => { espiao.geo!.fire("trackuserlocationstart") })
    act(() => { espiao.geo!.fire("error", { code: 1 }) })
    expect(aoErro).toHaveBeenCalledWith(1)

    act(() => { vi.advanceTimersByTime(1000) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(2) // o giro voltou a andar
  })

  it("cair para o 2º plano (arrastar) NÃO devolve o giro: o watch segue vivo em zoom alto", () => {
    montar({ geolocalizar: true, giroLento: true })
    const mapa = espiao.mapa!
    act(() => { espiao.geo!.fire("trackuserlocationstart") })

    // O maplibre dispara trackuserlocationend também no 2º plano — com o
    // watch ainda ativo. Girar aqui varreria a tela sobre a casa da pessoa.
    espiao.geo!.duble._watchState = "BACKGROUND"
    act(() => { espiao.geo!.fire("trackuserlocationend") })
    act(() => { vi.advanceTimersByTime(1500) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(1) // suspenso

    // Só o OFF de verdade libera.
    espiao.geo!.duble._watchState = "OFF"
    act(() => { espiao.geo!.fire("trackuserlocationend") })
    act(() => { vi.advanceTimersByTime(1000) })
    expect(mapa.easeTo).toHaveBeenCalledTimes(2)
  })

  it("sem movimento NOSSO em voo, o início do seguir não dá stop()", () => {
    // Parar QUALQUER movimento matava o enquadramento do próprio controle no
    // reclique a partir do 2º plano (o fitBounds roda antes do evento).
    montar({ geolocalizar: true }) // sem giro: nada nosso voando
    act(() => { espiao.geo!.fire("trackuserlocationstart") })
    expect(espiao.mapa!.stop).not.toHaveBeenCalled()
  })
})
