# tests/unit/test_wfs_authkey.py
"""Nó WFS com credencial salva: o authkey do GeoServer (na URL ou num
cabeçalho) e o Basic da credencial "wfs".

O cliente é o do owslib de verdade, montado do GetCapabilities enlatado dos
testes do filtro CQL; o `openURL` é dublado e guarda cada URL e os argumentos
de cada pedido. O que se protege:
- o segredo vai em TODO pedido: GetCapabilities, a sondagem do CQL, o
  DescribeFeatureType e cada página — pelo caminho do owslib e pelo nosso;
- só ao endereço do nó: anunciado outro host (ou outro esquema), o nó recusa
  antes do primeiro GetFeature;
- nunca numa mensagem nem no traceback, que vão à tela e ao banco;
- o cache de capabilities é por credencial;
- credencial escolhida e não resolvida não sai anônima.
"""
import base64
import traceback

import pytest
import requests
from owslib.feature.wfs200 import WebFeatureService_2_0_0

import flow.nodes.datasource.wfs as wfs
from app.core.credentials.schemas import CREDENTIAL_TYPE_SCHEMAS
from flow.utils.credencial_wfs import autenticacao_wfs

from .test_wfs_cql import _CAPS, _Servidor

URL = "http://x/ows"  # o GetCapabilities enlatado anuncia http://x/geoserver/ows
CHAVE = "c0ffee-SEGREDO-42"


def _authkey(**extra):
    return autenticacao_wfs(None, {"type": "geoserver_authkey", "token": CHAVE, **extra})


class _ServidorComArgs(_Servidor):
    """O servidor dublado, guardando também os argumentos de cada `openURL`."""

    def __init__(self):
        super().__init__()
        self.argumentos: list[dict] = []

    def __call__(self, url, data=None, method="Get", **kw):
        self.argumentos.append(kw)
        return super().__call__(url, data, method, **kw)


@pytest.fixture
def servidor(monkeypatch):
    import owslib.feature.wfs200 as wfs200
    import owslib.util
    import owslib.wfs as ows

    construcoes: list[dict] = []

    def _fabrica(url, version="2.0.0", timeout=30, headers=None, auth=None, **k):
        construcoes.append({"url": url, "headers": headers, "auth": auth})
        return WebFeatureService_2_0_0(url, version, _CAPS, timeout=timeout, headers=headers, auth=auth)

    monkeypatch.setattr(wfs, "_caps_cache", {})
    monkeypatch.setattr(wfs, "_cql_verificado", {})
    monkeypatch.setattr(wfs, "_CAPS_TTL_S", 3600)
    monkeypatch.setattr(ows, "WebFeatureService", _fabrica)
    falso = _ServidorComArgs()
    falso.construcoes = construcoes
    monkeypatch.setattr(owslib.util, "openURL", falso)
    monkeypatch.setattr(wfs200, "openURL", falso)
    monkeypatch.setattr("time.sleep", lambda s: None)
    return falso


# ── A credencial resolvida ───────────────────────────────────────────────────────

def test_sem_credencial_e_publico():
    assert autenticacao_wfs(None, None) is None
    assert autenticacao_wfs("", {}) is None


def test_credencial_escolhida_e_nao_resolvida_nao_sai_anonima():
    with pytest.raises(ValueError, match="não pôde ser resolvida"):
        autenticacao_wfs("3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05", {})


def test_padroes_do_authkey_quando_a_tela_nao_gravou():
    auth = autenticacao_wfs(None, {"type": "geoserver_authkey", "token": CHAVE, "parameter": "", "location": ""})
    assert (auth.tipo, auth.nome, auth.no_cabecalho) == ("authkey", "authkey", False)
    assert CHAVE not in repr(auth)  # nunca o segredo num log


