# flow/nodes/datasource/wfs.py
"""WFS node — reads features from a Web Feature Service and returns a GeoDataFrame."""
import asyncio
import html
import io
import ipaddress
import json
import os
import re
import threading
import time
import geopandas as gpd
import pandas as pd
from requests.auth import AuthBase
from typing import Any, Dict
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils import segredos_vivos
from flow.utils.credencial_wfs import AutenticacaoWFS, autenticacao_wfs, formas_do_segredo, sem_segredo
from flow.utils.leitura_geo import ler_geodataframe
from flow.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 60
_DEFAULT_MAX_FEATURES = 1000
# Features per GetFeature in automatic pagination.
_TAMANHO_DA_PAGINA = 10_000
_MAX_RETRIES = 2
_RETRY_DELAY = 3
# Ceiling on the wait between attempts. `_MAX_RETRIES` is 2, so it rarely bites —
# it's here because the shared policy requires a declared ceiling.
_RETRY_MAX_DELAY = 30.0

# ── Capabilities cache ───────────────────────────────────────────────────────
# `WebFeatureService(url)` does a synchronous GetCapabilities on construction, and
# the node redid it on EVERY run and EVERY retry — for a server like IBGE's
# (9,759 FeatureTypes) that's most of the node's time. The owslib object is
# read-only after `__init__` (`getfeature` only reads url/timeout/auth and
# builds the request), so reusing it across calls in the same executor process
# is safe. One-hour TTL by default; `WFS_CAPABILITIES_TTL_S=0` turns it off.
# `threading.Lock`, not asyncio: the node runs in `asyncio.to_thread`.
_CAPS_TTL_S = int(os.getenv("WFS_CAPABILITIES_TTL_S", "").strip() or "3600")
_CAPS_MAX = 64
# (url, version) without a credential; (url, version, credential fingerprint) with one.
_caps_cache: dict[tuple, tuple[Any, float]] = {}
_caps_lock = threading.Lock()


# ── Authentication (saved credential) ────────────────────────────────────────
# The credential arrives resolved by the server in `http_auth` (see
# app/services/credential_resolver.py) and is read by `autenticacao_wfs` — the
# same rules as the editor's layer listing (see flow/utils/credencial_wfs.py).
# Here, the rules for whoever talks to the server through owslib:
#
# - The secret only goes to the NODE'S ADDRESS (scheme + host). owslib fetches the
#   features at the address the GetCapabilities announces; if another host is
#   announced, the secret would go along — the node refuses before the first GetFeature.
# - The secret never leaves in a message: in a URL with `?authkey=`, requests
#   repeats it in the error text, and the error (with the traceback) goes to the
#   screen and to the database. Every message that leaves `_fetch_with_retry` goes
#   through `sem_segredo`, without the exception chain.
# - The capabilities cache is PER CREDENTIAL: the key decides what the server
#   shows, and an authenticated client must not serve another workflow on the executor.
# - With a credential, no redirect outside the node's origin: `requests` only
#   strips `Authorization` when the host changes, and a custom header (the authkey
#   in the header) would go along to the other host.
# - A rejected credential (HTTP 401/403) is not retried: three attempts with the
#   wrong password can lock an LDAP/AD account behind GeoServer.


_PORTA_PADRAO = {"http": 80, "https": 443}


def _origem(url: str) -> tuple[str, str, int | None]:
    """Normalized (scheme, host, port) — what decides "same address".

    The raw `netloc` distinguishes what every HTTP client treats as equal: the
    explicit default port (`https://h` × `https://h:443`, which a GeoServer without
    a Proxy Base URL announces), the host's trailing dot, the spellings of an IPv6
    and the `usuario@` in the URL — and each one became a false "another address" refusal.
    """
    partes = urlsplit(url)
    esquema = partes.scheme.lower()
    host = (partes.hostname or "").lower().rstrip(".")
    try:
        host = str(ipaddress.ip_address(host))
    except ValueError:
        pass
    try:
        porta = partes.port
    except ValueError:
        return esquema, host, -1  # a port that isn't a number: an origin of its own, and fail closed
    return esquema, host, porta or _PORTA_PADRAO.get(esquema)


class _AssinaturaDoNo(AuthBase):
    """The credential on every request of the node — owslib's and ours —, and what
    is checked on each response.

    It goes to `requests` as the request's `auth` (owslib's `auth_delegate`), and
    that's how a hook can be registered on the response: owslib doesn't allow
    turning off redirects, but the hook runs BEFORE `requests` follows
    to the new address. A redirect to another origin is refused there —
    neither the key in the header, nor the one in the URL, nor Basic leave for another
    host, and the run doesn't go on anonymously somewhere nobody chose. It's also
    the only point that still sees the HTTP status: owslib replaces it with a
    `ServiceException` carrying the response body.
    """

    def __init__(self, auth: "AutenticacaoWFS", url: str):
        # Key in the URL: it's already in the address (see `_wfs_client`); here it's
        # only put back on a redirect that drops it.
        self._cabecalhos = auth.cabecalhos()
        self._na_url = auth.parametros()
        self._origem = _origem(url)

    def __call__(self, pedido):
        pedido.headers.update(self._cabecalhos)
        pedido.register_hook("response", self._conferir_resposta)
        return pedido

    def _conferir_resposta(self, resposta, *args, **kwargs):
        # `ValueError`: the retry doesn't repeat it (see `_tentar_com_retry`).
        if resposta.status_code in (401, 403):
            raise ValueError(
                f"O servidor WFS recusou a credencial (HTTP {resposta.status_code}). Confira em "
                f"Credenciais a chave (ou o usuário e a senha) e se ela dá acesso a esta camada. A "
                f"consulta não foi repetida, para não bloquear a conta."
            )
        if not resposta.is_redirect:
            return resposta
        destino = urljoin(resposta.url, resposta.headers.get("location", ""))
        if _origem(destino) != self._origem:
            onde = urlsplit(destino)
            raise ValueError(
                f"O servidor WFS redirecionou o pedido para outro endereço "
                f"({onde.scheme}://{onde.netloc}{onde.path}). Com credencial, o nó só fala com o "
                f"endereço informado — o segredo não vai a outro host. Use no nó o endereço final."
            )
        if self._na_url and next(iter(self._na_url)) not in dict(parse_qsl(urlsplit(destino).query)):
            # Key in the URL: `requests` follows the Location AS IT CAME, and a
            # redirect that drops the query (nginx's `rewrite … ?`)
            # would send the next request ANONYMOUS — in header and Basic modes the
            # credential survives the hop on the same origin. The origin has already been
            # checked: the key goes back on the destination before `requests` follows it.
            resposta.headers["Location"] = _com_parametros(destino, self._na_url)
        return resposta


