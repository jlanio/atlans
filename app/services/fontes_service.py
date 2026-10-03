# app/services/fontes_service.py
"""
The catalog of pre-mapped sources — the only module that knows how to probe a WFS,
store a source and search for it.

Four clients read from here, and none of them talks to the network or the table on
its own: the MCP tools (`app/mcp/tools/fontes.py`), validation
(`conferir_fontes_da_definicao`, no network), the results consumer
(`aprender_de_execucao`) and the startup/verification loop
(`importar_pasta`, `verify_endpoint`).

Decisions that apply to everything here:

- **Every probe goes through `safe_httpx_request`** (IP pinning, no redirect,
  byte ceiling, timeout). owslib's `get_schema` does `openURL` with none of
  that and so is NOT used on the server — the DescribeFeatureType XSD is
  read by our own parser, with the same geometry table.
- **The row's identity is `chave`** = sha256(workspace | type | normalized
  url | type_name). The URL is normalized by the SAME function that
  `WFSNode` applies in `execute()` (`normalize_ows_endpoint_url`), so what
  the catalog stores is what the node actually uses, and validation checks a node in
  one query.
- **Search is by normalized text** (`busca`, no accents, lowercase), with
  `LIKE` per term and synonym expansion; 25 k rows × ~300 B is a
  millisecond scan. A trigram index is left for when it grows.
- **Verification is per ENDPOINT, not per layer**: one GetCapabilities marks every
  row for that URL at once (77 requests for the whole seed). The
  per-layer DescribeFeatureType only happens on demand (probe/register).
- **Writes do not commit**, except the two batches that manage their own
  transaction (`importar_pasta`, `verify_endpoint`). Whoever calls a tool
  commits at the end, as with the other MCP tools.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import quote, urlencode, urlparse

import httpx
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidSourceError
from app.core.utils.busca import contem
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.fonte_de_dados import DataSource
from app.services import fontes_vault
from flow.utils import segredos_vivos
from flow.utils.credencial_wfs import AutenticacaoWFS, secret_forms
from flow.utils.geo_helpers import normalize_ows_endpoint_url, safe_httpx_request, validate_url_ssrf

logger = get_logger("app.services.fontes")

KIND_WFS = "wfs"
NO_WFS = "WFS"
WFS_VERSIONS = ("1.0.0", "1.1.0", "2.0.0")
DEFAULT_VERSION = "2.0.0"
ORIGENS = ("vault", "aprendida", "manual")
# `origem` is never downgraded: a Vault source that an execution uses remains
# a Vault source. The order is the strength of each origin.
_ORIGIN_STRENGTH = {"aprendida": 0, "manual": 1, "vault": 2}
# The same for the schema: the live DescribeFeatureType beats the Vault table,
# which beats what an execution saw (column names only), which beats nothing.
_SCHEMA_STRENGTH = {None: 0, "run": 1, "vault": 2, "describe_feature_type": 3}

URL_MAX = 2048
# IBGE's GetCapabilities has 9,759 FeatureTypes — well above the interactive
# route's 10 MB. Here the ceiling is server-to-server.
TIMEOUT_CAPABILITIES_S = 30.0
MAX_CAPABILITIES_BYTES = 32 * 1024 * 1024
TIMEOUT_DESCRIBE_S = 15.0
MAX_DESCRIBE_BYTES = 2 * 1024 * 1024
SEARCH_LIMIT = 20
IMPORT_BATCH = 500

# The properties the WFS node declares TODAY. `version` stays in the catalog but
# does not go into the snippet the model pastes while the node does not declare it —
# pasting it would yield `undeclared_property` in validation. `cqlFilter` is left out
# on purpose: it belongs to the QUESTION, not the source — learned from an execution,
# its `uf = 'MT'` would stick to the snippet of every later one.
WFS_NODE_PROPERTIES = ("url", "typeName", "maxFeatures", "bbox", "crs", "sortBy", "timeout", "retries")

# Synonyms that apply even without `_sinonimos.md` in the Vault: the themes the
# product's phrases use. Keys and values are normalized on use.
DEFAULT_SYNONYMS: dict[str, set[str]] = {
    "focos de calor": {"queimadas", "incendio", "fogo", "hotspot", "focos"},
    "queimadas": {"focos de calor", "incendio", "fogo"},
    "terras indigenas": {"terra indigena", "ti", "indigena", "aldeia"},
    "terra indigena": {"terras indigenas", "ti", "indigena"},
    "unidades de conservacao": {"unidade de conservacao", "uc", "parque", "reserva"},
    "unidade de conservacao": {"uc", "parque", "reserva"},
    "municipios": {"municipio", "municipal", "limite municipal"},
    "hidrografia": {"rio", "rios", "drenagem"},
    "desmatamento": {"prodes", "deter", "supressao"},
    "escolas": {"escola", "educacao"},
}
_extra_synonyms: dict[str, set[str]] = {}

_CREDENTIAL_IN_URL = re.compile(r"://[^/@\s]+:[^/@\s]+@")
_SEPARATORS = re.compile(r"[\s,;/|]+")


# ── Erros ─────────────────────────────────────────────────────────────────────


class ProbeError(Exception):
    """A probe (GetCapabilities/DescribeFeatureType) that did not succeed.

    `codigo` is closed — `timeout | http_status | ssrf | tamanho | tls |
    sem_camadas | camada_inexistente | xml | rede` — so the route can map it to an
    HTTP status and the tool to a `reason`, without anyone reading the message.
    """

    def __init__(self, codigo: str, mensagem: str, *, status: int | None = None, candidates: list[str] | None = None):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status = status
        self.candidates = candidates or []

    def as_http(self) -> tuple[int, str]:
        """(status, detail) in the shape `GET /nodes/wfs/layers` has always returned."""
        if self.codigo == "timeout":
            return 504, "Timeout ao conectar ao servidor WFS."
        if self.codigo == "http_status":
            return 502, f"Servidor WFS retornou HTTP {self.status}."
        if self.codigo == "ssrf":
            return 403, f"URL bloqueada por segurança: {self.mensagem}"
        if self.codigo in ("tamanho", "tls"):
            return 502, self.mensagem
        if self.codigo in ("sem_camadas", "camada_inexistente"):
            return 404, self.mensagem
        # Generic so as not to leak internals (see V36 in nodes_router).
        return 502, "Erro ao conectar ao servidor WFS."


# ── Texto ─────────────────────────────────────────────────────────────────────


def normalize_text(texto: Any) -> str:
    """Lowercase, no accents, collapsed spaces — the form of `busca` and of the query."""
    if texto is None:
        return ""
    unaccented = unicodedata.normalize("NFKD", str(texto))
    plano = "".join(c for c in unaccented if not unicodedata.combining(c)).casefold()
    return " ".join(plano.split())


def normalize_url(url: Any) -> str:
    """The URL as the WFS node uses it — or `InvalidSourceError`.

    Pure on purpose (no DNS): the SSRF check happens at fetch time,
    in `safe_httpx_request`. Here we refuse what could never be a source:
    a scheme other than http(s), size, and embedded credentials (which would go to the
    database and to the snippet the model pastes).
    """
    texto = str(url or "").strip()
    if texto.startswith("<") and texto.endswith(">"):
        texto = texto[1:-1].strip()
    if not texto:
        raise InvalidSourceError("Informe a URL do serviço.")
    if len(texto) > URL_MAX:
        raise InvalidSourceError(f"URL excede o limite de {URL_MAX} caracteres.")
    partes = urlparse(texto)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        raise InvalidSourceError("URL inválida. Use http:// ou https://.")
    if _CREDENTIAL_IN_URL.search(texto) or "@" in partes.netloc:
        raise InvalidSourceError("A URL não pode carregar usuário e senha.")
    return normalize_ows_endpoint_url(texto)


def normalize_version(versao: Any) -> str:
    texto = str(versao or "").strip()
    return texto if texto in WFS_VERSIONS else DEFAULT_VERSION


def source_key(workspace_id: str | None, tipo: str, url: str, type_name: str | None) -> str:
    bruto = "\n".join((workspace_id or "", tipo, url, type_name or ""))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def search_text(
    *,
    instituicao: str | None,
    grupo: str | None,
    titulo: str | None,
    type_name: str | None,
    url: str | None,
    descricao: str | None,
    temas: Iterable[str] | None,
    esquema: Mapping[str, Any] | None,
) -> str:
    """The text that `LIKE` scans: everything that describes the source, normalized."""
    partes: list[str] = [instituicao or "", grupo or "", titulo or "", type_name or ""]
    if type_name:
        # `Funai:tis_poligonais` also answers to "tis poligonais".
        partes.append(re.sub(r"[:_]+", " ", type_name))
    if url:
        partes.append(urlparse(url).hostname or "")
    partes.append(descricao or "")
    partes.extend(str(t) for t in (temas or []))
    if isinstance(esquema, Mapping):
        for coluna in esquema.get("columns") or []:
            nome = coluna.get("name") if isinstance(coluna, Mapping) else coluna
            if nome:
                partes.append(str(nome))
    return normalize_text(" ".join(p for p in partes if p))


def set_synonyms(mapa: Mapping[str, Iterable[str]] | None) -> None:
    """Replaces the synonyms coming from the Vault (`_sinonimos.md`); the defaults remain."""
    global _extra_synonyms
    _extra_synonyms = {
        normalize_text(k): {normalize_text(v) for v in vs if normalize_text(v)}
        for k, vs in (mapa or {}).items()
        if normalize_text(k)
    }


def synonyms_of(termo: str) -> set[str]:
    chave = normalize_text(termo)
    saida: set[str] = set()
    for mapa in (DEFAULT_SYNONYMS, _extra_synonyms):
        for k, vs in mapa.items():
            kn = normalize_text(k)
            if kn == chave:
                saida.update(normalize_text(v) for v in vs)
            elif chave in {normalize_text(v) for v in vs}:
                saida.add(kn)
    saida.discard(chave)
    return {s for s in saida if s}


def query_terms(query: str | None) -> list[set[str]]:
    """Each query term with its variants (itself + synonyms).

    The whole query also counts as a term when it has more than one
    word: "focos de calor" (hotspots) must match the expression, not just
    "focos", "de" and "calor" separately. One-letter words and connectives
    are left out.
    """
    texto = normalize_text(query)
    if not texto:
        return []
    frase = {texto} | synonyms_of(texto)
    palavras = [p for p in _SEPARATORS.split(texto) if len(p) > 1 and p not in _CONNECTIVES]
    if len(palavras) <= 1:
        return [frase | (synonyms_of(palavras[0]) if palavras else set())]
    # Phrase OR (each word with its synonyms): rows with the whole phrase
    # match right away; rows with only the words match via the AND below.
    return [frase | {p} | synonyms_of(p) for p in palavras]


_CONNECTIVES = {"de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas", "e", "a", "o", "as", "os", "um", "uma", "por", "para", "com"}


# ── Capabilities e DescribeFeatureType ────────────────────────────────────────


@dataclass(frozen=True)
class ServiceLayer:
    name: str
    title: str | None = None
    abstract: str | None = None
    keywords: tuple[str, ...] = ()
    crs: str | None = None
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class Capabilities:
    version: str | None
    layers: tuple[ServiceLayer, ...]

    def by_name(self) -> dict[str, ServiceLayer]:
        return {c.name: c for c in self.layers}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _as_text(no: ET.Element | None) -> str | None:
    if no is None or no.text is None:
        return None
    texto = " ".join(no.text.split())
    return texto or None


def _child(no: ET.Element, *nomes: str) -> ET.Element | None:
    for filho in no:
        if _local(filho.tag) in nomes:
            return filho
    return None


def _parse_xml(texto: str | bytes) -> ET.Element:
    """`fromstring` with the protection the server needs: no DTD/entities.

    `defusedxml` is not a dependency; what an external DTD or a recursive
    entity would do here is blow up memory, and no legitimate GetCapabilities
    carries one. Rejecting the prefix is cheaper and safer than parsing.
    """
    cabeca = texto[:4096] if isinstance(texto, str) else texto[:4096].decode("utf-8", errors="replace")
    if "<!DOCTYPE" in cabeca or "<!ENTITY" in cabeca:
        raise ProbeError("xml", "Resposta XML com DTD ou entidades — recusada por segurança.")
    try:
        return ET.fromstring(texto)
    except ET.ParseError as exc:
        raise ProbeError("xml", f"Resposta não é um XML válido: {exc}") from exc


def _normalized_crs(valor: str | None) -> str | None:
    if not valor:
        return None
    achado = re.search(r"(?:EPSG|epsg)(?:::|:|/)(\d+)", valor)
    if achado:
        return f"EPSG:{achado.group(1)}"
    return valor.strip() or None


def _bbox(no: ET.Element) -> tuple[float, float, float, float] | None:
    """`WGS84BoundingBox` (2.0/1.1) or `LatLongBoundingBox` (1.0)."""
    try:
        if _local(no.tag) == "LatLongBoundingBox":
            return tuple(float(no.attrib[k]) for k in ("minx", "miny", "maxx", "maxy"))  # type: ignore[return-value]
        baixo, alto = _child(no, "LowerCorner"), _child(no, "UpperCorner")
        if baixo is None or alto is None:
            return None
        x0, y0 = (float(v) for v in (baixo.text or "").split()[:2])
        x1, y1 = (float(v) for v in (alto.text or "").split()[:2])
        return (x0, y0, x1, y1)
    except (KeyError, ValueError, TypeError):
        return None


def parsear_capabilities(xml: str | bytes) -> Capabilities:
    """The layers of a GetCapabilities, in any version (1.0.0, 1.1.0, 2.0.0)."""
    raiz = _parse_xml(xml)
    if _local(raiz.tag) in ("ExceptionReport", "ServiceExceptionReport"):
        texto = " ".join(t.strip() for t in raiz.itertext() if t.strip())[:300]
        raise ProbeError("http_status", f"O servidor respondeu com uma exceção WFS: {texto}", status=200)
    camadas: list[ServiceLayer] = []
    for no in raiz.iter():
        if _local(no.tag) != "FeatureType":
            continue
        nome = _as_text(_child(no, "Name"))
        if not nome:
            continue
        palavras: list[str] = []
        for kw in no.iter():
            if _local(kw.tag) == "Keyword" and _as_text(kw):
                palavras.append(_as_text(kw))  # type: ignore[arg-type]
            elif _local(kw.tag) == "Keywords" and _as_text(kw) and not list(kw):
                palavras.extend(p.strip() for p in (_as_text(kw) or "").split(",") if p.strip())
        crs_no = _child(no, "DefaultCRS", "DefaultSRS", "SRS")
        caixa = _child(no, "WGS84BoundingBox", "LatLongBoundingBox")
        camadas.append(ServiceLayer(
            name=nome,
            title=_as_text(_child(no, "Title")),
            abstract=_as_text(_child(no, "Abstract")),
            keywords=tuple(dict.fromkeys(palavras)),
            crs=_normalized_crs(_as_text(crs_no)),
            bbox=_bbox(caixa) if caixa is not None else None,
        ))
    return Capabilities(version=raiz.attrib.get("version"), layers=tuple(camadas))


def parsear_describe_feature_type(xml: str | bytes) -> dict:
    """`{columns, geometry_column, geometry_type, columns_source}` from an XSD.

    Reads the `element`s inside `sequence`: that is where GeoServer (and MapServer)
    list a FeatureType's attributes; the top-level `element`, which declares the
    type itself, is left out because it is never inside a sequence.
    """
    raiz = _parse_xml(xml)
    colunas: list[dict] = []
    geometry_col: str | None = None
    geometry_type: str | None = None
    for seq in raiz.iter():
        if _local(seq.tag) != "sequence":
            continue
        for el in seq:
            if _local(el.tag) != "element":
                continue
            nome, xsd_type = el.attrib.get("name"), el.attrib.get("type")
            if not nome or not xsd_type:
                continue
            local = xsd_type.split(":", 1)[1] if ":" in xsd_type else xsd_type
            if xsd_type.startswith("gml:") or local.endswith("PropertyType"):
                tipo = fontes_vault.GEOMETRIES.get(local, "Geometry")
                if geometry_col is None:
                    geometry_col, geometry_type = nome, tipo
            else:
                tipo = local
            colunas.append({
                "name": nome,
                "type": tipo,
                "xsd": xsd_type,
                "nullable": el.attrib.get("nillable", "true").lower() != "false",
            })
    return {
        "columns": colunas,
        "geometry_column": geometry_col,
        "geometry_type": geometry_type,
        "columns_source": "describe_feature_type",
    }


async def _fetch_text(url: str, *, timeout: float, max_bytes: int, auth: AutenticacaoWFS | None = None) -> str:
    """Safe GET; every failure becomes a `ProbeError` with a closed code.

    With `auth`, the request goes out signed: the authkey key in the URL or in a
    header, or Basic. No message from here repeats the URL — only the host, the
    status or the exception name —, so the key does not go back to the requester.
    """
    try:
        await asyncio.to_thread(validate_url_ssrf, url)
    except ValueError as exc:
        raise ProbeError("ssrf", str(exc)) from exc
    endereco, cabecalhos = url, None
    if auth is not None:
        # Concatenated, and not via httpx's `params`: it REPLACES the URL's query
        # with the one it receives — the GetCapabilities would go out without `service` and `request`.
        if auth.parametros():
            endereco = f"{url}{'&' if '?' in url else '?'}{urlencode(auth.parametros(), quote_via=quote)}"
        cabecalhos = auth.cabecalhos() or None
    try:
        # httpx logs the URL of every request (INFO): with the key in it, only `***`.
        with segredos_vivos.in_use(*secret_forms(auth)):
            resposta = await safe_httpx_request(
                "GET", endereco, timeout=timeout, max_response_bytes=max_bytes, headers=cabecalhos,
            )
        resposta.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ProbeError("timeout", "Timeout ao conectar ao servidor WFS.") from exc
    except httpx.HTTPStatusError as exc:
        raise ProbeError(
            "http_status", f"Servidor WFS retornou HTTP {exc.response.status_code}.",
            status=exc.response.status_code,
        ) from exc
    except ValueError as exc:
        # `safe_httpx_request` raises ValueError for SSRF (already covered above,
        # but rebinding between the two resolutions lands here) and for a response
        # above the ceiling.
        codigo = "tamanho" if "excedeu" in str(exc).lower() else "ssrf"
        raise ProbeError(codigo, str(exc)) from exc
    except RuntimeError as exc:
        # Invalid TLS chain, already turned into an actionable message by the helper.
        raise ProbeError("tls", str(exc)) from exc
    except ProbeError:
        raise
    except Exception as exc:  # network, DNS, connection refused
        raise ProbeError("rede", f"Erro ao conectar ao servidor WFS: {exc.__class__.__name__}") from exc
    return resposta.text


async def obter_capabilities(
    url: str, version: str = DEFAULT_VERSION, *, auth: AutenticacaoWFS | None = None,
) -> Capabilities:
    versao = normalize_version(version)
    xml = await _fetch_text(
        f"{url}?service=WFS&request=GetCapabilities&version={versao}",
        timeout=TIMEOUT_CAPABILITIES_S, max_bytes=MAX_CAPABILITIES_BYTES, auth=auth,
    )
    return await asyncio.to_thread(parsear_capabilities, xml)


async def listar_camadas_wfs(
    url: str, version: str = DEFAULT_VERSION, *, auth: AutenticacaoWFS | None = None,
) -> list[dict]:
    """`[{name, title}]` sorted by title — the body of `GET /nodes/wfs/layers`.

    `auth` is the node's credential: a GeoServer hides protected layers from
    anonymous users, and without it the editor would only offer the public ones.
    """
    caps = await obter_capabilities(url, version, auth=auth)
    if not caps.layers:
        raise ProbeError("sem_camadas", "Nenhuma camada encontrada no servidor WFS.")
    itens = [{"name": c.name, "title": c.title or c.name} for c in caps.layers]
    return sorted(itens, key=lambda item: item["title"])


async def describe_wfs_layer(url: str, type_name: str, version: str = DEFAULT_VERSION) -> dict:
    versao = normalize_version(version)
    parametro = "typeNames" if versao == "2.0.0" else "typeName"
    xml = await _fetch_text(
        f"{url}?service=WFS&request=DescribeFeatureType&version={versao}&{parametro}={type_name}",
        timeout=TIMEOUT_DESCRIBE_S, max_bytes=MAX_DESCRIBE_BYTES,
    )
    return await asyncio.to_thread(parsear_describe_feature_type, xml)


@dataclass
class Probe:
    url: str
    version: str
    capabilities: Capabilities
    camada: ServiceLayer | None = None
    esquema: dict | None = None


def _find_layer(caps: Capabilities, type_name: str) -> ServiceLayer | None:
    by_name = caps.by_name()
    if type_name in by_name:
        return by_name[type_name]
    # Without the namespace prefix, when it is unique.
    local = type_name.split(":", 1)[-1]
    candidates = [c for c in caps.layers if c.name.split(":", 1)[-1] == local]
    return candidates[0] if len(candidates) == 1 else None


async def sondar_wfs(url: str, type_name: str | None = None, version: str = DEFAULT_VERSION) -> Probe:
    """GetCapabilities and, with `type_name`, the layer and its DescribeFeatureType."""
    caps = await obter_capabilities(url, version)
    if not caps.layers:
        raise ProbeError("sem_camadas", "Nenhuma camada encontrada no servidor WFS.")
    sondagem = Probe(url=url, version=normalize_version(version), capabilities=caps)
    if not type_name:
        return sondagem
    camada = _find_layer(caps, type_name.strip())
    if camada is None:
        nomes = [c.name for c in caps.layers[:20]]
        raise ProbeError(
            "camada_inexistente",
            f"Camada '{type_name}' não encontrada no servidor WFS. Camadas disponíveis: "
            + ", ".join(nomes) + ("…" if len(caps.layers) > 20 else ""),
            candidates=nomes,
        )
    sondagem.camada = camada
    esquema = await describe_wfs_layer(url, camada.name, version)
    esquema["crs"] = camada.crs
    esquema["bbox"] = list(camada.bbox) if camada.bbox else None
    sondagem.esquema = esquema
    return sondagem


# ── Esquema ───────────────────────────────────────────────────────────────────


def merge_schema(atual: Mapping[str, Any] | None, novo: Mapping[str, Any] | None) -> dict | None:
    """The most complete schema, without losing what only the other one had.

    The COLUMNS come from the strongest source (`describe_feature_type` > `vault` >
    `run`); `crs`, `bbox` and `feature_count` come from the most recent one that has
    them, because only an execution or a GetCapabilities knows them.
    """
    if not atual and not novo:
        return None
    atual = dict(atual or {})
    novo = dict(novo or {})
    current_strength = _SCHEMA_STRENGTH.get(atual.get("columns_source") if atual.get("columns") else None, 0)
    new_strength = _SCHEMA_STRENGTH.get(novo.get("columns_source") if novo.get("columns") else None, 0)
    base, extra = (novo, atual) if new_strength >= current_strength and novo.get("columns") else (atual, novo)
    saida = dict(base)
    for chave in ("columns", "columns_source", "geometry_column", "geometry_type"):
        if not saida.get(chave) and extra.get(chave):
            saida[chave] = extra[chave]
    for chave in ("crs", "bbox", "feature_count"):
        if novo.get(chave) is not None:
            saida[chave] = novo[chave]
        elif atual.get(chave) is not None:
            saida[chave] = atual[chave]
    return saida


# ── Leitura ───────────────────────────────────────────────────────────────────


def _in_scope(workspace_ids: Iterable[str] | None):
    ids = [w for w in (workspace_ids or []) if w]
    if ids:
        return or_(DataSource.workspace_id.is_(None), DataSource.workspace_id.in_(ids))
    return DataSource.workspace_id.is_(None)


def _like(termo: str):
    # `busca` is already stored normalized (no accents, lowercase): plain LIKE.
    return contem(DataSource.busca, termo, ignore_case=False)


async def buscar(
    db: AsyncSession,
    workspace_ids: Iterable[str] | None,
    *,
    query: str | None = None,
    kind: str | None = None,
    institution: str | None = None,
    state: str | None = None,
    limit: int = SEARCH_LIMIT,
    offset: int = 0,
) -> tuple[list[DataSource], int]:
    """The sources within reach (platform + workspaces in scope) that match the query."""
    filtros = [DataSource.deleted_at.is_(None), _in_scope(workspace_ids)]
    if kind:
        filtros.append(DataSource.tipo == str(kind).strip().lower())
    if institution:
        # Exact (as in the catalog) OR normalized in the search text — whoever
        # types "ministerio da saude" finds "Ministério da Saúde".
        filtros.append(or_(DataSource.instituicao == str(institution).strip(), _like(normalize_text(institution))))
    if state:
        filtros.append(DataSource.estado == str(state).strip().lower())
    for variantes in query_terms(query):
        filtros.append(or_(*[_like(v) for v in sorted(variantes)]))
    condicao = and_(*filtros)
    total = (await db.execute(select(func.count()).select_from(DataSource).where(condicao))).scalar_one()
    linhas = await db.execute(
        select(DataSource)
        .where(condicao)
        .order_by(
            case((DataSource.estado == "ok", 0), else_=1),
            DataSource.prioridade,
            DataSource.usos.desc(),
            DataSource.titulo,
        )
        .offset(max(0, int(offset)))
        .limit(max(1, min(int(limit), 100)))
    )
    return list(linhas.scalars().all()), int(total)


async def obter(db: AsyncSession, source_id: str, workspace_ids: Iterable[str] | None) -> DataSource | None:
    linha = await db.execute(
        select(DataSource).where(
            DataSource.id_hash == str(source_id).strip(),
            DataSource.deleted_at.is_(None),
            _in_scope(workspace_ids),
        )
    )
    return linha.scalar_one_or_none()


async def get_by_key(db: AsyncSession, chave: str) -> DataSource | None:
    linha = await db.execute(select(DataSource).where(DataSource.chave == chave))
    return linha.scalar_one_or_none()


def node_snippet(fonte: DataSource) -> dict:
    """The node ready to paste into a definition — only the properties the node declares."""
    propriedades = {
        chave: valor
        for chave, valor in (fonte.propriedades or {}).items()
        if chave in WFS_NODE_PROPERTIES and valor not in (None, "")
    }
    propriedades.setdefault("url", fonte.url)
    if fonte.type_name:
        propriedades.setdefault("typeName", fonte.type_name)
    return {"name": fonte.no or NO_WFS, "type": "datasource", "properties": propriedades}


# ── Escrita ───────────────────────────────────────────────────────────────────


def _recompute_search(fonte: DataSource) -> None:
    fonte.busca = search_text(
        instituicao=fonte.instituicao, grupo=fonte.grupo, titulo=fonte.titulo,
        type_name=fonte.type_name, url=fonte.url, descricao=fonte.descricao,
        temas=fonte.temas or [], esquema=fonte.esquema,
    )


def _merged_themes(atuais: Sequence[str] | None, novos: Iterable[str] | None) -> list[str]:
    vistos: dict[str, str] = {}
    for tema in list(atuais or []) + list(novos or []):
        texto = str(tema).strip()
        if texto and normalize_text(texto) not in vistos:
            vistos[normalize_text(texto)] = texto
    return list(vistos.values())


async def upsert_source(
    db: AsyncSession,
    *,
    workspace_id: str | None,
    tipo: str,
    url: str,
    type_name: str | None,
    propriedades: Mapping[str, Any],
    origem: str,
    estado: str | None = None,
    esquema: Mapping[str, Any] | None = None,
    titulo: str | None = None,
    descricao: str | None = None,
    temas: Iterable[str] | None = None,
    dicas: str | None = None,
    instituicao: str | None = None,
    grupo: str | None = None,
    prioridade: int | None = None,
    created_by: str | None = None,
    verificada_em: datetime | None = None,
    ultimo_erro: str | None = None,
    vault_hash: str | None = None,
    count_usage: bool = False,
    no: str = NO_WFS,
) -> tuple[DataSource, str]:
    """Creates or updates the source for `chave`; returns `(fonte, "created" | "updated")`.

    Merge rules — what a weaker origin does NOT do:
    - does not resurrect a deleted row (`deleted_at`) when it is `aprendida`;
    - does not downgrade `origem` (vault > manual > aprendida);
    - does not erase a `titulo`/`descricao`/`dicas` someone wrote: it only fills blanks;
    - does not replace the schema with a weaker one (`merge_schema`).
    No commit: the caller decides the transaction.
    """
    assert origem in ORIGENS, origem
    url = normalize_url(url)
    type_name = (type_name or "").strip() or None
    chave = source_key(workspace_id, tipo, url, type_name)
    agora = utc_now_naive()
    fonte = await get_by_key(db, chave)
    props = {k: v for k, v in dict(propriedades or {}).items() if v not in (None, "")}
    props["url"], props["typeName"] = url, type_name

    if fonte is None:
        fonte = DataSource(
            workspace_id=workspace_id, tipo=tipo, no=no, url=url, type_name=type_name, chave=chave,
            propriedades=props, instituicao=instituicao, grupo=grupo, titulo=titulo, descricao=descricao,
            temas=_merged_themes([], temas), esquema=dict(esquema) if esquema else None, dicas=dicas,
            prioridade=prioridade or 2, origem=origem, estado=estado or "nao_verificada",
            verificada_em=verificada_em, ultimo_erro=ultimo_erro, vault_hash=vault_hash,
            usos=1 if count_usage else 0, usada_em=agora if count_usage else None,
            created_by=created_by, created_at=agora, updated_at=agora,
        )
        _recompute_search(fonte)
        db.add(fonte)
        await db.flush()
        return fonte, "created"

    if fonte.deleted_at is not None:
        if origem == "aprendida":
            # The person deleted it; an execution does not undo that.
            return fonte, "deleted"
        fonte.deleted_at = None

    if _ORIGIN_STRENGTH[origem] >= _ORIGIN_STRENGTH.get(fonte.origem, 0):
        fonte.origem = origem
    # Properties: the new ones on top, without erasing what only the catalog knew
    # (an execution does not bring `sortBy`; the Vault did).
    fonte.propriedades = {**(fonte.propriedades or {}), **props}
    fonte.no = no or fonte.no
    if titulo and not fonte.titulo:
        fonte.titulo = titulo
    if descricao and not fonte.descricao:
        fonte.descricao = descricao
    if dicas and not fonte.dicas:
        fonte.dicas = dicas
    if instituicao and not fonte.instituicao:
        fonte.instituicao = instituicao
    if grupo and not fonte.grupo:
        fonte.grupo = grupo
    if prioridade:
        fonte.prioridade = prioridade
    fonte.temas = _merged_themes(fonte.temas, temas)
    fonte.esquema = merge_schema(fonte.esquema, esquema)
    if estado:
        fonte.estado = estado
        fonte.ultimo_erro = ultimo_erro if estado != "ok" else None
    if verificada_em:
        fonte.verificada_em = verificada_em
    if vault_hash:
        fonte.vault_hash = vault_hash
    if count_usage:
        fonte.usos = int(fonte.usos or 0) + 1
        fonte.usada_em = agora
    fonte.updated_at = agora
    _recompute_search(fonte)
    await db.flush()
    return fonte, "updated"


# ── Validation (no network) ───────────────────────────────────────────────────


def _node_properties(no: Mapping[str, Any]) -> Mapping[str, Any]:
    for chave in ("parameters", "properties"):
        valor = no.get(chave)
        if isinstance(valor, Mapping):
            return valor
    dados = no.get("data")
    if isinstance(dados, Mapping) and isinstance(dados.get("properties"), Mapping):
        return dados["properties"]
    return {}


def _has_any_credential(no: Mapping[str, Any]) -> bool:
    """`credential_id` in ANY of the places where a node stores properties.

    `_node_properties` reads `parameters`/`properties` first; the resolver and the
    executor read `data.properties` first (`node_props`). With the credential in one and
    not the other, the execution went out authenticated and the layer went into the catalog.
    """
    dados = no.get("data")
    candidatos = (no.get("parameters"), no.get("properties"), dados.get("properties") if isinstance(dados, Mapping) else None)
    return any(isinstance(p, Mapping) and str(p.get("credential_id") or "").strip() for p in candidatos)


def source_nodes(nodes: Iterable[Mapping[str, Any]], descriptors: Mapping[str, Mapping[str, Any]] | None = None):
    """The nodes that read an external source and the (url, typeName) of each."""
    for no in nodes:
        if not isinstance(no, Mapping):
            continue
        nome = str(no.get("name") or "")
        descriptor = (descriptors or {}).get(nome) or {}
        kind = descriptor.get("source_kind") if descriptors is not None else (KIND_WFS if nome == NO_WFS else None)
        if kind != KIND_WFS:
            continue
        props = _node_properties(no)
        try:
            url = normalize_url(props.get("url"))
        except InvalidSourceError:
            continue
        type_name = str(props.get("typeName") or "").strip()
        if not type_name:
            continue
        yield no, url, type_name


async def conferir_fontes_da_definicao(
    db: AsyncSession,
    nodes: Iterable[Mapping[str, Any]],
    descriptors: Mapping[str, Mapping[str, Any]],
    workspace_id: str,
) -> list[dict]:
    """`unknown_source`/`failing_source` warnings for the definition's WFS nodes.

    Fails OPEN: any error here becomes a log line and an empty list — validation
    cannot depend on the catalog to respond.
    """
    try:
        alvos = list(source_nodes(nodes, descriptors))
        if not alvos:
            return []
        chaves: dict[str, tuple[Mapping[str, Any], str, str]] = {}
        for no, url, type_name in alvos:
            for ws in (workspace_id, None):
                chaves.setdefault(source_key(ws, KIND_WFS, url, type_name), (no, url, type_name))
        linhas = await db.execute(
            select(DataSource).where(DataSource.chave.in_(list(chaves)), DataSource.deleted_at.is_(None))
        )
        by_key = {f.chave: f for f in linhas.scalars().all()}
        avisos: list[dict] = []
        for no, url, type_name in alvos:
            found = by_key.get(source_key(workspace_id, KIND_WFS, url, type_name)) or by_key.get(
                source_key(None, KIND_WFS, url, type_name)
            )
            node_id = no.get("id")
            if found is None:
                avisos.append({
                    "code": "unknown_source", "severity": "warning", "node_id": node_id, "edge": None,
                    "message": (
                        f"nó 'WFS' (id={node_id}) aponta para url+typeName que não estão no catálogo do "
                        "workspace nem da plataforma. Use search_sources para uma fonte já mapeada, ou "
                        "probe_source / register_source para sondar e registrar esta antes de executar."
                    ),
                })
            elif found.estado == "falhando":
                quando = found.verificada_em.isoformat() if found.verificada_em else "sem data"
                motivo = (found.ultimo_erro or "sem detalhe")[:160]
                avisos.append({
                    "code": "failing_source", "severity": "warning", "node_id": node_id, "edge": None,
                    "message": (
                        f"nó 'WFS' (id={node_id}) usa a fonte {found.id_hash} que falhou na última "
                        f"verificação ({quando}): {motivo}. Confira com probe_source antes de executar."
                    ),
                })
        return avisos
    except Exception as exc:  # the catalog never brings down validation
        logger.warning("Catálogo de fontes indisponível na validação: %s", exc)
        return []


# ── Aprendizado (consumer) ────────────────────────────────────────────────────


def _run_schema(nid: str, stats: Mapping[str, Any], *, sliced: bool = False) -> dict | None:
    """What the execution saw of the layer.

    `sliced` (the node had a CQL or bbox filter): the extent and the count are
    those of the SLICE, not of the layer — they are not learned. The columns and the CRS
    still apply.
    """
    no_stats = stats.get(nid) if isinstance(stats.get(nid), Mapping) else {}
    metricas = ((stats.get("__metrics__") or {}).get("nodes") or {}).get(nid) or {}
    espacial = metricas.get("spatial") if isinstance(metricas, Mapping) else None
    espacial = espacial if isinstance(espacial, Mapping) else {}
    columns_by_output = no_stats.get("output_columns") if isinstance(no_stats.get("output_columns"), Mapping) else {}
    nomes = columns_by_output.get("output") if isinstance(columns_by_output, Mapping) else None
    esquema: dict = {}
    if isinstance(nomes, list) and nomes:
        esquema["columns"] = [{"name": str(n), "type": None, "xsd": None, "nullable": True} for n in nomes]
        esquema["columns_source"] = "run"
    for chave in ("crs",) if sliced else ("crs", "bbox", "feature_count"):
        if espacial.get(chave) is not None:
            esquema[chave] = espacial[chave]
    if not sliced and esquema.get("feature_count") is None and no_stats.get("output_features") is not None:
        esquema["feature_count"] = no_stats.get("output_features")
    return esquema or None


def _produces_bbox_string(node_name: str) -> bool:
    """Does the node declare `bbox_string` among its outputs (ComputeBoundingBox, another
    WFS)? On an edge without keys everything it produces goes into the next node."""
    try:
        from flow.registry import NODE_REGISTRY

        cls = NODE_REGISTRY.get(node_name)
        saidas = cls.description().get("outputs") or [] if cls is not None else []
    except Exception:  # registry unavailable or broken descriptor
        saidas = []
    return any(isinstance(s, Mapping) and s.get("name") == "bbox_string" for s in saidas)


def _bbox_from_edge(nid: str, definition: Mapping[str, Any]) -> bool:
    """Does the node receive the bbox from ANOTHER node? The WFS node reads
    `inputs["bbox_string"]` when the `bbox` field is empty (the ComputeBoundingBox → WFS
    case), and then the execution is also a slice: the extent and the count are not the layer's.

    The edge semantics are the executor's (flow/executor/edge_resolver.py): with
    `from_key`/`to_key`, the input port is `to_key or from_key`; without
    both, everything the origin produces goes in."""
    nomes = {
        str(n.get("id")): str(n.get("name") or "")
        for n in definition.get("nodes") or [] if isinstance(n, Mapping)
    }
    for aresta in definition.get("edges") or []:
        if not isinstance(aresta, Mapping) or str(aresta.get("target")) != nid:
            continue
        de, para = aresta.get("from_key") or None, aresta.get("to_key") or None
        if (para or de) == "bbox_string":
            return True
        if de is None and para is None and _produces_bbox_string(nomes.get(str(aresta.get("source")), "")):
            return True
    return False


async def aprender_de_execucao(
    db: AsyncSession, run: Any, stats: Mapping[str, Any], definition: Mapping[str, Any], *, first_close: bool
) -> int:
    """Registers (or updates) the sources that this execution's WFS nodes read successfully."""
    if not isinstance(definition, Mapping) or not isinstance(stats, Mapping):
        return 0
    quando = getattr(run, "end_time", None) or utc_now_naive()
    if getattr(quando, "tzinfo", None) is not None:
        quando = quando.replace(tzinfo=None)
    learned = 0
    for no, url, type_name in source_nodes(definition.get("nodes") or [], None):
        nid = str(no.get("id") or "")
        no_stats = stats.get(nid)
        if not isinstance(no_stats, Mapping) or no_stats.get("status") != "completed":
            continue
        props = _node_properties(no)
        # A layer read WITH a credential is protected: it does not go into the catalog — the
        # daily verification would probe it without the key and mark it as failing,
        # and the ready snippet would offer it to people without access.
        if _has_any_credential(no):
            continue
        sliced = (
            any(str(props.get(k) or "").strip() for k in ("cqlFilter", "bbox"))
            or _bbox_from_edge(nid, definition)
        )
        _, desfecho = await upsert_source(
            db,
            workspace_id=getattr(run, "workspace_id", None),
            tipo=KIND_WFS, url=url, type_name=type_name,
            propriedades={k: props.get(k) for k in WFS_NODE_PROPERTIES if props.get(k) not in (None, "")},
            origem="aprendida", estado="ok", esquema=_run_schema(nid, stats, sliced=sliced),
            titulo=None, verificada_em=quando, count_usage=first_close,
        )
        if desfecho != "deleted":
            learned += 1
    return learned


