"use client"
import { useState, type Ref } from "react"
import MapLibreMap, { type MapLibreMapHandle, type MapLayer, type PosicaoDoUsuario } from "../share/MapLibreMap"
import { centroDaRegiao, fusoDoNavegador } from "./mapa/regiao"
import { transformarRequisicao } from "./mapa/requisicao"
import { useTextos } from "./i18n"

export interface GloboProps {
  layers?: MapLayer[];
  /** Do useCamadas, para enquadrar/voar às camadas que a conversa põe no globo. */
  mapaRef?: Ref<MapLibreMapHandle>;
  /**
   * Gira o globo devagar (o hero da Home). Ao desligar, o mapa volta à REGIÃO
   * de quem abriu a página (o mesmo centro do início) — o primeiro token da
   * resposta traz o globo de volta.
   */
  girando?: boolean;
  /** O país da conexão (`CF-IPCountry`), a reserva quando o navegador esconde o fuso. */
  pais?: string | null;
  /** Sobe a localização resolvida (o `geolocate` do controle) para a Home anexar ao turno. */
  aoLocalizar?: (pos: PosicaoDoUsuario) => void;
  /** Sobe a falha de localização (código do navegador; 1 = permissão negada) — vira toast. */
  aoErroDeLocalizacao?: (codigo: number) => void;
}

/**
 * O globo 3D da Home: o MapLibreMap em projeção globe sobre a imagem HÍBRIDA
 * (satélite + vias e rótulos) que a instalação configurou (MAPA_HIBRIDO_URL; sem
 * ela, o satélite e, sem este, as ruas — web/lib/fundos-do-mapa.ts). É o único
 * basemap da Home — saiu o Dark Matter da CARTO e, com ele, a chave, o estilo
 * vetorial e o alternador (com um basemap só, não há para o que alternar). Não
 * há estado "sem basemap": a página sempre tem mapa.
 *
 * Raster na esfera deforma um pouco ao mudar de zoom (o MapLibre recomenda o
 * vetorial para o globo); com a imagem como basemap único isso é permanente e
 * aceito. A atribuição (MAPA_*_CREDITO) vem da fonte, recolhida no "ⓘ" da
 * chrome discreta — nunca escrita por nós.
 *
 * As camadas (saídas das execuções) entram por `layers`; o `mapaRef` deixa o
 * useCamadas enquadrar a camada nova.
 */
export default function Globo({ layers = [], mapaRef, girando = false, pais = null, aoLocalizar, aoErroDeLocalizacao }: GloboProps) {
  // A região é lida UMA vez, na montagem: o MapLibreMap constrói o mapa com
  // este centro e guarda-o como o destino da volta do hero — um array novo a
  // cada render não muda nada ali, mas o estado deixa isso explícito. No
  // servidor o fuso é o dele (e o valor não entra no HTML); vale o do cliente.
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
