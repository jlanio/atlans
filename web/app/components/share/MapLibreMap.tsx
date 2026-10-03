"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import * as maplibregl from "maplibre-gl";
import { useRef, useEffect, useCallback, useState, useId, forwardRef, useImperativeHandle } from "react";
import { TbMap, TbSatellite } from "react-icons/tb";
import { dayjs, fromBackend } from "@/lib/dayjs";
import { conjuntoDoFundo, type Basemap } from "@/lib/fundos-do-mapa";
import { useFundosDoMapa } from "./fundos-do-mapa";

// maplibre-gl 6 ships only as ESM and runs the worker from a URL, which with a
// bundler it cannot find on its own: without this, it creates the worker with
// the page's own URL, the worker dies silently and the vector tiles never load.
// The worker and the `maplibre-gl-shared.mjs` it imports are copied from the
// package to `public/maplibre` in build and dev (scripts/copiar-maplibre.mjs).
maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

export interface MapLayer {
  id: string;
  label: string;
  color: string;
  opacity: number;
  geojson: GeoJSON.FeatureCollection;
  visible: boolean;
  geomType?: string;
  bbox?: number[];
  /**
   * Published layer (MVT): this artifact's vector tiles. Overrides the portal's
   * global `workflowHash`/`tileLayerKeys` pair — the Home has layers from
   * different workflows, each with its own tile. When absent, the MVT path
   * follows the portal's (a single `workflowHash`).
   */
  mvt?: { workflowHash: string; layerKey: string };
  /**
   * The source file can be downloaded (`GET /artifacts/{id}/download`). It comes
   * from the server (`GlobeLayer.baixavel`), and it is NOT the same as "is on
   * the globe": a published layer appears with its content in PostGIS and may
   * have no file in storage. Whoever offers the action hides it when false.
   */
  baixavel?: boolean;
}

// ── The slow spin of the Home hero ───────────────────────────────────────────
// The numbers are those of the approved previewer: half a degree per second,
// westward (the Earth seen from space), in linear one-second steps chained on
// `moveend`; pause after a gesture; the return to `center`/`zoom` lasts the
// same as the bar transition (globals.css, `--home-dur`).
export const SPIN_SPEED_DEGREES_PER_S = 0.5;
export const SPIN_STEP_MS = 1000;
export const PAUSE_AFTER_GESTURE_MS = 2500;
export const REVOLUTION_DURATION_MS = 900;
const RESUME_INTERVAL_MS = 300;
// The framing before there is data (`fitBounds` replaces it when the layers
// arrive): the world, with no preferred region.
const DEFAULT_CENTER: [number, number] = [0, 20];
const DEFAULT_ZOOM = 1.5;
/** The gestures that pause the spin. `Map` event names: since maplibre-gl 6, `on`/`off` do not accept just any `string`. */
const GESTURES: readonly (keyof maplibregl.MapEventType)[] = ["mousedown", "touchstart", "wheel", "dragstart", "mouseup", "touchend", "dragend"];