def _pendurar_a_chave(wfs, url: str, auth: "AutenticacaoWFS") -> None:
    """The key on the addresses the server announces — only those of the node's origin.

    owslib builds each GetFeature from these addresses, preserving their
    query; hanging the key there carries it to every page. An address of another
    origin stays without it (and `_conferir_destino` refuses before using it).
    """
    for operacao in getattr(wfs, "operations", None) or []:
        for metodo in getattr(operacao, "methods", None) or []:
            destino = metodo.get("url")
            if not destino or _origem(destino) != _origem(url):
                continue
            if auth.nome not in dict(parse_qsl(urlsplit(destino).query)):
                metodo["url"] = _com_parametros(destino, {auth.nome: auth.segredo})


def _conferir_destino(wfs, url: str) -> None:
    """With a credential, the GetFeature has to go to the same origin as the node."""
    try:
        anunciado = next(
            m.get("url") for m in wfs.getOperationByName("GetFeature").methods
            if str(m.get("type") or "").lower() == "get"
        )
    except Exception:
        return  # without a GetFeature announcement owslib fails on its own, without requesting anything
    if anunciado and _origem(anunciado) != _origem(url):
        onde = urlsplit(anunciado)
        raise ValueError(
            f"O servidor anuncia outro endereço para buscar as feições "
            f"({onde.scheme}://{onde.netloc}{onde.path}), diferente do endereço do nó. Com "
            f"credencial, o nó só fala com o endereço informado — o segredo não vai a outro "
            f"host. Use no nó o endereço anunciado, ou corrija o 'Proxy Base URL' do GeoServer."
        )


def _wfs_client(
    url: str, version: str = "2.0.0", timeout: int = _DEFAULT_TIMEOUT, *,
    refresh: bool = False, auth: "AutenticacaoWFS | None" = None,
):
    """The `WebFeatureService` for `url`, from the cache while still valid.

    The construction (the network round trip) happens OUTSIDE the lock: holding the
    lock for up to 60 s would stall every WFS node in the process because of a slow
    server. A race builds it twice and the last one wins — cheap and with no visible effect.
    """
    from owslib.util import Authentication
    from owslib.wfs import WebFeatureService

    chave = (url, version) if auth is None else (url, version, auth.impressao)
    agora = time.monotonic()
    if _CAPS_TTL_S > 0 and not refresh:
        with _caps_lock:
            item = _caps_cache.get(chave)
        if item is not None and item[1] > agora:
            logger.info("WFS capabilities: cache (%s)", url)
            return item[0]

    endereco, extras = url, {}
    if auth is not None:
        # Basic and the key in the header go through the signature; the key in the URL,
        # in the address. The signature goes along regardless: it's what blocks
        # the redirect outside the origin.
        extras["auth"] = Authentication(auth_delegate=_AssinaturaDoNo(auth, url))
        endereco = _com_parametros(url, auth.parametros()) if auth.parametros() else url

    inicio = time.perf_counter()
    wfs = WebFeatureService(endereco, version=version, timeout=timeout, **extras)
    if auth is not None and auth.tipo == "authkey" and not auth.no_cabecalho:
        _pendurar_a_chave(wfs, url, auth)
    logger.info("WFS capabilities: rede em %d ms (%s)", (time.perf_counter() - inicio) * 1000, url)
    if _CAPS_TTL_S > 0:
        with _caps_lock:
            if len(_caps_cache) >= _CAPS_MAX and chave not in _caps_cache:
                # Teto: sai a entrada que expira primeiro.
                mais_velha = min(_caps_cache, key=lambda k: _caps_cache[k][1])
                _caps_cache.pop(mais_velha, None)
            _caps_cache[chave] = (wfs, agora + _CAPS_TTL_S)
    return wfs


# Regex to extract the error message from a WFS ExceptionReport XML
_WFS_ERROR_RE = re.compile(r"<ows:ExceptionText>(.*?)</ows:ExceptionText>", re.DOTALL)


def _sem_redigir(texto: str) -> str:
    return texto


def _parse_wfs_error(raw: str, redigir=_sem_redigir) -> str:
    """Extracts a readable message from a WFS error XML.

    `redigir` (the credential's `sem_segredo`) runs AFTER `html.unescape`
    and BEFORE any truncation: the key echoed with HTML entities (`&amp;`,
    `&#x27;`) only becomes the key again when unescaped, and a cut in the middle of it
    would leave a piece that no later redaction recognizes.
    """
    match = _WFS_ERROR_RE.search(raw)
    if match:
        return redigir(html.unescape(match.group(1).strip()))
    if re.search(r"<html|<!doctype html", raw[:500], re.IGNORECASE):
        # A firewall, login or maintenance page in place of the WFS: the text, without the tags.
        texto = redigir(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip())
        return f"o servidor respondeu uma página HTML em vez do WFS: {texto[:200]}"
    return redigir(html.unescape(raw))[:500]


# GeoServer refuses pagination (startIndex/count) on a layer without a primary key:
# without a PK it has no stable "natural order" between pages and requires a SORTBY.
# The raw message doesn't say what to do — we translate it into an actionable instruction.
_NATURAL_ORDER_RE = re.compile(
    r"natural order without a primary key|specify a manual sort", re.IGNORECASE
)


