# flow/nodes/datasource/wfs.py
"""Nó WFS — lê feições de um Web Feature Service e retorna GeoDataFrame."""
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
# Feições por GetFeature na paginação automática.
_TAMANHO_DA_PAGINA = 10_000
_MAX_RETRIES = 2
_RETRY_DELAY = 3
# Teto da espera entre tentativas. `_MAX_RETRIES` e 2, entao raramente morde —
# esta aqui porque a politica compartilhada exige um teto declarado.
_RETRY_MAX_DELAY = 30.0

# ── Cache de capabilities ────────────────────────────────────────────────────
# `WebFeatureService(url)` faz um GetCapabilities síncrono na construção, e o nó
# o refazia em TODA execução e em TODO retry — para um servidor como o do IBGE
# (9.759 FeatureTypes) isso é a maior parte do tempo do nó. O objeto do owslib é
# somente-leitura depois do `__init__` (o `getfeature` só lê url/timeout/auth e
# monta a requisição), então reaproveitá-lo entre chamadas do mesmo processo do
# executor é seguro. TTL de uma hora por padrão; `WFS_CAPABILITIES_TTL_S=0`
# desliga. `threading.Lock`, e não asyncio: o nó roda em `asyncio.to_thread`.
_CAPS_TTL_S = int(os.getenv("WFS_CAPABILITIES_TTL_S", "").strip() or "3600")
_CAPS_MAX = 64
# (url, versão) sem credencial; (url, versão, impressão da credencial) com ela.
_caps_cache: dict[tuple, tuple[Any, float]] = {}
_caps_lock = threading.Lock()


# ── Autenticação (credencial salva) ──────────────────────────────────────────
# A credencial chega resolvida pelo servidor em `http_auth` (ver
# app/services/credential_resolver.py) e é lida por `autenticacao_wfs` — as
# mesmas regras da listagem de camadas do editor (ver flow/utils/credencial_wfs.py).
# Aqui, três regras de quem fala com o servidor pelo owslib:
#
# - O segredo só vai ao ENDEREÇO DO NÓ (esquema + host). O owslib busca as
#   feições no endereço que o GetCapabilities anuncia; anunciado outro host, o
#   segredo iria junto — o nó recusa antes do primeiro GetFeature.
# - O segredo nunca sai numa mensagem: numa URL com `?authkey=` o requests o
#   repete no texto do erro, e o erro (com o traceback) vai à tela e ao banco.
#   Toda mensagem que deixa `_fetch_with_retry` passa por `sem_segredo`, sem a
#   cadeia de exceções.
# - O cache de capabilities é POR CREDENCIAL: a chave decide o que o servidor
#   mostra, e um cliente autenticado não pode servir a outro fluxo do executor.
# - Com credencial, nenhum redirecionamento para fora da origem do nó: o
#   `requests` só tira o `Authorization` quando o host muda, e um cabeçalho
#   próprio (o authkey no cabeçalho) seguiria junto para o outro host.
# - Credencial recusada (HTTP 401/403) não é repetida: três tentativas com a
#   senha errada podem bloquear uma conta de LDAP/AD por trás do GeoServer.


_PORTA_PADRAO = {"http": 80, "https": 443}