function _easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/** Read on the spot, not in a hook: here the value changes no markup at all. */
function _prefersReducedMotion(): boolean {
  return typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * The map texts — the control titles (MapLibre's `locale`, read by the screen
 * reader and in each button's `title`) and those of the feature popup. The
 * default is the Portuguese of the `/share` portal; the translated Home passes
 * those of its language. The controls are read in the constructor: the ones
 * at mount time apply.
 */
export interface MapTexts {
  controles: Readonly<Record<string, string>>;
  semAtributos: string;
  campos: (n: number) => string;
  /** The locale for the popup's numbers (`toLocaleString`). */
  numeros: string;
  /** `dayjs` formats for the popup's dates. */
  data: { comHora: string; semHora: string };
}

export const TEXTOS_DO_MAPA_PT: MapTexts = {
  // The document is lang="pt-BR": without this the canvas announces "Map" and
  // the buttons come out in English on the screen reader.
  controles: {
    "Map.Title": "Mapa",
    "NavigationControl.ZoomIn": "Aproximar",
    "NavigationControl.ZoomOut": "Afastar",
    "NavigationControl.ResetBearing": "Voltar ao norte",
    "AttributionControl.ToggleAttribution": "Créditos do mapa",
    "Popup.Close": "Fechar",
    "Marker.Title": "Marcador",
    "GeolocateControl.FindMyLocation": "Mostrar a minha localização",
    "GeolocateControl.LocationNotAvailable": "Localização indisponível",
  },
  semAtributos: "Sem atributos",
  campos: (n) => `${n} ${n === 1 ? "campo" : "campos"}`,
  numeros: "pt-BR",
  data: { comHora: "DD/MM/YYYY HH:mm:ss", semHora: "DD/MM/YYYY" },
};

export interface MapLibreMapHandle {
  fitToLayer: (layerId: string) => void;
  /**
   * Triggers the location control (the same button in the corner), for an
   * entry point OUTSIDE the map — the composer's "Usar minha localização" (use
   * my location). No-op without `geolocalizar`. The browser asks for permission
   * on the first trigger.
   */
  localizar: () => void;
}

/** The position the globe returns to the parent on the `geolocate` event. */
export interface UserPosition {
  lat: number;
  lon: number;
  /** Accuracy radius in meters (the browser's `accuracy`); `null` if absent. */
  precisao_m: number | null;
}

interface Props {
  layers: MapLayer[];
  visibleFields?: Record<string, string[]>;
  useMvt?: boolean;
  workflowHash?: string;
  tileLayerKeys?: Record<string, string>;
  /** Cache-busting: changes when the layer is re-published → invalidates old tiles. */
  tileLayerVersions?: Record<string, string>;
  isDark?: boolean;
  // ── Home extensions (all opt-in; without them the portal's behavior is
  //    identical to what it always was) ────────────────────────────────────────
  /** Map projection. "globe" draws the 3D sphere (applied on `style.load`). */
  projection?: "globe" | "mercator";
  /** Injects credentials into the assistant's private tiles. Passed to the constructor. */
  transformRequest?: maplibregl.RequestTransformFunction;
  /** Shows the basemap toggle (Mapa ↔ Satélite). */
  basemapToggle?: boolean;
  /**
   * The basemap the map is BORN with. Default: "streets", the portal's.
   * The Home is born in "hybrid" — the satellite imagery with roads and labels
   * that the installation configured — and stays in it: with no toggle, it is
   * its only basemap. With `basemapToggle`, only "streets" or "satellite" make
   * sense, the two sides the toggle knows.
   */
  basemapInicial?: Basemap;
  /**
   * Dresses MapLibre's chrome (zoom, compass, scale) in the toggle's
   * language — glass, thin border, low-contrast icon — and collapses the
   * attribution into an "ⓘ" that opens on click. The portal stays with the
   * MapLibre default: solid white box and attribution always open.
   */
  controlesDiscretos?: boolean;
  /** Vector tile prefix. Default: the portal's (`/terra/artifacts/tiles`). */
  tilesBaseUrl?: string;
  /**
   * Spins the globe slowly while `true` — the Home hero. Half a degree per
   * second westward, as in the approved previewer; pauses 2.5 s after any
   * gesture by the person; does not spin with `prefers-reduced-motion`. When it
   * goes back to `false`, the map RETURNS to `center`/`zoom` in 900 ms (in a
   * jump, with no motion): it is the return to the region of whoever opened the
   * page, on the first token of the answer.
   */
  giroLento?: boolean;
  /** Initial center. Default: the whole world, until the layers frame it. */
  center?: [number, number];
  /** Initial zoom. Default: 1.5. */
  zoom?: number;
  /**
   * Corner of the zoom/compass group. Default: "top-right" (the portal). It
   * exists because on full screens with an overlaid panel the default corner is
   * covered — the compass is the only way to set north straight after a gesture.
   */
  controlsPosition?: maplibregl.ControlPosition;
  /**
   * Turns on MapLibre's location control — Home only. A button in the control
   * group shows the person on the globe and FOLLOWS them in real time (the dot
   * and the map keep up as they move). Locating pauses the hero spin and cancels
   * the return to the region while following is active. The `/share` portal
   * does not turn it on. Requires `Permissions-Policy: geolocation=(self)`
   * (next.config.ts); the browser asks for permission on the first click.
   */
  geolocalizar?: boolean;
  /**
   * Called on every position resolved by the location control (MapLibre's
   * `geolocate` event), with the coordinate and the accuracy. The Home uses it
   * to attach the location to the assistant turn. Fires only with `geolocalizar`.
   */
  aoLocalizar?: (pos: UserPosition) => void;
  /**
   * Called when location FAILS (the control's `error` event), with the
   * browser's code (1 = permission denied). It is the only visible feedback from
   * the composer — the control button's state sits in the globe's corner,
   * invisible on the phone with the panel open on top.
   */
  aoErroDeLocalizacao?: (codigo: number) => void;
  /** The texts of the controls and the popup. Default: `TEXTOS_DO_MAPA_PT`. */
  textos?: MapTexts;
}

const FALLBACK_COLORS = ["#3b82f6", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6"];

// The basemaps come from the installation (MAPA_*, web/lib/fundos-do-mapa.ts):
// the code only ships OpenStreetMap streets. HYBRID is the satellite imagery
// PLUS roads and labels — the Home's basemap, which without it falls back to
// satellite and, without that, to streets. The portal toggles streets ↔
// satellite, and without satellite there is no toggle.

/** The minimal v8 style of a raster basemap — what the constructor builds. */
function _rasterStyle(ts: { tiles: string[]; attribution: string }): maplibregl.StyleSpecification {
  return {
    version: 8,
    sources: { basemap: { type: "raster", tiles: ts.tiles, tileSize: 256, attribution: ts.attribution } },
    layers: [{ id: "basemap", type: "raster", source: "basemap" }],
  };
}

/**
 * The CSS scoped to the map container. Pure and exported because it is the ONLY
 * part of MapLibre's appearance that does not go through React: popup and
 * controls are MapLibre's own DOM, with its own stylesheet — hence `!important`.
 *
 * `controlesDiscretos` dresses the map chrome (zoom, compass, scale) in the
 * same language as the basemap toggle — translucent glass, thin border, without
 * the white box with a ring. MapLibre's default is solid white, which over the
 * Home's near-black globe becomes the brightest object on the screen.
 *
 * It is NOT a "disappear" switch: the icon sits at 0.65 opacity and rises to
 * 1 on hover/focus; on touch, where there is no hover, the floor is higher.
 * Less contrast against the map, not less legible.
 */
export function _cssDoMapa(scope: string, isDark: boolean, controlesDiscretos: boolean): string {
  const popup = isDark
    ? `
        ${scope} .maplibregl-popup-content { background: #1e1e1e !important; color: #e5e5e5 !important; padding: 10px !important; border-radius: 8px !important; box-shadow: 0 4px 20px rgba(0,0,0,0.5) !important; }
        ${scope} .maplibregl-popup-anchor-bottom .maplibregl-popup-tip { border-top-color: #1e1e1e !important; }
        ${scope} .maplibregl-popup-anchor-top .maplibregl-popup-tip { border-bottom-color: #1e1e1e !important; }
        ${scope} .maplibregl-popup-close-button { color: #888 !important; }
        ${scope} .maplibregl-popup-close-button:hover { color: #e5e5e5 !important; background: rgba(255,255,255,0.1) !important; }
      `
    : `
        ${scope} .maplibregl-popup-content { background: #ffffff !important; color: #1a1a1a !important; padding: 10px !important; border-radius: 8px !important; box-shadow: 0 4px 20px rgba(0,0,0,0.15) !important; }
        ${scope} .maplibregl-popup-anchor-bottom .maplibregl-popup-tip { border-top-color: #ffffff !important; }
        ${scope} .maplibregl-popup-anchor-top .maplibregl-popup-tip { border-bottom-color: #ffffff !important; }
        ${scope} .maplibregl-popup-close-button { color: #666 !important; }
        ${scope} .maplibregl-popup-close-button:hover { color: #1a1a1a !important; background: rgba(0,0,0,0.05) !important; }
      `;

  if (!controlesDiscretos) return popup;

  // MapLibre's icons are SVG embedded in `background-image`, with the color
  // BAKED into the data URI (a dark gray). They cannot be recolored via `color`;
  // over the dark glass they would vanish. `invert` is what there is.
  const darkIconCss = isDark ? `${scope} .maplibregl-ctrl-icon { filter: invert(1); }` : "";

  return `${popup}
        ${scope} .maplibregl-ctrl-group {
          background: color-mix(in oklab, var(--background) 62%, transparent) !important;
          border: 1px solid color-mix(in oklab, var(--border) 55%, transparent) !important;
          border-radius: 12px !important;
          box-shadow: none !important;
          backdrop-filter: blur(8px);
          overflow: hidden;
        }
        ${scope} .maplibregl-ctrl-group button + button {
          border-top: 1px solid color-mix(in oklab, var(--border) 40%, transparent) !important;
        }
        ${scope} .maplibregl-ctrl-group button:not(:disabled):hover {
          background-color: color-mix(in oklab, var(--accent) 55%, transparent) !important;
        }
        ${darkIconCss}
        ${scope} .maplibregl-ctrl-icon { opacity: 0.65; transition: opacity 150ms ease; }
        ${scope} .maplibregl-ctrl-group button:hover .maplibregl-ctrl-icon,
        ${scope} .maplibregl-ctrl-group button:focus-visible .maplibregl-ctrl-icon { opacity: 1; }
        /* Sem hover para revelar: o piso sobe, senão a chrome fica fraca no toque. */
        @media (hover: none) {
          ${scope} .maplibregl-ctrl-icon { opacity: 0.85; }
        }
        /* Localizar: no estado ativo/segundo-plano o ícone é a mira na cor da
           marca (o azul padrão do MapLibre destoaria do terracota da Home). O
           filter:none desfaz o invert acima — inverter o terracota o estragaria.
           O ponto do usuário e o círculo de precisão idem. */
        ${scope} .maplibregl-ctrl-geolocate.maplibregl-ctrl-geolocate-active .maplibregl-ctrl-icon,
        ${scope} .maplibregl-ctrl-geolocate.maplibregl-ctrl-geolocate-background .maplibregl-ctrl-icon {
          filter: none; opacity: 1;
          background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='29' height='29' fill='%23e3773b' viewBox='0 0 20 20'%3E%3Cpath d='M10 4C9 4 9 5 9 5v.1A5 5 0 0 0 5.1 9H5s-1 0-1 1 1 1 1 1h.1A5 5 0 0 0 9 14.9v.1s0 1 1 1 1-1 1-1v-.1a5 5 0 0 0 3.9-3.9h.1s1 0 1-1-1-1-1-1h-.1A5 5 0 0 0 11 5.1V5s0-1-1-1m0 2.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 1 1 0-7'/%3E%3Ccircle cx='10' cy='10' r='2'/%3E%3C/svg%3E");
        }
        ${scope} .maplibregl-user-location-dot,
        ${scope} .maplibregl-user-location-dot::before { background-color: #e3773b; }
        ${scope} .maplibregl-user-location-accuracy-circle { background-color: rgba(227, 119, 59, 0.18); }
        /* A escala é a mesma família: sem ela, sobraria uma barra branca gritante
           ao lado de controles que acabaram de virar vidro. */
        ${scope} .maplibregl-ctrl-scale {
          background: color-mix(in oklab, var(--background) 55%, transparent) !important;
          border-color: color-mix(in oklab, var(--border) 60%, transparent) !important;
          color: var(--muted-foreground) !important;
          backdrop-filter: blur(6px);
          border-radius: 0 0 4px 4px !important;
        }
        /* O "ⓘ" da atribuição compacta e a caixa que ele abre. */
        ${scope} .maplibregl-ctrl-attrib.maplibregl-compact {
          background: color-mix(in oklab, var(--background) 62%, transparent) !important;
          border-radius: 12px !important;
          backdrop-filter: blur(8px);
        }
        ${scope} .maplibregl-ctrl-attrib-button { opacity: 0.6; }
        ${scope} .maplibregl-ctrl-attrib-button:hover { opacity: 1; }
        ${scope} .maplibregl-ctrl-attrib a { color: var(--muted-foreground) !important; }
      `;
}

const MapLibreMap = forwardRef<MapLibreMapHandle, Props>(function MapLibreMap(
  {
    layers, visibleFields, useMvt, workflowHash, tileLayerKeys, tileLayerVersions, isDark,
    projection, transformRequest, basemapToggle = true, basemapInicial = "streets",
    controlesDiscretos, tilesBaseUrl,
    center, zoom, controlsPosition = "top-right", giroLento = false, geolocalizar = false,
    aoLocalizar, aoErroDeLocalizacao, textos = TEXTOS_DO_MAPA_PT,
  },
  ref,
) {
  const mapId = useId().replace(/:/g, "");
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const initializedRef = useRef(false);
  const fittedRef = useRef(false);
  /**
   * The person is being located/followed: the hero spin is suspended and the
   * return to the region does not fire (otherwise the map would pull it away the
   * instant we find them). A ref, not state: the spin loop reads it live, with
   * no re-render. It only becomes `true` when `geolocalizar` turns on the control.
   */
  const geolocalizandoRef = useRef(false);
  /** The location control, kept so the handle's `localizar()` can trigger it. */
  const geoControlRef = useRef<maplibregl.GeolocateControl | null>(null);
  /** `aoLocalizar` in a ref: the event is bound at mount and the callback changes per render. */
  const onLocateRef = useRef(aoLocalizar);
  onLocateRef.current = aoLocalizar;
  const onLocationErrorRef = useRef(aoErroDeLocalizacao);
  onLocationErrorRef.current = aoErroDeLocalizacao;
  /**
   * One of OUR movements (spin step or return to the region) is in flight. It
   * is what the start of following may cut with `stop()` — cutting ANY
   * movement, as before, also killed the location control's own framing on
   * re-click from background mode (the fitBounds runs before the start event).
   */
  const spinInFlightRef = useRef(false);
  /**
   * Style loaded (`style.load` has already passed). It is what enables
   * `addSource`/`addLayer` — unlike `isStyleLoaded()`, which also requires
   * all sources to be up to date and is therefore false whenever a tile is in flight.
   */
  const styleReadyRef = useRef(false);
  /** Current layers for the pointer handlers, bound to the mount closure. */
  const layersRef = useRef<MapLayer[]>(layers);
  /** Ids from the last sync: the delta avoids scanning the whole style. */
  const previousIdsRef = useRef<string[]>([]);
  /**
   * The CURRENT layer sync, so `style.load` can call it.
   * A `setStyle` that falls into a full load erases sources and layers, and the
   * `[layers]` effect does not run again — the layers did not change. The
   * portal's basemap switch asks for `diff: true`, but MapLibre reloads the
   * whole style when the diff does not apply. Without this pointer, that reload
   * would erase the map's data layers.
   */
  const syncRef = useRef<() => void>(() => {});
  /**
   * The basemap ALREADY applied to the map. Without it the switch effect would
   * fire on mount and do a redundant `setStyle` right after the constructor.
   */
  const appliedBasemapRef = useRef<Basemap>(basemapInicial);
  const [basemap, setBasemap] = useState<Basemap>(basemapInicial);
  // The installation's tile servers. Read via ref in the effects: the map is
  // built once, and the context does not change during the page's life.
  const fundos = useFundosDoMapa();
  const basemapsRef = useRef(fundos);
  basemapsRef.current = fundos;
  // With no satellite configured, both sides of the toggle would be the same map.
  const withToggle = basemapToggle && Boolean(fundos.satelite);

  // ── Exposes fitToLayer / localizar to the parent ───────────────────────────
  useImperativeHandle(ref, () => ({
    fitToLayer(layerId: string) {
      const map = mapRef.current;
      if (!map) return;
      const layer = layers.find((l) => l.id === layerId);
      if (!layer) return;
      const bounds = new maplibregl.LngLatBounds();
      if (_estenderBounds(bounds, layer)) {
        map.fitBounds(bounds, { padding: 60, maxZoom: 15, duration: 600 });
      }
    },
    localizar() {
      const geo = geoControlRef.current;
      if (!geo) return; // without `geolocalizar`, the control does not exist
      // `trigger()` is a TOGGLE: when already following (or waiting for the fix), it
      // TURNS OFF tracking — the opposite of what the composer's "Usar minha
      // localização" asks for. In those states, we only re-emit the last position
      // (the chip comes back at once) and do not touch the control; from
      // background/OFF, trigger() does the right thing (recenters/turns back on).
      // maplibre internal fields, version pinned at 5.20.x; without them, it
      // falls back to the usual trigger().
      const interno = geo as unknown as { _watchState?: string; _lastKnownPosition?: GeolocationPosition };
      if (interno._watchState === "ACTIVE_LOCK" || interno._watchState === "WAITING_ACTIVE") {
        const c = interno._lastKnownPosition?.coords;
        if (c) {
          onLocateRef.current?.({
            lat: c.latitude,
            lon: c.longitude,
            precisao_m: Number.isFinite(c.accuracy) ? c.accuracy : null,
          });
        }
        return;
      }
      geo.trigger();
    },
  }));

  // ── Injeta o CSS escopado ao container (dark/light) ───────────────────────
  useEffect(() => {
    const styleId = `atlans-mapa-style-${mapId}`;
    let el = document.getElementById(styleId) as HTMLStyleElement | null;
    if (!el) {
      el = document.createElement("style");
      el.id = styleId;
      document.head.appendChild(el);
    }
    el.textContent = _cssDoMapa(`#map-${mapId}`, !!isDark, !!controlesDiscretos);
    return () => { el?.remove(); };
  }, [isDark, mapId, controlesDiscretos]);

  // ── Popup HTML (dark mode aware) ───────────────────────────────────────────
  const buildPopupHtml = useCallback(
    (layerLabel: string, properties: Record<string, unknown>, layerId: string, layerColor?: string) => {
      const fields = visibleFields?.[layerId];
      const entries = Object.entries(properties || {}).filter(([key]) => {
        if (fields && fields.length > 0) return fields.includes(key);
        return true;
      });

      // Audit (SEG-122): the layer color comes from publish_config.color (free
      // string) and is interpolated inside a `style="…"` that goes to Popup.setHTML.
      // Only a valid hex is accepted; anything else falls back to the default,
      // closing HTML/attribute injection through the color value.
      const VALID_HEX_COLOR = /^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;
      const color = layerColor && VALID_HEX_COLOR.test(layerColor) ? layerColor : "#FF6A00";
      const text = isDark ? "#e5e5e5" : "#1a1a1a";
      const muted = isDark ? "#888" : "#666";
      const codeBg = isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)";

      const subtext = isDark ? "#b8b8b8" : "#444";
      const border = isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)";
      const zebra = isDark ? "rgba(255,255,255,0.025)" : "rgba(0,0,0,0.025)";
      const okBg = isDark ? "rgba(34,197,94,0.18)" : "rgba(34,197,94,0.14)";
      const okText = isDark ? "#86efac" : "#15803d";
      const offBg = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)";
      const linkText = isDark ? "#7dd3fc" : "#0369a1";

      const escapeHtml = (s: string): string =>
        s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));

      const isUrl = (s: string): boolean => /^https?:\/\/\S+$/i.test(s);
      const isIsoDate = (s: string): boolean =>
        /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$/.test(s);

      const renderCell = (v: unknown): string => {
        if (v === null || v === undefined || v === "") {
          return `<span style="font-style:italic;color:${muted};font-size:11px">\u2014</span>`;
        }
        if (typeof v === "boolean") {
          const bg = v ? okBg : offBg;
          const fg = v ? okText : muted;
          const label = v ? "true" : "false";
          return `<span style="display:inline-block;padding:1px 6px;border-radius:8px;background:${bg};color:${fg};font-size:10px;font-weight:600">${label}</span>`;
        }
        if (typeof v === "number") {
          const formatted = Number.isFinite(v) ? v.toLocaleString(textos.numeros, { maximumFractionDigits: 6 }) : String(v);
          return `<span style="font-size:11px;color:${text};font-variant-numeric:tabular-nums">${formatted}</span>`;
        }
        if (typeof v === "object") {
          const json = escapeHtml(JSON.stringify(v, null, 2));
          return `<pre style="margin:0;padding:4px 6px;font-size:10px;border-radius:4px;background:${codeBg};color:${text};overflow-x:auto;white-space:pre-wrap;word-break:break-all;max-width:220px">${json}</pre>`;
        }
        const s = String(v);
        if (isUrl(s)) {
          const safe = escapeHtml(s);
          return `<a href="${safe}" target="_blank" rel="noopener noreferrer" style="font-size:11px;color:${linkText};text-decoration:none;word-break:break-all">${safe}</a>`;
        }
        if (isIsoDate(s)) {
          // Timestamp (has a time): treats a string with no offset as UTC and converts
          // to the local time zone — same helper as the rest of the app (fromBackend).
          // A raw `new Date(s)` interpreted the UTC as local, shifting by +offset.
          // Date-only (no time): has no time zone semantics — shown as it came so
          // as not to shift the day (UTC midnight would become the previous day in UTC-).
          const hasTime = s.includes("T");
          const dj = hasTime ? fromBackend(s) : dayjs(s);
          if (dj && dj.isValid()) {
            const out = dj.format(hasTime ? textos.data.comHora : textos.data.semHora);
            return `<span style="font-size:11px;color:${text}" title="${escapeHtml(s)}">${out}</span>`;
          }
        }
        return `<span style="font-size:11px;color:${text};word-break:break-word">${escapeHtml(s)}</span>`;
      };

      const safeLabel = escapeHtml(layerLabel);

      // Detects the feature's "name" property (selected panel) by convention
      const NAME_KEYS = ["nome", "name", "titulo", "title", "label", "rotulo", "descricao", "description"];
      const nameKey = entries.find(([k, v]) =>
        NAME_KEYS.includes(k.toLowerCase()) && v !== null && v !== undefined && v !== "" && typeof v !== "object"
      )?.[0];
      const nameVal = nameKey ? String(properties[nameKey]) : null;
      const safeName = nameVal ? escapeHtml(nameVal) : null;

      // Rows: omit the key promoted to the header to avoid duplication
      const bodyEntries = nameKey ? entries.filter(([k]) => k !== nameKey) : entries;
      const bodyCount = bodyEntries.length;

      const headerHtml = safeName
        ? `<div style="display:flex;flex-direction:column;gap:2px;padding:8px 10px;border-left:3px solid ${color};background:${zebra};position:sticky;top:0;z-index:1">
            <strong style="font-size:13px;color:${text};line-height:1.2;word-break:break-word">${safeName}</strong>
            <div style="display:flex;align-items:center;gap:6px">
              <span style="font-size:10px;color:${muted};text-transform:uppercase;letter-spacing:0.04em;font-weight:600">${safeLabel}</span>
              ${bodyCount > 0 ? `<span style="font-size:9px;color:${muted};padding:1px 6px;border-radius:8px;background:${offBg};font-weight:600">${escapeHtml(textos.campos(bodyCount))}</span>` : ""}
            </div>
          </div>`
        : `<div style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-left:3px solid ${color};background:${zebra};position:sticky;top:0;z-index:1">
            <strong style="font-size:12px;flex:1;color:${text}">${safeLabel}</strong>
            ${bodyCount > 0 ? `<span style="font-size:10px;color:${muted};padding:1px 7px;border-radius:8px;background:${offBg};font-weight:600">${escapeHtml(textos.campos(bodyCount))}</span>` : ""}
          </div>`;

      if (bodyCount === 0) {
        return `<div style="min-width:220px;border-radius:6px;overflow:hidden">
          ${headerHtml}
          ${!safeName ? `<div style="padding:14px;font-size:11px;color:${muted};text-align:center;font-style:italic">${escapeHtml(textos.semAtributos)}</div>` : ""}
        </div>`;
      }

      const rows = bodyEntries
        .map(([key, val], i) => {
          const bg = i % 2 === 1 ? zebra : "transparent";
          return `<tr style="background:${bg}">
            <td style="padding:5px 10px;color:${muted};font-size:9px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;white-space:nowrap;vertical-align:top;border-bottom:1px solid ${border}">${escapeHtml(key)}</td>
            <td style="padding:5px 10px 5px 0;max-width:220px;vertical-align:top;border-bottom:1px solid ${border};color:${subtext}">${renderCell(val)}</td>
          </tr>`;
        })
        .join("");

      return `<div style="min-width:240px;max-height:340px;overflow-y:auto;border-radius:6px">
        ${headerHtml}
        <table style="border-collapse:collapse;width:100%;table-layout:auto">${rows}</table>
      </div>`;
    },
    [visibleFields, isDark, textos],
  );
  // The click handler is registered ONCE (mount effect, deps []), so it
  // captures the FIRST render's `buildPopupHtml` — with that instant's
  // `isDark`/`visibleFields` baked into each cell's inline colors. Switching the
  // theme recreated the callback, but the handler kept calling the old one: the
  // popup opened half-updated (the container flips via CSS, the cells do not).
  // Reading it via ref — same idiom as `camadasRef`/`alvoDaVoltaRef` — makes the
  // click always use the current callback.
  const buildPopupHtmlRef = useRef(buildPopupHtml);
  buildPopupHtmlRef.current = buildPopupHtml;

  // ── Initialization ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || initializedRef.current) return;
    initializedRef.current = true;

    const map = new maplibregl.Map({
      container: containerRef.current,
      // The usual raster; `basemapInicial` picks WHICH one. The portal is born in
      // "streets" and toggles; the Home is born in "hybrid" and stays.
      style: _rasterStyle(conjuntoDoFundo(basemapsRef.current, basemapInicial)),
      center: center ?? DEFAULT_CENTER,
      zoom: zoom ?? DEFAULT_ZOOM,
      locale: { ...textos.controles },
      // `transformRequest`/`attributionControl` only exist for the Home; without them
      // the constructor stays identical to what it was.
      ...(transformRequest ? { transformRequest } : {}),
      // NEVER `customAttribution`. Every basemap we use already declares its own
      // attribution in the source (the MAPA_*_CREDITO credit). Passing our own
      // text on top did not replace the source's: MapLibre CONCATENATES the two
      // with " | ", and the Home showed the same thing twice. Letting the source
      // speak also keeps it right on its own when the basemap changes.
      //
      // `compact` collapses what remains into an "ⓘ" that opens on click. It is
      // the way MapLibre offers for the attribution to take little space — it
      // stays one click away, which is what OSM's ODbL and the providers' terms
      // ask for. Hidden, no.
      ...(controlesDiscretos ? { attributionControl: { compact: true as const } } : {}),
    });

    // `style.load` fires on every style loaded: on mount and whenever a
    // `setStyle` reloads the whole style. This is where we mark the map as
    // ready to receive layers and where the globe projection is (re)applied.
    map.on("style.load", () => {
      // `true` from the SECOND load on. It only exists if a `setStyle` fell into
      // a full load: the portal's basemap switch asks for `diff: true`, but
      // MapLibre reloads everything when the diff does not apply.
      const recarga = styleReadyRef.current;
      styleReadyRef.current = true;
      if (projection === "globe") map.setProjection({ type: "globe" });
      // The full load erases sources and layers, and the `[layers]` effect does
      // NOT run again — the layers did not change. Without this call, it would
      // erase the data layers from the map. On the FIRST load the one that syncs
      // is the `[layers]` effect itself, which waits for this same event
      // (`_quandoEstiloPronto`); calling here too would be repeated work.
      // `idsAnterioresRef` is left as is on purpose: it only feeds the
      // computation of what to REMOVE, and `_syncLayers` recreates what is
      // missing by looking at the map (`if (!map.getSource(src))`), not the list.
      if (recarga) syncRef.current();
    });

    map.addControl(new maplibregl.NavigationControl(), controlsPosition);
    // Locate (Home only): goes right below the zoom/compass, in the same corner.
    // `trackUserLocation` gives the FOLLOW mode (the camera follows the person
    // and drops to "background" when they drag the map); the dot and the
    // accuracy circle belong to the control itself. Locating RULES the globe: the
    // spin pauses and the return to the region does not fire while we follow —
    // it resumes when the person turns following off (or the error boot), if the
    // hero still asks for a spin.
    if (geolocalizar) {
      const geo = new maplibregl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
        showAccuracyCircle: true,
        fitBoundsOptions: { maxZoom: 16, duration: 1200 },
      });
      geo.on("trackuserlocationstart", () => {
        geolocalizandoRef.current = true;
        // Cuts only the in-flight spin/return step — stopping ANY movement
        // killed the control's own framing on re-click from
        // background mode (its fitBounds runs BEFORE this event).
        if (spinInFlightRef.current) map.stop();
      });
      geo.on("trackuserlocationend", () => {
        // This event also fires when dropping to BACKGROUND (the person dragged
        // the map), with the watch still alive and the zoom way up — resuming the
        // spin there swept the screen at 0.5°/s over the person's home. It only
        // releases when the control really went to OFF. `_watchState` is a
        // maplibre internal (version pinned at 5.20.x); if it disappears in an
        // update, the fallback is to release as before.
        const estado = (geo as unknown as { _watchState?: string })._watchState;
        if (estado && estado !== "OFF") return;
        geolocalizandoRef.current = false;
      });
      // Each resolved position (follow mode emits several) goes up to the parent —
      // it is what the Home attaches to the turn. The event carries a GeolocationPosition.
      geo.on("geolocate", (e) => {
        const c = (e as unknown as GeolocationPosition).coords;
        if (!c) return;
        onLocateRef.current?.({
          lat: c.latitude,
          lon: c.longitude,
          precisao_m: Number.isFinite(c.accuracy) ? c.accuracy : null,
        });
      });
      // PERMISSION DENIED drops the control to OFF WITHOUT `trackuserlocationend`
      // — without this handler the hero spin stayed suspended forever. And it is
      // the only way for the composer to give feedback on the failure (the
      // control button is hidden behind the panel on the phone).
      geo.on("error", (e) => {
        const codigo = (e as unknown as GeolocationPositionError | undefined)?.code ?? 0;
        if (codigo === 1) geolocalizandoRef.current = false;
        onLocationErrorRef.current?.(codigo);
      });
      geoControlRef.current = geo;
      map.addControl(geo, controlsPosition);
    }
    map.addControl(new maplibregl.ScaleControl(), "bottom-right");
    mapRef.current = map;

    // Any movement that ends (including a `stop()`) closes "our" flight — the
    // flag only turns back on when the spin/return fire the next easeTo.
    map.on("moveend", () => { spinInFlightRef.current = false; });

    map.on("mousemove", (e) => {
      const ids = _idsInterativos(map, layersRef.current);
      if (!ids.length) return;
      const feats = map.queryRenderedFeatures(e.point, { layers: ids });
      map.getCanvas().style.cursor = feats.length ? "pointer" : "";
    });

    map.on("click", (e) => {
      const ids = _idsInterativos(map, layersRef.current);
      if (!ids.length) return;
      const feats = map.queryRenderedFeatures(e.point, { layers: ids });
      if (!feats.length) {
        popupRef.current?.remove();
        return;
      }
      const f = feats[0];
      const lid = f.layer.id.replace(/^(fill|line|circle)-/, "");
      const meta = layersRef.current.find((l) => l.id === lid);
      popupRef.current?.remove();
      popupRef.current = new maplibregl.Popup({ maxWidth: "380px", closeButton: true, closeOnClick: false })
        .setLngLat(e.lngLat)
        .setHTML(buildPopupHtmlRef.current(meta?.label || "Feature", f.properties as Record<string, unknown>, lid, meta?.color))
        .addTo(map);
    });

    return () => {
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
      initializedRef.current = false;
      fittedRef.current = false;
      styleReadyRef.current = false;
      previousIdsRef.current = [];
      appliedBasemapRef.current = basemapInicial;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Slow spin (the Home hero) ──────────────────────────────────────────────
  // Declared AFTER the initialization: on mount with `giroLento` already on, the
  // map needs to exist when this effect runs. `center`/`zoom` come in via ref,
  // not through the dependencies: the Globo passes them as literals, and a new
  // array on every render would restart the spin (with a `stop()`) on every render.
  const returnTargetRef = useRef({ center, zoom });
  returnTargetRef.current = { center, zoom };
  const spunRef = useRef(false);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const reduceMotion = _prefersReducedMotion();

    if (!giroLento) {
      // Only what spun returns: in the portal, which never spins, this does nothing.
      if (!spunRef.current) return;
      spunRef.current = false;
      // Following the person: do NOT return to the region — that would pull the map
      // away the instant we find them (the owner's decision).
      if (geolocalizandoRef.current) return;
      const { center: c, zoom: z } = returnTargetRef.current;
      const destino = { center: c ?? DEFAULT_CENTER, zoom: z ?? DEFAULT_ZOOM };
      if (reduceMotion) map.jumpTo(destino);
      else {
        spinInFlightRef.current = true; // locating during the return may cut it
        map.easeTo({ ...destino, duration: REVOLUTION_DURATION_MS, easing: _easeInOutCubic, essential: true });
      }
      return;
    }

    spunRef.current = true;
    // Without motion the globe stays still — and the return, above, is a jump.
    if (reduceMotion) return;

    let lastGesture = -Infinity;
    const gesto = () => { lastGesture = Date.now(); };
    const passo = () => {
      // Localizando/seguindo a pessoa: o giro fica suspenso.
      if (geolocalizandoRef.current) return;
      if (map.isMoving()) return;
      if (Date.now() - lastGesture < PAUSE_AFTER_GESTURE_MS) return;
      const atual = map.getCenter();
      spinInFlightRef.current = true; // it is the step that the start of following may cut
      map.easeTo({
        center: [atual.lng - SPIN_SPEED_DEGREES_PER_S * (SPIN_STEP_MS / 1000), atual.lat],
        duration: SPIN_STEP_MS,
        easing: (n: number) => n,
        essential: true,
      });
    };
    for (const g of GESTURES) map.on(g, gesto);
    // Chains at the end of each step; the interval resumes after a gesture's pause.
    map.on("moveend", passo);
    const retomada = setInterval(passo, RESUME_INTERVAL_MS);
    passo();
    return () => {
      clearInterval(retomada);
      map.off("moveend", passo);
      for (const g of GESTURES) map.off(g, gesto);
      // Interrupts the in-flight step: the return (the next effect) starts from where
      // the globe is. On unmount the map may already have been removed — hence the try.
      try { map.stop(); } catch { /* mapa removido */ }
    };
  }, [giroLento]);

  // ── Basemap switch ─────────────────────────────────────────────────────────
  // The basemap is ONE raster source inside a style we build by hand. Switching
  // is patching `sources.basemap.tiles` — cheap, and the data layers do not even
  // flicker. (If the diff does not apply and MapLibre reloads the whole style,
  // the `style.load` above puts them back.) The attribution follows on its own:
  // MapLibre's control re-reads it from the style on every `styledata`.
  useEffect(() => {
    const map = mapRef.current;
    // Covers the mount: the state is born as `basemapInicial` and the map was
    // already built that way. Without the guard, the first render would do a
    // redundant `setStyle`.
    if (!map || appliedBasemapRef.current === basemap) return;
    appliedBasemapRef.current = basemap;
    const ts = conjuntoDoFundo(basemapsRef.current, basemap);
    const style = map.getStyle();
    if (style?.sources?.basemap) {
      (style.sources.basemap as Record<string, unknown>).tiles = ts.tiles;
      (style.sources.basemap as Record<string, unknown>).attribution = ts.attribution;
      map.setStyle(style, { diff: true });
    }
  }, [basemap]);

  // ── Sincronizar layers ─────────────────────────────────────────────────────
  useEffect(() => {
    layersRef.current = layers;
    const map = mapRef.current;
    if (!map) return;
    const sync = () => {
      const didFit = _syncLayers(
        map,
        layers,
        fittedRef.current,
        useMvt && workflowHash ? workflowHash : undefined,
        tileLayerKeys,
        tileLayerVersions,
        tilesBaseUrl,
        previousIdsRef.current,
      );
      previousIdsRef.current = layers.map((l) => l.id);
      if (didFit) fittedRef.current = true;
    };
    // `style.load` calls THIS sync after a `setStyle`. Keeping the current
    // closure is what keeps the conversation's layers on the globe when the
    // basemap changes — the `[layers]` effect does not run at that moment.
    syncRef.current = sync;
    // Waiting for `load`/`isStyleLoaded()` silently lost syncs: `load` fires
    // ONCE in the map's life (a `once` registered later never runs) and
    // `isStyleLoaded()` is false while any tile is in flight — on the vector
    // globe, the rule. What is enough to create layers is the style having
    // loaded, signaled once per style on `style.load`.
    return _quandoEstiloPronto(map, styleReadyRef.current, sync);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layers]);

  return (
    <div className="relative w-full h-full">
      <div id={`map-${mapId}`} ref={containerRef} className="w-full h-full" />

      {/* Basemap toggle. Two buttons and not a switch: the label of the
          ACTIVE side must stay visible — "Mapa"/"Satélite" say what you are
          seeing, and a switch would only say where you are going. */}
      {withToggle && (
      <div className="absolute bottom-6 left-3 z-10 flex rounded-xl overflow-hidden border border-border/50 shadow-lg bg-background/80 backdrop-blur-md">
        <button
          type="button"
          onClick={() => setBasemap("streets")}
          aria-pressed={basemap === "streets"}
          className={`flex items-center gap-1.5 px-3 py-2 text-[11px] font-medium transition-all max-md:min-h-10 ${
            basemap === "streets"
              ? "bg-accent text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
          }`}
        >
          <TbMap className="size-3.5" />
          Mapa
        </button>
        <span className="w-px bg-border/40" />
        <button
          type="button"
          onClick={() => setBasemap("satellite")}
          aria-pressed={basemap === "satellite"}
          className={`flex items-center gap-1.5 px-3 py-2 text-[11px] font-medium transition-all max-md:min-h-10 ${
            basemap === "satellite"
              ? "bg-accent text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
          }`}
        >
          <TbSatellite className="size-3.5" />
          Satélite
        </button>
      </div>
      )}
    </div>
  );
});