def _wfs_error_message(raw: str, type_name: str, redigir=_sem_redigir) -> str:
    """Readable message from the ExceptionReport; the 'no primary key' case becomes
    an instruction on how to fix it (set the SORTBY)."""
    msg = _parse_wfs_error(raw, redigir)
    if _NATURAL_ORDER_RE.search(msg):
        return (
            f"A camada '{type_name}' não tem chave primária no servidor, então a "
            f"paginação exige uma ordenação. Defina 'Ordenar por (SORTBY)' com um "
            f"atributo existente da camada (ex.: um campo de id). "
            f"Resposta do servidor: {msg}"
        )
    return msg


# The OWS codes that say "the request is wrong": retrying gives the same
# refusal. `NoApplicableCode`/`OperationProcessingFailed` (slow database, exhausted
# pool) remain retryable, as they always were.
_CODIGOS_DE_REQUISICAO_ERRADA = frozenset({
    "InvalidParameterValue", "MissingParameterValue", "OperationParsingFailed",
    "OperationNotSupported", "OptionNotSupported", "VersionNegotiationFailed",
})
_EXCEPTION_CODE_RE = re.compile(r'exceptionCode="([^"]+)"')
_LOCATOR_RE = re.compile(r'locator="([^"]+)"')
_MENCIONA_FILTRO_RE = re.compile(r"cql|filter", re.IGNORECASE)
# Without an exceptionCode (owslib delivers only the ExceptionText when the
# Content-Type is exactly text/xml), the GeoServer CQL parser's sentence is the only
# sign of a wrong request. PARSE sentences, and not the word "filter": GeoTools
# writes "Error occured filtering features" when the database goes down — transient,
# and retryable.
_ERRO_DE_PARSE_DO_CQL_RE = re.compile(
    r"could not parse|illegal filter|unable to parse|illegal property name|parsing failed|"
    r"encountered \"|\bcql\b",
    re.IGNORECASE,
)
# The web server in front of the WFS (Tomcat, Jetty, nginx) refusing the request
# line: HTML, no exceptionCode, and retrying doesn't help.
_URL_LONGA_RE = re.compile(
    r"request header is too large|request-uri too long|uri too long|header too large|http status 414",
    re.IGNORECASE,
)


def _erro_do_servidor(
    raw: str, type_name: str, com_cql: bool, auth: "AutenticacaoWFS | None" = None,
) -> Exception:
    """The server's refusal as an exception: `ValueError` (not retried) when the
    request is wrong; `RuntimeError` (retried) for the rest. The message is the
    server's text, not the raw XML.

    A wrong-request `exceptionCode` decides on its own. `NoApplicableCode`
    is ambiguous — it's how GeoServer delivers a CQL SYNTAX error (the
    `CQLFilterKvpParser` raises the ServiceException without a code, and the handler
    sets `NoApplicableCode` and HTTP 400) and also a database that went down —, so
    with it, as with no code at all, the CQL parser's sentence decides, only when
    there's a filter; "Error occured filtering features" remains retryable. The hint
    "confira o filtro CQL" (check the CQL filter) only goes in when the `locator`
    (or its absence) points to the filter; a `locator="outputFormat"` gets its own hint.

    The secret is removed from the body BEFORE the message is truncated, including
    the HTML-escaped form (see `_parse_wfs_error`): a page that repeats the request's
    URL, cut in the middle of the key, would leave its beginning behind — and
    no later redaction would recognize the piece.
    """
    raw = sem_segredo(raw, auth)
    msg = _wfs_error_message(raw, type_name, lambda texto: sem_segredo(texto, auth))
    achado = _EXCEPTION_CODE_RE.search(raw)
    codigo = achado.group(1) if achado else None
    achado = _LOCATOR_RE.search(raw)
    locator = achado.group(1) if achado else None
    if com_cql and _URL_LONGA_RE.search(msg):
        return _erro_de_url_longa(None)
    if codigo in _CODIGOS_DE_REQUISICAO_ERRADA:
        errada = True
    elif codigo in (None, "NoApplicableCode"):
        errada = bool(com_cql and _ERRO_DE_PARSE_DO_CQL_RE.search(msg))
    else:
        errada = False
    if not errada:
        return RuntimeError(msg)
    dica = ""
    if locator and locator.lower() == "outputformat":
        dica = " O servidor não serve GeoJSON (outputFormat=application/json), que o nó exige."
    elif com_cql and (not locator or _MENCIONA_FILTRO_RE.search(locator) or _MENCIONA_FILTRO_RE.search(msg)):
        dica = " Confira o filtro CQL (a sintaxe e os nomes de atributo)."
    return ValueError(f"O servidor WFS recusou a consulta: {msg.rstrip('.')}.{dica}")


def _excecoes_do_servico() -> tuple[type[BaseException], ...]:
    """The exceptions through which owslib delivers the server's voice.

    There are two classes: the one in `owslib.util` (`openURL`, for HTTP 400/401/403 and
    for an XML body with an Exception) and the one in `owslib.feature.wfs200` (the
    `getfeature`, for a short OGC ServiceExceptionReport).
    """
    from owslib.util import ServiceException as DoUtil
    try:
        from owslib.feature.wfs200 import ServiceException as DoWfs200
    except ImportError:
        return (DoUtil,)
    return (DoUtil, DoWfs200)


def _parse_sortby(raw: str) -> list[str] | None:
    """Splits the 'Ordenar por' field into a list (owslib does `','.join(sortby)`):
    'gid, nome DESC' -> ['gid', 'nome DESC']; empty -> None (no SORTBY)."""
    itens = [s.strip() for s in raw.split(",") if s.strip()]
    return itens or None


