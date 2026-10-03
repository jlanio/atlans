# tests/unit/test_wfs_node.py
"""WFS node: SORTBY to paginate layers without a primary key + error translation.

Regression of the error reported against a state geoportal's GeoServer:
"Cannot do natural order without a primary key ...". GeoServer requires a SORTBY
to paginate (startIndex/count) a layer without a PK; the node now accepts
'Ordenar por' (Sort by) and, when the server refuses, translates the raw message
into an actionable instruction.
"""
import pytest

import flow.nodes.datasource.wfs as wfs


# ── _parse_sortby ──────────────────────────────────────────────────────────────

def test_parse_sortby_divide_por_virgula_para_lista():
    # owslib does `','.join(sortby)`, so the value needs to arrive as a list.
    assert wfs._parse_sortby("gid") == ["gid"]
    assert wfs._parse_sortby("gid, nome") == ["gid", "nome"]
    assert wfs._parse_sortby("gid DESC") == ["gid DESC"]  # direction goes with the attribute
    assert wfs._parse_sortby(" a , , b ") == ["a", "b"]   # empty entries between commas are dropped


def test_parse_sortby_vazio_vira_none():
    assert wfs._parse_sortby("") is None
    assert wfs._parse_sortby("   ") is None


# ── owslib stub ──────────────────────────────────────────────────────────────────

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
    """Records getfeature's kwargs and returns a configurable response."""
    ultimo_kwargs: dict = {}
    resposta: bytes = _UMA_FEICAO

    def __init__(self, *a, **k):
        pass

    @property
    def contents(self):
        # Contains the layers used in the tests (the existence check passes).
        return {"camada": object(), "camada_sem_pk": object()}

    def getfeature(self, **kwargs):
        # `type(self)`: the counted subclass has its own `resposta` and
        # `ultimo_kwargs`, and what one test leaves on the parent does not leak into it.
        type(self).ultimo_kwargs = dict(kwargs)
        return _FakeResponse(type(self).resposta)


@pytest.fixture(autouse=True)
def _cache_limpo(monkeypatch):
    """The capabilities cache is process-wide: each test starts without it."""
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


# ── Error translation (item 3) ───────────────────────────────────────────────────

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
    assert "Ordenar por" in msg            # points to the field that solves it
    assert "chave primária" in msg
    # Preserves the server's detail for anyone who wants the raw text.
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
    assert "Ordenar por" not in msg  # does not apply the PK case's text to an unrelated error


# ── Capabilities cache ───────────────────────────────────────────────────────────

class _FakeWFSContado(_FakeWFS):
    """Counts the constructions (= GetCapabilities) and lets the layers change."""
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

    # A getfeature that fails twice does not redo GetCapabilities on every attempt.
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
    # The new layer appeared on the server after the cache was built.
    _FakeWFSContado.camadas = ("camada", "nova")
    wfs._fetch_wfs_features("http://x/ows", "nova", 10)
    assert wfs_contado.construcoes == 2
    # And a layer that really does not exist costs ONE refresh, not one per attempt.
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


# ── SSRF: the user's URL is validated before owslib fetches it ───────────────
# Unlike HttpRequest/SendWebhook (safe_httpx_request with IP pinning), the
# WFSNode handed the URL straight to owslib. Without validation, a WFS pointing
# to 169.254.169.254 (cloud metadata) or an internal service would be requested.

import geopandas as gpd  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402


def _no_wfs(url, type_name="camada", **extra):
    return wfs.WFSNode("n", {"url": url, "typeName": type_name, **extra})


async def test_execute_bloqueia_ssrf_para_endereco_interno(monkeypatch):
    """Mutation: remove the call to validate_url_ssrf in execute.

    A link-local address (cloud metadata) is refused BEFORE the fetch — owslib
    never gets to fetch it.
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
    """Mutation: call the fetch without validating the URL.

    The validation runs and only then is owslib called (happy path intact).
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
