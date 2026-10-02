# tests/unit/test_wfs_node.py
"""Nó WFS: SORTBY para paginar camadas sem chave primária + tradução do erro.

Regressão do erro reportado contra o GeoServer de um geoportal estadual:
"Cannot do natural order without a primary key ...". O GeoServer exige um SORTBY
para paginar (startIndex/count) uma camada sem PK; o nó agora aceita 'Ordenar por'
e, quando o servidor recusa, traduz a mensagem crua para uma instrução acionável.
"""
import pytest

import flow.nodes.datasource.wfs as wfs


# ── _parse_sortby ──────────────────────────────────────────────────────────────

def test_parse_sortby_divide_por_virgula_para_lista():
    # owslib faz `','.join(sortby)`, então o valor precisa chegar como lista.
    assert wfs._parse_sortby("gid") == ["gid"]
    assert wfs._parse_sortby("gid, nome") == ["gid", "nome"]
    assert wfs._parse_sortby("gid DESC") == ["gid DESC"]  # direção acompanha o atributo
    assert wfs._parse_sortby(" a , , b ") == ["a", "b"]   # vazios entre vírgulas somem


def test_parse_sortby_vazio_vira_none():
    assert wfs._parse_sortby("") is None
    assert wfs._parse_sortby("   ") is None


# ── Dublê do owslib ──────────────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload


_UMA_FEICAO = (
    b'{"type":"FeatureCollection","features":['
    b'{"type":"Feature","geometry":{"type":"Point","coordinates":[0,0]},'
    b'"properties":{"id":1}}]}'
)


class _FakeWFS:
    """Registra os kwargs de getfeature e devolve uma resposta configurável."""
    ultimo_kwargs: dict = {}
    resposta: bytes = _UMA_FEICAO

    def __init__(self, *a, **k):
        pass

    @property
    def contents(self):
        # Contém as camadas usadas nos testes (a validação de existência passa).
        return {"camada": object(), "camada_sem_pk": object()}

    def getfeature(self, **kwargs):
        # `type(self)`: a subclasse contada tem os seus próprios `resposta` e
        # `ultimo_kwargs`, e o que um teste deixa no pai não vaza para ela.
        type(self).ultimo_kwargs = dict(kwargs)
        return _FakeResponse(type(self).resposta)


@pytest.fixture(autouse=True)
def _cache_limpo(monkeypatch):
    """O cache de capabilities é do processo: cada teste começa sem ele."""
    monkeypatch.setattr(wfs, "_caps_cache", {})


@pytest.fixture
def fake_wfs(monkeypatch):
    import owslib.wfs as ows
    _FakeWFS.ultimo_kwargs = {}
    _FakeWFS.resposta = _UMA_FEICAO
    monkeypatch.setattr(ows, "WebFeatureService", _FakeWFS)
    return _FakeWFS


# ── SORTBY (item 2) ──────────────────────────────────────────────────────────────

def test_sortby_vai_como_lista_ao_getfeature(fake_wfs):
    wfs._fetch_wfs_features("http://x/ows", "camada", 1000, sort_by=["gid"])
    assert fake_wfs.ultimo_kwargs.get("sortby") == ["gid"]


def test_sem_sortby_nao_manda_a_chave(fake_wfs):
    wfs._fetch_wfs_features("http://x/ows", "camada", 1000, sort_by=None)
    assert "sortby" not in fake_wfs.ultimo_kwargs


# ── Tradução do erro (item 3) ────────────────────────────────────────────────────

_ERRO_ORDEM_NATURAL = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1" version="2.0.0">'
    b'<ows:Exception exceptionCode="NoApplicableCode"><ows:ExceptionText>'
    b'Cannot do natural order without a primary key, please add it or specify a '
    b'manual sort over existing attributes'
    b'</ows:ExceptionText></ows:Exception></ows:ExceptionReport>'
)


def test_erro_de_ordem_natural_vira_mensagem_acionavel(fake_wfs):
    fake_wfs.resposta = _ERRO_ORDEM_NATURAL
    with pytest.raises(RuntimeError) as ei:
        wfs._fetch_wfs_features("http://x/ows", "camada_sem_pk", 1000)
    msg = str(ei.value)
    assert "camada_sem_pk" in msg          # cita a camada
    assert "Ordenar por" in msg            # aponta o campo que resolve
    assert "chave primária" in msg
    # Preserva o detalhe do servidor para quem quiser o texto cru.
    assert "natural order" in msg


def test_outros_erros_wfs_passam_sem_reescrever(fake_wfs):
    fake_wfs.resposta = (
        b'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1">'
        b'<ows:Exception><ows:ExceptionText>Feature type nao encontrado</ows:ExceptionText>'
        b'</ows:Exception></ows:ExceptionReport>'
    )
    with pytest.raises(RuntimeError) as ei:
        wfs._fetch_wfs_features("http://x/ows", "camada", 1000)
    msg = str(ei.value)
    assert "Feature type nao encontrado" in msg
    assert "Ordenar por" not in msg  # nao aplica o texto do caso de PK a erro alheio


# ── Cache de capabilities ────────────────────────────────────────────────────────

class _FakeWFSContado(_FakeWFS):
    """Conta as construções (= GetCapabilities) e deixa as camadas mudarem."""
    construcoes = 0
    camadas = ("camada",)

    def __init__(self, *a, **k):
        type(self).construcoes += 1
        self._camadas = tuple(type(self).camadas)

    @property
    def contents(self):
        return {c: object() for c in self._camadas}