@pytest.mark.parametrize("http_auth, erro", [
    ({"type": "geoserver_authkey", "token": "  "}, "não tem a chave"),
    ({"type": "geoserver_authkey", "token": "abc\r\nX: y"}, "caracteres de controle"),
    ({"type": "geoserver_authkey", "token": "abc12"}, "menos de 6 caracteres"),
    ({"type": "geoserver_authkey", "token": CHAVE, "parameter": "auth key&x=1"}, "não é válido"),
    ({"type": "geoserver_authkey", "token": CHAVE, "location": "cookie"}, "'url' ou 'header'"),
    ({"type": "geoserver_authkey", "token": CHAVE, "parameter": "Host", "location": "header"}, "não pode mandar"),
    ({"type": "geoserver_authkey", "token": CHAVE, "parameter": "service"}, "parâmetro do próprio WFS"),
    ({"type": "geoserver_authkey", "token": CHAVE, "parameter": "CQL_FILTER", "location": "url"}, "parâmetro do próprio WFS"),
    ({"type": "geoserver_authkey", "token": "chavę-SEGREDA-99", "location": "header"}, "fora do ASCII"),
    ({"type": "wfs", "username": "u", "password": ""}, "usuário e senha"),
    ({"type": "wfs", "username": "u", "password": "geo"}, "menos de 6 caracteres"),  # pragma: allowlist secret
    ({"type": "http_bearer", "token": CHAVE}, "não serve para o nó WFS"),
])
def test_credencial_invalida_e_recusada(http_auth, erro):
    with pytest.raises(ValueError, match=erro):
        autenticacao_wfs(None, http_auth)


def test_a_chave_fora_do_ascii_so_e_recusada_no_cabecalho():
    # Na URL ela vai percent-encoded, e o requests a codifica sem reclamar.
    assert autenticacao_wfs(None, {"type": "geoserver_authkey", "token": "chavę-SEGREDA-99"}).segredo == "chavę-SEGREDA-99"


def test_a_impressao_nao_colide_entre_usuario_e_senha():
    a = autenticacao_wfs(None, {"type": "wfs", "username": "a|b", "password": "c-segredo"})
    b = autenticacao_wfs(None, {"type": "wfs", "username": "a", "password": "b|c-segredo"})
    assert a.impressao != b.impressao


@pytest.mark.parametrize("a, b, mesma", [
    ("https://h/x", "https://h:443/x", True),
    ("http://h/x", "http://h:80/x", True),
    ("http://h/x", "http://h./x", True),
    ("http://u:p@h/x", "http://h/x", True),
    ("http://[::1]:8080/x", "http://[0:0:0:0:0:0:0:1]:8080/x", True),
    ("http://H/x", "http://h/x", True),
    ("http://h/x", "http://h:8443/x", False),
    ("http://h/x", "https://h/x", False),
    ("http://h/x", "http://outro/x", False),
])
def test_a_origem_e_a_que_todo_cliente_http_ve(a, b, mesma):
    # Um GeoServer sem Proxy Base URL anuncia `scheme://host:port` — com a
    # porta padrão explícita, era recusado como "outro endereço".
    assert (wfs._origem(a) == wfs._origem(b)) is mesma


def test_a_chave_so_e_pendurada_nos_enderecos_da_origem_do_no():
    from types import SimpleNamespace
    metodos = [
        {"type": "Get", "url": "http://x:80/geoserver/ows"},   # a origem do nó (porta padrão explícita)
        {"type": "Get", "url": "http://outro-host/geoserver/ows"},
        {"type": "Post", "url": "https://x/geoserver/ows"},      # mesmo host, outro esquema
    ]
    cliente = SimpleNamespace(operations=[SimpleNamespace(methods=metodos)])
    wfs._pendurar_a_chave(cliente, "http://x/ows", _authkey())
    assert metodos[0]["url"] == f"http://x:80/geoserver/ows?authkey={CHAVE}"
    assert CHAVE not in metodos[1]["url"] and CHAVE not in metodos[2]["url"]


def test_o_pedido_feito_a_mao_recebe_o_segredo_no_lugar_certo():
    # O que a listagem de camadas do editor usa (httpx, fora do owslib).
    assert (_authkey().parametros(), _authkey().cabecalhos()) == ({"authkey": CHAVE}, {})
    no_cabecalho = _authkey(parameter="X-Chave", location="header")
    assert (no_cabecalho.parametros(), no_cabecalho.cabecalhos()) == ({}, {"X-Chave": CHAVE})
    basic = autenticacao_wfs(None, {"type": "wfs", "username": "leitor", "password": CHAVE})
    assert basic.parametros() == {} and basic.cabecalhos()["Authorization"].startswith("Basic ")