export default MapLibreMap;

// ── Helpers ────────────────────────────────────────────────────────────────────

/**
 * Clickable ids derived from the component's layers. They used to come from
 * `map.getStyle()`, which serializes ALL sources and layers of the style — with
 * a vector basemap (over a hundred layers) that happened on every mousemove.
 * Here the cost is proportional to our layers, which are few.
 * Exported for tests.
 */
export function _idsInterativos(map: maplibregl.Map, layers: MapLayer[]): string[] {
  const ids: string[] = [];
  for (const layer of layers) {
    if (!layer.visible) continue;
    for (const prefixo of ["fill-", "line-", "circle-"]) {
      const id = `${prefixo}${layer.id}`;
      // The layer may not exist (a geometry type that does not use it) and
      // `queryRenderedFeatures` with a nonexistent id brings down the whole query.
      if (map.getLayer(id)) ids.push(id);
    }
  }
  return ids;
}

/**
 * Runs `sync` now, if the style has already loaded, or on the next `style.load`.
 * Returns the listener cleanup. Exported for tests.
 */
export function _quandoEstiloPronto(
  map: maplibregl.Map,
  styleReady: boolean,
  sync: () => void,
): (() => void) | undefined {
  if (styleReady) {
    sync();
    return undefined;
  }
  map.once("style.load", sync);
  return () => { map.off("style.load", sync); };
}

