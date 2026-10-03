# tests/unit/test_wfs_cql.py
"""WFS node: the CQL filter (`CQL_FILTER`, GeoServer's ECQL) applied on the server.

The client is the REAL owslib one (`WebFeatureService_2_0_0` built from a
canned GetCapabilities), so the URLs come from the real builder
(`getGETGetFeatureRequest`); only `openURL` is stubbed, by a server that
records each URL and responds by request type.

What is protected:
- the filter goes to the SERVER on every page, with the usual SORTBY and srsName;
- with a bbox, the clip goes into the CQL itself and the `bbox` KVP is not sent
  along (GeoServer refuses both together); the geometry comes from
  DescribeFeatureType, including for a line layer (MultiCurve, which owslib's
  list does not know);
- a server that ignores the parameter is refused with an error; when it cannot
  verify (network, 5xx), the node does NOT proceed with the entire layer;
- an empty layer does not "verify" the server;
- the server's refusal of a bad request is not retried; a transient failure
  is still retried; the messages arrive readable.
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

# GeoServer's DescribeFeatureType for a LINE layer: MultiCurve.
_XSD_LINES = b"""<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:ns="http://ns"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema" targetNamespace="http://ns">
  <xsd:complexType name="rodoviasType"><xsd:complexContent>
    <xsd:extension base="gml:AbstractFeatureType"><xsd:sequence>
      <xsd:element name="sigla_uf" nillable="true" type="xsd:string"/>
      <xsd:element name="geom" nillable="true" type="gml:MultiCurvePropertyType"/>
    </xsd:sequence></xsd:extension></xsd:complexContent></xsd:complexType>
  <xsd:element name="rodovias" substitutionGroup="gml:AbstractFeature" type="ns:rodoviasType"/>