def test_o_no_declara_a_credencial_e_o_campo_injetado():
    props = {p["name"]: p for p in wfs.WFSNode.description()["properties"]}
    assert props["credential_id"]["type"] == "credential"
    assert set(props["credential_id"]["credential_types"]) <= set(CREDENTIAL_TYPE_SCHEMAS)
    assert props["http_auth"]["type"] == "object" and props["http_auth"]["default"] == {}


# ── O segredo em todo pedido ─────────────────────────────────────────────────────

def test_authkey_na_url_vai_em_todo_pedido(servidor):
    auth = _authkey()
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, bbox=(1, 2, 3, 4), cql_filter="a = 1", auth=auth)
    assert f"authkey={CHAVE}" in servidor.construcoes[0]["url"]  # o GetCapabilities
    tipos = {"hits" if p.get("resultType") == "hits" else p.get("request") for p in servidor.pedidos}
    assert {"hits", "DescribeFeatureType", "GetFeature"} <= tipos
    for pedido in servidor.pedidos:  # sondagem, controle, DescribeFeatureType e a página
        assert pedido.get("authkey") == CHAVE


def test_authkey_na_url_tambem_no_caminho_do_owslib(servidor):
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, auth=_authkey())
    (pagina,) = servidor.paginas_pedidas  # o getfeature do owslib, sem filtro
    assert pagina.get("authkey") == CHAVE


def test_nome_do_parametro_configuravel(servidor):
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, auth=_authkey(parameter="chave"))
    (pagina,) = servidor.paginas_pedidas
    assert pagina.get("chave") == CHAVE and "authkey" not in pagina


def _assinado(kw: dict) -> dict:
    """Os cabeçalhos que a assinatura do pedido põe — o que o `requests` enviaria."""
    pedido = requests.Request("GET", "http://x/ows").prepare()
    kw["auth"].auth_delegate(pedido)
    return dict(pedido.headers)


def test_authkey_no_cabecalho_vai_em_todo_pedido_e_nunca_na_url(servidor):
    auth = _authkey(location="header")
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, bbox=(1, 2, 3, 4), cql_filter="a = 1", auth=auth)
    assert _assinado(servidor.construcoes[0])["authkey"] == CHAVE  # o GetCapabilities
    assert servidor.argumentos and all(_assinado(kw)["authkey"] == CHAVE for kw in servidor.argumentos)
    assert not any(CHAVE in u for u in servidor.urls + [servidor.construcoes[0]["url"]])


def test_basic_vai_pela_assinatura_do_pedido(servidor):
    auth = autenticacao_wfs(None, {"type": "wfs", "username": "leitor", "password": CHAVE})
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1", auth=auth)
    esperado = "Basic " + base64.b64encode(f"leitor:{CHAVE}".encode()).decode()
    assert _assinado(servidor.construcoes[0])["Authorization"] == esperado
    assert servidor.argumentos and all(_assinado(kw)["Authorization"] == esperado for kw in servidor.argumentos)
    assert not any(CHAVE in u for u in servidor.urls)


def test_o_refresh_do_getcapabilities_tambem_leva_a_chave(servidor):
    # Camada fora do GetCapabilities: o nó o refaz UMA vez antes de acusar.
    with pytest.raises(ValueError):
        wfs._fetch_wfs_features(URL, "ns:publicada_agora", 10, auth=_authkey())
    assert len(servidor.construcoes) == 2
    assert all(f"authkey={CHAVE}" in c["url"] for c in servidor.construcoes)


# ── Só ao endereço do nó ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("endereco_do_no", ["http://outro-host/ows", "https://x/ows"])
def test_outra_origem_anunciada_recusa_antes_do_getfeature(servidor, endereco_do_no):
    # O GetCapabilities anuncia http://x/...: outro host, ou o mesmo host sem TLS.
    with pytest.raises(ValueError, match="anuncia outro endereço"):
        wfs._fetch_wfs_features(endereco_do_no, "ns:rodovias", 10, auth=_authkey())
    assert servidor.urls == []  # nenhum GetFeature, nenhuma sondagem


def test_sem_credencial_o_host_anunciado_segue_valendo(servidor):
    wfs._fetch_wfs_features("http://outro-host/ows", "ns:rodovias", 10)
    assert len(servidor.paginas_pedidas) == 1