/**
 * Filter by the feature's geometry type. Also accepts the Multi* variants
 * (GeoJSON returns them; MVT only the simple ones). Exported for tests.
 */
export function _filtroGeom(...tipos: Array<"Point" | "LineString" | "Polygon">): maplibregl.FilterSpecification {
  const aceitos = tipos.flatMap((t) => [t, `Multi${t}`]);
  return ["in", ["geometry-type"], ["literal", aceitos]];
}

/**
 * Ids of THIS component's layers present in the style (suffix of `fill-`/
 * `line-`/`circle-` whose source is `src-*`, plus orphan `src-*` sources).
 * Compatibility path for callers of `_syncLayers` without the previous list.
 */
function _ownStyleLayers(map: maplibregl.Map): string[] {
  const estilo = map.getStyle();
  const ids = new Set<string>();
  for (const l of estilo.layers || []) {
    const m = /^(fill|line|circle)-(.+)$/.exec(l.id);
    const src = (l as { source?: string }).source;
    if (m && typeof src === "string" && src.startsWith("src-")) ids.add(m[2]);
  }
  for (const srcId of Object.keys(estilo.sources || {})) {
    const m = /^src-(.+)$/.exec(srcId);
    if (m) ids.add(m[1]);
  }
  return [...ids];
}