def _origem(url: str) -> tuple[str, str, int | None]:
    """(esquema, host, porta) normalizados — o que decide "mesmo endereço".

    O `netloc` cru distingue o que todo cliente HTTP trata como igual: a porta
    padrão explícita (`https://h` × `https://h:443`, que um GeoServer sem Proxy
    Base URL anuncia), o ponto final do host, as grafias de um IPv6 e o
    `usuario@` na URL — e cada uma virava uma recusa falsa de "outro endereço".
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
        return esquema, host, -1  # porta que não é número: origem só dela, e fecha
    return esquema, host, porta or _PORTA_PADRAO.get(esquema)


class _AssinaturaDoNo(AuthBase):
    """A credencial em cada pedido do nó — os do owslib e os nossos —, e o que
    se confere em cada resposta.

    Vai ao `requests` como o `auth` do pedido (o `auth_delegate` do owslib), e
    é por aí que dá para registrar um gancho na resposta: o owslib não deixa
    desligar o redirecionamento, mas o gancho roda ANTES de o `requests` seguir
    para o endereço novo. Redirecionamento para outra origem é recusado ali —
    nem a chave no cabeçalho, nem a da URL, nem o Basic saem para outro host,
    e a execução não segue anônima num lugar que ninguém escolheu. É também o
    único ponto que ainda vê o status HTTP: o owslib o troca por uma
    `ServiceException` com o corpo da resposta.
    """

    def __init__(self, auth: "AutenticacaoWFS", url: str):
        # Chave na URL: já está no endereço (ver `_wfs_client`); aqui só se
        # repõe num redirecionamento que a descarte.
        self._cabecalhos = auth.cabecalhos()
        self._na_url = auth.parametros()
        self._origem = _origem(url)

    def __call__(self, pedido):
        pedido.headers.update(self._cabecalhos)
        pedido.register_hook("response", self._conferir_resposta)
        return pedido

    def _conferir_resposta(self, resposta, *args, **kwargs):
        # `ValueError`: o retry não repete (ver `_tentar_com_retry`).
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
            # Chave na URL: o `requests` segue a Location COMO VEIO, e um
            # redirecionamento que descarta a query (o `rewrite … ?` do nginx)
            # levaria o pedido seguinte ANÔNIMO — nos modos cabeçalho e Basic a
            # credencial sobrevive ao salto na mesma origem. A origem já está
            # conferida: a chave volta ao destino antes de o `requests` segui-lo.
            resposta.headers["Location"] = _com_parametros(destino, self._na_url)
        return resposta


def _pendurar_a_chave(wfs, url: str, auth: "AutenticacaoWFS") -> None:
    """A chave nos endereços que o servidor anuncia — só nos da origem do nó.

    O owslib monta cada GetFeature a partir desses endereços, preservando a
    query deles; pendurar a chave ali a leva a toda página. Endereço de outra
    origem fica sem ela (e `_conferir_destino` recusa antes de usá-lo).
    """
    for operacao in getattr(wfs, "operations", None) or []:
        for metodo in getattr(operacao, "methods", None) or []:
            destino = metodo.get("url")
            if not destino or _origem(destino) != _origem(url):
                continue
            if auth.nome not in dict(parse_qsl(urlsplit(destino).query)):
                metodo["url"] = _com_parametros(destino, {auth.nome: auth.segredo})


def _conferir_destino(wfs, url: str) -> None:
    """Com credencial, o GetFeature tem de ir à mesma origem do nó."""
    try:
        anunciado = next(
            m.get("url") for m in wfs.getOperationByName("GetFeature").methods
            if str(m.get("type") or "").lower() == "get"
        )
    except Exception:
        return  # sem anúncio de GetFeature o owslib falha sozinho, sem pedir nada
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
    """O `WebFeatureService` de `url`, do cache quando ainda vale.

    A construção (a ida à rede) acontece FORA do lock: segurar o lock por até
    60 s travaria todo nó WFS do processo por causa de um servidor lento. Uma
    corrida constrói duas vezes e a última vence — barato e sem efeito visível.
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
        # O Basic e a chave no cabeçalho vão pela assinatura; a chave na URL,
        # no endereço. A assinatura vai de todo jeito: é ela que barra o
        # redirecionamento para fora da origem.
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


# Regex para extrair mensagem de erro de ExceptionReport XML do WFS
_WFS_ERROR_RE = re.compile(r"<ows:ExceptionText>(.*?)</ows:ExceptionText>", re.DOTALL)


def _sem_redigir(texto: str) -> str:
    return texto


def _parse_wfs_error(raw: str, redigir=_sem_redigir) -> str:
    """Extrai mensagem legível de XML de erro WFS.

    `redigir` (o `sem_segredo` da credencial) corre DEPOIS do `html.unescape`
    e ANTES de qualquer corte: a chave ecoada com entidades HTML (`&amp;`,
    `&#x27;`) só volta a ser a chave ao desescapar, e um corte no meio dela
    deixaria um pedaço que nenhuma redação depois reconhece.
    """
    match = _WFS_ERROR_RE.search(raw)
    if match:
        return redigir(html.unescape(match.group(1).strip()))
    if re.search(r"<html|<!doctype html", raw[:500], re.IGNORECASE):
        # Página de firewall, login ou manutenção no lugar do WFS: o texto, sem as tags.
        texto = redigir(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip())
        return f"o servidor respondeu uma página HTML em vez do WFS: {texto[:200]}"
    return redigir(html.unescape(raw))[:500]