# ── CQL filter ───────────────────────────────────────────────────────────────
# `CQL_FILTER` is a GeoServer vendor parameter (ECQL). The filter runs ON THE
# SERVER and before pagination: `maxFeatures` counts only what passed, and nothing
# that didn't pass crosses the network. Three precautions live here:
#
# - owslib has no way to send a vendor parameter in `getfeature`: with a
#   filter, the URL comes out of its SAME builder (`getGETGetFeatureRequest`) and
#   gets `CQL_FILTER` appended at the end.
# - In GeoServer, BBOX and CQL_FILTER are mutually exclusive in the request.
#   With both, the clip goes into the CQL itself as `BBOX("<geometria>", …)`,
#   in the layer's default CRS — the same one the field's bbox was always read in.
# - A server that doesn't know the parameter (MapServer, ArcGIS, QGIS Server)
#   IGNORES it silently and would return the whole layer as if it were the clip.
#   A probe (`CQL_FILTER=EXCLUDE`, which must match zero features) turns into a
#   clear error before the first page. Without being able to ask (network, 5xx),
#   the node doesn't proceed: the failure propagates and is retried; a server that
#   neither reports the count nor speaks GeoJSON doesn't pass either (GDAL would read
#   the whole layer in GML without complaining).

# Above this, the GET is usually refused by the web server itself: Tomcat and
# Jetty stop at 8 KB counting the request line AND the headers — and the
# credential adds one (Basic, or the key in the header). The response is
# an HTML page that is neither GeoJSON nor an ExceptionReport.
_MAX_URL_COM_CQL = 7500
# Headroom for what the URL gains after the initial check: the clip's
# `BBOX(...)` and the `startindex` of the following pages.
_FOLGA_DA_URL = 250

# Servers that have already shown they apply CQL_FILTER: url -> expires at.
_cql_verificado: dict[str, float] = {}
_CQL_VERIFICADO_MAX = 256

_NUMBER_MATCHED_RE = re.compile(r'numberMatched="(\d+)"')
_CRS_EPSG_RE = re.compile(r"EPSG:\d+")


def _parse_cql(raw: Any) -> str | None:
    """The field's filter, with no leading/trailing spaces; empty -> None (no filter)."""
    texto = str(raw or "").strip()
    return texto or None


def _numero_cql(valor: float) -> str:
    """Number in decimal notation (no exponent, which not every CQL parser accepts)."""
    texto = f"{valor:.12f}".rstrip("0").rstrip(".")
    return "0" if texto in ("", "-0") else texto


def _cql_com_bbox(cql: str, bbox: tuple, geometria: str, crs: str | None) -> str:
    """`BBOX("geom", minx, miny, maxx, maxy[, 'EPSG:x']) AND (<filtro>)`.

    The parentheses around the author's filter keep an `OR` of theirs from
    escaping the clip. The geometry name always goes in double quotes: there are
    layers whose geometry is called `point` (an ECQL keyword) or `ms:geom`. The
    CRS only goes in when it's a plain EPSG code — `OGC:CRS84` and the like
    GeoTools may not decode, and without it the layer's default CRS applies.
    """
    nome = '"' + geometria.replace('"', "") + '"'
    coords = ", ".join(_numero_cql(v) for v in bbox)
    crs_arg = f", '{crs}'" if crs and _CRS_EPSG_RE.fullmatch(crs) else ""
    return f"BBOX({nome}, {coords}{crs_arg}) AND ({cql})"


def _com_parametros(url: str, params: dict[str, str]) -> str:
    """Appends parameters to a URL's QUERY (a space becomes %20) — before the
    fragment, if there is one: glued to the end of `…/ows#x`, they would fall into the
    fragment and the request would go out without the key."""
    if not params:
        return url
    partes = urlsplit(url)
    query = f"{partes.query}&" if partes.query else ""
    return urlunsplit(partes._replace(query=query + urlencode(params, quote_via=quote)))


def _crs_padrao(wfs, type_name: str) -> str | None:
    """The layer's default CRS (`EPSG:4674`) — the one of the bbox sent in the request."""
    try:
        opcoes = wfs.contents[type_name].crsOptions
        return opcoes[0].getcode() if opcoes else None
    except Exception:
        return None


def _local(tag: Any) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


# The GML geometric property types (`<nome>PropertyType`): those of the
# source catalog (`fontes_vault.GEOMETRIAS`) plus the 3D, composite and
# generic ones of an app-schema/INSPIRE schema.
_GEOMETRIAS_GML = frozenset({
    "Point", "MultiPoint", "Curve", "MultiCurve", "LineString", "MultiLineString",
    "Surface", "MultiSurface", "Polygon", "MultiPolygon", "Geometry", "MultiGeometry",
    "Solid", "MultiSolid", "CompositeCurve", "CompositeSurface", "CompositeSolid",
    "GeometricPrimitive", "GeometricAggregate", "GeometricComplex",
})
_ESPACO_GML = "http://www.opengis.net/gml"


def _geometria_do_xsd(raiz) -> str | None:
    """The first geometric attribute of a DescribeFeatureType.

    A geometry is an `element` of a `sequence` whose type is a GML geometric
    property (Point, Curve, MultiCurve, Surface, Geometry…). owslib's fixed
    list doesn't know Curve/MultiCurve, and every line layer from
    DNIT or ANA would end up without geometry. Ending in `PropertyType` isn't
    enough: in an INSPIRE or app-schema schema the first such one is `inspireId`
    (IdentifierPropertyType) or an association (gml:FeaturePropertyType) — and the
    BBOX would go with the wrong name. Only children of `sequence`: the top-level element
    of a layer called `landProperty` has the type `ns:landPropertyType`.
    """
    nsmap = getattr(raiz, "nsmap", None) or {}
    for sequencia in raiz.iter():
        if _local(sequencia.tag) != "sequence":
            continue
        for el in sequencia:
            if _local(el.tag) != "element":
                continue
            nome, tipo = el.get("name"), el.get("type")
            if not nome or not tipo:
                continue
            prefixo, _, local = tipo.rpartition(":")
            if not local.endswith("PropertyType") or local[: -len("PropertyType")] not in _GEOMETRIAS_GML:
                continue
            espaco = nsmap.get(prefixo or None)
            if espaco is not None and not espaco.startswith(_ESPACO_GML):
                continue  # a `ns:PointPropertyType` from the schema itself is not GML
            return nome
    return None