</xsd:schema>"""

_XSD_WITHOUT_GEOMETRY = _XSD_LINES.replace(
    b'<xsd:element name="geom" nillable="true" type="gml:MultiCurvePropertyType"/>', b""
)


def _features(n: int) -> bytes:
    itens = b",".join(
        b'{"type":"Feature","geometry":{"type":"Point","coordinates":[0,0]},"properties":{"id":%d}}' % i
        for i in range(n)
    )
    return b'{"type":"FeatureCollection","features":[' + itens + b"]}"


def _hits(n) -> bytes:
    return b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" numberMatched="%s" numberReturned="0"/>' % str(n).encode()


class _FakeResponse:
    def __init__(self, corpo: bytes):
        self._response_body = corpo

    def read(self):
        return self._response_body

    def info(self):
        return {}


class _FakeServer:
    """The stubbed `openURL`. Responds by request type and records each URL.

    - `hits[with_filter]`: the numberMatched of a `resultType=hits` with/without CQL;
    - `paginas`: the GetFeature pages, in order (the last one repeats);
    - `esquemas`: the DescribeFeatureType per layer;
    - `falhas`: exceptions to raise, in order, before responding (one per request).
    """

    def __init__(self):
        self.urls: list[str] = []
        self.hits = {True: 0, False: 5}
        self.amostra = {True: 0, False: 1}  # features in the GeoJSON sample, with/without CQL
        self.paginas: list[bytes | Exception] = [_features(1)]
        self.esquemas = {"ns:rodovias": _XSD_LINES, "ns:tabela": _XSD_WITHOUT_GEOMETRY}
        self.falhas: list[Exception] = []

    def __call__(self, url, data=None, method="Get", **kw):
        self.urls.append(url)
        if self.falhas:
            raise self.falhas.pop(0)
        p = self.params(len(self.urls) - 1)
        if p.get("request") == "DescribeFeatureType":
            return _FakeResponse(self.esquemas[p["typeNames"]])
        with_filter = "CQL_FILTER" in p
        if p.get("resultType") == "hits":
            return _FakeResponse(_hits(self.hits[with_filter]))
        if p.get("count") == "1" and p.get("startindex") is None and self.sonda_por_amostra:
            if self.amostra_em_gml:
                return _FakeResponse(b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" numberMatched="unknown"><wfs:member/></wfs:FeatureCollection>')
            return _FakeResponse(_features(self.amostra[with_filter]))
        resposta = self.paginas.pop(0) if len(self.paginas) > 1 else self.paginas[0]
        if isinstance(resposta, Exception):
            raise resposta
        return _FakeResponse(resposta)

    sonda_por_amostra = False
    amostra_em_gml = False  # o servidor ignora o outputFormat e responde GML

    def params(self, i: int) -> dict:
        return dict(parse_qsl(urlsplit(self.urls[i]).query))

    @property
    def pedidos(self) -> list[dict]:
        return [self.params(i) for i in range(len(self.urls))]

    @property
    def requested_pages(self) -> list[dict]:
        return [
            p for p in self.pedidos
            if p.get("request") == "GetFeature" and p.get("resultType") != "hits"
            and not (self.sonda_por_amostra and p.get("count") == "1")
        ]

    @property
    def probes(self) -> list[dict]:
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
    falso = _FakeServer()
    monkeypatch.setattr(owslib.util, "openURL", falso)
    monkeypatch.setattr(wfs200, "openURL", falso)
    monkeypatch.setattr("time.sleep", lambda s: None)
    return falso


# ── The pure pieces ──────────────────────────────────────────────────────────────

def test_parse_cql_strips_the_ends_and_empty_becomes_none():
    assert wfs._parse_cql("  sigla_uf = 'MT' ") == "sigla_uf = 'MT'"
    for vazio in ("", "   ", None):
        assert wfs._parse_cql(vazio) is None


def test_cql_with_bbox_clips_protects_the_filter_and_names_the_geometry():
    cql = wfs._cql_with_bbox("a = 1 OR b = 2", (-64.01, -9.01, -63.82, -8.83), "geom", "EPSG:4674")
    # The author's OR does not escape the clip; the geometry goes in quotes
    # (some layers have a geometry named `point`, an ECQL word).
    assert cql == "BBOX(\"geom\", -64.01, -9.01, -63.82, -8.83, 'EPSG:4674') AND (a = 1 OR b = 2)"
    assert wfs._cql_with_bbox("x", (0, 0, 1, 1), "point", None).startswith('BBOX("point", 0, 0, 1, 1) AND')


def test_cql_with_bbox_only_accepts_epsg_crs_and_numbers_without_exponent():
    cql = wfs._cql_with_bbox("x > 0", (0.0000001, -0.0, 10, 20), "ms:msGeometry", "OGC:CRS84")
    assert cql == 'BBOX("ms:msGeometry", 0.0000001, 0, 10, 20) AND (x > 0)'


def test_xsd_geometry_recognizes_multicurve_and_absence():
    from owslib.etree import etree
    assert wfs._xsd_geometry(etree.fromstring(_XSD_LINES)) == "geom"
    assert wfs._xsd_geometry(etree.fromstring(_XSD_WITHOUT_GEOMETRY)) is None


def _xsd(sequencia: str, *, layer_name: str = "camada", extra_ns: str = "") -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:ns="http://ns" {extra_ns}
    xmlns:xsd="http://www.w3.org/2001/XMLSchema" targetNamespace="http://ns">
  <xsd:element name="{layer_name}" substitutionGroup="gml:AbstractFeature" type="ns:{layer_name}Type"/>
  <xsd:complexType name="{layer_name}Type"><xsd:complexContent>
    <xsd:extension base="gml:AbstractFeatureType"><xsd:sequence>{sequencia}</xsd:sequence></xsd:extension>
  </xsd:complexContent></xsd:complexType>
</xsd:schema>""".encode()