# GeoServer recusa paginação (startIndex/count) em camada sem chave primária:
# sem PK ele não tem "ordem natural" estável entre páginas e exige um SORTBY.
# A mensagem crua não diz o que fazer — traduzimos para uma instrução acionável.
_NATURAL_ORDER_RE = re.compile(
    r"natural order without a primary key|specify a manual sort", re.IGNORECASE
)


def _wfs_error_message(raw: str, type_name: str, redigir=_sem_redigir) -> str:
    """Mensagem legível do ExceptionReport; o caso 'sem chave primária' vira uma
    instrução de resolver (definir o SORTBY)."""
    msg = _parse_wfs_error(raw, redigir)
    if _NATURAL_ORDER_RE.search(msg):
        return (
            f"A camada '{type_name}' não tem chave primária no servidor, então a "
            f"paginação exige uma ordenação. Defina 'Ordenar por (SORTBY)' com um "
            f"atributo existente da camada (ex.: um campo de id). "
            f"Resposta do servidor: {msg}"
        )
    return msg


# Os códigos OWS que dizem "a requisição está errada": repetir dá a mesma
# recusa. `NoApplicableCode`/`OperationProcessingFailed` (banco lento, pool
# esgotado) seguem retentáveis, como sempre foram.
_CODIGOS_DE_REQUISICAO_ERRADA = frozenset({
    "InvalidParameterValue", "MissingParameterValue", "OperationParsingFailed",
    "OperationNotSupported", "OptionNotSupported", "VersionNegotiationFailed",
})
_EXCEPTION_CODE_RE = re.compile(r'exceptionCode="([^"]+)"')
_LOCATOR_RE = re.compile(r'locator="([^"]+)"')
_MENCIONA_FILTRO_RE = re.compile(r"cql|filter", re.IGNORECASE)
# Sem exceptionCode (o owslib entrega só o ExceptionText quando o Content-Type
# é exatamente text/xml), a frase do parser de CQL do GeoServer é o único sinal
# de requisição errada. Frases de PARSE, e não a palavra "filter": o GeoTools
# escreve "Error occured filtering features" quando o banco cai — transitório,
# e retentável.
_ERRO_DE_PARSE_DO_CQL_RE = re.compile(
    r"could not parse|illegal filter|unable to parse|illegal property name|parsing failed|"
    r"encountered \"|\bcql\b",
    re.IGNORECASE,
)
# O servidor web em frente ao WFS (Tomcat, Jetty, nginx) recusando a linha do
# pedido: HTML, sem exceptionCode, e repetir não ajuda.
_URL_LONGA_RE = re.compile(
    r"request header is too large|request-uri too long|uri too long|header too large|http status 414",
    re.IGNORECASE,
)