def _coluna_de_geometria(wfs, type_name: str) -> str:
    """The name of the layer's geometry, via DescribeFeatureType.

    Network, timeout and 5xx propagate as they came (the query is retried); only a
    response read WITHOUT a geometry becomes a configuration error.
    """
    from owslib.etree import etree
    from owslib.util import openURL

    url = _com_parametros(wfs.url, {
        "service": "WFS", "version": wfs.version,
        "request": "DescribeFeatureType", "typeNames": type_name,
    })
    corpo = openURL(url, None, "Get", timeout=wfs.timeout, headers=wfs.headers, auth=wfs.auth).read()
    try:
        raiz = etree.fromstring(corpo)
    except Exception as exc:
        raise RuntimeError(
            f"O DescribeFeatureType de '{type_name}' não veio em XML legível."
        ) from exc
    coluna = _geometria_do_xsd(raiz)
    if not coluna:
        raise ValueError(
            f"Para usar o bbox junto com o filtro CQL, o nó precisa da coluna de geometria "
            f"da camada '{type_name}', e o DescribeFeatureType dela não declara nenhuma. "
            f"Deixe o bbox vazio e ponha o recorte no próprio filtro: "
            f"BBOX(<geometria>, minx, miny, maxx, maxy) AND (<seu filtro>)."
        )
    return coluna


def _pedir(wfs, type_name: str, extras: dict[str, str], **montagem) -> bytes:
    """A GetFeature built by owslib, with extra parameters."""
    from owslib.util import openURL

    base = wfs.getGETGetFeatureRequest(typename=[type_name], **montagem)
    url = _com_parametros(base, extras)
    return openURL(url, None, "Get", timeout=wfs.timeout, headers=wfs.headers, auth=wfs.auth).read()


def _texto(corpo: Any) -> str:
    return corpo.decode("utf-8", errors="replace") if isinstance(corpo, bytes) else str(corpo)


def _quantas_casam(wfs, type_name: str, cql: str | None, auth: "AutenticacaoWFS | None" = None) -> int:
    """How many features match (with the filter, if any).

    First `resultType=hits` (with `count=1`, so that a server that ignores
    hits doesn't dump the layer); without a numeric `numberMatched` (GeoServer's
    "unknown" when it skips the count), a sample feature in GeoJSON decides.
    With neither one nor the other the node does NOT proceed: a server that ignores
    CQL_FILTER and doesn't speak GeoJSON would return the whole layer in GML as if
    it were the clip — and GDAL would read it without complaining.
    """
    extras = {"CQL_FILTER": cql} if cql else {}
    corpo = _pedir(wfs, type_name, {"resultType": "hits", **extras}, maxfeatures=1)
    achado = _NUMBER_MATCHED_RE.search(_texto(corpo[:4096]))
    if achado:
        return int(achado.group(1))
    corpo = _texto(_pedir(wfs, type_name, extras, maxfeatures=1, outputFormat="application/json"))
    if "<ows:ExceptionReport" in corpo or "<ServiceException" in corpo:
        # The server refused the sample (it doesn't serve GeoJSON, for example): its
        # voice, classified as on any page.
        raise _erro_do_servidor(corpo, type_name, bool(cql), auth)
    try:
        return len(json.loads(corpo).get("features") or [])
    except (ValueError, AttributeError, TypeError):
        raise ValueError(
            f"Não foi possível verificar se este servidor WFS aplica o filtro CQL: ele não informou "
            f"a contagem (numberMatched) nem respondeu em GeoJSON para a camada '{type_name}'. Deixe "
            f"o filtro vazio e filtre depois de ler, ou use o bbox para o recorte espacial."
        ) from None


def _garantir_que_aplica_cql(wfs, url: str, type_name: str, auth: "AutenticacaoWFS | None" = None) -> bool:
    """Refuses a server that ignores CQL_FILTER (it would return the whole layer).

    `CQL_FILTER=EXCLUDE` matches zero features on servers that apply it: a positive
    count proves the parameter was ignored. Zero is also what an EMPTY
    layer gives on any server — the proof that the server applies the
    CQL is only complete when the layer shows a feature: the first filtered
    page that comes with something (see `_fetch_wfs_features`, which then calls
    `_registrar_cql_verificado`). Returns whether that confirmation is pending.

    No second count, of the whole layer, for this: a `count(*)`
    on a table with millions of rows (the case CQL exists for) blew
    the timeout and brought down the run whose filter had already been proven.
    """
    agora = time.monotonic()
    with _caps_lock:
        expira = _cql_verificado.get(url)
    if expira is not None and expira > agora:
        return False
    if _quantas_casam(wfs, type_name, "EXCLUDE", auth) > 0:
        raise ValueError(
            "Este servidor WFS não aplica o filtro CQL: ele ignorou o parâmetro "
            "CQL_FILTER e devolveria a camada inteira. O filtro CQL é uma extensão do "
            "GeoServer. Deixe o filtro vazio e filtre depois de ler (por exemplo, com "
            "um nó de filtro de atributos), ou use o bbox para o recorte espacial."
        )
    return _CAPS_TTL_S > 0


def _registrar_cql_verificado(url: str) -> None:
    """The server at `url` applies CQL: valid for the cache TTL, per server."""
    agora = time.monotonic()
    with _caps_lock:
        for chave in [k for k, v in _cql_verificado.items() if v <= agora]:
            del _cql_verificado[chave]
        if len(_cql_verificado) >= _CQL_VERIFICADO_MAX:
            _cql_verificado.pop(min(_cql_verificado, key=_cql_verificado.get), None)
        _cql_verificado[url] = agora + _CAPS_TTL_S


def _url_da_pagina(wfs, kwargs: dict, cql: str) -> str:
    """The URL of a GetFeature page, with CQL_FILTER at the end."""
    base = wfs.getGETGetFeatureRequest(
        typename=[kwargs["typename"]],
        maxfeatures=kwargs["maxfeatures"],
        srsname=kwargs.get("srsname"),
        outputFormat=kwargs["outputFormat"],
        startindex=kwargs.get("startindex"),
        sortby=kwargs.get("sortby"),
    )
    return _com_parametros(base, {"CQL_FILTER": cql})


