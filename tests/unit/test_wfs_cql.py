# tests/unit/test_wfs_cql.py
"""Nó WFS: o filtro CQL (`CQL_FILTER`, ECQL do GeoServer) aplicado no servidor.

O cliente é o do owslib DE VERDADE (`WebFeatureService_2_0_0` montado de um
GetCapabilities enlatado), então as URLs saem do montador real
(`getGETGetFeatureRequest`); só o `openURL` é dublado, por um servidor que
guarda cada URL e responde por tipo de pedido.

O que se protege:
- o filtro vai ao SERVIDOR em toda página, com o SORTBY e o srsName de sempre;
- com bbox, o recorte entra no próprio CQL e a KVP `bbox` não vai junto (o
  GeoServer recusa as duas); a geometria sai do DescribeFeatureType, inclusive
  de camada de linhas (MultiCurve, que a lista do owslib não conhece);
- servidor que ignora o parâmetro é recusado com erro; sem conseguir
  verificar (rede, 5xx), o nó NÃO segue com a camada inteira;
- camada vazia não "verifica" o servidor;
- a recusa do servidor por requisição errada não é retentada; a falha
  transitória segue retentada; as mensagens chegam legíveis.
"""
from urllib.parse import parse_qsl, urlsplit

import pytest
import requests
from owslib.feature.wfs200 import ServiceException as ServiceExceptionWfs200
from owslib.feature.wfs200 import WebFeatureService_2_0_0
from owslib.util import ServiceException

import flow.nodes.datasource.wfs as wfs

URL = "http://x/ows"

_CAPS = b"""<?xml version="1.0" encoding="UTF-8"?>
<wfs:WFS_Capabilities version="2.0.0" xmlns:wfs="http://www.opengis.net/wfs/2.0"
    xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:xlink="http://www.w3.org/1999/xlink">
  <ows:ServiceIdentification><ows:Title>GeoServer Web Feature Service</ows:Title>
    <ows:ServiceType>WFS</ows:ServiceType><ows:ServiceTypeVersion>2.0.0</ows:ServiceTypeVersion>
  </ows:ServiceIdentification>
  <ows:OperationsMetadata>
    <ows:Operation name="GetFeature"><ows:DCP><ows:HTTP>
      <ows:Get xlink:href="http://x/geoserver/ows"/></ows:HTTP></ows:DCP></ows:Operation>
  </ows:OperationsMetadata>
  <wfs:FeatureTypeList>
    <wfs:FeatureType><wfs:Name>ns:rodovias</wfs:Name><wfs:Title>Rodovias</wfs:Title>
      <wfs:DefaultCRS>urn:ogc:def:crs:EPSG::4674</wfs:DefaultCRS></wfs:FeatureType>
    <wfs:FeatureType><wfs:Name>ns:vazia</wfs:Name><wfs:Title>Vazia</wfs:Title>
      <wfs:DefaultCRS>urn:ogc:def:crs:EPSG::4674</wfs:DefaultCRS></wfs:FeatureType>
    <wfs:FeatureType><wfs:Name>ns:tabela</wfs:Name><wfs:Title>Sem geometria</wfs:Title>
      <wfs:DefaultCRS>urn:ogc:def:crs:EPSG::4674</wfs:DefaultCRS></wfs:FeatureType>
  </wfs:FeatureTypeList>
</wfs:WFS_Capabilities>"""

# O DescribeFeatureType do GeoServer para uma camada de LINHAS: MultiCurve.
_XSD_LINHAS = b"""<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:ns="http://ns"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema" targetNamespace="http://ns">
  <xsd:complexType name="rodoviasType"><xsd:complexContent>
    <xsd:extension base="gml:AbstractFeatureType"><xsd:sequence>
      <xsd:element name="sigla_uf" nillable="true" type="xsd:string"/>
      <xsd:element name="geom" nillable="true" type="gml:MultiCurvePropertyType"/>
    </xsd:sequence></xsd:extension></xsd:complexContent></xsd:complexType>
  <xsd:element name="rodovias" substitutionGroup="gml:AbstractFeature" type="ns:rodoviasType"/>
</xsd:schema>"""

