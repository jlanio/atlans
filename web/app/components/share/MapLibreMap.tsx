"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import * as maplibregl from "maplibre-gl";
import { useRef, useEffect, useCallback, useState, useId, forwardRef, useImperativeHandle } from "react";
import { TbMap, TbSatellite } from "react-icons/tb";
import { dayjs, fromBackend } from "@/lib/dayjs";
import { conjuntoDoFundo, type Basemap } from "@/lib/fundos-do-mapa";
import { useFundosDoMapa } from "./fundos-do-mapa";

// O maplibre-gl 6 só sai em ESM e roda o worker a partir de uma URL, que com
// bundler ele não acha sozinho: sem isto, cria o worker com a URL da própria
// página, o worker morre em silêncio e os tiles vetoriais nunca carregam. O
// worker e o `maplibre-gl-shared.mjs` que ele importa são copiados do pacote
// para `public/maplibre` no build e no dev (scripts/copiar-maplibre.mjs).
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
   * Camada publicada (MVT): tiles vetoriais deste artefato. Sobrepõe o par
   * global `workflowHash`/`tileLayerKeys` do portal — a Home tem camadas de
   * fluxos diferentes, cada uma com o seu tile. Quando ausente, o caminho MVT
   * segue o do portal (um `workflowHash` só).
   */
  mvt?: { workflowHash: string; layerKey: string };
  /**
   * O arquivo de origem pode ser baixado (`GET /artifacts/{id}/download`). Vem
   * do servidor (`CamadaDoGlobo.baixavel`), e NÃO é o mesmo que "está no globo":
   * uma camada publicada aparece com o conteúdo no PostGIS e pode não ter
   * arquivo no storage. Quem oferece a ação a esconde quando é falso.
   */
  baixavel?: boolean;
}

// ── O giro lento do hero da Home ─────────────────────────────────────────────
// Os números são os do previewer aprovado: meio grau por segundo, para oeste (a
// Terra vista do espaço), em passos lineares de um segundo encadeados no
// `moveend`; pausa depois de um gesto; a volta ao `center`/`zoom` dura o mesmo
// que a transição da barra (globals.css, `--home-dur`).
export const VELOCIDADE_DO_GIRO_GRAUS_POR_S = 0.5;
export const PASSO_DO_GIRO_MS = 1000;
export const PAUSA_APOS_GESTO_MS = 2500;
export const DURACAO_DA_VOLTA_MS = 900;
const INTERVALO_DE_RETOMADA_MS = 300;
// O enquadramento antes de haver dado (o `fitBounds` o troca quando as camadas
// chegam): o mundo, sem região de preferência.
const CENTRO_PADRAO: [number, number] = [0, 20];
const ZOOM_PADRAO = 1.5;
/** Os gestos que pausam o giro. Nomes de evento do `Map`: desde o maplibre-gl 6, `on`/`off` não aceitam uma `string` qualquer. */
const GESTOS: readonly (keyof maplibregl.MapEventType)[] = ["mousedown", "touchstart", "wheel", "dragstart", "mouseup", "touchend", "dragend"];