@pytest.mark.parametrize("sequencia, extra_ns, camada, esperado", [
    # Application schema (INSPIRE): the association and the identifier come before the geometry.
    ('<xsd:element name="relatedTo" type="gml:FeaturePropertyType"/>'
     '<xsd:element name="inspireId" type="base:IdentifierPropertyType"/>'
     '<xsd:element name="validTime" type="gml:TimePeriodPropertyType"/>'
     '<xsd:element name="geometry" type="gml:GeometryPropertyType"/>',
     'xmlns:base="http://inspire.ec.europa.eu/schemas/base/3.3"', "camada", "geometry"),
    # Layer without geometry whose NAME ends in Property: the top-level element is not an attribute.
    ('<xsd:element name="valor" type="xsd:string"/>', "", "landProperty", None),
    # MapServer: the top-level element before the complexType, and msGeometry.
    ('<xsd:element name="msGeometry" type="gml:GeometryPropertyType"/>', "", "ownedProperty", "msGeometry"),
    # A PointPropertyType from the schema itself is not GML.
    ('<xsd:element name="ponto" type="ns:PointPropertyType"/><xsd:element name="geom" type="gml:PointPropertyType"/>',
     "", "camada", "geom"),
    # Duas geometrias: a primeira.
    ('<xsd:element name="centroid" type="gml:PointPropertyType"/><xsd:element name="geom" type="gml:MultiSurfacePropertyType"/>',
     "", "camada", "centroid"),
    # 3D and composite types are geometry too.
    ('<xsd:element name="geom" type="gml:SolidPropertyType"/>', "", "camada", "geom"),
    ('<xsd:element name="geom" type="gml:GeometricPrimitivePropertyType"/>', "", "camada", "geom"),
])
def test_xsd_geometry_ignores_what_is_not_gml_geometry(sequencia, extra_ns, camada, esperado):
    from owslib.etree import etree
    assert wfs._xsd_geometry(etree.fromstring(_xsd(sequencia, layer_name=camada, extra_ns=extra_ns))) == esperado


def test_server_error_decodes_and_classifies():
    # The REAL GeoServer shape for a CQL syntax error: the parser raises the
    # ServiceException without a code, and the handler delivers `NoApplicableCode`
    # (HTTP 400), with no locator. By the code alone it would be retryable.
    invalido = (
        '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception '
        'exceptionCode="NoApplicableCode"><ows:ExceptionText>'
        "Could not parse CQL filter list. Encountered &quot;=&quot; at line 1</ows:ExceptionText>"
        "</ows:Exception></ows:ExceptionReport>"
    )
    erro = wfs._server_error(invalido, "ns:rodovias", with_cql=True)
    assert isinstance(erro, ValueError)
    assert 'Encountered "=" at line 1' in str(erro)  # entidade decodificada
    assert "Confira o filtro CQL" in str(erro)
    # A bad-request code decides on its own, whatever the text.
    assert isinstance(wfs._server_error(
        invalido.replace('exceptionCode="NoApplicableCode"', 'exceptionCode="InvalidParameterValue" locator="cql_filter"'),
        "ns:rodovias", with_cql=True,
    ), ValueError)

    transient = invalido.replace(
        "Could not parse CQL filter list. Encountered &quot;=&quot; at line 1",
        "pool error Timeout waiting for idle object",
    )
    assert isinstance(wfs._server_error(transient, "ns:rodovias", with_cql=True), RuntimeError)
    # GeoTools talking about a database that went down mid-filter: retryable.
    assert isinstance(wfs._server_error(
        invalido.replace("Could not parse CQL filter list. Encountered &quot;=&quot; at line 1", "Error occured filtering features"),
        "ns:rodovias", with_cql=True,
    ), RuntimeError)
    # Without a filter, a message that talks about a filter does not change the classification.
    assert isinstance(wfs._server_error("Illegal filter", "ns:rodovias", with_cql=False), RuntimeError)


def test_with_params_puts_the_key_in_the_query_and_never_in_the_fragment():
    # Appended to the end of `…/ows#x` the key would land in the fragment, and the
    # request followed after a redirect would go out anonymous.
    assert wfs._with_params("http://x/ows", {"authkey": "K 1"}) == "http://x/ows?authkey=K%201"  # pragma: allowlist secret
    assert wfs._with_params("http://x/ows?a=1", {"authkey": "K"}) == "http://x/ows?a=1&authkey=K"
    assert wfs._with_params("http://x/ows#f", {"authkey": "K"}) == "http://x/ows?authkey=K#f"
    assert wfs._with_params("http://x/ows?a=1#f", {"authkey": "K"}) == "http://x/ows?a=1&authkey=K#f"
    assert wfs._with_params("http://x/ows", {}) == "http://x/ows"