# ── Verification ──────────────────────────────────────────────────────────────


@dataclass
class CheckSummary:
    url: str
    ok: int = 0
    falhando: int = 0
    erro: str | None = None


async def endpoints_to_verify(
    db: AsyncSession, *, stale_for: int | None = None
) -> list[tuple[str, str]]:
    """The catalog's distinct URLs (with each one's WFS version).

    `stale_for` (seconds): only URLs with some layer never
    verified or verified longer ago than that — the mode of the initial
    verification at startup, which does not redo what the previous round already did.
    """
    consulta = select(DataSource.url, DataSource.propriedades).where(
        DataSource.deleted_at.is_(None), DataSource.tipo == KIND_WFS
    )
    if stale_for is not None:
        limite = utc_now_naive() - timedelta(seconds=max(0, stale_for))
        consulta = consulta.where(
            or_(DataSource.verificada_em.is_(None), DataSource.verificada_em < limite)
        )
    linhas = await db.execute(consulta)
    vistos: dict[str, str] = {}
    for url, props in linhas.all():
        versao = normalize_version((props or {}).get("version"))
        vistos.setdefault(url, versao)
    return sorted(vistos.items())


async def verify_endpoint(db: AsyncSession, url: str, version: str = DEFAULT_VERSION) -> CheckSummary:
    """ONE GetCapabilities marks every row for that URL: `ok` (with crs/bbox
    from the capabilities) or `falhando`. Endpoint down: all `falhando`.
    Commits at the end — it is a batch."""
    resumo = CheckSummary(url=url)
    linhas = await db.execute(
        select(DataSource).where(
            DataSource.url == url, DataSource.tipo == KIND_WFS, DataSource.deleted_at.is_(None)
        )
    )
    fontes = list(linhas.scalars().all())
    if not fontes:
        return resumo
    agora = utc_now_naive()
    try:
        caps = await obter_capabilities(url, version)
    except ProbeError as exc:
        resumo.erro = exc.mensagem
        for fonte in fontes:
            fonte.estado, fonte.ultimo_erro, fonte.verificada_em, fonte.updated_at = "falhando", exc.mensagem[:500], agora, agora
            resumo.falhando += 1
        await db.commit()
        return resumo

    for fonte in fontes:
        camada = _find_layer(caps, fonte.type_name or "")
        if camada is None:
            fonte.estado = "falhando"
            fonte.ultimo_erro = "camada não consta no GetCapabilities"
            resumo.falhando += 1
        else:
            fonte.estado, fonte.ultimo_erro = "ok", None
            fonte.esquema = merge_schema(
                fonte.esquema,
                {"crs": camada.crs, "bbox": list(camada.bbox) if camada.bbox else None},
            )
            if camada.title and not fonte.titulo:
                fonte.titulo = camada.title
            if camada.abstract and not fonte.descricao:
                fonte.descricao = camada.abstract[:2000]
            if camada.keywords:
                fonte.temas = _merged_themes(fonte.temas, camada.keywords)
            _recompute_search(fonte)
            resumo.ok += 1
        fonte.verificada_em, fonte.updated_at = agora, agora
    await db.commit()
    return resumo


