"use client"
import { useState, type Ref } from "react"
import MapLibreMap, { type MapLibreMapHandle, type MapLayer, type PosicaoDoUsuario } from "../share/MapLibreMap"
import { centroDaRegiao, fusoDoNavegador } from "./mapa/regiao"
import { transformarRequisicao } from "./mapa/requisicao"
import { useTextos } from "./i18n"

export interface GloboProps {
  layers?: MapLayer[];
  /** From useCamadas, to frame/fly to the layers the conversation puts on the globe. */
  mapaRef?: Ref<MapLibreMapHandle>;
  /**
   * Spins the globe slowly (the Home hero). When turned off, the map returns to
   * the REGION of whoever opened the page (the same center as at the start) —
   * the first token of the answer brings the globe back.
   */
  girando?: boolean;
  /** The connection's country (`CF-IPCountry`), the fallback when the browser hides the time zone. */
  pais?: string | null;
  /** Lifts the resolved location (the control's `geolocate`) up for the Home to attach to the turn. */
  aoLocalizar?: (pos: PosicaoDoUsuario) => void;
  /** Lifts the location failure up (browser code; 1 = permission denied) — becomes a toast. */
  aoErroDeLocalizacao?: (codigo: number) => void;
}

/**
 * The Home's 3D globe: the MapLibreMap in globe projection over the HYBRID
 * imagery (satellite + roads and labels) the installation configured
 * (MAPA_HIBRIDO_URL; without it, satellite and, without that, streets —
 * web/lib/fundos-do-mapa.ts). It is the Home's only basemap — CARTO's Dark
 * Matter went away and, with it, the key, the vector style and the switcher
 * (with a single basemap, there is nothing to switch to). There is no "no
 * basemap" state: the page always has a map.
 *
 * Raster on the sphere warps a little when zooming (MapLibre recommends vector
 * for the globe); with imagery as the only basemap this is permanent and
 * accepted. The attribution (MAPA_*_CREDITO) comes from the source, tucked into
 * the "ⓘ" of the discreet chrome — never written by us.
 *
 * The layers (run outputs) come in through `layers`; `mapaRef` lets useCamadas
 * frame the new layer.
 */
export default function Globo({ layers = [], mapaRef, girando = false, pais = null, aoLocalizar, aoErroDeLocalizacao }: GloboProps) {
  // The region is read ONCE, on mount: MapLibreMap builds the map with this
  // center and keeps it as the destination of the hero's return — a new array
  // on every render changes nothing there, but the state makes that explicit.
  // On the server the time zone is the server's (and the value does not go into
  // the HTML); the client's is the one that counts.
  const [centro] = useState(() => centroDaRegiao({ fuso: fusoDoNavegador(), pais }))
  const textos = useTextos().casca.mapa
  return (
    <MapLibreMap
      ref={mapaRef}
      layers={layers}
      isDark
      giroLento={girando}
      basemapInicial="hybrid"
      basemapToggle={false}
      projection="globe"
      transformRequest={transformarRequisicao}
      controlesDiscretos
      geolocalizar
      aoLocalizar={aoLocalizar}
      aoErroDeLocalizacao={aoErroDeLocalizacao}
      tilesBaseUrl="/terra/assistente/tiles"
      center={centro}
      zoom={2.3}
      textos={textos}
    />
  )
}