def test_the_exception_code_decides_before_the_word_filter():
    # GeoTools writes "Error occured filtering features" when PostGIS goes
    # down: NoApplicableCode, transient — the word "filter" does not make it a
    # CQL filter error, and the execution keeps being retried.
    db_went_down = (
        '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception '
        'exceptionCode="NoApplicableCode"><ows:ExceptionText>java.io.IOException: Error occured '
        "filtering features / Connection refused</ows:ExceptionText></ows:Exception></ows:ExceptionReport>"
    )
    erro = wfs._server_error(db_went_down, "ns:rodovias", with_cql=True)
    assert isinstance(erro, RuntimeError) and "Confira o filtro" not in str(erro)
    # No code (owslib only delivers the ExceptionText): the parser's phrase decides,
    # not the bare word.
    assert isinstance(wfs._server_error("Illegal filter", "ns:rodovias", with_cql=True), ValueError)
    assert isinstance(wfs._server_error("Unable to parse CQL", "ns:rodovias", with_cql=True), ValueError)
    assert isinstance(wfs._server_error("Error occured filtering features", "ns:rodovias", with_cql=True), RuntimeError)


def test_cql_hint_only_appears_when_the_locator_points_at_the_filter():
    def relatorio(locator, texto):
        loc = f' locator="{locator}"' if locator else ""
        return (
            f'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception '
            f'exceptionCode="InvalidParameterValue"{loc}><ows:ExceptionText>{texto}</ows:ExceptionText>'
            f"</ows:Exception></ows:ExceptionReport>"
        )
    # The server does not serve GeoJSON: that is the hint, not "check the filter".
    geojson = wfs._server_error(relatorio("outputFormat", "Invalid outputFormat value: application/json"), "ns:x", with_cql=True)
    assert isinstance(geojson, ValueError)
    assert "não serve GeoJSON" in str(geojson) and "Confira o filtro" not in str(geojson)
    # Another parameter pointed at: no retry, but the filter is not blamed.
    srs = wfs._server_error(relatorio("srsName", "Unknown srs EPSG:99"), "ns:x", with_cql=True)
    assert isinstance(srs, ValueError) and "Confira o filtro" not in str(srs)
    # No locator, with a filter: the filter is the usual suspect.
    sem = wfs._server_error(relatorio(None, "Illegal property name: foo"), "ns:x", with_cql=True)
    assert "Confira o filtro" in str(sem)


def test_tomcat_400_for_long_url_is_not_retried(servidor):
    # The request line exceeded the web server's limit: HTML, no exceptionCode.
    pagina = ("<html><head><title>HTTP Status 400 – Bad Request</title></head><body>"
              "<h1>HTTP Status 400 – Bad Request</h1><p>Request header is too large</p></body></html>")
    servidor.paginas = [ServiceException(pagina)]
    with pytest.raises(ValueError, match="longo demais") as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, "a = 1")
    assert len(servidor.requested_pages) == 1  # no retry
    assert str(wfs._MAX_URL_WITH_CQL) in str(ei.value)


def test_html_page_becomes_summary_without_tags():
    msg = wfs._parse_wfs_error("<!DOCTYPE html><html><body><h1>Acesso negado</h1><p>WAF &amp; cia</p></body></html>")
    assert msg == "o servidor respondeu uma página HTML em vez do WFS: Acesso negado WAF & cia"


# ── Without a filter, nothing changes ────────────────────────────────────────────