def _erro_de_url_longa(tamanho: int | None) -> ValueError:
    """`tamanho` is what the node measured; `None` when it was the web server that refused."""
    medida = f"{tamanho} caracteres na URL; " if tamanho else ""
    return ValueError(
        f"O filtro CQL é longo demais para a requisição ({medida}o limite prático é "
        f"{_MAX_URL_COM_CQL}). Encurte o filtro — troque listas longas de valores por um "
        f"intervalo ou por um recorte espacial."
    )


def _getfeature_com_cql(wfs, kwargs: dict, cql: str):
    """owslib's `getfeature`, with the CQL_FILTER it doesn't know how to send."""
    from owslib.util import openURL

    url = _url_da_pagina(wfs, kwargs, cql)
    if len(url) > _MAX_URL_COM_CQL:
        raise _erro_de_url_longa(len(url))
    return openURL(url, None, "Get", timeout=wfs.timeout, headers=wfs.headers, auth=wfs.auth)


def _fetch_wfs_features(
    url: str,
    type_name: str,
    max_features: int,
    bbox: tuple | None = None,
    srs_name: str | None = None,
    sort_by: list[str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
    cql_filter: str | None = None,
    auth: "AutenticacaoWFS | None" = None,
) -> gpd.GeoDataFrame:
    """Connects to a WFS endpoint with automatic pagination and returns a GeoDataFrame."""
    wfs = _wfs_client(url, "2.0.0", timeout, auth=auth)

    # Validates that the layer exists on the server. If it came from the cache and the
    # layer isn't there, redoes the GetCapabilities ONCE before complaining: a layer
    # published less than an hour ago must not become a false "não encontrada" (not found).
    available = list(wfs.contents.keys())
    if type_name not in available:
        wfs = _wfs_client(url, "2.0.0", timeout, refresh=True, auth=auth)
        available = list(wfs.contents.keys())
    if type_name not in available:
        raise ValueError(
            f"Camada '{type_name}' não encontrada no servidor WFS. "
            f"Camadas disponíveis: {', '.join(available[:20])}"
            f"{'...' if len(available) > 20 else ''}"
        )
    if auth is not None:
        _conferir_destino(wfs, url)

    # With a CQL filter: the server needs to apply it, and the bbox (if any) goes
    # into the filter itself — see the "CQL filter" block above.
    cql = cql_filter
    confirmar_o_cql = False
    if cql:
        # Before any request: a filter that doesn't fit in the URL fails right away, and
        # not in the middle of pagination.
        primeira = _url_da_pagina(wfs, {
            "typename": type_name, "maxfeatures": min(max_features, _TAMANHO_DA_PAGINA),
            "srsname": srs_name, "outputFormat": "application/json", "sortby": sort_by,
        }, cql)
        if len(primeira) + (_FOLGA_DA_URL if bbox else 30) > _MAX_URL_COM_CQL:
            raise _erro_de_url_longa(len(primeira))
        confirmar_o_cql = _garantir_que_aplica_cql(wfs, url, type_name, auth)
        if bbox:
            cql = _cql_com_bbox(cql, bbox, _coluna_de_geometria(wfs, type_name), _crs_padrao(wfs, type_name))
            bbox = None

    # Automatic pagination: fetches in blocks until reaching maxFeatures
    page_size = min(max_features, _TAMANHO_DA_PAGINA)
    all_chunks: list[gpd.GeoDataFrame] = []
    start_index = 0
    total_fetched = 0

    while total_fetched < max_features:
        remaining = max_features - total_fetched
        count = min(page_size, remaining)

        kwargs: dict = {
            "typename": type_name,
            "maxfeatures": count,
            "startindex": start_index,
            "outputFormat": "application/json",
        }
        if bbox:
            kwargs["bbox"] = bbox
        if srs_name:
            kwargs["srsname"] = srs_name
        # owslib does `','.join(sortby)`, so it needs to be a list. It goes on every
        # page (including the 1st): GeoServer requires SORTBY whenever there's a
        # startIndex, and the loop sends startindex from the start.
        if sort_by:
            kwargs["sortby"] = sort_by

        response = _getfeature_com_cql(wfs, kwargs, cql) if cql else wfs.getfeature(**kwargs)
        raw = response.read()

        # Detecta erro XML do servidor WFS
        raw_str = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        if "<ows:ExceptionReport" in raw_str or "<ServiceException" in raw_str:
            raise _erro_do_servidor(raw_str, type_name, bool(cql), auth)

        # `ler_geodataframe` refuses a response that is an OGR VRT document
        # (malicious WFS server) before GDAL opens it — see leitura_geo.py.
        chunk = ler_geodataframe(io.BytesIO(raw if isinstance(raw, bytes) else raw.encode()))

        if chunk.empty:
            break
        if confirmar_o_cql:
            # The layer has a feature and EXCLUDE matched zero: the server applies CQL.
            _registrar_cql_verificado(url)
            confirmar_o_cql = False

        all_chunks.append(chunk)
        total_fetched += len(chunk)
        start_index += len(chunk)

        # If it received fewer than requested, there are no more pages
        if len(chunk) < count:
            break

    if not all_chunks:
        return gpd.GeoDataFrame()

    # pd.concat of GeoDataFrames returns a GeoDataFrame; gpd.concat does NOT exist —
    # the previous code crashed on paginated WFS results (>1 chunk).
    gdf = pd.concat(all_chunks, ignore_index=True) if len(all_chunks) > 1 else all_chunks[0]

    return gdf


def _fetch_with_retry(
    url: str,
    type_name: str,
    max_features: int,
    bbox: tuple | None,
    srs_name: str | None,
    sort_by: list[str] | None,
    timeout: int,
    retries: int,
    retry_delay: float,
    cql_filter: str | None = None,
    auth: "AutenticacaoWFS | None" = None,
) -> gpd.GeoDataFrame:
    """Wrapper with retry and exponential backoff.

    With a credential, every message that leaves here goes through `sem_segredo` and
    without the exception chain: the original error (the one from requests, with the URL
    and the key) would go whole into the traceback, which reaches the screen and the
    database. And, while the fetch runs, no log in the process carries the key — not
    even the DEBUG of owslib and urllib3, which write each request's URL (see
    `segredos_vivos`).
    """
    try:
        with segredos_vivos.em_uso(*formas_do_segredo(auth)):
            return _tentar_com_retry(
                url, type_name, max_features, bbox, srs_name, sort_by, timeout,
                retries, retry_delay, cql_filter, auth,
            )
    except Exception as exc:
        if auth is None:
            raise
        base = ValueError if isinstance(exc, ValueError) else ImportError if isinstance(exc, ImportError) else RuntimeError
        raise base(sem_segredo(str(exc), auth)) from None


def _tentar_com_retry(
    url: str,
    type_name: str,
    max_features: int,
    bbox: tuple | None,
    srs_name: str | None,
    sort_by: list[str] | None,
    timeout: int,
    retries: int,
    retry_delay: float,
    cql_filter: str | None,
    auth: "AutenticacaoWFS | None",
) -> gpd.GeoDataFrame:
    import time
    from flow.utils.backoff import espera_exponencial
    from flow.utils.geo_helpers import is_tls_verify_error, tls_verify_error_message

    excecoes_do_servico = _excecoes_do_servico()
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return _fetch_wfs_features(
                url, type_name, max_features, bbox, srs_name, sort_by, timeout, cql_filter, auth,
            )
        except (ImportError, ValueError):
            raise  # Configuration errors — retries make no sense
        except excecoes_do_servico as exc:
            # The server's voice (the raw message is the whole XML): a wrong
            # request — invalid filter, rejected parameter — is not retried;
            # the rest (slow database, exhausted pool) follows the usual retry.
            erro = _erro_do_servidor(str(exc), type_name, bool(cql_filter), auth)
            if isinstance(erro, ValueError):
                raise erro from exc
            last_exc = erro
            if attempt < retries:
                delay = espera_exponencial(attempt, inicial=retry_delay, teto=_RETRY_MAX_DELAY)
                logger.warning(
                    "WFS tentativa %d/%d falhou: %s. Retentando em %.1fs...",
                    attempt + 1, retries + 1, sem_segredo(str(erro), auth), delay,
                )
                time.sleep(delay)
        except Exception as exc:
            # An invalid TLS chain doesn't fix itself: retrying only makes the
            # user wait out the whole backoff to see the same error, and
            # urllib3's raw message doesn't say what to do.
            if is_tls_verify_error(exc):
                raise RuntimeError(tls_verify_error_message(url, exc)) from exc
            last_exc = exc
            if attempt < retries:
                delay = espera_exponencial(attempt, inicial=retry_delay, teto=_RETRY_MAX_DELAY)
                logger.warning(
                    "WFS tentativa %d/%d falhou: %s. Retentando em %.1fs...",
                    attempt + 1, retries + 1, sem_segredo(str(exc), auth), delay,
                )
                time.sleep(delay)
    raise RuntimeError(f"WFS falhou após {retries + 1} tentativa(s): {last_exc}") from last_exc


@register_node
class WFSNode(BaseNode):

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "WFS",
            "alias": "WFS (Web Feature Service)",
            "description": (
                "Lê feições de um endpoint WFS com suporte a bbox, filtro CQL no servidor, "
                "paginação automática e retry."
            ),
            "type": "datasource",
            "dynamic_output": True,
            # The node reads an EXTERNAL SOURCE of this kind: the source catalog answers
            # for it (`search_sources(kind="wfs")`), validation checks the URL
            # against the catalog and `describe_node` advises not to invent url/typeName.
            "source_kind": "wfs",
            "properties": [
                {
                    "name": "url", "required": True, "placeholder": "https://servidor/geoserver/ows",
                    "label": "URL",
                    "type": "string",
                    "default": "",
                    "description": "URL base do serviço WFS.",
                },
                {
                    "name": "typeName", "required": True,
                    "label": "Camada (typeName)",
                    "type": "string",
                    "default": "",
                    "description": "Nome da camada (typename) a ser consultada.",
                },
                {
                    "name": "credential_id",
                    "label": "Credencial",
                    "type": "credential",
                    "credential_types": ["geoserver_authkey", "wfs"],
                    "default": "",
                    "description": (
                        "Opcional, para serviço protegido: a chave authkey do GeoServer ou usuário e "
                        "senha (Basic), salvos em Credenciais. O segredo só vai ao endereço do nó e "
                        "nunca é gravado na definição do workflow."
                    ),
                },
                {
                    # INJECTED by the server from `credential_id` (the same
                    # contract as HttpRequest). Declared because `validate()`
                    # rebuilds the parameters from this list and would discard
                    # whatever wasn't here; the UI hides it by name.
                    "name": "http_auth",
                    "label": "Autenticação resolvida",
                    "type": "object",
                    "default": {},
                    "description": (
                        "Preenchida automaticamente a partir da credencial escolhida. Não "
                        "editável: o segredo nunca é gravado na definição do workflow."
                    ),
                },
                {
                    "name": "maxFeatures",
                    "label": "Máx. de feições",
                    "type": "integer",
                    "default": 1000,
                    "description": "Número máximo de feições a serem retornadas.",
                },
                {
                    "name": "bbox",
                    "label": "Bounding box (bbox)",
                    "type": "string",
                    "default": "",
                    "description": "Bounding box: minx,miny,maxx,maxy (ex: -64.01,-9.01,-63.82,-8.83). Vazio = sem filtro espacial.",
                },
                {
                    "name": "cqlFilter",
                    "label": "Filtro CQL (CQL_FILTER)",
                    "type": "string",
                    "default": "",
                    "placeholder": "sigla_uf = 'MT' AND area_ha > 100",
                    "description": (
                        "Filtro por atributos e/ou geometria aplicado NO SERVIDOR, antes da "
                        "paginação (ECQL do GeoServer). Ex.: sigla_uf = 'MT' AND area_ha > 100; "
                        "nome LIKE 'São%'; data >= '2025-01-01'; "
                        "INTERSECTS(geom, POINT(-56.1 -15.6)). Com o bbox preenchido, o recorte "
                        "entra no filtro sozinho. Extensão do GeoServer: servidor que não a "
                        "aplica é recusado com erro, em vez de devolver a camada inteira. "
                        "Vazio = sem filtro."
                    ),
                },
                {
                    "name": "crs",
                    "label": "CRS de saída",
                    "type": "string",
                    "default": "",
                    "description": "CRS de saída (ex: EPSG:4326). Vazio = CRS original do servidor.",
                },
                {
                    "name": "sortBy",
                    "label": "Ordenar por (SORTBY)",
                    "type": "string",
                    "default": "",
                    "description": (
                        "Atributo(s) para ordenar o resultado (ex.: 'gid' ou 'gid DESC'; "
                        "separe vários por vírgula). Necessário para paginar camadas sem chave "
                        "primária no servidor. Vazio = ordem do servidor."
                    ),
                },
                {
                    "name": "timeout",
                    "label": "Tempo limite (s)",
                    "type": "integer",
                    "default": _DEFAULT_TIMEOUT,
                    "description": "Timeout em segundos para a conexão WFS.",
                },
                {
                    "name": "retries",
                    "label": "Tentativas",
                    "type": "integer",
                    "default": _MAX_RETRIES,
                    "description": "Número de tentativas em caso de falha (0 = sem retry).",
                },
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe", "description": "GeoDataFrame com as feições"},
                {"name": "feature_count", "type": "number", "description": "Número de feições retornadas"},
                {"name": "crs", "type": "string", "description": "CRS do GeoDataFrame"},
                {"name": "bbox_string", "type": "string", "description": "Bbox das feições: minx,miny,maxx,maxy"},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        # Normaliza: descarta query/fragment caso usuario tenha colado URL
        # completa do GetCapabilities (ex: ...ows?service=wms&version=...)
        from flow.utils.geo_helpers import normalize_ows_endpoint_url, validate_url_ssrf
        url = normalize_ows_endpoint_url(self.get_param("url", ""))
        type_name = self.get_param("typeName", "").strip()
        max_features = self.get_param_int("maxFeatures", _DEFAULT_MAX_FEATURES)
        timeout = self.get_param_int("timeout", _DEFAULT_TIMEOUT)
        retries = self.get_param_int("retries", _MAX_RETRIES)
        srs_name = self.get_param("crs", "").strip() or None
        sort_by = _parse_sortby(self.get_param("sortBy", ""))
        cql_filter = _parse_cql(self.get_param("cqlFilter", ""))
        auth = autenticacao_wfs(self.get_param("credential_id"), self.get_param("http_auth"))

        if not url:
            raise ValueError("Parâmetro 'url' é obrigatório.")
        if not type_name:
            raise ValueError("Parâmetro 'typeName' é obrigatório.")
        if max_features <= 0:
            raise ValueError("Parâmetro 'maxFeatures' deve ser maior que zero.")

        # SSRF: the URL comes from the user and owslib fetches it directly (GetCapabilities/
        # GetFeature), unlike HttpRequest/SendWebhook, which go through
        # safe_httpx_request with IP pinning. Without this check, a WFS pointing
        # to 169.254.169.254 (cloud metadata), internal MinIO/Redis/Postgres or
        # step-ca would be requested, and the error message would return the body to the
        # panel (blind SSRF -> partially blind). validate_url_ssrf resolves the
        # host and refuses internal/private/loopback/link-local/reserved IPs.
        # Residual (follow-up): owslib does its own resolution and follows redirects,
        # so a TOCTOU/DNS-rebinding window remains — the ideal is a transport
        # with IP pinning in owslib. Runs in a thread: getaddrinfo would block the loop.
        await asyncio.to_thread(validate_url_ssrf, url)

        # bbox: accepts it from the manual field OR from another node's input (e.g.: ComputeBoundingBox.bbox_string)
        bbox_str = self.get_param("bbox", "").strip()
        if not bbox_str:
            bbox_str = str(inputs.get("bbox_string", "")).strip()
        bbox = None
        if bbox_str:
            parts = [float(v.strip()) for v in bbox_str.split(",")]
            if len(parts) != 4:
                raise ValueError(
                    f"Parâmetro 'bbox' deve ter 4 valores (minx,miny,maxx,maxy). Recebido: {len(parts)} valores."
                )
            bbox = tuple(parts)

        logger.info(
            "Conectando ao WFS: %s | camada: %s | máx: %s | timeout: %ds%s%s%s%s",
            url, type_name, max_features, timeout,
            f" | bbox: {bbox_str}" if bbox else "",
            f" | crs: {srs_name}" if srs_name else "",
            f" | ordenar: {', '.join(sort_by)}" if sort_by else "",
            f" | cql: {cql_filter}" if cql_filter else "",
        )

        try:
            gdf = await asyncio.to_thread(
                _fetch_with_retry, url, type_name, max_features,
                bbox, srs_name, sort_by, timeout, retries, _RETRY_DELAY, cql_filter,
                auth=auth,
            )
        except ImportError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Erro ao consultar WFS: {sem_segredo(str(e), auth)}") from e

        if gdf.empty:
            logger.warning("Nenhuma feição retornada do WFS para a camada '%s'.", type_name)

        # Output metadata
        crs_str = str(gdf.crs) if gdf.crs else ""
        result_bbox = ""
        if not gdf.empty:
            b = gdf.total_bounds
            result_bbox = f"{b[0]},{b[1]},{b[2]},{b[3]}"

        logger.info("WFS carregado: %d feições, CRS: %s", len(gdf), crs_str)

        return {
            "output": gdf,
            "feature_count": len(gdf),
            "crs": crs_str,
            "bbox_string": result_bbox,
        }