# ── O segredo nunca numa mensagem ────────────────────────────────────────────────

@pytest.mark.parametrize("chave", [CHAVE, "a+b/c=d&e"])
def test_o_segredo_nao_sai_na_mensagem_nem_no_traceback(servidor, chave):
    from urllib.parse import quote, quote_plus
    auth = autenticacao_wfs(None, {"type": "geoserver_authkey", "token": chave})
    servidor.paginas = [requests.HTTPError(
        f"500 Server Error: Internal for url: http://x/geoserver/ows?authkey={quote(chave, safe='')}"
        f"&k2={quote_plus(chave)}&k3={chave}"
    )]
    with pytest.raises(RuntimeError) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 2, 0.0, None, auth)
    texto = str(ei.value) + "".join(traceback.format_exception(ei.value))
    for forma in {chave, quote(chave, safe=""), quote_plus(chave)}:
        assert forma not in texto
    assert "***" in str(ei.value)


def test_o_segredo_nao_sai_no_log_da_tentativa(servidor, caplog):
    import logging
    servidor.paginas = [requests.ConnectionError(f"Max retries exceeded with url: /ows?authkey={CHAVE}")]
    with caplog.at_level(logging.WARNING):
        with pytest.raises(RuntimeError):
            wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 1, 0.0, None, _authkey())
    assert "tentativa" in caplog.text and CHAVE not in caplog.text


def test_enquanto_busca_nenhum_log_do_processo_leva_a_chave(monkeypatch, caplog):
    # O DEBUG do urllib3 (e do owslib) escreve a URL de cada pedido.
    import logging
    import geopandas as gpd

    def _busca(*args):
        logging.getLogger("urllib3.connectionpool").debug('"GET /ows?authkey=%s HTTP/1.1" 200', CHAVE)
        return gpd.GeoDataFrame(geometry=[])

    monkeypatch.setattr(wfs, "_tentar_com_retry", _busca)
    with caplog.at_level(logging.DEBUG):
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 0, 0.0, None, _authkey())
    assert "GET /ows?authkey=***" in caplog.text and CHAVE not in caplog.text


def test_nem_no_log_da_tentativa_de_uma_recusa_do_servidor(servidor, caplog):
    # O ramo da ServiceException (a voz do servidor) tem o seu próprio log.
    import logging
    from owslib.util import ServiceException
    servidor.paginas = [ServiceException(f"<ows:ExceptionText>pool esgotado em /ows?authkey={CHAVE}</ows:ExceptionText>")]
    with caplog.at_level(logging.WARNING):
        with pytest.raises(RuntimeError):
            wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 1, 0.0, None, _authkey())
    assert "tentativa" in caplog.text and CHAVE not in caplog.text


def test_o_erro_de_configuracao_continua_valueerror(servidor):
    # ValueError é o que o executor NÃO retenta: achatar para RuntimeError na
    # redação faria a recusa de configuração ser repetida.
    with pytest.raises(ValueError, match="anuncia outro endereço"):
        wfs._fetch_with_retry("http://outro-host/ows", "ns:rodovias", 10, None, None, None, 5, 2, 0.0, None, _authkey())


def test_a_chave_ecoada_com_entidades_html_tambem_e_redigida_antes_do_corte(servidor):
    # Um proxy ecoa a chave ESCAPADA (`&amp;`, `&lt;`, `&#x27;`): só depois do
    # html.unescape ela volta a ser a chave — e o corte de 200 caracteres caía
    # no meio dela, deixando um pedaço que nenhuma redação reconhece.
    import html as _html
    from owslib.util import ServiceException
    chave = "seg&redo<x>'42-ABCDEFGHIJ-KLMNOP"  # pragma: allowlist secret
    auth = autenticacao_wfs(None, {"type": "geoserver_authkey", "token": chave})
    antes = "x" * (200 - 12 - len("Unauthorized ") - len("?authkey="))
    pagina = f"<html><body>Unauthorized {antes}?authkey={_html.escape(chave, quote=True)}</body></html>"
    servidor.paginas = [ServiceException(pagina)]
    with pytest.raises((RuntimeError, ValueError)) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 0, 0.0, None, auth)
    msg = str(ei.value)
    assert "Unauthorized" in msg and "***" in msg
    assert chave[:8] not in msg and chave[8:20] not in msg