def test_without_filter_the_path_is_the_usual_getfeature(servidor):
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, bbox=(-64.0, -9.0, -63.0, -8.0))
    assert servidor.probes == []
    (pagina,) = servidor.requested_pages
    assert "CQL_FILTER" not in pagina
    # owslib's bbox KVP: axes swapped for the layer's lat/lon URN.
    assert pagina["bbox"] == "-9.0,-64.0,-8.0,-63.0,urn:ogc:def:crs:EPSG::4674"


# ── With a filter ────────────────────────────────────────────────────────────────

def test_the_filter_goes_to_the_server_with_sortby_and_srsname(servidor):
    gdf = wfs._fetch_wfs_features(
        URL, "ns:rodovias", 10, srs_name="EPSG:4326", sort_by=["gid"], cql_filter="sigla_uf = 'MT'",
    )
    assert len(gdf) == 1

    (exclude,) = servidor.probes  # only the EXCLUDE: the page with a feature is the missing proof
    assert exclude["CQL_FILTER"] == "EXCLUDE" and exclude["count"] == "1"
    assert URL in wfs._cql_verificado  # the layer has a feature: the verification counts

    (pagina,) = servidor.requested_pages
    assert pagina["CQL_FILTER"] == "sigla_uf = 'MT'"
    assert pagina["sortby"] == "gid" and pagina["srsname"] == "EPSG:4326"
    assert pagina["typenames"] == "ns:rodovias" and pagina["outputFormat"] == "application/json"
    assert "bbox" not in pagina
    # A space becomes %20 (not +) in the URL.
    assert "sigla_uf%20%3D%20%27MT%27" in servidor.urls[-1]


def test_with_bbox_the_clip_goes_into_the_cql_of_a_line_layer(servidor):
    wfs._fetch_wfs_features(
        URL, "ns:rodovias", 10, bbox=(-64.01, -9.01, -63.82, -8.83), cql_filter="sigla_uf = 'MT'",
    )
    (pagina,) = servidor.requested_pages
    assert pagina["CQL_FILTER"] == (
        "BBOX(\"geom\", -64.01, -9.01, -63.82, -8.83, 'EPSG:4674') AND (sigla_uf = 'MT')"
    )
    # With owslib's REAL builder: the bbox KVP is not sent along (GeoServer refuses both).
    assert "bbox" not in pagina
    assert any(p.get("request") == "DescribeFeatureType" and p["typeNames"] == "ns:rodovias" for p in servidor.pedidos)


def test_with_bbox_and_layer_without_geometry_the_error_says_what_to_do(servidor):
    with pytest.raises(ValueError, match=r"BBOX\(<geometria>"):
        wfs._fetch_wfs_features(URL, "ns:tabela", 10, bbox=(1, 2, 3, 4), cql_filter="a = 1")
    assert servidor.requested_pages == []


def test_describe_feature_type_offline_is_retried_and_does_not_become_configuration_error(servidor):
    wfs._cql_verificado[URL] = float("inf")  # already verified: only DescribeFeatureType is requested
    servidor.falhas = [requests.HTTPError("503 Server Error: Service Unavailable")]
    gdf = wfs._fetch_with_retry(URL, "ns:rodovias", 10, (1, 2, 3, 4), None, None, 5, 2, 0.0, "a = 1")
    assert len(gdf) == 1  # a 2ª tentativa passou
    describes = [p for p in servidor.pedidos if p.get("request") == "DescribeFeatureType"]
    assert len(describes) == 2


def test_the_filter_goes_on_every_page(servidor, monkeypatch):
    monkeypatch.setattr(wfs, "_TAMANHO_DA_PAGINA", 2)
    servidor.paginas = [_features(2), _features(2), _features(1)]
    gdf = wfs._fetch_wfs_features(URL, "ns:rodovias", 5, sort_by=["gid"], cql_filter="id >= 0")

    assert len(gdf) == 5
    paginas = servidor.requested_pages
    assert [p.get("startindex") for p in paginas] == [None, "2", "4"]
    assert [p["count"] for p in paginas] == ["2", "2", "1"]
    # The filter (and the sorting) go on EVERY page: it is the server that paginates the filtered set.
    assert all(p["CQL_FILTER"] == "id >= 0" and p["sortby"] == "gid" for p in paginas)