function _easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/** Lido na hora, e não num hook: aqui o valor não muda markup nenhum. */
function _prefereMenosMovimento(): boolean {
  return typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Os textos do mapa — os títulos dos controles (o `locale` do MapLibre, lido
 * pelo leitor de tela e no `title` de cada botão) e os do popup de feição. O
 * padrão é o português do portal `/share`; a Home traduzida passa os do idioma
 * dela. Os controles são lidos no construtor: valem os da montagem.
 */
export interface TextosDoMapa {
  controles: Readonly<Record<string, string>>;
  semAtributos: string;
  campos: (n: number) => string;
  /** O locale dos números do popup (`toLocaleString`). */
  numeros: string;
  /** Formatos `dayjs` das datas do popup. */
  data: { comHora: string; semHora: string };
}

export const TEXTOS_DO_MAPA_PT: TextosDoMapa = {
  // O documento é lang="pt-BR": sem isto o canvas anuncia "Map" e os botões
  // saem em inglês no leitor de tela.
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
   * Aciona o controle de localização (o mesmo botão do canto), para uma entrada
   * FORA do mapa — o "Usar minha localização" do compositor. No-op sem
   * `geolocalizar`. O navegador pede a permissão no primeiro acionamento.
   */
  localizar: () => void;
}

/** A posição que o globo devolve ao pai no evento `geolocate`. */
export interface PosicaoDoUsuario {
  lat: number;
  lon: number;
  /** Raio de precisão em metros (o `accuracy` do navegador); `null` se ausente. */
  precisao_m: number | null;
}

interface Props {
  layers: MapLayer[];
  visibleFields?: Record<string, string[]>;
  useMvt?: boolean;
  workflowHash?: string;
  tileLayerKeys?: Record<string, string>;
  /** Cache-busting: muda quando a camada é re-publicada → invalida tiles antigas. */
  tileLayerVersions?: Record<string, string>;
  isDark?: boolean;
  // ── Extensões da Home (todas opt-in; sem elas o comportamento do portal é
  //    idêntico ao de sempre) ────────────────────────────────────────────────
  /** Projeção do mapa. "globe" desenha a esfera 3D (aplicada no `style.load`). */
  projection?: "globe" | "mercator";
  /** Injeta credenciais nos tiles privados do assistente. Repassado ao construtor. */
  transformRequest?: maplibregl.RequestTransformFunction;
  /** Mostra o alternador de basemap (Mapa ↔ Satélite). */
  basemapToggle?: boolean;
  /**
   * O basemap com que o mapa NASCE. Padrão: "streets" (as ruas), o do portal.
   * A Home nasce em "hybrid" — a imagem de satélite com vias e rótulos que a
   * instalação configurou — e fica nele: sem alternador, é o único basemap dela.
   * Com `basemapToggle`, só faz sentido "streets" ou "satellite", os dois lados
   * que o alternador conhece.
   */
  basemapInicial?: Basemap;
  /**
   * Veste a chrome do MapLibre (zoom, bússola, escala) com a linguagem do
   * alternador — vidro, borda fina, ícone de baixo contraste — e recolhe a
   * atribuição a um "ⓘ" que abre no clique. O portal segue no padrão do
   * MapLibre: caixa branca sólida e atribuição sempre aberta.
   */
  controlesDiscretos?: boolean;
  /** Prefixo dos tiles vetoriais. Padrão: os do portal (`/terra/artifacts/tiles`). */
  tilesBaseUrl?: string;
  /**
   * Gira o globo devagar enquanto `true` — o hero da Home. Meio grau por
   * segundo para oeste, como no previewer aprovado; pausa 2,5 s depois de
   * qualquer gesto da pessoa; não gira com `prefers-reduced-motion`. Ao voltar
   * a `false`, o mapa RETORNA a `center`/`zoom` em 900 ms (num salto, sem
   * movimento): é a volta à região de quem abriu a página no primeiro token da resposta.
   */
  giroLento?: boolean;
  /** Centro inicial. Padrão: o mundo inteiro, até as camadas enquadrarem. */
  center?: [number, number];
  /** Zoom inicial. Padrão: 1.5. */
  zoom?: number;
  /**
   * Canto do grupo de zoom/bússola. Padrão: "top-right" (o portal). Existe
   * porque em telas cheias com painel sobreposto o canto padrão fica coberto —
   * a bússola é o único jeito de reendireitar o norte depois de um gesto.
   */
  controlsPosition?: maplibregl.ControlPosition;
  /**
   * Liga o controle de localização do MapLibre — só a Home. Um botão no grupo
   * de controles mostra a pessoa no globo e a SEGUE em tempo real (o ponto e o
   * mapa acompanham enquanto ela anda). Localizar pausa o giro do hero e cancela
   * a volta à região enquanto o seguir estiver ativo. O portal `/share` não o
   * liga. Exige `Permissions-Policy: geolocation=(self)` (next.config.ts); o
   * navegador pede a permissão no primeiro clique.
   */
  geolocalizar?: boolean;
  /**
   * Chamado a cada posição resolvida pelo controle de localização (o evento
   * `geolocate` do MapLibre), com a coordenada e a precisão. A Home usa para
   * anexar a localização ao turno do assistente. Só dispara com `geolocalizar`.
   */
  aoLocalizar?: (pos: PosicaoDoUsuario) => void;
  /**
   * Chamado quando a localização FALHA (o evento `error` do controle), com o
   * código do navegador (1 = permissão negada). É o único retorno visível a
   * partir do compositor — o estado do botão do controle fica no canto do
   * globo, invisível no telefone com o painel aberto por cima.
   */
  aoErroDeLocalizacao?: (codigo: number) => void;
  /** Os textos dos controles e do popup. Padrão: `TEXTOS_DO_MAPA_PT`. */
  textos?: TextosDoMapa;
}

const FALLBACK_COLORS = ["#3b82f6", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6"];

// Os fundos vêm da instalação (MAPA_*, web/lib/fundos-do-mapa.ts): o código
// só traz as ruas do OpenStreetMap. O HÍBRIDO é a imagem de satélite MAIS vias e
// rótulos — o basemap da Home, que sem ele cai no satélite e, sem este, nas
// ruas. O portal alterna ruas ↔ satélite, e sem satélite não há alternador.

/** O estilo v8 mínimo de um basemap raster — o que o construtor monta. */
function _estiloRaster(ts: { tiles: string[]; attribution: string }): maplibregl.StyleSpecification {
  return {
    version: 8,
    sources: { basemap: { type: "raster", tiles: ts.tiles, tileSize: 256, attribution: ts.attribution } },
    layers: [{ id: "basemap", type: "raster", source: "basemap" }],
  };
}

/**
 * O CSS escopado ao container do mapa. Puro e exportado porque é a ÚNICA parte
 * da aparência do MapLibre que não passa pelo React: popup e controles são DOM
 * do próprio MapLibre, com folha de estilo própria — daí o `!important`.
 *
 * `controlesDiscretos` veste a chrome do mapa (zoom, bússola, escala) com a
 * mesma linguagem do alternador de basemap — vidro translúcido, borda fina,
 * sem a caixa branca com anel. O padrão do MapLibre é branco sólido, que sobre
 * o globo quase preto da Home vira o objeto mais claro da tela.
 *
 * NÃO é um interruptor de "sumir": o ícone fica em 0,65 de opacidade e sobe a
 * 1 no hover/foco; no toque, onde não existe hover, o piso é mais alto. Menos
 * contraste contra o mapa, e não menos legível.
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

  // Os ícones do MapLibre são SVG embutido em `background-image`, com a cor
  // ASSADA no data URI (um cinza escuro). Não dá para recolori-los por `color`;
  // sobre o vidro escuro eles sumiriam. `invert` é o que existe.
  const iconeEscuro = isDark ? `${scope} .maplibregl-ctrl-icon { filter: invert(1); }` : "";

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
        ${iconeEscuro}
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
   * A pessoa está sendo localizada/seguida: o giro do hero fica suspenso e a
   * volta à região não dispara (senão o mapa a puxaria para longe no instante
   * em que a encontramos). Ref, não estado: o laço do giro a lê ao vivo, sem
   * re-render. Só vira `true` quando `geolocalizar` liga o controle.
   */
  const geolocalizandoRef = useRef(false);
  /** O controle de localização, guardado para o `localizar()` do handle acioná-lo. */
  const geoControlRef = useRef<maplibregl.GeolocateControl | null>(null);
  /** `aoLocalizar` num ref: o evento é ligado na montagem e o callback muda por render. */
  const aoLocalizarRef = useRef(aoLocalizar);
  aoLocalizarRef.current = aoLocalizar;
  const aoErroDeLocalizacaoRef = useRef(aoErroDeLocalizacao);
  aoErroDeLocalizacaoRef.current = aoErroDeLocalizacao;
  /**
   * Há um movimento NOSSO (passo do giro ou volta à região) em voo. É o que o
   * início do seguir pode cortar com `stop()` — cortar QUALQUER movimento, como
   * antes, matava também o enquadramento do próprio controle de localização no
   * reclique a partir do 2º plano (o fitBounds roda antes do evento de start).
   */
  const giroEmVooRef = useRef(false);
  /**
   * Estilo carregado (o `style.load` já passou). É o que habilita
   * `addSource`/`addLayer` — diferente de `isStyleLoaded()`, que também exige
   * todas as fontes em dia e por isso é falso sempre que há tile em voo.
   */
  const estiloProntoRef = useRef(false);
  /** Camadas atuais para os handlers de ponteiro, presos ao closure da montagem. */
  const camadasRef = useRef<MapLayer[]>(layers);
  /** Ids da última sincronização: o delta dispensa varrer o estilo inteiro. */
  const idsAnterioresRef = useRef<string[]>([]);
  /**
   * A sincronização de camadas ATUAL, para o `style.load` poder chamá-la.
   * Um `setStyle` que caia em carga completa apaga sources e layers, e o
   * efeito de `[layers]` não roda de novo — as camadas não mudaram. A troca
   * de basemap do portal pede `diff: true`, mas o MapLibre recarrega o estilo
   * inteiro quando o diff não se aplica. Sem este ponteiro, essa recarga
   * apagaria as camadas de dados do mapa.
   */
  const sincronizarRef = useRef<() => void>(() => {});
  /**
   * O basemap JÁ aplicado ao mapa. Sem ele o efeito da troca dispararia na
   * montagem e faria um `setStyle` redundante logo depois do construtor.
   */
  const basemapAplicadoRef = useRef<Basemap>(basemapInicial);
  const [basemap, setBasemap] = useState<Basemap>(basemapInicial);
  // Os servidores de tiles da instalação. Lidos por ref nos efeitos: o mapa é
  // construído uma vez, e o contexto não muda durante a vida da página.
  const fundos = useFundosDoMapa();
  const fundosRef = useRef(fundos);
  fundosRef.current = fundos;
  // Sem satélite configurado, os dois lados do alternador seriam o mesmo mapa.
  const comAlternador = basemapToggle && Boolean(fundos.satelite);

  // ── Expõe fitToLayer / localizar para o pai ────────────────────────────────
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
      if (!geo) return; // sem `geolocalizar`, o controle não existe
      // `trigger()` é um ALTERNADOR: já seguindo (ou aguardando o fix), ele
      // DESLIGA o rastreio — o oposto do que o "Usar minha localização" do
      // compositor pede. Nesses estados, só reemitimos a última posição (o
      // chip volta na hora) e não tocamos no controle; do 2º plano/OFF, o
      // trigger() faz o certo (recentra/religa). Campos internos do maplibre,
      // versão pinada em 5.20.x; sem eles, cai no trigger() de sempre.
      const interno = geo as unknown as { _watchState?: string; _lastKnownPosition?: GeolocationPosition };
      if (interno._watchState === "ACTIVE_LOCK" || interno._watchState === "WAITING_ACTIVE") {
        const c = interno._lastKnownPosition?.coords;
        if (c) {
          aoLocalizarRef.current?.({
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

      // Auditoria (SEG-122): a cor da camada vem de publish_config.color (string
      // livre) e é interpolada dentro de `style="…"` que vai para Popup.setHTML.
      // Só aceita hex válido; qualquer outra coisa cai no padrão, fechando a
      // injeção de HTML/atributo pelo valor da cor.
      const COR_HEX_OK = /^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;
      const color = layerColor && COR_HEX_OK.test(layerColor) ? layerColor : "#FF6A00";
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
          // Timestamp (tem hora): trata string sem offset como UTC e converte
          // para o fuso local — mesmo helper do resto do app (fromBackend).
          // `new Date(s)` cru interpretava o UTC como local, deslocando +offset.
          // Data-so (sem hora): nao tem semantica de fuso — exibe como veio para
          // nao deslocar o dia (meia-noite UTC viraria o dia anterior em UTC-).
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

      // Detecta a propriedade de "nome" do feature (painel selecionado) por convenção
      const NAME_KEYS = ["nome", "name", "titulo", "title", "label", "rotulo", "descricao", "description"];
      const nameKey = entries.find(([k, v]) =>
        NAME_KEYS.includes(k.toLowerCase()) && v !== null && v !== undefined && v !== "" && typeof v !== "object"
      )?.[0];
      const nameVal = nameKey ? String(properties[nameKey]) : null;
      const safeName = nameVal ? escapeHtml(nameVal) : null;

      // Linhas: omitir a chave promovida ao header para evitar duplicação
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
  // O handler de clique é registrado UMA vez (efeito de montagem, deps []), então
  // captura o `buildPopupHtml` do PRIMEIRO render — com o `isDark`/`visibleFields`
  // daquele instante assados nas cores inline de cada célula. Trocar o tema
  // recriava o callback, mas o handler seguia chamando o velho: o popup abria
  // meio-atualizado (o container já vira pelo CSS, as células não). Lê-lo por ref
  // — mesmo idioma de `camadasRef`/`alvoDaVoltaRef` — faz o clique usar sempre o
  // callback corrente.
  const buildPopupHtmlRef = useRef(buildPopupHtml);
  buildPopupHtmlRef.current = buildPopupHtml;

  // ── Inicialização ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || initializedRef.current) return;
    initializedRef.current = true;

    const map = new maplibregl.Map({
      container: containerRef.current,
      // O raster de sempre; `basemapInicial` escolhe QUAL. O portal nasce em
      // "streets" e alterna; a Home nasce em "hybrid" e fica.
      style: _estiloRaster(conjuntoDoFundo(fundosRef.current, basemapInicial)),
      center: center ?? CENTRO_PADRAO,
      zoom: zoom ?? ZOOM_PADRAO,
      locale: { ...textos.controles },
      // `transformRequest`/`attributionControl` só existem para a Home; sem eles
      // o construtor fica idêntico ao de antes.
      ...(transformRequest ? { transformRequest } : {}),
      // NUNCA `customAttribution`. Todo basemap que usamos já declara a própria
      // atribuição na fonte (o crédito de MAPA_*_CREDITO). Passar um texto
      // nosso por cima não substituía a da fonte: o MapLibre CONCATENA os dois
      // com " | ", e a Home mostrava a mesma coisa duas vezes. Deixar a fonte
      // falar também trava sozinha quando o basemap troca.
      //
      // `compact` recolhe o que sobra a um "ⓘ" que abre no clique. É a forma que
      // o MapLibre oferece para a atribuição ocupar pouco — ela continua a um
      // clique, que é o que a ODbL do OSM e os termos dos provedores pedem. Some, não.
      ...(controlesDiscretos ? { attributionControl: { compact: true as const } } : {}),
    });

    // `style.load` dispara a cada estilo carregado: na montagem e sempre que um
    // `setStyle` recarrega o estilo inteiro. É aqui que marcamos o mapa como
    // apto a receber camadas e que a projeção globo é (re)aplicada.
    map.on("style.load", () => {
      // `true` da SEGUNDA carga em diante. Ela só existe se um `setStyle` caiu
      // em carga completa: a troca de basemap do portal pede `diff: true`, mas
      // o MapLibre recarrega tudo quando o diff não se aplica.
      const recarga = estiloProntoRef.current;
      estiloProntoRef.current = true;
      if (projection === "globe") map.setProjection({ type: "globe" });
      // A carga completa apaga sources e layers, e o efeito de `[layers]` NÃO
      // roda de novo — as camadas não mudaram. Sem esta chamada, ela apagaria
      // do mapa as camadas de dados. Na PRIMEIRA carga quem sincroniza é o
      // próprio efeito de `[layers]`, que espera por este mesmo evento
      // (`_quandoEstiloPronto`); chamar aqui também seria trabalho repetido.
      // `idsAnterioresRef` fica como está de propósito: ele só alimenta o
      // cálculo do que REMOVER, e `_syncLayers` recria o que falta olhando o
      // mapa (`if (!map.getSource(src))`), não a lista.
      if (recarga) sincronizarRef.current();
    });

    map.addControl(new maplibregl.NavigationControl(), controlsPosition);
    // Localizar (só a Home): entra logo abaixo do zoom/bússola, no mesmo canto.
    // `trackUserLocation` dá o modo SEGUIR (a câmera acompanha a pessoa e cai
    // para "segundo plano" quando ela arrasta o mapa); o ponto e o círculo de
    // precisão são do próprio controle. Localizar MANDA no globo: o giro pausa e
    // a volta à região não dispara enquanto seguimos — retoma quando ela desliga
    // o seguir (ou o boot do erro), se o hero ainda pedir giro.
    if (geolocalizar) {
      const geo = new maplibregl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
        showAccuracyCircle: true,
        fitBoundsOptions: { maxZoom: 16, duration: 1200 },
      });
      geo.on("trackuserlocationstart", () => {
        geolocalizandoRef.current = true;
        // Corta só o passo do giro/volta em voo — parar QUALQUER movimento
        // matava o enquadramento do próprio controle no reclique a partir do
        // 2º plano (o fitBounds dele roda ANTES deste evento).
        if (giroEmVooRef.current) map.stop();
      });
      geo.on("trackuserlocationend", () => {
        // Este evento também dispara ao cair para o 2º PLANO (a pessoa arrastou
        // o mapa), com o watch ainda vivo e o zoom lá em cima — retomar o giro
        // aí varria a tela a 0,5°/s sobre a casa da pessoa. Só libera quando o
        // controle foi mesmo a OFF. `_watchState` é interno do maplibre (versão
        // pinada em 5.20.x); se sumir numa atualização, o fallback é liberar
        // como antes.
        const estado = (geo as unknown as { _watchState?: string })._watchState;
        if (estado && estado !== "OFF") return;
        geolocalizandoRef.current = false;
      });
      // Cada posição resolvida (o modo seguir emite várias) sobe ao pai — é o
      // que a Home anexa ao turno. O evento carrega um GeolocationPosition.
      geo.on("geolocate", (e) => {
        const c = (e as unknown as GeolocationPosition).coords;
        if (!c) return;
        aoLocalizarRef.current?.({
          lat: c.latitude,
          lon: c.longitude,
          precisao_m: Number.isFinite(c.accuracy) ? c.accuracy : null,
        });
      });
      // PERMISSÃO NEGADA derruba o controle para OFF SEM `trackuserlocationend`
      // — sem este handler o giro do hero ficava suspenso para sempre. E é o
      // único jeito de o compositor dar retorno da falha (o botão do controle
      // fica escondido atrás do painel no telefone).
      geo.on("error", (e) => {
        const codigo = (e as unknown as GeolocationPositionError | undefined)?.code ?? 0;
        if (codigo === 1) geolocalizandoRef.current = false;
        aoErroDeLocalizacaoRef.current?.(codigo);
      });
      geoControlRef.current = geo;
      map.addControl(geo, controlsPosition);
    }
    map.addControl(new maplibregl.ScaleControl(), "bottom-right");
    mapRef.current = map;

    // Qualquer movimento que termina (inclusive um `stop()`) encerra o "nosso"
    // voo — o flag só religa quando o giro/volta dispararem o próximo easeTo.
    map.on("moveend", () => { giroEmVooRef.current = false; });

    map.on("mousemove", (e) => {
      const ids = _idsInterativos(map, camadasRef.current);
      if (!ids.length) return;
      const feats = map.queryRenderedFeatures(e.point, { layers: ids });
      map.getCanvas().style.cursor = feats.length ? "pointer" : "";
    });

    map.on("click", (e) => {
      const ids = _idsInterativos(map, camadasRef.current);
      if (!ids.length) return;
      const feats = map.queryRenderedFeatures(e.point, { layers: ids });
      if (!feats.length) {
        popupRef.current?.remove();
        return;
      }
      const f = feats[0];
      const lid = f.layer.id.replace(/^(fill|line|circle)-/, "");
      const meta = camadasRef.current.find((l) => l.id === lid);
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
      estiloProntoRef.current = false;
      idsAnterioresRef.current = [];
      basemapAplicadoRef.current = basemapInicial;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Giro lento (o hero da Home) ────────────────────────────────────────────
  // Declarado DEPOIS da inicialização: na montagem com `giroLento` já ligado, o
  // mapa precisa existir quando este efeito rodar. `center`/`zoom` entram por
  // ref, e não pelas dependências: o Globo os passa como literais, e um array
  // novo a cada render reiniciaria o giro (com um `stop()`) a cada render.
  const alvoDaVoltaRef = useRef({ center, zoom });
  alvoDaVoltaRef.current = { center, zoom };
  const girouRef = useRef(false);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const reduzMovimento = _prefereMenosMovimento();

    if (!giroLento) {
      // Só volta quem girou: no portal, que nunca gira, isto não faz nada.
      if (!girouRef.current) return;
      girouRef.current = false;
      // Seguindo a pessoa: NÃO voltar à região — isso a puxaria para longe no
      // instante em que a encontramos (decisão do dono).
      if (geolocalizandoRef.current) return;
      const { center: c, zoom: z } = alvoDaVoltaRef.current;
      const destino = { center: c ?? CENTRO_PADRAO, zoom: z ?? ZOOM_PADRAO };
      if (reduzMovimento) map.jumpTo(destino);
      else {
        giroEmVooRef.current = true; // localizar durante a volta pode cortá-la
        map.easeTo({ ...destino, duration: DURACAO_DA_VOLTA_MS, easing: _easeInOutCubic, essential: true });
      }
      return;
    }

    girouRef.current = true;
    // Sem movimento o globo fica parado — e a volta, acima, é um salto.
    if (reduzMovimento) return;

    let ultimoGesto = -Infinity;
    const gesto = () => { ultimoGesto = Date.now(); };
    const passo = () => {
      // Localizando/seguindo a pessoa: o giro fica suspenso.
      if (geolocalizandoRef.current) return;
      if (map.isMoving()) return;
      if (Date.now() - ultimoGesto < PAUSA_APOS_GESTO_MS) return;
      const atual = map.getCenter();
      giroEmVooRef.current = true; // é o passo que o início do seguir pode cortar
      map.easeTo({
        center: [atual.lng - VELOCIDADE_DO_GIRO_GRAUS_POR_S * (PASSO_DO_GIRO_MS / 1000), atual.lat],
        duration: PASSO_DO_GIRO_MS,
        easing: (n: number) => n,
        essential: true,
      });
    };
    for (const g of GESTOS) map.on(g, gesto);
    // Encadeia no fim de cada passo; o intervalo retoma depois da pausa de um gesto.
    map.on("moveend", passo);
    const retomada = setInterval(passo, INTERVALO_DE_RETOMADA_MS);
    passo();
    return () => {
      clearInterval(retomada);
      map.off("moveend", passo);
      for (const g of GESTOS) map.off(g, gesto);
      // Interrompe o passo em voo: a volta (o efeito seguinte) parte de onde o
      // globo está. Num desmonte o mapa já pode ter sido removido — daí o try.
      try { map.stop(); } catch { /* mapa removido */ }
    };
  }, [giroLento]);

  // ── Troca de basemap ───────────────────────────────────────────────────────
  // O basemap é UMA fonte raster dentro de um estilo que montamos à mão. Trocar
  // é remendar `sources.basemap.tiles` — barato, e as camadas de dados nem
  // piscam. (Se o diff não se aplicar e o MapLibre recarregar o estilo inteiro,
  // o `style.load` acima as recoloca.) A atribuição acompanha sozinha: o
  // controle do MapLibre a relê do estilo a cada `styledata`.
  useEffect(() => {
    const map = mapRef.current;
    // Cobre a montagem: o estado nasce em `basemapInicial` e o mapa já foi
    // construído assim. Sem o guarda, o primeiro render faria um `setStyle`
    // redundante.
    if (!map || basemapAplicadoRef.current === basemap) return;
    basemapAplicadoRef.current = basemap;
    const ts = conjuntoDoFundo(fundosRef.current, basemap);
    const style = map.getStyle();
    if (style?.sources?.basemap) {
      (style.sources.basemap as Record<string, unknown>).tiles = ts.tiles;
      (style.sources.basemap as Record<string, unknown>).attribution = ts.attribution;
      map.setStyle(style, { diff: true });
    }
  }, [basemap]);

  // ── Sincronizar layers ─────────────────────────────────────────────────────
  useEffect(() => {
    camadasRef.current = layers;
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
        idsAnterioresRef.current,
      );
      idsAnterioresRef.current = layers.map((l) => l.id);
      if (didFit) fittedRef.current = true;
    };
    // O `style.load` chama ESTA sincronização depois de um `setStyle`. Guardar
    // o closure atual é o que mantém as camadas da conversa no globo quando o
    // basemap troca — o efeito de `[layers]` não roda nessa hora.
    sincronizarRef.current = sync;
    // Esperar por `load`/`isStyleLoaded()` perdia sincronizações em silêncio:
    // `load` dispara UMA vez na vida do mapa (um `once` registrado depois nunca
    // roda) e `isStyleLoaded()` é falso enquanto houver tile em voo — no globo
    // vetorial, a regra. O que basta para criar camadas é o estilo ter
    // carregado, sinalizado uma vez por estilo em `style.load`.
    return _quandoEstiloPronto(map, estiloProntoRef.current, sync);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layers]);

  return (
    <div className="relative w-full h-full">
      <div id={`map-${mapId}`} ref={containerRef} className="w-full h-full" />

      {/* Alternador de basemap. Dois botões e não um interruptor: o rótulo do
          lado ATIVO tem de ficar visível — "Mapa"/"Satélite" dizem o que se está
          vendo, e um interruptor só diria para onde se vai. */}
      {comAlternador && (
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
 * Ids clicáveis derivados das camadas do componente. Antes vinham de
 * `map.getStyle()`, que serializa TODAS as fontes e camadas do estilo — com um
 * basemap vetorial (mais de cem camadas) isso acontecia a cada mousemove.
 * Aqui o custo é proporcional às nossas camadas, que são poucas.
 * Exportada para teste.
 */
export function _idsInterativos(map: maplibregl.Map, layers: MapLayer[]): string[] {
  const ids: string[] = [];
  for (const layer of layers) {
    if (!layer.visible) continue;
    for (const prefixo of ["fill-", "line-", "circle-"]) {
      const id = `${prefixo}${layer.id}`;
      // A camada pode não existir (tipo de geometria que não a usa) e
      // `queryRenderedFeatures` com id inexistente derruba a consulta inteira.
      if (map.getLayer(id)) ids.push(id);
    }
  }
  return ids;
}

/**
 * Roda `sync` agora, se o estilo já carregou, ou no próximo `style.load`.
 * Devolve a limpeza do listener. Exportada para teste.
 */
export function _quandoEstiloPronto(
  map: maplibregl.Map,
  estiloPronto: boolean,
  sync: () => void,
): (() => void) | undefined {
  if (estiloPronto) {
    sync();
    return undefined;
  }
  map.once("style.load", sync);
  return () => { map.off("style.load", sync); };
}

/**
 * Filtro por tipo de geometria do feature. Aceita também as variantes Multi*
 * (o GeoJSON as devolve; o MVT só as simples). Exportada para teste.
 */
export function _filtroGeom(...tipos: Array<"Point" | "LineString" | "Polygon">): maplibregl.FilterSpecification {
  const aceitos = tipos.flatMap((t) => [t, `Multi${t}`]);
  return ["in", ["geometry-type"], ["literal", aceitos]];
}

/**
 * Ids das camadas DESTE componente presentes no estilo (sufixo de `fill-`/
 * `line-`/`circle-` cuja fonte é `src-*`, mais fontes `src-*` órfãs). Caminho
 * de compatibilidade para quem chama `_syncLayers` sem a lista anterior.
 */
function _nossasCamadasDoEstilo(map: maplibregl.Map): string[] {
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

// O maplibre-gl 6 tipa o nome e o valor de cada propriedade de pintura. O tipo
// que os lista vem do style-spec, que não é dependência direta: daí lê-los da
// assinatura do `setPaintProperty`.
type PropriedadeDePintura = Parameters<maplibregl.Map["setPaintProperty"]>[1];
type ValorDePintura = Parameters<maplibregl.Map["setPaintProperty"]>[2];

/** Só escreve a propriedade quando ela de fato mudou (evita repintar o estilo). */
function _definirPaint(map: maplibregl.Map, id: string, prop: PropriedadeDePintura, valor: ValorDePintura): void {
  if (map.getPaintProperty(id, prop) !== valor) {
    map.setPaintProperty(id, prop, valor);
  }
}

function _definirVisibilidade(map: maplibregl.Map, id: string, visivel: boolean): void {
  const alvo = visivel ? "visible" : "none";
  // `visibility` ausente equivale a "visible" — não reescreve à toa.
  const atual = map.getLayoutProperty(id, "visibility") ?? "visible";
  if (atual !== alvo) map.setLayoutProperty(id, "visibility", alvo);
}

/** Retorna true se fitBounds foi chamado nesta invocação. Exportada para teste. */
export function _syncLayers(
  map: maplibregl.Map,
  layers: MapLayer[],
  alreadyFitted: boolean,
  mvtWorkflowHash?: string,
  tileLayerKeys?: Record<string, string>,
  tileLayerVersions?: Record<string, string>,
  tilesBaseUrl?: string,
  idsAnteriores?: string[],
): boolean {
  // ── Remove as camadas que sumiram da lista ─────────────────────────────────
  // A Home tira camada do globo (o portal tem lista estável, então nada some
  // lá). Só mexe no que ESTE componente criou — camadas cuja fonte é `src-*` —,
  // nunca nas do próprio basemap. Layers antes das fontes:
  // não dá para remover uma fonte ainda em uso.
  // Quem passa `idsAnteriores` (o componente, via ref) fecha o delta sem
  // `getStyle()`, que serializa todas as fontes e camadas do basemap.
  const desejadas = new Set(layers.map((l) => l.id));
  const removidas = idsAnteriores
    ? idsAnteriores.filter((id) => !desejadas.has(id))
    : _nossasCamadasDoEstilo(map).filter((id) => !desejadas.has(id));
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

    // MVT por camada (a Home) tem precedência sobre o par global do portal.
    const layerKey = tileLayerKeys?.[layer.id];
    const mvtInfo = layer.mvt ?? (mvtWorkflowHash && layerKey ? { workflowHash: mvtWorkflowHash, layerKey } : undefined);
    const useMvt = !!mvtInfo;

    if (!map.getSource(src)) {
      if (mvtInfo) {
        // Cache-buster: query string baseada na ultima publicacao da camada.
        // Sem isso, MapLibre/Cloudflare/browser servem tiles velhos apos uma
        // re-publicacao (max-age=3600 no backend) — usuario ve dados misturados.
        const version = tileLayerVersions?.[layer.id]
        const versionQs = version ? `?v=${encodeURIComponent(version)}` : ""
        // Padrão: tiles do portal. A Home passa `/terra/assistente/tiles`.
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

    // geomType null NÃO renderia nada, em silêncio. Inferimos do primeiro
    // feature (GeoJSON). Num MVT sem tipo declarado caímos em `semTipo`: aí
    // adicionamos as três camadas COM filtro por `geometry-type`. O filtro é
    // obrigatório: um layer `circle` desenha um círculo por VÉRTICE, inclusive
    // os de um polígono, e um layer `fill` triangula até LineString — sem ele
    // um talhão vira uma nuvem de bolinhas no portal público.
    const gt = layer.geomType || _sniffGeomType(layer.geojson);
    const semTipo = useMvt && !gt;
    const isPoly = gt.includes("Polygon");
    const isLine = gt.includes("LineString");
    const isPoint = gt.includes("Point");
    const sourceLayer = mvtInfo ? mvtInfo.layerKey : undefined;

    if (isPoly || semTipo) {
      if (!map.getLayer(fillId)) {
        map.addLayer({
          id: fillId, type: "fill", source: src, ...(sourceLayer ? { "source-layer": sourceLayer } : {}),
          ...(semTipo ? { filter: _filtroGeom("Polygon") } : {}),
          paint: { "fill-color": color, "fill-opacity": layer.opacity },
        });
      } else {
        _definirPaint(map, fillId, "fill-color", color);
        _definirPaint(map, fillId, "fill-opacity", layer.opacity);
      }
      _definirVisibilidade(map, fillId, layer.visible);
    }

    if (isPoly || isLine || semTipo) {
      if (!map.getLayer(lineId)) {
        map.addLayer({
          id: lineId, type: "line", source: src, ...(sourceLayer ? { "source-layer": sourceLayer } : {}),
          // Sem tipo declarado, a borda cobre polígono E linha: os dois têm contorno.
          ...(semTipo ? { filter: _filtroGeom("Polygon", "LineString") } : {}),
          paint: { "line-color": color, "line-width": isPoly ? 1.5 : 2.5, "line-opacity": 0.9 },
        });
      } else {
        _definirPaint(map, lineId, "line-color", color);
      }
      _definirVisibilidade(map, lineId, layer.visible);
    }

    if (isPoint || semTipo) {
      if (!map.getLayer(circleId)) {
        map.addLayer({
          id: circleId, type: "circle", source: src, ...(sourceLayer ? { "source-layer": sourceLayer } : {}),
          ...(semTipo ? { filter: _filtroGeom("Point") } : {}),
          paint: { "circle-color": color, "circle-radius": 6, "circle-opacity": layer.opacity, "circle-stroke-color": "#fff", "circle-stroke-width": 1.5 },
        });
      } else {
        _definirPaint(map, circleId, "circle-color", color);
        _definirPaint(map, circleId, "circle-opacity", layer.opacity);
      }
      _definirVisibilidade(map, circleId, layer.visible);
    }

    if (layer.visible && _estenderBounds(bounds, layer)) hasBounds = true;
  });

  // fitBounds apenas na primeira carga
  if (hasBounds && !alreadyFitted) {
    map.fitBounds(bounds, { padding: 50, maxZoom: 15 });
    return true;
  }
  return false;
}

/** Tipo de geometria do primeiro feature — "" se não houver (ex.: MVT). */
export function _sniffGeomType(fc: GeoJSON.FeatureCollection): string {
  const g = fc?.features?.find((f) => f.geometry)?.geometry;
  return g?.type ?? "";
}

/** Estende `bounds` pela bbox da camada, ou pelas coordenadas dos features.
    Retorna true se estendeu. */
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