// maplibre-gl 6 types the name and value of each paint property. The type that
// lists them comes from style-spec, which is not a direct dependency: hence
// reading them from the `setPaintProperty` signature.
type PaintProperty = Parameters<maplibregl.Map["setPaintProperty"]>[1];
type PaintValue = Parameters<maplibregl.Map["setPaintProperty"]>[2];

/** Only writes the property when it actually changed (avoids repainting the style). */
function _setPaint(map: maplibregl.Map, id: string, prop: PaintProperty, valor: PaintValue): void {
  if (map.getPaintProperty(id, prop) !== valor) {
    map.setPaintProperty(id, prop, valor);
  }
}

function _setVisibility(map: maplibregl.Map, id: string, visivel: boolean): void {
  const alvo = visivel ? "visible" : "none";
  // A missing `visibility` is equivalent to "visible" — do not rewrite for nothing.
  const atual = map.getLayoutProperty(id, "visibility") ?? "visible";
  if (atual !== alvo) map.setLayoutProperty(id, "visibility", alvo);
}

/** Returns true if fitBounds was called in this invocation. Exported for tests. */
export function _syncLayers(
  map: maplibregl.Map,
  layers: MapLayer[],
  alreadyFitted: boolean,
  mvtWorkflowHash?: string,
  tileLayerKeys?: Record<string, string>,
  tileLayerVersions?: Record<string, string>,
  tilesBaseUrl?: string,
  previousIds?: string[],
): boolean {
  // ── Removes the layers that left the list ──────────────────────────────────
  // The Home removes layers from the globe (the portal has a stable list, so
  // nothing disappears there). It only touches what THIS component created —
  // layers whose source is `src-*` —, never the basemap's own. Layers before
  // sources: a source still in use cannot be removed.
  // Whoever passes `idsAnteriores` (the component, via ref) closes the delta
  // without `getStyle()`, which serializes all of the basemap's sources and layers.
  const wantedIds = new Set(layers.map((l) => l.id));
  const removidas = previousIds
    ? previousIds.filter((id) => !wantedIds.has(id))
    : _ownStyleLayers(map).filter((id) => !wantedIds.has(id));
  for (const id of removidas) {
    for (const prefixo of ["fill-", "line-", "circle-"]) {
      if (map.getLayer(`${prefixo}${id}`)) map.removeLayer(`${prefixo}${id}`);
    }
    if (map.getSource(`src-${id}`)) map.removeSource(`src-${id}`);
  }

  const bounds = new maplibregl.LngLatBounds();
  let hasBounds = false;

  layers.forEach((layer, i) => {
    const src = `src-${layer.id}`;
    const fillId = `fill-${layer.id}`;
    const lineId = `line-${layer.id}`;
    const circleId = `circle-${layer.id}`;
    const color = layer.color || FALLBACK_COLORS[i % FALLBACK_COLORS.length];

    // Per-layer MVT (the Home) takes precedence over the portal's global pair.
    const layerKey = tileLayerKeys?.[layer.id];
    const mvtInfo = layer.mvt ?? (mvtWorkflowHash && layerKey ? { workflowHash: mvtWorkflowHash, layerKey } : undefined);
    const useMvt = !!mvtInfo;

    if (!map.getSource(src)) {
      if (mvtInfo) {
        // Cache-buster: query string based on the layer's last publication.
        // Without it, MapLibre/Cloudflare/browser serve stale tiles after a
        // re-publication (max-age=3600 on the backend) — the user sees mixed data.
        const version = tileLayerVersions?.[layer.id]
        const versionQs = version ? `?v=${encodeURIComponent(version)}` : ""
        // Default: portal tiles. The Home passes `/terra/assistente/tiles`.
        const base = tilesBaseUrl ?? `${window.location.origin}/terra/artifacts/tiles`
        map.addSource(src, {
          type: "vector",
          tiles: [`${base}/${mvtInfo.workflowHash}/${mvtInfo.layerKey}/{z}/{x}/{y}.pbf${versionQs}`],
          minzoom: 0,
          maxzoom: 16,
        });
      } else {
        map.addSource(src, { type: "geojson", data: layer.geojson });
      }
    } else if (!useMvt) {
      (map.getSource(src) as maplibregl.GeoJSONSource).setData(layer.geojson);
    }

    // A null geomType rendered NOTHING, silently. We infer it from the first
    // feature (GeoJSON). In an MVT with no declared type we fall into `semTipo`:
    // there we add the three layers WITH a `geometry-type` filter. The filter is
    // mandatory: a `circle` layer draws a circle per VERTEX, including those of
    // a polygon, and a `fill` layer triangulates even a LineString — without it
    // a field plot becomes a cloud of dots on the public portal.
    const gt = layer.geomType || _sniffGeomType(layer.geojson);
    const withoutType = useMvt && !gt;
    const isPoly = gt.includes("Polygon");
    const isLine = gt.includes("LineString");
    const isPoint = gt.includes("Point");
    const sourceLayer = mvtInfo ? mvtInfo.layerKey : undefined;

    if (isPoly || withoutType) {
      if (!map.getLayer(fillId)) {
        map.addLayer({
          id: fillId, type: "fill", source: src, ...(sourceLayer ? { "source-layer": sourceLayer } : {}),
          ...(withoutType ? { filter: _filtroGeom("Polygon") } : {}),
          paint: { "fill-color": color, "fill-opacity": layer.opacity },
        });
      } else {
        _setPaint(map, fillId, "fill-color", color);
        _setPaint(map, fillId, "fill-opacity", layer.opacity);
      }
      _setVisibility(map, fillId, layer.visible);
    }

    if (isPoly || isLine || withoutType) {
      if (!map.getLayer(lineId)) {
        map.addLayer({
          id: lineId, type: "line", source: src, ...(sourceLayer ? { "source-layer": sourceLayer } : {}),
          // With no declared type, the outline covers polygon AND line: both have an outline.
          ...(withoutType ? { filter: _filtroGeom("Polygon", "LineString") } : {}),
          paint: { "line-color": color, "line-width": isPoly ? 1.5 : 2.5, "line-opacity": 0.9 },
        });
      } else {
        _setPaint(map, lineId, "line-color", color);
      }
      _setVisibility(map, lineId, layer.visible);
    }

    if (isPoint || withoutType) {
      if (!map.getLayer(circleId)) {
        map.addLayer({
          id: circleId, type: "circle", source: src, ...(sourceLayer ? { "source-layer": sourceLayer } : {}),
          ...(withoutType ? { filter: _filtroGeom("Point") } : {}),
          paint: { "circle-color": color, "circle-radius": 6, "circle-opacity": layer.opacity, "circle-stroke-color": "#fff", "circle-stroke-width": 1.5 },
        });
      } else {
        _setPaint(map, circleId, "circle-color", color);
        _setPaint(map, circleId, "circle-opacity", layer.opacity);
      }
      _setVisibility(map, circleId, layer.visible);
    }

    if (layer.visible && _estenderBounds(bounds, layer)) hasBounds = true;
  });

  // fitBounds only on the first load
  if (hasBounds && !alreadyFitted) {
    map.fitBounds(bounds, { padding: 50, maxZoom: 15 });
    return true;
  }
  return false;
}