# ── A sondagem ───────────────────────────────────────────────────────────────────

def test_server_that_ignores_the_filter_is_refused_before_the_first_page(servidor):
    servidor.hits[True] = 5  # EXCLUDE casou tudo: o CQL_FILTER foi ignorado
    with pytest.raises(ValueError, match="não aplica o filtro CQL"):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="sigla_uf = 'MT'")
    assert servidor.requested_pages == []


def test_unknown_count_decides_by_the_sample(servidor):
    servidor.hits = {True: "unknown", False: "unknown"}
    servidor.sonda_por_amostra = True
    servidor.amostra = {True: 1, False: 1}  # EXCLUDE returned a feature: ignored
    with pytest.raises(ValueError, match="não aplica o filtro CQL"):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    assert servidor.requested_pages == []

    servidor.urls.clear()
    servidor.amostra = {True: 0, False: 1}  # EXCLUDE empty and the layer has a feature: applies
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    assert len(servidor.requested_pages) == 1 and URL in wfs._cql_verificado


def test_server_that_neither_reports_the_count_nor_speaks_geojson_is_refused(servidor):
    # Ignores CQL_FILTER, does not report numberMatched and responds with GML to
    # a GeoJSON request: before, it went on with a warning in the log, and GDAL
    # read the entire layer.
    servidor.hits = {True: "unknown", False: "unknown"}
    servidor.sonda_por_amostra = True
    servidor.amostra_em_gml = True
    with pytest.raises(ValueError, match="Não foi possível verificar"):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    assert servidor.requested_pages == [] and wfs._cql_verificado == {}


def test_sample_refused_by_outputformat_says_the_server_does_not_serve_geojson(servidor, monkeypatch):
    servidor.hits = {True: "unknown", False: "unknown"}
    servidor.sonda_por_amostra = True
    recusa = (
        '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception '
        'exceptionCode="InvalidParameterValue" locator="outputFormat"><ows:ExceptionText>'
        "Invalid outputFormat value: application/json</ows:ExceptionText></ows:Exception></ows:ExceptionReport>"
    )
    servidor.amostra_em_gml = True
    original = servidor.__call__

    def _with_refusal(url, data=None, method="Get", **kw):
        resposta = original(url, data, method, **kw)
        p = servidor.params(len(servidor.urls) - 1)
        return _FakeResponse(recusa.encode()) if p.get("outputFormat") == "application/json" and p.get("count") == "1" else resposta

    import owslib.util
    import owslib.feature.wfs200 as wfs200
    monkeypatch.setattr(owslib.util, "openURL", _with_refusal)
    monkeypatch.setattr(wfs200, "openURL", _with_refusal)
    with pytest.raises(ValueError) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, "a = 1")
    assert "não serve GeoJSON" in str(ei.value) and "Confira o filtro" not in str(ei.value)
    assert servidor.requested_pages == []  # and no retry


def test_whole_layer_count_is_no_longer_requested(servidor, monkeypatch):
    # A count(*) on a table with millions of rows blew the timeout and brought
    # down the execution whose filter had already been proven. The proof the
    # EXCLUDE lacks (the layer has a feature) comes from the first page itself.
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    assert [s.get("CQL_FILTER") for s in servidor.probes] == ["EXCLUDE"]
    assert URL in wfs._cql_verificado

    # With the TTL turned off the probe repeats on every execution — and only the probe.
    monkeypatch.setattr(wfs, "_CAPS_TTL_S", 0)
    monkeypatch.setattr(wfs, "_cql_verificado", {})
    servidor.urls.clear()
    for _ in range(2):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    assert [s.get("CQL_FILTER") for s in servidor.probes] == ["EXCLUDE", "EXCLUDE"]
    assert wfs._cql_verificado == {}


def test_unable_to_ask_the_node_does_not_proceed_with_the_whole_layer(servidor):
    servidor.hits[True] = 5  # o servidor ignora o CQL...
    servidor.falhas = [requests.ConnectionError("caiu")]  # ...and the 1st probe does not even arrive
    with pytest.raises(ValueError, match="não aplica o filtro CQL"):
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, "a = 1")
    assert servidor.requested_pages == []  # a falha foi retentada, e a sondagem refeita recusou