# ── Vault import ──────────────────────────────────────────────────────────────


@dataclass
class ResumoDaImportacao:
    criadas: int = 0
    atualizadas: int = 0
    iguais: int = 0
    removidas: int = 0
    ignoradas: dict[str, int] = field(default_factory=dict)
    erros: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        ign = ", ".join(f"{n} {m}" for m, n in sorted(self.ignoradas.items())) or "nenhuma"
        return (
            f"{self.criadas} criadas, {self.atualizadas} atualizadas, {self.iguais} iguais, "
            f"{self.removidas} removidas; pastas ignoradas: {ign}"
            + (f"; erros: {len(self.erros)}" if self.erros else "")
        )


# The text fields the database limits, and what to do when the Vault brings something
# larger. The distinction is not a matter of taste:
#
# - **display** (`instituicao`, `grupo`): cutting loses the tail of a label. The
#   source keeps working and keeps being found by search.
# - **functional** (`type_name`, `url`): cutting creates a source that points to
#   a layer that does not exist — the `type_name` goes literally into the WFS query,
#   and the `chave` derives from it. Such a record is SKIPPED, with an error in the summary.
#
# `titulo` is not here because it became TEXT (scripts/init_schema.sql; the
# historical migration a3c81d7e2f46 made the change): it is
# written by people and any fixed limit would overflow again in the next catalog.
_FUNCTIONAL_COLUMNS = ("type_name", "url")