def _erro_do_servidor(
    raw: str, type_name: str, com_cql: bool, auth: "AutenticacaoWFS | None" = None,
) -> Exception:
    """A recusa do servidor como exceção: `ValueError` (não retenta) quando a
    requisição está errada; `RuntimeError` (retenta) no resto. A mensagem é o
    texto do servidor, não o XML cru.

    Um `exceptionCode` de requisição errada decide sozinho. `NoApplicableCode`
    é ambíguo — é como o GeoServer entrega o erro de SINTAXE do CQL (o
    `CQLFilterKvpParser` levanta a ServiceException sem código, e o handler
    põe `NoApplicableCode` e HTTP 400) e também um banco que caiu —, então
    com ele, como sem código nenhum, a frase do parser de CQL decide, só com
    filtro; "Error occured filtering features" segue retentável. A dica
    "confira o filtro CQL" só entra quando o `locator` (ou a falta dele) aponta
    o filtro; um `locator="outputFormat"` ganha a dica dele.

    O segredo sai do corpo ANTES de a mensagem ser cortada, inclusive da forma
    escapada em HTML (ver `_parse_wfs_error`): uma página que repete a URL do
    pedido, cortada no meio da chave, deixaria o começo dela para trás — e
    nenhuma redação depois reconheceria o pedaço.
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
    """As exceções com que o owslib entrega a voz do servidor.

    São duas classes: a de `owslib.util` (o `openURL`, para HTTP 400/401/403 e
    para corpo XML com Exception) e a de `owslib.feature.wfs200` (o
    `getfeature`, para um ServiceExceptionReport OGC curto).
    """
    from owslib.util import ServiceException as DoUtil
    try:
        from owslib.feature.wfs200 import ServiceException as DoWfs200
    except ImportError:
        return (DoUtil,)
    return (DoUtil, DoWfs200)


def _parse_sortby(raw: str) -> list[str] | None:
    """Divide o campo 'Ordenar por' em lista (o owslib faz `','.join(sortby)`):
    'gid, nome DESC' -> ['gid', 'nome DESC']; vazio -> None (sem SORTBY)."""
    itens = [s.strip() for s in raw.split(",") if s.strip()]
    return itens or None


# ── Filtro CQL ───────────────────────────────────────────────────────────────
# `CQL_FILTER` é parâmetro de fornecedor do GeoServer (ECQL). O filtro roda NO
# SERVIDOR e antes da paginação: `maxFeatures` conta só o que passou, e nada
# que não passou atravessa a rede. Três cuidados moram aqui:
#
# - O owslib não tem como mandar parâmetro de fornecedor no `getfeature`: com
#   filtro, a URL sai do MESMO montador dele (`getGETGetFeatureRequest`) e
#   ganha o `CQL_FILTER` no fim.
# - No GeoServer, BBOX e CQL_FILTER são mutuamente exclusivos na requisição.
#   Com os dois, o recorte entra no próprio CQL como `BBOX("<geometria>", …)`,
#   no CRS padrão da camada — o mesmo em que o bbox do campo sempre foi lido.
# - Servidor que não conhece o parâmetro (MapServer, ArcGIS, QGIS Server) o
#   IGNORA em silêncio e devolveria a camada inteira como se fosse o recorte.
#   Uma sondagem (`CQL_FILTER=EXCLUDE`, que tem de casar zero feições) vira
#   erro claro antes da primeira página. Sem conseguir perguntar (rede, 5xx),
#   o nó não segue: a falha sobe e é retentada; servidor que não diz a
#   contagem nem fala GeoJSON também não passa (o GDAL leria a camada inteira
#   em GML sem reclamar).

# Acima disto o GET costuma ser recusado pelo próprio servidor web: Tomcat e
# Jetty param em 8 KB contados com a linha do pedido E os cabeçalhos — e a
# credencial acrescenta um (o Basic, ou a chave no cabeçalho). A resposta é
# uma página HTML que não é GeoJSON nem ExceptionReport.
_MAX_URL_COM_CQL = 7500
# Folga para o que a URL ganha depois da checagem inicial: o `BBOX(...)` do
# recorte e o `startindex` das páginas seguintes.
_FOLGA_DA_URL = 250

# Servidores que já mostraram que aplicam o CQL_FILTER: url -> expira em.
_cql_verificado: dict[str, float] = {}
_CQL_VERIFICADO_MAX = 256

_NUMBER_MATCHED_RE = re.compile(r'numberMatched="(\d+)"')
_CRS_EPSG_RE = re.compile(r"EPSG:\d+")


def _parse_cql(raw: Any) -> str | None:
    """O filtro do campo, sem espaços nas pontas; vazio -> None (sem filtro)."""
    texto = str(raw or "").strip()
    return texto or None


def _numero_cql(valor: float) -> str:
    """Número em notação decimal (sem expoente, que nem todo parser de CQL aceita)."""
    texto = f"{valor:.12f}".rstrip("0").rstrip(".")
    return "0" if texto in ("", "-0") else texto


def _cql_com_bbox(cql: str, bbox: tuple, geometria: str, crs: str | None) -> str:
    """`BBOX("geom", minx, miny, maxx, maxy[, 'EPSG:x']) AND (<filtro>)`.

    Os parênteses em volta do filtro de quem escreveu impedem que um `OR` dele
    escape do recorte. O nome da geometria vai sempre entre aspas duplas: há
    camadas cuja geometria se chama `point` (palavra do ECQL) ou `ms:geom`. O
    CRS só entra quando é um código EPSG simples — `OGC:CRS84` e afins o
    GeoTools pode não decodificar, e sem ele vale o CRS padrão da camada.
    """
    nome = '"' + geometria.replace('"', "") + '"'
    coords = ", ".join(_numero_cql(v) for v in bbox)
    crs_arg = f", '{crs}'" if crs and _CRS_EPSG_RE.fullmatch(crs) else ""
    return f"BBOX({nome}, {coords}{crs_arg}) AND ({cql})"


def _com_parametros(url: str, params: dict[str, str]) -> str:
    """Acrescenta parâmetros à QUERY de uma URL (espaço vira %20) — antes do
    fragmento, se houver: colados no fim de `…/ows#x`, eles cairiam no
    fragmento e o pedido sairia sem a chave."""
    if not params:
        return url
    partes = urlsplit(url)
    query = f"{partes.query}&" if partes.query else ""
    return urlunsplit(partes._replace(query=query + urlencode(params, quote_via=quote)))


def _crs_padrao(wfs, type_name: str) -> str | None:
    """O CRS padrão da camada (`EPSG:4674`) — o do bbox que vai à requisição."""
    try:
        opcoes = wfs.contents[type_name].crsOptions
        return opcoes[0].getcode() if opcoes else None
    except Exception:
        return None


def _local(tag: Any) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


# Os tipos de propriedade geométrica do GML (`<nome>PropertyType`): os do
# catálogo de fontes (`fontes_vault.GEOMETRIAS`) mais os 3D, os compostos e os
# genéricos de um esquema app-schema/INSPIRE.
_GEOMETRIAS_GML = frozenset({
    "Point", "MultiPoint", "Curve", "MultiCurve", "LineString", "MultiLineString",
    "Surface", "MultiSurface", "Polygon", "MultiPolygon", "Geometry", "MultiGeometry",
    "Solid", "MultiSolid", "CompositeCurve", "CompositeSurface", "CompositeSolid",
    "GeometricPrimitive", "GeometricAggregate", "GeometricComplex",
})
_ESPACO_GML = "http://www.opengis.net/gml"


def _geometria_do_xsd(raiz) -> str | None:
    """O primeiro atributo geométrico de um DescribeFeatureType.

    Geometria é um `element` de uma `sequence` cujo tipo é uma propriedade
    geométrica do GML (Point, Curve, MultiCurve, Surface, Geometry…). A lista
    fixa do owslib não conhece Curve/MultiCurve, e toda camada de linhas do
    DNIT ou da ANA ficaria sem geometria. Terminar em `PropertyType` não
    basta: num esquema INSPIRE ou app-schema o primeiro assim é `inspireId`
    (IdentifierPropertyType) ou uma associação (gml:FeaturePropertyType) — e o
    BBOX iria com o nome errado. Só filhos de `sequence`: o elemento de topo de
    uma camada chamada `landProperty` tem o tipo `ns:landPropertyType`.
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
                continue  # um `ns:PointPropertyType` do próprio esquema não é GML
            return nome
    return None