_XSD_SEM_GEOMETRIA = _XSD_LINHAS.replace(
    b'<xsd:element name="geom" nillable="true" type="gml:MultiCurvePropertyType"/>', b""
)


def _feicoes(n: int) -> bytes:
    itens = b",".join(
        b'{"type":"Feature","geometry":{"type":"Point","coordinates":[0,0]},"properties":{"id":%d}}' % i
        for i in range(n)
    )
    return b'{"type":"FeatureCollection","features":[' + itens + b"]}"


def _hits(n) -> bytes:
    return b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" numberMatched="%s" numberReturned="0"/>' % str(n).encode()


class _Resposta:
    def __init__(self, corpo: bytes):
        self._corpo = corpo

    def read(self):
        return self._corpo

    def info(self):
        return {}


class _Servidor:
    """O `openURL` dublado. Responde por tipo de pedido e guarda cada URL.

    - `hits[com_filtro]`: o numberMatched de um `resultType=hits` com/sem CQL;
    - `paginas`: as páginas do GetFeature, em ordem (a última se repete);
    - `esquemas`: o DescribeFeatureType por camada;
    - `falhas`: exceções a levantar, na ordem, antes de responder (uma por pedido).
    """

    def __init__(self):
        self.urls: list[str] = []
        self.hits = {True: 0, False: 5}
        self.amostra = {True: 0, False: 1}  # feições na amostra GeoJSON, com/sem CQL
        self.paginas: list[bytes | Exception] = [_feicoes(1)]
        self.esquemas = {"ns:rodovias": _XSD_LINHAS, "ns:tabela": _XSD_SEM_GEOMETRIA}
        self.falhas: list[Exception] = []

    def __call__(self, url, data=None, method="Get", **kw):
        self.urls.append(url)
        if self.falhas:
            raise self.falhas.pop(0)
        p = self.params(len(self.urls) - 1)
        if p.get("request") == "DescribeFeatureType":
            return _Resposta(self.esquemas[p["typeNames"]])
        com_filtro = "CQL_FILTER" in p
        if p.get("resultType") == "hits":
            return _Resposta(_hits(self.hits[com_filtro]))
        if p.get("count") == "1" and p.get("startindex") is None and self.sonda_por_amostra:
            if self.amostra_em_gml:
                return _Resposta(b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" numberMatched="unknown"><wfs:member/></wfs:FeatureCollection>')
            return _Resposta(_feicoes(self.amostra[com_filtro]))
        resposta = self.paginas.pop(0) if len(self.paginas) > 1 else self.paginas[0]
        if isinstance(resposta, Exception):
            raise resposta
        return _Resposta(resposta)

    sonda_por_amostra = False
    amostra_em_gml = False  # o servidor ignora o outputFormat e responde GML

    def params(self, i: int) -> dict:
        return dict(parse_qsl(urlsplit(self.urls[i]).query))

    @property
    def pedidos(self) -> list[dict]:
        return [self.params(i) for i in range(len(self.urls))]

    @property
    def paginas_pedidas(self) -> list[dict]:
        return [
            p for p in self.pedidos
            if p.get("request") == "GetFeature" and p.get("resultType") != "hits"
            and not (self.sonda_por_amostra and p.get("count") == "1")
        ]

    @property
    def sondas(self) -> list[dict]:
        return [p for p in self.pedidos if p.get("resultType") == "hits"]


@pytest.fixture
def servidor(monkeypatch):
    import owslib.feature.wfs200 as wfs200
    import owslib.util
    import owslib.wfs as ows

    monkeypatch.setattr(wfs, "_caps_cache", {})
    monkeypatch.setattr(wfs, "_cql_verificado", {})
    monkeypatch.setattr(wfs, "_CAPS_TTL_S", 3600)
    monkeypatch.setattr(
        ows, "WebFeatureService",
        lambda url, version="2.0.0", timeout=30, **k: WebFeatureService_2_0_0(url, version, _CAPS, timeout=timeout),
    )
    falso = _Servidor()
    monkeypatch.setattr(owslib.util, "openURL", falso)
    monkeypatch.setattr(wfs200, "openURL", falso)
    monkeypatch.setattr("time.sleep", lambda s: None)
    return falso


# ── As peças puras ───────────────────────────────────────────────────────────────

def test_parse_cql_tira_as_pontas_e_vazio_vira_none():
    assert wfs._parse_cql("  sigla_uf = 'MT' ") == "sigla_uf = 'MT'"
    for vazio in ("", "   ", None):
        assert wfs._parse_cql(vazio) is None


def test_cql_com_bbox_recorta_protege_o_filtro_e_cita_a_geometria():
    cql = wfs._cql_com_bbox("a = 1 OR b = 2", (-64.01, -9.01, -63.82, -8.83), "geom", "EPSG:4674")
    # O OR de quem escreveu não escapa do recorte; a geometria vai entre aspas
    # (há camadas cuja geometria se chama `point`, palavra do ECQL).
    assert cql == "BBOX(\"geom\", -64.01, -9.01, -63.82, -8.83, 'EPSG:4674') AND (a = 1 OR b = 2)"
    assert wfs._cql_com_bbox("x", (0, 0, 1, 1), "point", None).startswith('BBOX("point", 0, 0, 1, 1) AND')


def test_cql_com_bbox_so_passa_crs_epsg_e_numero_sem_expoente():
    cql = wfs._cql_com_bbox("x > 0", (0.0000001, -0.0, 10, 20), "ms:msGeometry", "OGC:CRS84")
    assert cql == 'BBOX("ms:msGeometry", 0.0000001, 0, 10, 20) AND (x > 0)'


def test_geometria_do_xsd_reconhece_multicurve_e_ausencia():
    from owslib.etree import etree
    assert wfs._geometria_do_xsd(etree.fromstring(_XSD_LINHAS)) == "geom"
    assert wfs._geometria_do_xsd(etree.fromstring(_XSD_SEM_GEOMETRIA)) is None


def _xsd(sequencia: str, *, nome_da_camada: str = "camada", extra_ns: str = "") -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:ns="http://ns" {extra_ns}
    xmlns:xsd="http://www.w3.org/2001/XMLSchema" targetNamespace="http://ns">
  <xsd:element name="{nome_da_camada}" substitutionGroup="gml:AbstractFeature" type="ns:{nome_da_camada}Type"/>
  <xsd:complexType name="{nome_da_camada}Type"><xsd:complexContent>
    <xsd:extension base="gml:AbstractFeatureType"><xsd:sequence>{sequencia}</xsd:sequence></xsd:extension>
  </xsd:complexContent></xsd:complexType>
</xsd:schema>""".encode()


@pytest.mark.parametrize("sequencia, extra_ns, camada, esperado", [
    # Esquema de aplicação (INSPIRE): a associação e o identificador vêm antes da geometria.
    ('<xsd:element name="relatedTo" type="gml:FeaturePropertyType"/>'
     '<xsd:element name="inspireId" type="base:IdentifierPropertyType"/>'
     '<xsd:element name="validTime" type="gml:TimePeriodPropertyType"/>'
     '<xsd:element name="geometry" type="gml:GeometryPropertyType"/>',
     'xmlns:base="http://inspire.ec.europa.eu/schemas/base/3.3"', "camada", "geometry"),
    # Camada sem geometria cujo NOME termina em Property: o elemento de topo não é atributo.
    ('<xsd:element name="valor" type="xsd:string"/>', "", "landProperty", None),
    # MapServer: o elemento de topo antes do complexType, e msGeometry.
    ('<xsd:element name="msGeometry" type="gml:GeometryPropertyType"/>', "", "ownedProperty", "msGeometry"),
    # Um PointPropertyType do próprio esquema não é GML.
    ('<xsd:element name="ponto" type="ns:PointPropertyType"/><xsd:element name="geom" type="gml:PointPropertyType"/>',
     "", "camada", "geom"),
    # Duas geometrias: a primeira.
    ('<xsd:element name="centroid" type="gml:PointPropertyType"/><xsd:element name="geom" type="gml:MultiSurfacePropertyType"/>',
     "", "camada", "centroid"),
    # 3D e compostos também são geometria.
    ('<xsd:element name="geom" type="gml:SolidPropertyType"/>', "", "camada", "geom"),
    ('<xsd:element name="geom" type="gml:GeometricPrimitivePropertyType"/>', "", "camada", "geom"),
])
def test_geometria_do_xsd_ignora_o_que_nao_e_geometria_gml(sequencia, extra_ns, camada, esperado):
    from owslib.etree import etree
    assert wfs._geometria_do_xsd(etree.fromstring(_xsd(sequencia, nome_da_camada=camada, extra_ns=extra_ns))) == esperado


def test_erro_do_servidor_decodifica_e_classifica():
    # A forma REAL do GeoServer para um erro de sintaxe do CQL: o parser levanta
    # a ServiceException sem código, e o handler entrega `NoApplicableCode`
    # (HTTP 400), sem locator. Pelo código sozinho seria retentável.
    invalido = (
        '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception '
        'exceptionCode="NoApplicableCode"><ows:ExceptionText>'
        "Could not parse CQL filter list. Encountered &quot;=&quot; at line 1</ows:ExceptionText>"
        "</ows:Exception></ows:ExceptionReport>"
    )
    erro = wfs._erro_do_servidor(invalido, "ns:rodovias", com_cql=True)
    assert isinstance(erro, ValueError)
    assert 'Encountered "=" at line 1' in str(erro)  # entidade decodificada
    assert "Confira o filtro CQL" in str(erro)
    # Um código de requisição errada decide sozinho, seja qual for o texto.
    assert isinstance(wfs._erro_do_servidor(
        invalido.replace('exceptionCode="NoApplicableCode"', 'exceptionCode="InvalidParameterValue" locator="cql_filter"'),
        "ns:rodovias", com_cql=True,
    ), ValueError)

    transitorio = invalido.replace(
        "Could not parse CQL filter list. Encountered &quot;=&quot; at line 1",
        "pool error Timeout waiting for idle object",
    )
    assert isinstance(wfs._erro_do_servidor(transitorio, "ns:rodovias", com_cql=True), RuntimeError)
    # O GeoTools falando de um banco que caiu no meio do filtro: retentável.
    assert isinstance(wfs._erro_do_servidor(
        invalido.replace("Could not parse CQL filter list. Encountered &quot;=&quot; at line 1", "Error occured filtering features"),
        "ns:rodovias", com_cql=True,
    ), RuntimeError)
    # Sem filtro, a mensagem que fala de filtro não muda a classificação.
    assert isinstance(wfs._erro_do_servidor("Illegal filter", "ns:rodovias", com_cql=False), RuntimeError)


def test_com_parametros_poe_a_chave_na_query_e_nunca_no_fragmento():
    # Colada no fim de `…/ows#x` a chave cairia no fragmento, e o pedido
    # seguido depois de um redirecionamento sairia anônimo.
    assert wfs._com_parametros("http://x/ows", {"authkey": "K 1"}) == "http://x/ows?authkey=K%201"  # pragma: allowlist secret
    assert wfs._com_parametros("http://x/ows?a=1", {"authkey": "K"}) == "http://x/ows?a=1&authkey=K"
    assert wfs._com_parametros("http://x/ows#f", {"authkey": "K"}) == "http://x/ows?authkey=K#f"
    assert wfs._com_parametros("http://x/ows?a=1#f", {"authkey": "K"}) == "http://x/ows?a=1&authkey=K#f"
    assert wfs._com_parametros("http://x/ows", {}) == "http://x/ows"


def test_o_exception_code_decide_antes_da_palavra_filter():
    # O GeoTools escreve "Error occured filtering features" quando o PostGIS
    # cai: NoApplicableCode, transitório — a palavra "filter" não o torna um
    # erro do filtro CQL, e a execução segue retentada.
    banco_caiu = (
        '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception '
        'exceptionCode="NoApplicableCode"><ows:ExceptionText>java.io.IOException: Error occured '
        "filtering features / Connection refused</ows:ExceptionText></ows:Exception></ows:ExceptionReport>"
    )
    erro = wfs._erro_do_servidor(banco_caiu, "ns:rodovias", com_cql=True)
    assert isinstance(erro, RuntimeError) and "Confira o filtro" not in str(erro)
    # Sem código (o owslib só entrega o ExceptionText): a frase do parser decide,
    # e não a palavra solta.
    assert isinstance(wfs._erro_do_servidor("Illegal filter", "ns:rodovias", com_cql=True), ValueError)
    assert isinstance(wfs._erro_do_servidor("Unable to parse CQL", "ns:rodovias", com_cql=True), ValueError)
    assert isinstance(wfs._erro_do_servidor("Error occured filtering features", "ns:rodovias", com_cql=True), RuntimeError)


def test_a_dica_do_cql_so_entra_quando_o_locator_aponta_o_filtro():
    def relatorio(locator, texto):
        loc = f' locator="{locator}"' if locator else ""
        return (
            f'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception '
            f'exceptionCode="InvalidParameterValue"{loc}><ows:ExceptionText>{texto}</ows:ExceptionText>'
            f"</ows:Exception></ows:ExceptionReport>"
        )
    # O servidor não serve GeoJSON: a dica é essa, não "confira o filtro".
    geojson = wfs._erro_do_servidor(relatorio("outputFormat", "Invalid outputFormat value: application/json"), "ns:x", com_cql=True)
    assert isinstance(geojson, ValueError)
    assert "não serve GeoJSON" in str(geojson) and "Confira o filtro" not in str(geojson)
    # Outro parâmetro apontado: não retenta, mas não culpa o filtro.
    srs = wfs._erro_do_servidor(relatorio("srsName", "Unknown srs EPSG:99"), "ns:x", com_cql=True)
    assert isinstance(srs, ValueError) and "Confira o filtro" not in str(srs)
    # Sem locator, com filtro: o filtro é o suspeito de sempre.
    sem = wfs._erro_do_servidor(relatorio(None, "Illegal property name: foo"), "ns:x", com_cql=True)
    assert "Confira o filtro" in str(sem)


def test_o_400_do_tomcat_por_url_longa_nao_e_retentado(servidor):
    # A linha do pedido passou do limite do servidor web: HTML, sem exceptionCode.
    pagina = ("<html><head><title>HTTP Status 400 – Bad Request</title></head><body>"
              "<h1>HTTP Status 400 – Bad Request</h1><p>Request header is too large</p></body></html>")
    servidor.paginas = [ServiceException(pagina)]
    with pytest.raises(ValueError, match="longo demais") as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, "a = 1")
    assert len(servidor.paginas_pedidas) == 1  # sem retry
    assert str(wfs._MAX_URL_COM_CQL) in str(ei.value)


def test_pagina_html_vira_resumo_sem_tags():
    msg = wfs._parse_wfs_error("<!DOCTYPE html><html><body><h1>Acesso negado</h1><p>WAF &amp; cia</p></body></html>")
    assert msg == "o servidor respondeu uma página HTML em vez do WFS: Acesso negado WAF & cia"


# ── Sem filtro, nada muda ────────────────────────────────────────────────────────

def test_sem_filtro_o_caminho_e_o_getfeature_de_sempre(servidor):
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, bbox=(-64.0, -9.0, -63.0, -8.0))
    assert servidor.sondas == []
    (pagina,) = servidor.paginas_pedidas
    assert "CQL_FILTER" not in pagina
    # A KVP bbox do owslib: eixos trocados para a URN lat/lon da camada.
    assert pagina["bbox"] == "-9.0,-64.0,-8.0,-63.0,urn:ogc:def:crs:EPSG::4674"


# ── Com filtro ───────────────────────────────────────────────────────────────────

def test_o_filtro_vai_ao_servidor_com_sortby_e_srsname(servidor):
    gdf = wfs._fetch_wfs_features(
        URL, "ns:rodovias", 10, srs_name="EPSG:4326", sort_by=["gid"], cql_filter="sigla_uf = 'MT'",
    )
    assert len(gdf) == 1

    (exclude,) = servidor.sondas  # só o EXCLUDE: a página com feição é a prova que falta
    assert exclude["CQL_FILTER"] == "EXCLUDE" and exclude["count"] == "1"
    assert URL in wfs._cql_verificado  # a camada tem feição: a verificação vale

    (pagina,) = servidor.paginas_pedidas
    assert pagina["CQL_FILTER"] == "sigla_uf = 'MT'"
    assert pagina["sortby"] == "gid" and pagina["srsname"] == "EPSG:4326"
    assert pagina["typenames"] == "ns:rodovias" and pagina["outputFormat"] == "application/json"
    assert "bbox" not in pagina
    # Espaço vira %20 (e não +) na URL.
    assert "sigla_uf%20%3D%20%27MT%27" in servidor.urls[-1]


def test_com_bbox_o_recorte_entra_no_cql_de_uma_camada_de_linhas(servidor):
    wfs._fetch_wfs_features(
        URL, "ns:rodovias", 10, bbox=(-64.01, -9.01, -63.82, -8.83), cql_filter="sigla_uf = 'MT'",
    )
    (pagina,) = servidor.paginas_pedidas
    assert pagina["CQL_FILTER"] == (
        "BBOX(\"geom\", -64.01, -9.01, -63.82, -8.83, 'EPSG:4674') AND (sigla_uf = 'MT')"
    )
    # Com o montador REAL do owslib: a KVP bbox não vai junto (o GeoServer recusa as duas).
    assert "bbox" not in pagina
    assert any(p.get("request") == "DescribeFeatureType" and p["typeNames"] == "ns:rodovias" for p in servidor.pedidos)


def test_com_bbox_e_camada_sem_geometria_o_erro_diz_o_que_fazer(servidor):
    with pytest.raises(ValueError, match=r"BBOX\(<geometria>"):
        wfs._fetch_wfs_features(URL, "ns:tabela", 10, bbox=(1, 2, 3, 4), cql_filter="a = 1")
    assert servidor.paginas_pedidas == []


def test_describe_feature_type_fora_do_ar_e_retentado_e_nao_vira_erro_de_configuracao(servidor):
    wfs._cql_verificado[URL] = float("inf")  # já verificado: só o DescribeFeatureType pede
    servidor.falhas = [requests.HTTPError("503 Server Error: Service Unavailable")]
    gdf = wfs._fetch_with_retry(URL, "ns:rodovias", 10, (1, 2, 3, 4), None, None, 5, 2, 0.0, "a = 1")
    assert len(gdf) == 1  # a 2ª tentativa passou
    describes = [p for p in servidor.pedidos if p.get("request") == "DescribeFeatureType"]
    assert len(describes) == 2


def test_o_filtro_vai_em_todas_as_paginas(servidor, monkeypatch):
    monkeypatch.setattr(wfs, "_TAMANHO_DA_PAGINA", 2)
    servidor.paginas = [_feicoes(2), _feicoes(2), _feicoes(1)]
    gdf = wfs._fetch_wfs_features(URL, "ns:rodovias", 5, sort_by=["gid"], cql_filter="id >= 0")

    assert len(gdf) == 5
    paginas = servidor.paginas_pedidas
    assert [p.get("startindex") for p in paginas] == [None, "2", "4"]
    assert [p["count"] for p in paginas] == ["2", "2", "1"]
    # O filtro (e a ordenação) vão em TODA página: é o servidor que pagina o conjunto filtrado.
    assert all(p["CQL_FILTER"] == "id >= 0" and p["sortby"] == "gid" for p in paginas)


# ── A sondagem ───────────────────────────────────────────────────────────────────

def test_servidor_que_ignora_o_filtro_e_recusado_antes_da_primeira_pagina(servidor):
    servidor.hits[True] = 5  # EXCLUDE casou tudo: o CQL_FILTER foi ignorado
    with pytest.raises(ValueError, match="não aplica o filtro CQL"):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="sigla_uf = 'MT'")
    assert servidor.paginas_pedidas == []


def test_contagem_desconhecida_decide_pela_amostra(servidor):
    servidor.hits = {True: "unknown", False: "unknown"}
    servidor.sonda_por_amostra = True
    servidor.amostra = {True: 1, False: 1}  # EXCLUDE devolveu uma feição: ignorado
    with pytest.raises(ValueError, match="não aplica o filtro CQL"):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    assert servidor.paginas_pedidas == []

    servidor.urls.clear()
    servidor.amostra = {True: 0, False: 1}  # EXCLUDE vazio e a camada tem feição: aplica
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    assert len(servidor.paginas_pedidas) == 1 and URL in wfs._cql_verificado


def test_servidor_que_nao_diz_a_contagem_nem_fala_geojson_e_recusado(servidor):
    # Ignora o CQL_FILTER, não informa numberMatched e responde GML ao pedido de
    # GeoJSON: antes seguia com um aviso no log, e o GDAL lia a camada inteira.
    servidor.hits = {True: "unknown", False: "unknown"}
    servidor.sonda_por_amostra = True
    servidor.amostra_em_gml = True
    with pytest.raises(ValueError, match="Não foi possível verificar"):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    assert servidor.paginas_pedidas == [] and wfs._cql_verificado == {}


def test_amostra_recusada_por_outputformat_diz_que_o_servidor_nao_serve_geojson(servidor, monkeypatch):
    servidor.hits = {True: "unknown", False: "unknown"}
    servidor.sonda_por_amostra = True
    recusa = (
        '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception '
        'exceptionCode="InvalidParameterValue" locator="outputFormat"><ows:ExceptionText>'
        "Invalid outputFormat value: application/json</ows:ExceptionText></ows:Exception></ows:ExceptionReport>"
    )
    servidor.amostra_em_gml = True
    original = servidor.__call__

    def _com_recusa(url, data=None, method="Get", **kw):
        resposta = original(url, data, method, **kw)
        p = servidor.params(len(servidor.urls) - 1)
        return _Resposta(recusa.encode()) if p.get("outputFormat") == "application/json" and p.get("count") == "1" else resposta

    import owslib.util
    import owslib.feature.wfs200 as wfs200
    monkeypatch.setattr(owslib.util, "openURL", _com_recusa)
    monkeypatch.setattr(wfs200, "openURL", _com_recusa)
    with pytest.raises(ValueError) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, "a = 1")
    assert "não serve GeoJSON" in str(ei.value) and "Confira o filtro" not in str(ei.value)
    assert servidor.paginas_pedidas == []  # e sem retry


def test_a_contagem_da_camada_inteira_nao_e_mais_pedida(servidor, monkeypatch):
    # Um count(*) numa tabela de milhões de linhas estourava o timeout e
    # derrubava a execução cujo filtro já estava provado. A prova que falta ao
    # EXCLUDE (a camada tem feição) vem da própria primeira página.
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    assert [s.get("CQL_FILTER") for s in servidor.sondas] == ["EXCLUDE"]
    assert URL in wfs._cql_verificado

    # Com o TTL desligado a sondagem se repete a cada execução — e só ela.
    monkeypatch.setattr(wfs, "_CAPS_TTL_S", 0)
    monkeypatch.setattr(wfs, "_cql_verificado", {})
    servidor.urls.clear()
    for _ in range(2):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    assert [s.get("CQL_FILTER") for s in servidor.sondas] == ["EXCLUDE", "EXCLUDE"]
    assert wfs._cql_verificado == {}


def test_sem_conseguir_perguntar_o_no_nao_segue_com_a_camada_inteira(servidor):
    servidor.hits[True] = 5  # o servidor ignora o CQL...
    servidor.falhas = [requests.ConnectionError("caiu")]  # ...e a 1ª sondagem nem chega
    with pytest.raises(ValueError, match="não aplica o filtro CQL"):
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, "a = 1")
    assert servidor.paginas_pedidas == []  # a falha foi retentada, e a sondagem refeita recusou


def test_camada_vazia_nao_verifica_o_servidor(servidor):
    servidor.hits = {True: 0, False: 0}
    servidor.paginas = [_feicoes(0)]  # EXCLUDE zero E a camada vazia: nada prova
    assert wfs._fetch_wfs_features(URL, "ns:vazia", 10, cql_filter="a = 1").empty
    assert wfs._cql_verificado == {}
    servidor.paginas = [_feicoes(1)]

    # Outra camada do mesmo servidor sonda de novo — e o servidor que ignora é pego.
    servidor.urls.clear()
    servidor.hits = {True: 5, False: 5}
    with pytest.raises(ValueError, match="não aplica o filtro CQL"):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")


def test_a_verificacao_vale_pelo_ttl_por_servidor(servidor):
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    wfs._fetch_wfs_features(URL, "ns:vazia", 10, cql_filter="a = 2")
    assert len([s for s in servidor.sondas if s.get("CQL_FILTER") == "EXCLUDE"]) == 1


def test_o_cache_da_verificacao_tem_teto(servidor, monkeypatch):
    monkeypatch.setattr(wfs, "_CQL_VERIFICADO_MAX", 2)
    for host in ("a", "b", "c"):
        wfs._fetch_wfs_features(f"http://{host}/ows", "ns:rodovias", 10, cql_filter="a = 1")
    assert len(wfs._cql_verificado) == 2 and "http://a/ows" not in wfs._cql_verificado


# ── Recusa do servidor ───────────────────────────────────────────────────────────

# A forma real do GeoServer (ver `test_erro_do_servidor_decodifica_e_classifica`).
_CQL_INVALIDO = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1" version="2.0.0">'
    '<ows:Exception exceptionCode="NoApplicableCode">'
    "<ows:ExceptionText>Could not parse CQL filter list. Encountered &quot;=&quot;</ows:ExceptionText>"
    "</ows:Exception></ows:ExceptionReport>"
)


def test_filtro_invalido_nao_e_retentado_e_chega_legivel(servidor):
    servidor.paginas = [ServiceException(_CQL_INVALIDO)]
    with pytest.raises(ValueError) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, "a == 1")
    msg = str(ei.value)
    assert msg.startswith("O servidor WFS recusou a consulta:")
    assert 'Could not parse CQL filter list. Encountered "="' in msg
    assert "<ows:" not in msg and "&quot;" not in msg
    assert len(servidor.paginas_pedidas) == 1  # sem retry


def test_falha_transitoria_do_servidor_segue_retentada(servidor):
    transitoria = _CQL_INVALIDO.replace(
        "Could not parse CQL filter list. Encountered &quot;=&quot;", "pool error Timeout waiting for idle object",
    )
    servidor.paginas = [ServiceException(transitoria), _feicoes(1)]
    gdf = wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, "a = 1")
    assert len(gdf) == 1 and len(servidor.paginas_pedidas) == 2


def test_a_excecao_do_wfs200_tambem_e_a_voz_do_servidor(servidor):
    servidor.paginas = [ServiceExceptionWfs200("Cannot do natural order without a primary key")] * 3
    with pytest.raises(RuntimeError) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0)
    # Retentada (NoApplicableCode implícito), e a tradução acionável de sempre no fim.
    assert "Ordenar por" in str(ei.value)


def test_filtro_longo_demais_falha_antes_de_qualquer_pedido(servidor):
    enorme = "id IN (" + ", ".join(str(i) for i in range(3000)) + ")"
    with pytest.raises(ValueError, match="longo demais"):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter=enorme)
    assert servidor.urls == []


# ── O nó ─────────────────────────────────────────────────────────────────────────

def test_o_no_declara_o_filtro():
    props = {p["name"]: p for p in wfs.WFSNode.description()["properties"]}
    assert props["cqlFilter"]["type"] == "string" and props["cqlFilter"]["default"] == ""
    assert "GeoServer" in props["cqlFilter"]["description"]


async def test_execute_repassa_o_filtro(monkeypatch):
    import geopandas as gpd
    import flow.utils.geo_helpers as geo
    from unittest.mock import MagicMock

    monkeypatch.setattr(geo, "validate_url_ssrf", lambda u: ("1.2.3.4", "host"))
    fetch = MagicMock(return_value=gpd.GeoDataFrame(geometry=[]))
    monkeypatch.setattr(wfs, "_fetch_with_retry", fetch)

    no = wfs.WFSNode("n", {"url": "https://geo.exemplo.gov.br/ows", "typeName": "camada",
                           "cqlFilter": "  sigla_uf = 'MT'  "})
    await no.execute({})
    assert fetch.call_args.args[-1] == "sigla_uf = 'MT'"

    fetch.reset_mock()
    no = wfs.WFSNode("n", {"url": "https://geo.exemplo.gov.br/ows", "typeName": "camada"})
    await no.execute({})
    assert fetch.call_args.args[-1] is None