def _column_limit(coluna: str) -> int | None:
    """The COLUMN's limit, read from the model.

    Read, not copied: a constant repeated here would diverge the day the
    column changed, and the divergence would show up as the same overflow this
    guard exists to prevent.
    """
    return getattr(DataSource.__table__.c[coluna].type, "length", None)


def _truncate(valor: str | None, limite: int | None) -> str | None:
    if valor is None or limite is None or len(valor) <= limite:
        return valor
    return valor[: max(1, limite - 1)] + "…"


def _long_functional_field(registro: fontes_vault.RegistroDoVault) -> str | None:
    """The error message when a field that can NOT be cut does not fit."""
    for coluna in _FUNCTIONAL_COLUMNS:
        limite = _column_limit(coluna)
        valor = getattr(registro, coluna, None)
        if limite is not None and valor is not None and len(str(valor)) > limite:
            return (
                f"`{coluna}` tem {len(str(valor))} caracteres e a coluna aceita {limite}. "
                "Cortá-lo apontaria para uma camada que não existe, então o registro foi "
                "pulado."
            )
    return None


def _apply_record(fonte: DataSource, registro: fontes_vault.RegistroDoVault, agora: datetime) -> None:
    """The fields the Vault dictates on a `vault` row. Preserves what the catalog
    learned on its own (state, verification, uses) and what a future UI edits
    on top of blanks."""
    fonte.propriedades = {**(fonte.propriedades or {}), **registro.propriedades}
    # Cut at the COLUMN's limit: they are labels, and a label without its tail still
    # works. Without this, one of them over the limit brought down the whole batch — and
    # with it all the rest of the catalog.
    fonte.instituicao = _truncate(registro.instituicao, _column_limit("instituicao"))
    fonte.grupo = _truncate(registro.grupo, _column_limit("grupo"))
    fonte.titulo = registro.titulo
    fonte.descricao = registro.descricao
    fonte.temas = _merged_themes(registro.temas, [])
    fonte.dicas = registro.dicas
    fonte.prioridade = registro.prioridade
    fonte.esquema = merge_schema(fonte.esquema, registro.esquema)
    fonte.vault_hash = registro.vault_hash
    fonte.updated_at = agora
    _recompute_search(fonte)