def test_empty_layer_does_not_check_the_server(servidor):
    servidor.hits = {True: 0, False: 0}
    servidor.paginas = [_features(0)]  # EXCLUDE zero E a camada vazia: nada prova
    assert wfs._fetch_wfs_features(URL, "ns:vazia", 10, cql_filter="a = 1").empty
    assert wfs._cql_verificado == {}
    servidor.paginas = [_features(1)]

    # Another layer of the same server probes again — and the server that ignores it is caught.
    servidor.urls.clear()
    servidor.hits = {True: 5, False: 5}
    with pytest.raises(ValueError, match="não aplica o filtro CQL"):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")


def test_check_lasts_for_the_ttl_per_server(servidor):
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1")
    wfs._fetch_wfs_features(URL, "ns:vazia", 10, cql_filter="a = 2")
    assert len([s for s in servidor.probes if s.get("CQL_FILTER") == "EXCLUDE"]) == 1


def test_the_check_cache_has_a_ceiling(servidor, monkeypatch):
    monkeypatch.setattr(wfs, "_CQL_VERIFICADO_MAX", 2)
    for host in ("a", "b", "c"):
        wfs._fetch_wfs_features(f"http://{host}/ows", "ns:rodovias", 10, cql_filter="a = 1")
    assert len(wfs._cql_verificado) == 2 and "http://a/ows" not in wfs._cql_verificado


# ── Server refusal ───────────────────────────────────────────────────────────────

# The real GeoServer shape (see `test_server_error_decodes_and_classifies`).
_INVALID_CQL = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1" version="2.0.0">'
    '<ows:Exception exceptionCode="NoApplicableCode">'
    "<ows:ExceptionText>Could not parse CQL filter list. Encountered &quot;=&quot;</ows:ExceptionText>"
    "</ows:Exception></ows:ExceptionReport>"
)


def test_invalid_filter_is_not_retried_and_arrives_readable(servidor):
    servidor.paginas = [ServiceException(_INVALID_CQL)]
    with pytest.raises(ValueError) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, "a == 1")
    msg = str(ei.value)
    assert msg.startswith("O servidor WFS recusou a consulta:")
    assert 'Could not parse CQL filter list. Encountered "="' in msg
    assert "<ows:" not in msg and "&quot;" not in msg
    assert len(servidor.requested_pages) == 1  # no retry


def test_transient_server_failure_keeps_being_retried(servidor):
    transitoria = _INVALID_CQL.replace(
        "Could not parse CQL filter list. Encountered &quot;=&quot;", "pool error Timeout waiting for idle object",
    )
    servidor.paginas = [ServiceException(transitoria), _features(1)]
    gdf = wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, "a = 1")
    assert len(gdf) == 1 and len(servidor.requested_pages) == 2


def test_wfs200_exception_is_also_the_server_voice(servidor):
    servidor.paginas = [ServiceExceptionWfs200("Cannot do natural order without a primary key")] * 3
    with pytest.raises(RuntimeError) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0)
    # Retried (implicit NoApplicableCode), and the usual actionable translation at the end.
    assert "Ordenar por" in str(ei.value)


def test_too_long_filter_fails_before_any_request(servidor):
    enorme = "id IN (" + ", ".join(str(i) for i in range(3000)) + ")"
    with pytest.raises(ValueError, match="longo demais"):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter=enorme)
    assert servidor.urls == []


# ── The node ─────────────────────────────────────────────────────────────────────

def test_the_node_declares_the_filter():
    props = {p["name"]: p for p in wfs.WFSNode.description()["properties"]}
    assert props["cqlFilter"]["type"] == "string" and props["cqlFilter"]["default"] == ""
    assert "GeoServer" in props["cqlFilter"]["description"]


async def test_execute_passes_the_filter_on(monkeypatch):
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