def _coluna_de_geometria(wfs, type_name: str) -> str:
    """O nome da geometria da camada, pelo DescribeFeatureType.

    Rede, timeout e 5xx sobem como vieram (a consulta é retentada); só uma
    resposta lida SEM geometria vira erro de configuração.
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
    """Um GetFeature montado pelo owslib, com parâmetros a mais."""
    from owslib.util import openURL

    base = wfs.getGETGetFeatureRequest(typename=[type_name], **montagem)
    url = _com_parametros(base, extras)
    return openURL(url, None, "Get", timeout=wfs.timeout, headers=wfs.headers, auth=wfs.auth).read()


def _texto(corpo: Any) -> str:
    return corpo.decode("utf-8", errors="replace") if isinstance(corpo, bytes) else str(corpo)


def _quantas_casam(wfs, type_name: str, cql: str | None, auth: "AutenticacaoWFS | None" = None) -> int:
    """Quantas feições casam (com o filtro, se houver).

    Primeiro `resultType=hits` (com `count=1`, para um servidor que ignore o
    hits não despejar a camada); sem `numberMatched` numérico (o "unknown" do
    GeoServer que pula a contagem), uma feição de amostra em GeoJSON decide.
    Sem nem uma coisa nem outra o nó NÃO segue: um servidor que ignora o
    CQL_FILTER e não fala GeoJSON devolveria a camada inteira em GML como se
    fosse o recorte — e o GDAL a leria sem reclamar.
    """
    extras = {"CQL_FILTER": cql} if cql else {}
    corpo = _pedir(wfs, type_name, {"resultType": "hits", **extras}, maxfeatures=1)
    achado = _NUMBER_MATCHED_RE.search(_texto(corpo[:4096]))
    if achado:
        return int(achado.group(1))
    corpo = _texto(_pedir(wfs, type_name, extras, maxfeatures=1, outputFormat="application/json"))
    if "<ows:ExceptionReport" in corpo or "<ServiceException" in corpo:
        # O servidor recusou a amostra (não serve GeoJSON, por exemplo): a
        # voz dele, classificada como em qualquer página.
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
    """Recusa servidor que ignora o CQL_FILTER (devolveria a camada inteira).

    `CQL_FILTER=EXCLUDE` casa zero feições em quem o aplica: uma contagem
    positiva prova que o parâmetro foi ignorado. Zero também é o que uma
    camada VAZIA dá em qualquer servidor — a prova de que o servidor aplica o
    CQL só se completa quando a camada mostra uma feição: a primeira página
    filtrada que vier com algo (ver `_fetch_wfs_features`, que então chama
    `_registrar_cql_verificado`). Devolve se essa confirmação está pendente.

    Sem uma segunda contagem, da camada inteira, para isso: um `count(*)`
    numa tabela de milhões de linhas (o caso para que o CQL existe) estourava
    o timeout e derrubava a execução cujo filtro já estava provado.
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
    """O servidor de `url` aplica o CQL: vale pelo TTL do cache, por servidor."""
    agora = time.monotonic()
    with _caps_lock:
        for chave in [k for k, v in _cql_verificado.items() if v <= agora]:
            del _cql_verificado[chave]
        if len(_cql_verificado) >= _CQL_VERIFICADO_MAX:
            _cql_verificado.pop(min(_cql_verificado, key=_cql_verificado.get), None)
        _cql_verificado[url] = agora + _CAPS_TTL_S