async def importar_pasta(db: AsyncSession, caminho: str | Path, *, workspace_id: str | None = None) -> ResumoDaImportacao:
    """Imports `<caminho>/<INSTITUIÇÃO>/` as `vault` sources (platform-wide by
    default). Idempotent by `chave` + `vault_hash`: reimporting the same folder is
    one query and zero writes. Commits per batch."""
    resumo = ResumoDaImportacao()
    raiz = Path(caminho)
    if not raiz.is_dir():
        resumo.erros.append(f"pasta não encontrada: {raiz}")
        return resumo
    set_synonyms(await asyncio.to_thread(fontes_vault.synonyms_of, raiz))
    itens = await asyncio.to_thread(lambda: list(fontes_vault.read_folder(raiz)))

    linhas = await db.execute(
        select(DataSource.id, DataSource.chave, DataSource.vault_hash).where(
            DataSource.origem == "vault",
            DataSource.workspace_id.is_(None) if workspace_id is None else DataSource.workspace_id == workspace_id,
        )
    )
    existentes: dict[str, tuple[int, str | None]] = {chave: (id_, h) for id_, chave, h in linhas.all()}
    vistas: set[str] = set()
    agora = utc_now_naive()
    pendentes = 0

    for item in itens:
        if isinstance(item, fontes_vault.Skipped):
            resumo.ignoradas[item.motivo] = resumo.ignoradas.get(item.motivo, 0) + 1
            continue
        try:
            url = normalize_url(item.url)
        except InvalidSourceError as exc:
            resumo.erros.append(f"{item.instituicao}/{item.type_name}: {exc.detail}")
            continue
        # BEFORE any computation with the record: the `chave` derives from the
        # `type_name`, and a value the database will refuse must not reach
        # `db.add`. The commit is per BATCH, so a row that overflows takes along
        # its 499 neighbors and aborts the rest of the import — that is how 75% of the
        # catalog vanished in production with nothing but an ERROR in the log.
        longo = _long_functional_field(item)
        if longo:
            resumo.erros.append(f"{item.instituicao}/{item.type_name}: {longo}")
            continue
        chave = source_key(workspace_id, KIND_WFS, url, item.type_name)
        if chave in vistas:
            continue  # a mesma camada listada duas vezes na nota
        vistas.add(chave)
        existente = existentes.get(chave)
        if existente and existente[1] == item.vault_hash:
            resumo.iguais += 1
            continue
        if existente:
            fonte = await db.get(DataSource, existente[0])
            if fonte is None:
                continue
            fonte.deleted_at = None
            _apply_record(fonte, item, agora)
            resumo.atualizadas += 1
        else:
            fonte = DataSource(
                workspace_id=workspace_id, tipo=KIND_WFS, no=NO_WFS, url=url, type_name=item.type_name,
                chave=chave, propriedades={}, origem="vault", estado="nao_verificada",
                created_at=agora, updated_at=agora,
            )
            _apply_record(fonte, item, agora)
            db.add(fonte)
            resumo.criadas += 1
        pendentes += 1
        if pendentes >= IMPORT_BATCH:
            await db.commit()
            pendentes = 0

    # The Vault is the source of truth for the `vault` origin: what vanished from the folder
    # leaves the catalog (soft delete — the row and the history stay).
    vanished = [id_ for chave, (id_, _) in existentes.items() if chave not in vistas]
    for id_ in vanished:
        fonte = await db.get(DataSource, id_)
        if fonte is not None and fonte.deleted_at is None:
            fonte.deleted_at, fonte.updated_at = agora, agora
            resumo.removidas += 1
    await db.commit()
    return resumo