/** Geometry type of the first feature — "" if there is none (e.g. MVT). */
export function _sniffGeomType(fc: GeoJSON.FeatureCollection): string {
  const g = fc?.features?.find((f) => f.geometry)?.geometry;
  return g?.type ?? "";
}

/** Extends `bounds` by the layer's bbox, or by the features' coordinates.
    Returns true if it extended. */
export function _estenderBounds(bounds: maplibregl.LngLatBounds, layer: MapLayer): boolean {
  if (layer.bbox && layer.bbox.length === 4) {
    bounds.extend([layer.bbox[0], layer.bbox[1]] as [number, number]);
    bounds.extend([layer.bbox[2], layer.bbox[3]] as [number, number]);
    return true;
  }
  let has = false;
  if (layer.geojson?.features?.length) {
    for (const f of layer.geojson.features) {
      if (!f.geometry) continue;
      for (const c of _coords(f.geometry)) {
        bounds.extend(c as [number, number]);
        has = true;
      }
    }
  }
  return has;
}

function _coords(g: GeoJSON.Geometry): number[][] {
  switch (g.type) {
    case "Point": return [g.coordinates as number[]];
    case "MultiPoint": case "LineString": return g.coordinates as number[][];
    case "MultiLineString": case "Polygon": return (g.coordinates as number[][][]).flat();
    case "MultiPolygon": return (g.coordinates as number[][][][]).flat(2);
    case "GeometryCollection": return g.geometries.flatMap(_coords);
    default: return [];
  }
}
