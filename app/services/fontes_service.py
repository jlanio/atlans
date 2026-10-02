# app/services/fontes_service.py
"""
O catálogo de fontes pré-mapeadas — o único módulo que sabe sondar um WFS,
gravar uma fonte e procurá-la.

Quatro clientes leem daqui, e nenhum deles fala com a rede ou com a tabela por
conta própria: as tools MCP (`app/mcp/tools/fontes.py`), a validação
(`conferir_fontes_da_definicao`, sem rede), o consumidor de resultados
(`aprender_de_execucao`) e o laço de arranque/verificação
(`importar_pasta`, `verificar_endpoint`).

Decisões que valem para tudo aqui:

- **Toda sondagem passa por `safe_httpx_request`** (pin de IP, sem redirect,
  teto de bytes, timeout). O `get_schema` do owslib faz `openURL` sem nada
  disso e por isso NÃO é usado no servidor — o XSD do DescribeFeatureType é
  lido por um parser próprio, com a mesma tabela de geometrias.
- **A identidade da linha é `chave`** = sha256(workspace | tipo | url
  normalizada | type_name). A URL é normalizada pela MESMA função que o
  `WFSNode` aplica em `execute()` (`normalize_ows_endpoint_url`), então o que
  o catálogo guarda é o que o nó de fato usa, e a validação confere um nó em
  uma consulta.
- **A busca é por texto normalizado** (`busca`, sem acento, minúsculas), com
  `LIKE` por termo e expansão por sinônimos; 25 k linhas × ~300 B é uma
  varredura de milissegundos. Um índice trigram fica para quando crescer.
- **Verificar é por ENDPOINT, não por camada**: um GetCapabilities marca todas
  as linhas daquela URL de uma vez (77 pedidos para a semente inteira). O
  DescribeFeatureType, por camada, só acontece sob demanda (sondar/registrar).
- **Escrita não faz commit**, salvo os dois lotes que gerenciam a própria
  transação (`importar_pasta`, `verificar_endpoint`). Quem chama uma tool
  commita no fim, como nas demais tools do MCP.
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

from app.core.exceptions import FonteInvalidaError
from app.core.utils.busca import contem
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.fonte_de_dados import FonteDeDados
from app.services import fontes_vault
from flow.utils import segredos_vivos
from flow.utils.credencial_wfs import AutenticacaoWFS, formas_do_segredo
from flow.utils.geo_helpers import normalize_ows_endpoint_url, safe_httpx_request, validate_url_ssrf

logger = get_logger("app.services.fontes")

TIPO_WFS = "wfs"
NO_WFS = "WFS"
VERSOES_WFS = ("1.0.0", "1.1.0", "2.0.0")
VERSAO_PADRAO = "2.0.0"
ORIGENS = ("vault", "aprendida", "manual")
# `origem` nunca é rebaixada: uma fonte do Vault que uma execução usa continua
# sendo do Vault. A ordem é a força de cada origem.
_FORCA_DA_ORIGEM = {"aprendida": 0, "manual": 1, "vault": 2}
# O mesmo para o esquema: o DescribeFeatureType ao vivo vence a tabela do Vault,
# que vence o que uma execução viu (só nomes de coluna), que vence o vazio.
_FORCA_DO_ESQUEMA = {None: 0, "run": 1, "vault": 2, "describe_feature_type": 3}

URL_MAX = 2048
# O GetCapabilities do IBGE tem 9.759 FeatureTypes — bem acima dos 10 MB da rota
# interativa. Aqui o teto é do servidor para o servidor.
TIMEOUT_CAPABILITIES_S = 30.0
MAX_CAPABILITIES_BYTES = 32 * 1024 * 1024
TIMEOUT_DESCRIBE_S = 15.0
MAX_DESCRIBE_BYTES = 2 * 1024 * 1024
LIMITE_DE_BUSCA = 20
LOTE_DE_IMPORTACAO = 500

# As propriedades que o nó WFS declara HOJE. `version` fica no catálogo mas não
# entra no trecho que o modelo cola enquanto o nó não a declarar — colá-la
# renderia `undeclared_property` na validação. `cqlFilter` fica de fora de
# propósito: é da PERGUNTA, não da fonte — aprendido de uma execução, o
# `uf = 'MT'` dela grudaria no trecho de todas as próximas.
PROPRIEDADES_DO_NO_WFS = ("url", "typeName", "maxFeatures", "bbox", "crs", "sortBy", "timeout", "retries")

# Sinônimos que valem mesmo sem `_sinonimos.md` no Vault: os temas que as
# frases do produto usam. Chaves e valores são normalizados no uso.
SINONIMOS_PADRAO: dict[str, set[str]] = {
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
_sinonimos_extra: dict[str, set[str]] = {}

_CREDENCIAL_NA_URL = re.compile(r"://[^/@\s]+:[^/@\s]+@")
_SEPARADORES = re.compile(r"[\s,;/|]+")


# ── Erros ─────────────────────────────────────────────────────────────────────


class SondagemError(Exception):
    """Uma sondagem (GetCapabilities/DescribeFeatureType) que não deu certo.

    `codigo` é fechado — `timeout | http_status | ssrf | tamanho | tls |
    sem_camadas | camada_inexistente | xml | rede` — para a rota traduzir em
    status HTTP e a tool em `reason`, sem ninguém ler a mensagem.
    """

    def __init__(self, codigo: str, mensagem: str, *, status: int | None = None, candidatas: list[str] | None = None):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status = status
        self.candidatas = candidatas or []

    def como_http(self) -> tuple[int, str]:
        """(status, detail) na forma que `GET /nodes/wfs/layers` sempre respondeu."""
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
        # Genérico para não vazar internals (ver V36 em nodes_router).
        return 502, "Erro ao conectar ao servidor WFS."


# ── Texto ─────────────────────────────────────────────────────────────────────


def normalizar_texto(texto: Any) -> str:
    """Minúsculas, sem acento, espaços colapsados — a forma de `busca` e da consulta."""
    if texto is None:
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    plano = "".join(c for c in sem_acento if not unicodedata.combining(c)).casefold()
    return " ".join(plano.split())


def normalizar_url(url: Any) -> str:
    """A URL como o nó WFS a usa — ou `FonteInvalidaError`.

    Pura de propósito (sem DNS): a checagem de SSRF acontece na hora de buscar,
    em `safe_httpx_request`. Aqui se recusa o que nunca poderia ser fonte:
    scheme fora de http(s), tamanho e credencial embutida (que iria para o
    banco e para o trecho que o modelo cola).
    """
    texto = str(url or "").strip()
    if texto.startswith("<") and texto.endswith(">"):
        texto = texto[1:-1].strip()
    if not texto:
        raise FonteInvalidaError("Informe a URL do serviço.")
    if len(texto) > URL_MAX:
        raise FonteInvalidaError(f"URL excede o limite de {URL_MAX} caracteres.")
    partes = urlparse(texto)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        raise FonteInvalidaError("URL inválida. Use http:// ou https://.")
    if _CREDENCIAL_NA_URL.search(texto) or "@" in partes.netloc:
        raise FonteInvalidaError("A URL não pode carregar usuário e senha.")
    return normalize_ows_endpoint_url(texto)


def normalizar_versao(versao: Any) -> str:
    texto = str(versao or "").strip()
    return texto if texto in VERSOES_WFS else VERSAO_PADRAO


def chave_da_fonte(workspace_id: str | None, tipo: str, url: str, type_name: str | None) -> str:
    bruto = "\n".join((workspace_id or "", tipo, url, type_name or ""))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def texto_de_busca(
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
    """O texto que `LIKE` varre: tudo o que descreve a fonte, normalizado."""
    partes: list[str] = [instituicao or "", grupo or "", titulo or "", type_name or ""]
    if type_name:
        # `Funai:tis_poligonais` também responde por "tis poligonais".
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
    return normalizar_texto(" ".join(p for p in partes if p))


def definir_sinonimos(mapa: Mapping[str, Iterable[str]] | None) -> None:
    """Troca os sinônimos vindos do Vault (`_sinonimos.md`); os padrão continuam."""
    global _sinonimos_extra
    _sinonimos_extra = {
        normalizar_texto(k): {normalizar_texto(v) for v in vs if normalizar_texto(v)}
        for k, vs in (mapa or {}).items()
        if normalizar_texto(k)
    }


def sinonimos_de(termo: str) -> set[str]:
    chave = normalizar_texto(termo)
    saida: set[str] = set()
    for mapa in (SINONIMOS_PADRAO, _sinonimos_extra):
        for k, vs in mapa.items():
            kn = normalizar_texto(k)
            if kn == chave:
                saida.update(normalizar_texto(v) for v in vs)
            elif chave in {normalizar_texto(v) for v in vs}:
                saida.add(kn)
    saida.discard(chave)
    return {s for s in saida if s}


def termos_da_consulta(query: str | None) -> list[set[str]]:
    """Cada termo da consulta com as suas variantes (o próprio + sinônimos).

    A consulta inteira também conta como um termo quando tem mais de uma
    palavra: "focos de calor" precisa casar com a expressão, não só com
    "focos", "de" e "calor" separados. Palavras de uma letra e conectivos
    ficam de fora.
    """
    texto = normalizar_texto(query)
    if not texto:
        return []
    frase = {texto} | sinonimos_de(texto)
    palavras = [p for p in _SEPARADORES.split(texto) if len(p) > 1 and p not in _CONECTIVOS]
    if len(palavras) <= 1:
        return [frase | (sinonimos_de(palavras[0]) if palavras else set())]
    # Frase OU (cada palavra com os sinônimos dela): quem tem a frase inteira
    # casa de primeira; quem só tem as palavras casa pelo AND abaixo.
    return [frase | {p} | sinonimos_de(p) for p in palavras]


_CONECTIVOS = {"de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas", "e", "a", "o", "as", "os", "um", "uma", "por", "para", "com"}


# ── Capabilities e DescribeFeatureType ────────────────────────────────────────


@dataclass(frozen=True)
class CamadaDoServico:
    name: str
    title: str | None = None
    abstract: str | None = None
    keywords: tuple[str, ...] = ()
    crs: str | None = None
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class Capabilities:
    version: str | None
    layers: tuple[CamadaDoServico, ...]

    def por_nome(self) -> dict[str, CamadaDoServico]:
        return {c.name: c for c in self.layers}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _texto(no: ET.Element | None) -> str | None:
    if no is None or no.text is None:
        return None
    texto = " ".join(no.text.split())
    return texto or None


def _filho(no: ET.Element, *nomes: str) -> ET.Element | None:
    for filho in no:
        if _local(filho.tag) in nomes:
            return filho
    return None


def _parse_xml(texto: str | bytes) -> ET.Element:
    """`fromstring` com a proteção que o servidor precisa: sem DTD/entidades.

    `defusedxml` não é dependência; o que um DTD externo ou uma entidade
    recursiva faria aqui é estourar memória, e nenhum GetCapabilities legítimo
    traz um. Rejeitar o prefixo é mais barato e mais seguro que parsear.
    """
    cabeca = texto[:4096] if isinstance(texto, str) else texto[:4096].decode("utf-8", errors="replace")
    if "<!DOCTYPE" in cabeca or "<!ENTITY" in cabeca:
        raise SondagemError("xml", "Resposta XML com DTD ou entidades — recusada por segurança.")
    try:
        return ET.fromstring(texto)
    except ET.ParseError as exc:
        raise SondagemError("xml", f"Resposta não é um XML válido: {exc}") from exc


def _crs_normalizado(valor: str | None) -> str | None:
    if not valor:
        return None
    achado = re.search(r"(?:EPSG|epsg)(?:::|:|/)(\d+)", valor)
    if achado:
        return f"EPSG:{achado.group(1)}"
    return valor.strip() or None


def _bbox(no: ET.Element) -> tuple[float, float, float, float] | None:
    """`WGS84BoundingBox` (2.0/1.1) ou `LatLongBoundingBox` (1.0)."""
    try:
        if _local(no.tag) == "LatLongBoundingBox":
            return tuple(float(no.attrib[k]) for k in ("minx", "miny", "maxx", "maxy"))  # type: ignore[return-value]
        baixo, alto = _filho(no, "LowerCorner"), _filho(no, "UpperCorner")
        if baixo is None or alto is None:
            return None
        x0, y0 = (float(v) for v in (baixo.text or "").split()[:2])
        x1, y1 = (float(v) for v in (alto.text or "").split()[:2])
        return (x0, y0, x1, y1)
    except (KeyError, ValueError, TypeError):
        return None


def parsear_capabilities(xml: str | bytes) -> Capabilities:
    """As camadas de um GetCapabilities, em qualquer versão (1.0.0, 1.1.0, 2.0.0)."""
    raiz = _parse_xml(xml)
    if _local(raiz.tag) in ("ExceptionReport", "ServiceExceptionReport"):
        texto = " ".join(t.strip() for t in raiz.itertext() if t.strip())[:300]
        raise SondagemError("http_status", f"O servidor respondeu com uma exceção WFS: {texto}", status=200)
    camadas: list[CamadaDoServico] = []
    for no in raiz.iter():
        if _local(no.tag) != "FeatureType":
            continue
        nome = _texto(_filho(no, "Name"))
        if not nome:
            continue
        palavras: list[str] = []
        for kw in no.iter():
            if _local(kw.tag) == "Keyword" and _texto(kw):
                palavras.append(_texto(kw))  # type: ignore[arg-type]
            elif _local(kw.tag) == "Keywords" and _texto(kw) and not list(kw):
                palavras.extend(p.strip() for p in (_texto(kw) or "").split(",") if p.strip())
        crs_no = _filho(no, "DefaultCRS", "DefaultSRS", "SRS")
        caixa = _filho(no, "WGS84BoundingBox", "LatLongBoundingBox")
        camadas.append(CamadaDoServico(
            name=nome,
            title=_texto(_filho(no, "Title")),
            abstract=_texto(_filho(no, "Abstract")),
            keywords=tuple(dict.fromkeys(palavras)),
            crs=_crs_normalizado(_texto(crs_no)),
            bbox=_bbox(caixa) if caixa is not None else None,
        ))
    return Capabilities(version=raiz.attrib.get("version"), layers=tuple(camadas))


def parsear_describe_feature_type(xml: str | bytes) -> dict:
    """`{columns, geometry_column, geometry_type, columns_source}` de um XSD.

    Lê os `element` dentro de `sequence`: é onde o GeoServer (e o MapServer)
    listam os atributos de um FeatureType; o `element` de topo, que declara o
    próprio tipo, fica de fora porque nunca está numa sequence.
    """
    raiz = _parse_xml(xml)
    colunas: list[dict] = []
    geometria_col: str | None = None
    geometria_tipo: str | None = None
    for seq in raiz.iter():
        if _local(seq.tag) != "sequence":
            continue
        for el in seq:
            if _local(el.tag) != "element":
                continue
            nome, tipo_xsd = el.attrib.get("name"), el.attrib.get("type")
            if not nome or not tipo_xsd:
                continue
            local = tipo_xsd.split(":", 1)[1] if ":" in tipo_xsd else tipo_xsd
            if tipo_xsd.startswith("gml:") or local.endswith("PropertyType"):
                tipo = fontes_vault.GEOMETRIAS.get(local, "Geometry")
                if geometria_col is None:
                    geometria_col, geometria_tipo = nome, tipo
            else:
                tipo = local
            colunas.append({
                "name": nome,
                "type": tipo,
                "xsd": tipo_xsd,
                "nullable": el.attrib.get("nillable", "true").lower() != "false",
            })
    return {
        "columns": colunas,
        "geometry_column": geometria_col,
        "geometry_type": geometria_tipo,
        "columns_source": "describe_feature_type",
    }


async def _buscar(url: str, *, timeout: float, max_bytes: int, auth: AutenticacaoWFS | None = None) -> str:
    """GET seguro; toda falha vira `SondagemError` com um código fechado.

    Com `auth`, o pedido sai assinado: a chave do authkey na URL ou num
    cabeçalho, ou o Basic. Nenhuma mensagem daqui repete a URL — só o host, o
    status ou o nome da exceção —, então a chave não volta a quem pediu.
    """
    try:
        await asyncio.to_thread(validate_url_ssrf, url)
    except ValueError as exc:
        raise SondagemError("ssrf", str(exc)) from exc
    endereco, cabecalhos = url, None
    if auth is not None:
        # Concatenada, e não pelo `params` do httpx: ele TROCA a query da URL
        # pela que recebe — o GetCapabilities sairia sem `service` e `request`.
        if auth.parametros():
            endereco = f"{url}{'&' if '?' in url else '?'}{urlencode(auth.parametros(), quote_via=quote)}"
        cabecalhos = auth.cabecalhos() or None
    try:
        # O httpx loga a URL de cada pedido (INFO): com a chave nela, só `***`.
        with segredos_vivos.em_uso(*formas_do_segredo(auth)):
            resposta = await safe_httpx_request(
                "GET", endereco, timeout=timeout, max_response_bytes=max_bytes, headers=cabecalhos,
            )
        resposta.raise_for_status()
    except httpx.TimeoutException as exc:
        raise SondagemError("timeout", "Timeout ao conectar ao servidor WFS.") from exc
    except httpx.HTTPStatusError as exc:
        raise SondagemError(
            "http_status", f"Servidor WFS retornou HTTP {exc.response.status_code}.",
            status=exc.response.status_code,
        ) from exc
    except ValueError as exc:
        # `safe_httpx_request` levanta ValueError para SSRF (já coberto acima,
        # mas o rebinding entre as duas resoluções cai aqui) e para resposta
        # acima do teto.
        codigo = "tamanho" if "excedeu" in str(exc).lower() else "ssrf"
        raise SondagemError(codigo, str(exc)) from exc
    except RuntimeError as exc:
        # Cadeia TLS inválida, já traduzida em mensagem acionável pelo helper.
        raise SondagemError("tls", str(exc)) from exc
    except SondagemError:
        raise
    except Exception as exc:  # rede, DNS, conexão recusada
        raise SondagemError("rede", f"Erro ao conectar ao servidor WFS: {exc.__class__.__name__}") from exc
    return resposta.text


async def obter_capabilities(
    url: str, version: str = VERSAO_PADRAO, *, auth: AutenticacaoWFS | None = None,
) -> Capabilities:
    versao = normalizar_versao(version)
    xml = await _buscar(
        f"{url}?service=WFS&request=GetCapabilities&version={versao}",
        timeout=TIMEOUT_CAPABILITIES_S, max_bytes=MAX_CAPABILITIES_BYTES, auth=auth,
    )
    return await asyncio.to_thread(parsear_capabilities, xml)


async def listar_camadas_wfs(
    url: str, version: str = VERSAO_PADRAO, *, auth: AutenticacaoWFS | None = None,
) -> list[dict]:
    """`[{name, title}]` ordenado por título — o corpo de `GET /nodes/wfs/layers`.

    `auth` é a credencial do nó: um GeoServer esconde do anônimo as camadas
    protegidas, e sem ela o editor só ofereceria as públicas.
    """
    caps = await obter_capabilities(url, version, auth=auth)
    if not caps.layers:
        raise SondagemError("sem_camadas", "Nenhuma camada encontrada no servidor WFS.")
    itens = [{"name": c.name, "title": c.title or c.name} for c in caps.layers]
    return sorted(itens, key=lambda item: item["title"])


async def descrever_camada_wfs(url: str, type_name: str, version: str = VERSAO_PADRAO) -> dict:
    versao = normalizar_versao(version)
    parametro = "typeNames" if versao == "2.0.0" else "typeName"
    xml = await _buscar(
        f"{url}?service=WFS&request=DescribeFeatureType&version={versao}&{parametro}={type_name}",
        timeout=TIMEOUT_DESCRIBE_S, max_bytes=MAX_DESCRIBE_BYTES,
    )
    return await asyncio.to_thread(parsear_describe_feature_type, xml)


@dataclass
class Sondagem:
    url: str
    version: str
    capabilities: Capabilities
    camada: CamadaDoServico | None = None
    esquema: dict | None = None


def _achar_camada(caps: Capabilities, type_name: str) -> CamadaDoServico | None:
    por_nome = caps.por_nome()
    if type_name in por_nome:
        return por_nome[type_name]
    # Sem o prefixo do namespace, quando for único.
    local = type_name.split(":", 1)[-1]
    candidatas = [c for c in caps.layers if c.name.split(":", 1)[-1] == local]
    return candidatas[0] if len(candidatas) == 1 else None


async def sondar_wfs(url: str, type_name: str | None = None, version: str = VERSAO_PADRAO) -> Sondagem:
    """GetCapabilities e, com `type_name`, a camada e o seu DescribeFeatureType."""
    caps = await obter_capabilities(url, version)
    if not caps.layers:
        raise SondagemError("sem_camadas", "Nenhuma camada encontrada no servidor WFS.")
    sondagem = Sondagem(url=url, version=normalizar_versao(version), capabilities=caps)
    if not type_name:
        return sondagem
    camada = _achar_camada(caps, type_name.strip())
    if camada is None:
        nomes = [c.name for c in caps.layers[:20]]
        raise SondagemError(
            "camada_inexistente",
            f"Camada '{type_name}' não encontrada no servidor WFS. Camadas disponíveis: "
            + ", ".join(nomes) + ("…" if len(caps.layers) > 20 else ""),
            candidatas=nomes,
        )
    sondagem.camada = camada
    esquema = await descrever_camada_wfs(url, camada.name, version)
    esquema["crs"] = camada.crs
    esquema["bbox"] = list(camada.bbox) if camada.bbox else None
    sondagem.esquema = esquema
    return sondagem


# ── Esquema ───────────────────────────────────────────────────────────────────


def fundir_esquema(atual: Mapping[str, Any] | None, novo: Mapping[str, Any] | None) -> dict | None:
    """O esquema mais completo, sem perder o que só o outro tinha.

    As COLUNAS vêm da fonte mais forte (`describe_feature_type` > `vault` >
    `run`); `crs`, `bbox` e `feature_count` vêm do mais recente que os tiver,
    porque só uma execução ou um GetCapabilities os conhece.
    """
    if not atual and not novo:
        return None
    atual = dict(atual or {})
    novo = dict(novo or {})
    forca_atual = _FORCA_DO_ESQUEMA.get(atual.get("columns_source") if atual.get("columns") else None, 0)
    forca_nova = _FORCA_DO_ESQUEMA.get(novo.get("columns_source") if novo.get("columns") else None, 0)
    base, extra = (novo, atual) if forca_nova >= forca_atual and novo.get("columns") else (atual, novo)
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


def _no_escopo(workspace_ids: Iterable[str] | None):
    ids = [w for w in (workspace_ids or []) if w]
    if ids:
        return or_(FonteDeDados.workspace_id.is_(None), FonteDeDados.workspace_id.in_(ids))
    return FonteDeDados.workspace_id.is_(None)


def _like(termo: str):
    # `busca` já é gravada normalizada (sem acento, minúsculas): LIKE simples.
    return contem(FonteDeDados.busca, termo, ignorar_caixa=False)


async def buscar(
    db: AsyncSession,
    workspace_ids: Iterable[str] | None,
    *,
    query: str | None = None,
    kind: str | None = None,
    institution: str | None = None,
    state: str | None = None,
    limit: int = LIMITE_DE_BUSCA,
    offset: int = 0,
) -> tuple[list[FonteDeDados], int]:
    """As fontes ao alcance (plataforma + workspaces do escopo) que casam com a consulta."""
    filtros = [FonteDeDados.deleted_at.is_(None), _no_escopo(workspace_ids)]
    if kind:
        filtros.append(FonteDeDados.tipo == str(kind).strip().lower())
    if institution:
        # Exata (como está no catálogo) OU normalizada no texto de busca — quem
        # escreve "ministerio da saude" encontra "Ministério da Saúde".
        filtros.append(or_(FonteDeDados.instituicao == str(institution).strip(), _like(normalizar_texto(institution))))
    if state:
        filtros.append(FonteDeDados.estado == str(state).strip().lower())
    for variantes in termos_da_consulta(query):
        filtros.append(or_(*[_like(v) for v in sorted(variantes)]))
    condicao = and_(*filtros)
    total = (await db.execute(select(func.count()).select_from(FonteDeDados).where(condicao))).scalar_one()
    linhas = await db.execute(
        select(FonteDeDados)
        .where(condicao)
        .order_by(
            case((FonteDeDados.estado == "ok", 0), else_=1),
            FonteDeDados.prioridade,
            FonteDeDados.usos.desc(),
            FonteDeDados.titulo,
        )
        .offset(max(0, int(offset)))
        .limit(max(1, min(int(limit), 100)))
    )
    return list(linhas.scalars().all()), int(total)


async def obter(db: AsyncSession, source_id: str, workspace_ids: Iterable[str] | None) -> FonteDeDados | None:
    linha = await db.execute(
        select(FonteDeDados).where(
            FonteDeDados.id_hash == str(source_id).strip(),
            FonteDeDados.deleted_at.is_(None),
            _no_escopo(workspace_ids),
        )
    )
    return linha.scalar_one_or_none()


async def obter_por_chave(db: AsyncSession, chave: str) -> FonteDeDados | None:
    linha = await db.execute(select(FonteDeDados).where(FonteDeDados.chave == chave))
    return linha.scalar_one_or_none()


def trecho_do_no(fonte: FonteDeDados) -> dict:
    """O nó pronto para colar numa definition — só as propriedades que o nó declara."""
    propriedades = {
        chave: valor
        for chave, valor in (fonte.propriedades or {}).items()
        if chave in PROPRIEDADES_DO_NO_WFS and valor not in (None, "")
    }
    propriedades.setdefault("url", fonte.url)
    if fonte.type_name:
        propriedades.setdefault("typeName", fonte.type_name)
    return {"name": fonte.no or NO_WFS, "type": "datasource", "properties": propriedades}


# ── Escrita ───────────────────────────────────────────────────────────────────


def _recalcular_busca(fonte: FonteDeDados) -> None:
    fonte.busca = texto_de_busca(
        instituicao=fonte.instituicao, grupo=fonte.grupo, titulo=fonte.titulo,
        type_name=fonte.type_name, url=fonte.url, descricao=fonte.descricao,
        temas=fonte.temas or [], esquema=fonte.esquema,
    )


def _temas_unidos(atuais: Sequence[str] | None, novos: Iterable[str] | None) -> list[str]:
    vistos: dict[str, str] = {}
    for tema in list(atuais or []) + list(novos or []):
        texto = str(tema).strip()
        if texto and normalizar_texto(texto) not in vistos:
            vistos[normalizar_texto(texto)] = texto
    return list(vistos.values())


async def upsert_fonte(
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
    contar_uso: bool = False,
    no: str = NO_WFS,
) -> tuple[FonteDeDados, str]:
    """Cria ou atualiza a fonte de `chave`; devolve `(fonte, "created" | "updated")`.

    Regras de fusão — o que uma origem mais fraca NÃO faz:
    - não ressuscita uma linha apagada (`deleted_at`) quando é `aprendida`;
    - não rebaixa `origem` (vault > manual > aprendida);
    - não apaga `titulo`/`descricao`/`dicas` que alguém escreveu: só preenche o vazio;
    - não troca o esquema por um mais fraco (`fundir_esquema`).
    Sem commit: quem chama decide a transação.
    """
    assert origem in ORIGENS, origem
    url = normalizar_url(url)
    type_name = (type_name or "").strip() or None
    chave = chave_da_fonte(workspace_id, tipo, url, type_name)
    agora = utc_now_naive()
    fonte = await obter_por_chave(db, chave)
    props = {k: v for k, v in dict(propriedades or {}).items() if v not in (None, "")}
    props["url"], props["typeName"] = url, type_name

    if fonte is None:
        fonte = FonteDeDados(
            workspace_id=workspace_id, tipo=tipo, no=no, url=url, type_name=type_name, chave=chave,
            propriedades=props, instituicao=instituicao, grupo=grupo, titulo=titulo, descricao=descricao,
            temas=_temas_unidos([], temas), esquema=dict(esquema) if esquema else None, dicas=dicas,
            prioridade=prioridade or 2, origem=origem, estado=estado or "nao_verificada",
            verificada_em=verificada_em, ultimo_erro=ultimo_erro, vault_hash=vault_hash,
            usos=1 if contar_uso else 0, usada_em=agora if contar_uso else None,
            created_by=created_by, created_at=agora, updated_at=agora,
        )
        _recalcular_busca(fonte)
        db.add(fonte)
        await db.flush()
        return fonte, "created"

    if fonte.deleted_at is not None:
        if origem == "aprendida":
            # A pessoa apagou; uma execução não desfaz isso.
            return fonte, "deleted"
        fonte.deleted_at = None

    if _FORCA_DA_ORIGEM[origem] >= _FORCA_DA_ORIGEM.get(fonte.origem, 0):
        fonte.origem = origem
    # Propriedades: as novas por cima, sem apagar o que só o catálogo sabia
    # (uma execução não traz `sortBy`; o Vault trouxe).
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
    fonte.temas = _temas_unidos(fonte.temas, temas)
    fonte.esquema = fundir_esquema(fonte.esquema, esquema)
    if estado:
        fonte.estado = estado
        fonte.ultimo_erro = ultimo_erro if estado != "ok" else None
    if verificada_em:
        fonte.verificada_em = verificada_em
    if vault_hash:
        fonte.vault_hash = vault_hash
    if contar_uso:
        fonte.usos = int(fonte.usos or 0) + 1
        fonte.usada_em = agora
    fonte.updated_at = agora
    _recalcular_busca(fonte)
    await db.flush()
    return fonte, "updated"


# ── Validação (sem rede) ──────────────────────────────────────────────────────


def _propriedades_do_no(no: Mapping[str, Any]) -> Mapping[str, Any]:
    for chave in ("parameters", "properties"):
        valor = no.get(chave)
        if isinstance(valor, Mapping):
            return valor
    dados = no.get("data")
    if isinstance(dados, Mapping) and isinstance(dados.get("properties"), Mapping):
        return dados["properties"]
    return {}


def _alguma_credencial(no: Mapping[str, Any]) -> bool:
    """`credential_id` em QUALQUER dos lugares onde um nó guarda propriedades.

    `_propriedades_do_no` lê `parameters`/`properties` primeiro; o resolver e o
    executor, `data.properties` primeiro (`node_props`). Com a credencial num e
    não no outro, a execução saía autenticada e a camada entrava no catálogo.
    """
    dados = no.get("data")
    candidatos = (no.get("parameters"), no.get("properties"), dados.get("properties") if isinstance(dados, Mapping) else None)
    return any(isinstance(p, Mapping) and str(p.get("credential_id") or "").strip() for p in candidatos)


def nos_de_fonte(nodes: Iterable[Mapping[str, Any]], descriptors: Mapping[str, Mapping[str, Any]] | None = None):
    """Os nós que leem uma fonte externa e o (url, typeName) de cada um."""
    for no in nodes:
        if not isinstance(no, Mapping):
            continue
        nome = str(no.get("name") or "")
        descriptor = (descriptors or {}).get(nome) or {}
        kind = descriptor.get("source_kind") if descriptors is not None else (TIPO_WFS if nome == NO_WFS else None)
        if kind != TIPO_WFS:
            continue
        props = _propriedades_do_no(no)
        try:
            url = normalizar_url(props.get("url"))
        except FonteInvalidaError:
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
    """Avisos `unknown_source`/`failing_source` para os nós WFS da definição.

    Falha ABERTA: qualquer erro aqui vira log e lista vazia — a validação não
    pode depender do catálogo para responder.
    """
    try:
        alvos = list(nos_de_fonte(nodes, descriptors))
        if not alvos:
            return []
        chaves: dict[str, tuple[Mapping[str, Any], str, str]] = {}
        for no, url, type_name in alvos:
            for ws in (workspace_id, None):
                chaves.setdefault(chave_da_fonte(ws, TIPO_WFS, url, type_name), (no, url, type_name))
        linhas = await db.execute(
            select(FonteDeDados).where(FonteDeDados.chave.in_(list(chaves)), FonteDeDados.deleted_at.is_(None))
        )
        por_chave = {f.chave: f for f in linhas.scalars().all()}
        avisos: list[dict] = []
        for no, url, type_name in alvos:
            achada = por_chave.get(chave_da_fonte(workspace_id, TIPO_WFS, url, type_name)) or por_chave.get(
                chave_da_fonte(None, TIPO_WFS, url, type_name)
            )
            node_id = no.get("id")
            if achada is None:
                avisos.append({
                    "code": "unknown_source", "severity": "warning", "node_id": node_id, "edge": None,
                    "message": (
                        f"nó 'WFS' (id={node_id}) aponta para url+typeName que não estão no catálogo do "
                        "workspace nem da plataforma. Use search_sources para uma fonte já mapeada, ou "
                        "probe_source / register_source para sondar e registrar esta antes de executar."
                    ),
                })
            elif achada.estado == "falhando":
                quando = achada.verificada_em.isoformat() if achada.verificada_em else "sem data"
                motivo = (achada.ultimo_erro or "sem detalhe")[:160]
                avisos.append({
                    "code": "failing_source", "severity": "warning", "node_id": node_id, "edge": None,
                    "message": (
                        f"nó 'WFS' (id={node_id}) usa a fonte {achada.id_hash} que falhou na última "
                        f"verificação ({quando}): {motivo}. Confira com probe_source antes de executar."
                    ),
                })
        return avisos
    except Exception as exc:  # o catálogo nunca derruba a validação
        logger.warning("Catálogo de fontes indisponível na validação: %s", exc)
        return []


# ── Aprendizado (consumer) ────────────────────────────────────────────────────


def _esquema_da_execucao(nid: str, stats: Mapping[str, Any], *, recortada: bool = False) -> dict | None:
    """O que a execução viu da camada.

    `recortada` (o nó tinha filtro CQL ou bbox): a extensão e a contagem são
    as do RECORTE, não as da camada — não são aprendidas. As colunas e o CRS
    continuam valendo.
    """
    no_stats = stats.get(nid) if isinstance(stats.get(nid), Mapping) else {}
    metricas = ((stats.get("__metrics__") or {}).get("nodes") or {}).get(nid) or {}
    espacial = metricas.get("spatial") if isinstance(metricas, Mapping) else None
    espacial = espacial if isinstance(espacial, Mapping) else {}
    colunas_por_saida = no_stats.get("output_columns") if isinstance(no_stats.get("output_columns"), Mapping) else {}
    nomes = colunas_por_saida.get("output") if isinstance(colunas_por_saida, Mapping) else None
    esquema: dict = {}
    if isinstance(nomes, list) and nomes:
        esquema["columns"] = [{"name": str(n), "type": None, "xsd": None, "nullable": True} for n in nomes]
        esquema["columns_source"] = "run"
    for chave in ("crs",) if recortada else ("crs", "bbox", "feature_count"):
        if espacial.get(chave) is not None:
            esquema[chave] = espacial[chave]
    if not recortada and esquema.get("feature_count") is None and no_stats.get("output_features") is not None:
        esquema["feature_count"] = no_stats.get("output_features")
    return esquema or None


def _produz_bbox_string(nome_do_no: str) -> bool:
    """O nó declara `bbox_string` entre as saídas (ComputeBoundingBox, outro
    WFS)? Numa aresta sem chaves tudo o que ele produz entra no nó seguinte."""
    try:
        from flow.registry import NODE_REGISTRY

        cls = NODE_REGISTRY.get(nome_do_no)
        saidas = cls.description().get("outputs") or [] if cls is not None else []
    except Exception:  # registro indisponível ou descriptor quebrado
        saidas = []
    return any(isinstance(s, Mapping) and s.get("name") == "bbox_string" for s in saidas)


def _bbox_por_aresta(nid: str, definition: Mapping[str, Any]) -> bool:
    """O nó recebe o bbox de OUTRO nó? O nó WFS lê `inputs["bbox_string"]`
    quando o campo `bbox` está vazio (o caso ComputeBoundingBox → WFS), e aí a
    execução também é um recorte: a extensão e a contagem não são as da camada.

    A semântica da aresta é a do executor (flow/executor/edge_resolver.py): com
    `from_key`/`to_key`, a porta de entrada é `to_key or from_key`; sem os
    dois, entra tudo o que a origem produz."""
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
        if de is None and para is None and _produz_bbox_string(nomes.get(str(aresta.get("source")), "")):
            return True
    return False


async def aprender_de_execucao(
    db: AsyncSession, run: Any, stats: Mapping[str, Any], definition: Mapping[str, Any], *, first_close: bool
) -> int:
    """Registra (ou atualiza) as fontes que os nós WFS desta execução leram com sucesso."""
    if not isinstance(definition, Mapping) or not isinstance(stats, Mapping):
        return 0
    quando = getattr(run, "end_time", None) or utc_now_naive()
    if getattr(quando, "tzinfo", None) is not None:
        quando = quando.replace(tzinfo=None)
    aprendidas = 0
    for no, url, type_name in nos_de_fonte(definition.get("nodes") or [], None):
        nid = str(no.get("id") or "")
        no_stats = stats.get(nid)
        if not isinstance(no_stats, Mapping) or no_stats.get("status") != "completed":
            continue
        props = _propriedades_do_no(no)
        # Camada lida COM credencial é protegida: não entra no catálogo — a
        # verificação diária a sondaria sem a chave e a marcaria como falhando,
        # e o trecho pronto a ofereceria a quem não tem acesso.
        if _alguma_credencial(no):
            continue
        recortada = (
            any(str(props.get(k) or "").strip() for k in ("cqlFilter", "bbox"))
            or _bbox_por_aresta(nid, definition)
        )
        _, desfecho = await upsert_fonte(
            db,
            workspace_id=getattr(run, "workspace_id", None),
            tipo=TIPO_WFS, url=url, type_name=type_name,
            propriedades={k: props.get(k) for k in PROPRIEDADES_DO_NO_WFS if props.get(k) not in (None, "")},
            origem="aprendida", estado="ok", esquema=_esquema_da_execucao(nid, stats, recortada=recortada),
            titulo=None, verificada_em=quando, contar_uso=first_close,
        )
        if desfecho != "deleted":
            aprendidas += 1
    return aprendidas


# ── Verificação ───────────────────────────────────────────────────────────────


@dataclass
class ResumoDaVerificacao:
    url: str
    ok: int = 0
    falhando: int = 0
    erro: str | None = None


async def endpoints_para_verificar(
    db: AsyncSession, *, desatualizados_ha: int | None = None
) -> list[tuple[str, str]]:
    """As URLs distintas do catálogo (com a versão do WFS de cada uma).

    `desatualizados_ha` (segundos): só as URLs com alguma camada nunca
    verificada ou verificada há mais tempo que isso — o modo da verificação
    inicial da subida, que não refaz o que a rodada anterior já fez.
    """
    consulta = select(FonteDeDados.url, FonteDeDados.propriedades).where(
        FonteDeDados.deleted_at.is_(None), FonteDeDados.tipo == TIPO_WFS
    )
    if desatualizados_ha is not None:
        limite = utc_now_naive() - timedelta(seconds=max(0, desatualizados_ha))
        consulta = consulta.where(
            or_(FonteDeDados.verificada_em.is_(None), FonteDeDados.verificada_em < limite)
        )
    linhas = await db.execute(consulta)
    vistos: dict[str, str] = {}
    for url, props in linhas.all():
        versao = normalizar_versao((props or {}).get("version"))
        vistos.setdefault(url, versao)
    return sorted(vistos.items())


async def verificar_endpoint(db: AsyncSession, url: str, version: str = VERSAO_PADRAO) -> ResumoDaVerificacao:
    """UM GetCapabilities marca todas as linhas daquela URL: `ok` (com crs/bbox
    do capabilities) ou `falhando`. Endpoint fora do ar: todas `falhando`.
    Commita no fim — é um lote."""
    resumo = ResumoDaVerificacao(url=url)
    linhas = await db.execute(
        select(FonteDeDados).where(
            FonteDeDados.url == url, FonteDeDados.tipo == TIPO_WFS, FonteDeDados.deleted_at.is_(None)
        )
    )
    fontes = list(linhas.scalars().all())
    if not fontes:
        return resumo
    agora = utc_now_naive()
    try:
        caps = await obter_capabilities(url, version)
    except SondagemError as exc:
        resumo.erro = exc.mensagem
        for fonte in fontes:
            fonte.estado, fonte.ultimo_erro, fonte.verificada_em, fonte.updated_at = "falhando", exc.mensagem[:500], agora, agora
            resumo.falhando += 1
        await db.commit()
        return resumo

    for fonte in fontes:
        camada = _achar_camada(caps, fonte.type_name or "")
        if camada is None:
            fonte.estado = "falhando"
            fonte.ultimo_erro = "camada não consta no GetCapabilities"
            resumo.falhando += 1
        else:
            fonte.estado, fonte.ultimo_erro = "ok", None
            fonte.esquema = fundir_esquema(
                fonte.esquema,
                {"crs": camada.crs, "bbox": list(camada.bbox) if camada.bbox else None},
            )
            if camada.title and not fonte.titulo:
                fonte.titulo = camada.title
            if camada.abstract and not fonte.descricao:
                fonte.descricao = camada.abstract[:2000]
            if camada.keywords:
                fonte.temas = _temas_unidos(fonte.temas, camada.keywords)
            _recalcular_busca(fonte)
            resumo.ok += 1
        fonte.verificada_em, fonte.updated_at = agora, agora
    await db.commit()
    return resumo


# ── Importação do Vault ───────────────────────────────────────────────────────


@dataclass
class ResumoDaImportacao:
    criadas: int = 0
    atualizadas: int = 0
    iguais: int = 0
    removidas: int = 0
    ignoradas: dict[str, int] = field(default_factory=dict)
    erros: list[str] = field(default_factory=list)

    def como_texto(self) -> str:
        ign = ", ".join(f"{n} {m}" for m, n in sorted(self.ignoradas.items())) or "nenhuma"
        return (
            f"{self.criadas} criadas, {self.atualizadas} atualizadas, {self.iguais} iguais, "
            f"{self.removidas} removidas; pastas ignoradas: {ign}"
            + (f"; erros: {len(self.erros)}" if self.erros else "")
        )


# Os campos de texto que o banco limita, e o que fazer quando o Vault traz algo
# maior. A distinção não é de gosto:
#
# - **exibição** (`instituicao`, `grupo`): cortar perde a cauda de um rótulo. A
#   fonte continua funcionando e continua sendo achada pela busca.
# - **funcional** (`type_name`, `url`): cortar cria uma fonte que aponta para
#   uma camada que não existe — o `type_name` vai literalmente na consulta WFS,
#   e a `chave` deriva dele. Um registro assim é PULADO, com erro no resumo.
#
# `titulo` não está aqui porque virou TEXT (scripts/init_schema.sql; a
# migração histórica a3c81d7e2f46 fez a troca): ele é
# escrito por gente e qualquer limite fixo volta a estourar no próximo catálogo.
_FUNCIONAIS = ("type_name", "url")


def _limite(coluna: str) -> int | None:
    """O limite da COLUNA, lido do modelo.

    Lido, e não copiado: uma constante repetida aqui divergiria no dia em que a
    coluna mudasse, e a divergência apareceria como o mesmo estouro que esta
    guarda existe para impedir.
    """
    return getattr(FonteDeDados.__table__.c[coluna].type, "length", None)


def _cortar(valor: str | None, limite: int | None) -> str | None:
    if valor is None or limite is None or len(valor) <= limite:
        return valor
    return valor[: max(1, limite - 1)] + "…"


def _campo_funcional_longo(registro: fontes_vault.RegistroDoVault) -> str | None:
    """A mensagem de erro quando um campo que NÃO pode ser cortado não cabe."""
    for coluna in _FUNCIONAIS:
        limite = _limite(coluna)
        valor = getattr(registro, coluna, None)
        if limite is not None and valor is not None and len(str(valor)) > limite:
            return (
                f"`{coluna}` tem {len(str(valor))} caracteres e a coluna aceita {limite}. "
                "Cortá-lo apontaria para uma camada que não existe, então o registro foi "
                "pulado."
            )
    return None


def _aplicar_registro(fonte: FonteDeDados, registro: fontes_vault.RegistroDoVault, agora: datetime) -> None:
    """Os campos que o Vault dita numa linha `vault`. Preserva o que o catálogo
    aprendeu por conta (estado, verificação, usos) e o que a UI de um dia editar
    por cima do vazio."""
    fonte.propriedades = {**(fonte.propriedades or {}), **registro.propriedades}
    # Cortados no limite da COLUNA: são rótulos, e um rótulo sem a cauda ainda
    # serve. Sem isto, um deles fora do limite derrubava o lote inteiro — e com
    # ele todo o resto do catálogo.
    fonte.instituicao = _cortar(registro.instituicao, _limite("instituicao"))
    fonte.grupo = _cortar(registro.grupo, _limite("grupo"))
    fonte.titulo = registro.titulo
    fonte.descricao = registro.descricao
    fonte.temas = _temas_unidos(registro.temas, [])
    fonte.dicas = registro.dicas
    fonte.prioridade = registro.prioridade
    fonte.esquema = fundir_esquema(fonte.esquema, registro.esquema)
    fonte.vault_hash = registro.vault_hash
    fonte.updated_at = agora
    _recalcular_busca(fonte)


async def importar_pasta(db: AsyncSession, caminho: str | Path, *, workspace_id: str | None = None) -> ResumoDaImportacao:
    """Importa `<caminho>/<INSTITUIÇÃO>/` como fontes `vault` (da plataforma por
    padrão). Idempotente por `chave` + `vault_hash`: reimportar a mesma pasta é
    uma consulta e zero escritas. Commita por lote."""
    resumo = ResumoDaImportacao()
    raiz = Path(caminho)
    if not raiz.is_dir():
        resumo.erros.append(f"pasta não encontrada: {raiz}")
        return resumo
    definir_sinonimos(await asyncio.to_thread(fontes_vault.sinonimos_de, raiz))
    itens = await asyncio.to_thread(lambda: list(fontes_vault.ler_pasta(raiz)))

    linhas = await db.execute(
        select(FonteDeDados.id, FonteDeDados.chave, FonteDeDados.vault_hash).where(
            FonteDeDados.origem == "vault",
            FonteDeDados.workspace_id.is_(None) if workspace_id is None else FonteDeDados.workspace_id == workspace_id,
        )
    )
    existentes: dict[str, tuple[int, str | None]] = {chave: (id_, h) for id_, chave, h in linhas.all()}
    vistas: set[str] = set()
    agora = utc_now_naive()
    pendentes = 0

    for item in itens:
        if isinstance(item, fontes_vault.Ignorada):
            resumo.ignoradas[item.motivo] = resumo.ignoradas.get(item.motivo, 0) + 1
            continue
        try:
            url = normalizar_url(item.url)
        except FonteInvalidaError as exc:
            resumo.erros.append(f"{item.instituicao}/{item.type_name}: {exc.detail}")
            continue
        # ANTES de qualquer conta com o registro: a `chave` deriva do
        # `type_name`, e um valor que o banco vai recusar não pode chegar ao
        # `db.add`. O commit é por LOTE, então uma linha que estoura leva junto
        # as 499 vizinhas e aborta o resto da importação — foi assim que 75 % do
        # catálogo sumiu em produção sem nada além de um ERROR no log.
        longo = _campo_funcional_longo(item)
        if longo:
            resumo.erros.append(f"{item.instituicao}/{item.type_name}: {longo}")
            continue
        chave = chave_da_fonte(workspace_id, TIPO_WFS, url, item.type_name)
        if chave in vistas:
            continue  # a mesma camada listada duas vezes na nota
        vistas.add(chave)
        existente = existentes.get(chave)
        if existente and existente[1] == item.vault_hash:
            resumo.iguais += 1
            continue
        if existente:
            fonte = await db.get(FonteDeDados, existente[0])
            if fonte is None:
                continue
            fonte.deleted_at = None
            _aplicar_registro(fonte, item, agora)
            resumo.atualizadas += 1
        else:
            fonte = FonteDeDados(
                workspace_id=workspace_id, tipo=TIPO_WFS, no=NO_WFS, url=url, type_name=item.type_name,
                chave=chave, propriedades={}, origem="vault", estado="nao_verificada",
                created_at=agora, updated_at=agora,
            )
            _aplicar_registro(fonte, item, agora)
            db.add(fonte)
            resumo.criadas += 1
        pendentes += 1
        if pendentes >= LOTE_DE_IMPORTACAO:
            await db.commit()
            pendentes = 0

    # O Vault é a fonte da verdade da origem `vault`: o que sumiu da pasta sai
    # do catálogo (soft delete — a linha e o histórico ficam).
    sumidas = [id_ for chave, (id_, _) in existentes.items() if chave not in vistas]
    for id_ in sumidas:
        fonte = await db.get(FonteDeDados, id_)
        if fonte is not None and fonte.deleted_at is None:
            fonte.deleted_at, fonte.updated_at = agora, agora
            resumo.removidas += 1
    await db.commit()
    return resumo