@pytest.fixture
def wfs_contado(monkeypatch):
    import owslib.wfs as ows
    _FakeWFSContado.construcoes = 0
    _FakeWFSContado.camadas = ("camada",)
    _FakeWFSContado.resposta = _UMA_FEICAO
    monkeypatch.setattr(ows, "WebFeatureService", _FakeWFSContado)
    monkeypatch.setattr(wfs, "_CAPS_TTL_S", 3600)
    return _FakeWFSContado


def test_capabilities_sao_reaproveitadas_entre_chamadas_e_retries(wfs_contado, monkeypatch):
    wfs._fetch_wfs_features("http://x/ows", "camada", 10)
    wfs._fetch_wfs_features("http://x/ows", "camada", 10)
    assert wfs_contado.construcoes == 1

    # Um getfeature que falha duas vezes não refaz o GetCapabilities a cada tentativa.
    tentativas = {"n": 0}
    original = _FakeWFSContado.getfeature

    def _instavel(self, **kwargs):
        tentativas["n"] += 1
        if tentativas["n"] < 3:
            raise ConnectionError("caiu")
        return original(self, **kwargs)

    monkeypatch.setattr(_FakeWFSContado, "getfeature", _instavel)
    monkeypatch.setattr("time.sleep", lambda s: None)
    wfs._fetch_with_retry("http://x/ows", "camada", 10, None, None, None, 5, 2, 0.0)
    assert tentativas["n"] == 3 and wfs_contado.construcoes == 1


def test_ttl_vencido_reconstroi(wfs_contado):
    wfs._fetch_wfs_features("http://x/ows", "camada", 10)
    chave = ("http://x/ows", "2.0.0")
    obj, _ = wfs._caps_cache[chave]
    wfs._caps_cache[chave] = (obj, 0.0)  # expirou
    wfs._fetch_wfs_features("http://x/ows", "camada", 10)
    assert wfs_contado.construcoes == 2


def test_camada_ausente_forca_um_refresh_antes_de_falhar(wfs_contado):
    wfs._fetch_wfs_features("http://x/ows", "camada", 10)
    # A camada nova apareceu no servidor depois de o cache ter sido montado.
    _FakeWFSContado.camadas = ("camada", "nova")
    wfs._fetch_wfs_features("http://x/ows", "nova", 10)
    assert wfs_contado.construcoes == 2
    # E uma camada que não existe mesmo custa UM refresh, não um por tentativa.
    with pytest.raises(ValueError, match="não encontrada"):
        wfs._fetch_wfs_features("http://x/ows", "fantasma", 10)
    assert wfs_contado.construcoes == 3


def test_ttl_zero_desliga_o_cache(wfs_contado, monkeypatch):
    monkeypatch.setattr(wfs, "_CAPS_TTL_S", 0)
    wfs._fetch_wfs_features("http://x/ows", "camada", 10)
    wfs._fetch_wfs_features("http://x/ows", "camada", 10)
    assert wfs_contado.construcoes == 2 and wfs._caps_cache == {}


def test_o_cache_tem_teto(wfs_contado, monkeypatch):
    monkeypatch.setattr(wfs, "_CAPS_MAX", 2)
    for host in ("a", "b", "c"):
        wfs._fetch_wfs_features(f"http://{host}/ows", "camada", 10)
    assert len(wfs._caps_cache) == 2 and ("http://a/ows", "2.0.0") not in wfs._caps_cache


# ── SSRF: a URL do usuario e validada antes de o owslib busca-la ─────────────
# Ao contrario de HttpRequest/SendWebhook (safe_httpx_request com IP-pinning), o
# WFSNode entregava a URL direto ao owslib. Sem validacao, um WFS apontando para
# 169.254.169.254 (metadata cloud) ou um servico interno seria requisitado.

import geopandas as gpd  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402


def _no_wfs(url, type_name="camada", **extra):
    return wfs.WFSNode("n", {"url": url, "typeName": type_name, **extra})


async def test_execute_bloqueia_ssrf_para_endereco_interno(monkeypatch):
    """Mutacao: remover a chamada a validate_url_ssrf no execute.

    Um endereco link-local (metadata cloud) e recusado ANTES do fetch — o
    owslib nunca chega a busca-lo.
    """
    fetch = MagicMock()
    monkeypatch.setattr(wfs, "_fetch_with_retry", fetch)
    no = _no_wfs("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(ValueError) as exc:
        await no.execute({})
    msg = str(exc.value).lower()
    assert "interno" in msg or "privado" in msg
    fetch.assert_not_called()


async def test_execute_valida_ssrf_antes_de_buscar(monkeypatch):
    """Mutacao: chamar o fetch sem validar a URL.

    A validacao roda e so entao o owslib e chamado (caminho feliz intacto).
    """
    import flow.utils.geo_helpers as geo
    vistos = {}

    def _fake_validate(u):
        vistos["url"] = u
        return ("1.2.3.4", "host")

    monkeypatch.setattr(geo, "validate_url_ssrf", _fake_validate)
    fetch = MagicMock(return_value=gpd.GeoDataFrame(geometry=[]))
    monkeypatch.setattr(wfs, "_fetch_with_retry", fetch)

    no = _no_wfs("https://geoserver.exemplo.gov.br/ows", "camada")
    await no.execute({})
    assert "geoserver.exemplo.gov.br" in vistos.get("url", "")
    assert fetch.called