def test_a_senha_do_basic_tambem_some_na_forma_base64(servidor, caplog):
    # `Authorization: Basic base64(usuario:senha)` é como a senha VIAJA — e é o
    # que um proxy ou WAF que ecoa os cabeçalhos põe na página de erro.
    import logging
    from owslib.util import ServiceException
    from flow.utils.credencial_wfs import formas_do_segredo, sem_segredo
    auth = autenticacao_wfs(None, {"type": "wfs", "username": "leitor", "password": CHAVE})
    par = base64.b64encode(f"leitor:{CHAVE}".encode()).decode()
    assert par in formas_do_segredo(auth)
    assert sem_segredo(f"request headers: Authorization: Basic {par}", auth) == "request headers: Authorization: Basic ***"

    servidor.paginas = [ServiceException(f"<ows:ExceptionText>proxy error; headers: Authorization: Basic {par}</ows:ExceptionText>")]
    with caplog.at_level(logging.WARNING):
        with pytest.raises(RuntimeError) as ei:
            wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 1, 0.0, None, auth)
    assert par not in str(ei.value) and par not in caplog.text and CHAVE not in caplog.text


def test_a_pagina_que_repete_a_url_nao_deixa_pedaco_da_chave(servidor):
    # Uma página HTML de erro (um 400 de proxy ou WAF) chega como a
    # ServiceException do owslib, com o corpo. A mensagem é cortada em 200
    # caracteres e o corte cai no meio da chave: sobrariam os 25 primeiros dos
    # 36 — e nenhuma redação depois reconhece o pedaço.
    from owslib.util import ServiceException
    chave = "SEGREDO-0123456789-abcdefghij-XYZ-42"  # pragma: allowlist secret
    auth = autenticacao_wfs(None, {"type": "geoserver_authkey", "token": chave})
    antes = "x" * (200 - 25 - len("Unauthorized ") - len("?authkey="))
    pagina = f"<html><body>Unauthorized {antes}?authkey={chave}</body></html>"
    servidor.paginas = [ServiceException(pagina)]
    with pytest.raises((RuntimeError, ValueError)) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 0, 0.0, None, auth)
    assert "Unauthorized" in str(ei.value)  # a mensagem é mesmo a da página
    assert chave[:12] not in str(ei.value)


# ── Cache por credencial ─────────────────────────────────────────────────────────

def test_o_cache_de_capabilities_e_por_credencial(servidor):
    outra = autenticacao_wfs(None, {"type": "geoserver_authkey", "token": "outra-chave"})
    for auth in (_authkey(), outra, None, _authkey()):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, auth=auth)
    # A mesma chave reaproveita; outra chave e o anônimo constroem o seu.
    assert len(servidor.construcoes) == 3
    assert all(CHAVE not in repr(k) for k in wfs._caps_cache)  # a chave do cache não guarda o segredo


# ── O nó ─────────────────────────────────────────────────────────────────────────

async def test_execute_resolve_a_credencial_e_a_repassa(monkeypatch):
    import geopandas as gpd
    import flow.utils.geo_helpers as geo
    from unittest.mock import MagicMock

    monkeypatch.setattr(geo, "validate_url_ssrf", lambda u: ("1.2.3.4", "host"))
    fetch = MagicMock(return_value=gpd.GeoDataFrame(geometry=[]))
    monkeypatch.setattr(wfs, "_fetch_with_retry", fetch)

    no = wfs.WFSNode("n", {"url": URL, "typeName": "ns:rodovias",
                           "http_auth": {"type": "geoserver_authkey", "token": CHAVE}})
    await no.execute({})
    auth = fetch.call_args.kwargs["auth"]
    assert auth.tipo == "authkey" and auth.segredo == CHAVE


async def test_execute_nao_consulta_com_credencial_nao_resolvida(monkeypatch):
    from unittest.mock import MagicMock
    fetch = MagicMock()
    monkeypatch.setattr(wfs, "_fetch_with_retry", fetch)
    no = wfs.WFSNode("n", {"url": URL, "typeName": "ns:rodovias",
                           "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05"})
    with pytest.raises(ValueError, match="não pôde ser resolvida"):
        await no.execute({})
    fetch.assert_not_called()