def _url_da_pagina(wfs, kwargs: dict, cql: str) -> str:
    """A URL de uma página do GetFeature, com o CQL_FILTER no fim."""
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
    """`tamanho` é o que o nó mediu; `None` quando foi o servidor web que recusou."""
    medida = f"{tamanho} caracteres na URL; " if tamanho else ""
    return ValueError(
        f"O filtro CQL é longo demais para a requisição ({medida}o limite prático é "
        f"{_MAX_URL_COM_CQL}). Encurte o filtro — troque listas longas de valores por um "
        f"intervalo ou por um recorte espacial."
    )


def _getfeature_com_cql(wfs, kwargs: dict, cql: str):
    """O `getfeature` do owslib, com o CQL_FILTER que ele não sabe mandar."""
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
    """Conecta a um endpoint WFS com paginação automática e retorna GeoDataFrame."""
    wfs = _wfs_client(url, "2.0.0", timeout, auth=auth)

    # Valida se a camada existe no servidor. Se veio do cache e a camada não
    # está lá, refaz o GetCapabilities UMA vez antes de acusar: uma camada
    # publicada há menos de uma hora não pode virar falso "não encontrada".
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

    # Com filtro CQL: o servidor precisa aplicá-lo, e o bbox (se houver) entra
    # no próprio filtro — ver o bloco "Filtro CQL" acima.
    cql = cql_filter
    confirmar_o_cql = False
    if cql:
        # Antes de qualquer pedido: um filtro que não cabe na URL falha já, e
        # não no meio da paginação.
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

    # Paginação automática: busca em blocos até atingir maxFeatures
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
        # owslib faz `','.join(sortby)`, então precisa ser lista. Vai em toda
        # página (inclusive a 1ª): o GeoServer exige o SORTBY sempre que houver
        # startIndex, e o laço já manda startindex desde o começo.
        if sort_by:
            kwargs["sortby"] = sort_by

        response = _getfeature_com_cql(wfs, kwargs, cql) if cql else wfs.getfeature(**kwargs)
        raw = response.read()

        # Detecta erro XML do servidor WFS
        raw_str = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        if "<ows:ExceptionReport" in raw_str or "<ServiceException" in raw_str:
            raise _erro_do_servidor(raw_str, type_name, bool(cql), auth)

        # `ler_geodataframe` recusa uma resposta que seja um documento OGR VRT
        # (servidor WFS malicioso) antes de o GDAL abri-la — ver leitura_geo.py.
        chunk = ler_geodataframe(io.BytesIO(raw if isinstance(raw, bytes) else raw.encode()))

        if chunk.empty:
            break
        if confirmar_o_cql:
            # A camada tem feição e o EXCLUDE casou zero: o servidor aplica o CQL.
            _registrar_cql_verificado(url)
            confirmar_o_cql = False

        all_chunks.append(chunk)
        total_fetched += len(chunk)
        start_index += len(chunk)

        # Se recebeu menos que o solicitado, não há mais páginas
        if len(chunk) < count:
            break

    if not all_chunks:
        return gpd.GeoDataFrame()

    # pd.concat de GeoDataFrames retorna GeoDataFrame; gpd.concat NAO existe —
    # o codigo anterior crashava em resultados WFS paginados (>1 chunk).
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
    """Wrapper com retry e backoff exponencial.

    Com credencial, toda mensagem que sai daqui passa por `sem_segredo` e sem a
    cadeia de exceções: o erro original (o do requests, com a URL e a chave)
    iria inteiro no traceback, que chega à tela e ao banco. E, enquanto a busca
    roda, nenhum log do processo leva a chave — nem o DEBUG do owslib e do
    urllib3, que escrevem a URL de cada pedido (ver `segredos_vivos`).
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
            raise  # Erros de configuração — não faz sentido retries
        except excecoes_do_servico as exc:
            # A voz do servidor (a mensagem crua é o XML inteiro): requisição
            # errada — filtro inválido, parâmetro recusado — não é retentada;
            # o resto (banco lento, pool esgotado) segue o retry de sempre.
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
            # Cadeia TLS inválida não se resolve sozinha: retentar só faz o
            # usuário esperar o backoff inteiro para ver o mesmo erro, e a
            # mensagem crua do urllib3 não diz o que fazer.
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
            # O nó lê uma FONTE EXTERNA deste tipo: o catálogo de fontes responde
            # por ele (`search_sources(kind="wfs")`), a validação confere a URL
            # contra o catálogo e `describe_node` orienta a não inventar url/typeName.
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
                    # INJETADA pelo servidor a partir de `credential_id` (o mesmo
                    # contrato do HttpRequest). Declarada porque `validate()`
                    # reconstrói os parâmetros a partir desta lista e descartaria
                    # o que não estivesse aqui; a UI a esconde pelo nome.
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

        # SSRF: a URL vem do usuario e o owslib a busca direto (GetCapabilities/
        # GetFeature), diferente de HttpRequest/SendWebhook que passam por
        # safe_httpx_request com IP-pinning. Sem esta checagem, um WFS apontando
        # para 169.254.169.254 (metadata cloud), MinIO/Redis/Postgres internos ou
        # step-ca seria requisitado, e a mensagem de erro devolveria o corpo ao
        # painel (SSRF cego -> parcialmente cego). validate_url_ssrf resolve o
        # host e recusa IP interno/privado/loopback/link-local/reservado.
        # Residual (follow-up): owslib faz a propria resolucao e segue redirect,
        # entao resta uma janela de TOCTOU/DNS-rebinding — o ideal e um transporte
        # com IP-pinning no owslib. Roda em thread: getaddrinfo bloquearia o loop.
        await asyncio.to_thread(validate_url_ssrf, url)

        # bbox: aceita do campo manual OU do input de outro node (ex: ComputeBoundingBox.bbox_string)
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

        # Metadados de saída
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
