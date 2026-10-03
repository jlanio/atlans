# tests/unit/test_wfs_authkey.py
"""WFS node with a saved credential: the GeoServer authkey (in the URL or in a
header) and the Basic auth of the "wfs" credential.

The client is the real owslib one, built from the canned GetCapabilities of the
CQL filter tests; `openURL` is stubbed and records each URL and the arguments of
each request. What is protected:
- the secret goes in EVERY request: GetCapabilities, the CQL probe, the
  DescribeFeatureType and each page — through owslib's path and through ours;
- only to the node's address: if another host (or another scheme) is
  advertised, the node refuses before the first GetFeature;
- never in a message or in the traceback, which go to the screen and the database;
- the capabilities cache is per credential;
- a chosen credential that is not resolved does not go out anonymously.
"""
import base64
import traceback

import pytest
import requests
from owslib.feature.wfs200 import WebFeatureService_2_0_0

import flow.nodes.datasource.wfs as wfs
from app.core.credentials.schemas import CREDENTIAL_TYPE_SCHEMAS
from flow.utils.credencial_wfs import wfs_authentication

from .test_wfs_cql import _CAPS, _FakeServer

URL = "http://x/ows"  # o GetCapabilities enlatado anuncia http://x/geoserver/ows
CHAVE = "c0ffee-SEGREDO-42"


def _authkey(**extra):
    return wfs_authentication(None, {"type": "geoserver_authkey", "token": CHAVE, **extra})


class _ServerWithArgs(_FakeServer):
    """The stubbed server, also recording the arguments of each `openURL`."""

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

    def _wfs_factory(url, version="2.0.0", timeout=30, headers=None, auth=None, **k):
        construcoes.append({"url": url, "headers": headers, "auth": auth})
        return WebFeatureService_2_0_0(url, version, _CAPS, timeout=timeout, headers=headers, auth=auth)

    monkeypatch.setattr(wfs, "_caps_cache", {})
    monkeypatch.setattr(wfs, "_cql_verificado", {})
    monkeypatch.setattr(wfs, "_CAPS_TTL_S", 3600)
    monkeypatch.setattr(ows, "WebFeatureService", _wfs_factory)
    falso = _ServerWithArgs()
    falso.construcoes = construcoes
    monkeypatch.setattr(owslib.util, "openURL", falso)
    monkeypatch.setattr(wfs200, "openURL", falso)
    monkeypatch.setattr("time.sleep", lambda s: None)
    return falso


# ── A credencial resolvida ───────────────────────────────────────────────────────

def test_without_credential_is_public():
    assert wfs_authentication(None, None) is None
    assert wfs_authentication("", {}) is None


def test_chosen_unresolved_credential_does_not_go_out_anonymous():
    with pytest.raises(ValueError, match="não pôde ser resolvida"):
        wfs_authentication("3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05", {})


def test_authkey_defaults_when_the_screen_did_not_store():
    auth = wfs_authentication(None, {"type": "geoserver_authkey", "token": CHAVE, "parameter": "", "location": ""})
    assert (auth.tipo, auth.nome, auth.no_cabecalho) == ("authkey", "authkey", False)
    assert CHAVE not in repr(auth)  # never the secret in a log


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
def test_invalid_credential_is_refused(http_auth, erro):
    with pytest.raises(ValueError, match=erro):
        wfs_authentication(None, http_auth)


def test_non_ascii_key_is_only_refused_in_the_header():
    # In the URL it goes percent-encoded, and requests encodes it without complaint.
    assert wfs_authentication(None, {"type": "geoserver_authkey", "token": "chavę-SEGREDA-99"}).segredo == "chavę-SEGREDA-99"


def test_fingerprint_does_not_collide_between_user_and_password():
    a = wfs_authentication(None, {"type": "wfs", "username": "a|b", "password": "c-segredo"})
    b = wfs_authentication(None, {"type": "wfs", "username": "a", "password": "b|c-segredo"})
    assert a.fingerprint != b.fingerprint


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
def test_origin_is_what_every_http_client_sees(a, b, mesma):
    # A GeoServer without a Proxy Base URL advertises `scheme://host:port` — with
    # the default port explicit, it was refused as "another address".
    assert (wfs._origin(a) == wfs._origin(b)) is mesma


def test_key_is_only_attached_to_addresses_of_the_node_origin():
    from types import SimpleNamespace
    metodos = [
        {"type": "Get", "url": "http://x:80/geoserver/ows"},   # the node's origin (explicit default port)
        {"type": "Get", "url": "http://outro-host/geoserver/ows"},
        {"type": "Post", "url": "https://x/geoserver/ows"},      # same host, another scheme
    ]
    cliente = SimpleNamespace(operations=[SimpleNamespace(methods=metodos)])
    wfs._attach_key(cliente, "http://x/ows", _authkey())
    assert metodos[0]["url"] == f"http://x:80/geoserver/ows?authkey={CHAVE}"
    assert CHAVE not in metodos[1]["url"] and CHAVE not in metodos[2]["url"]


def test_handmade_request_gets_the_secret_in_the_right_place():
    # What the editor's layer listing uses (httpx, outside owslib).
    assert (_authkey().parametros(), _authkey().cabecalhos()) == ({"authkey": CHAVE}, {})
    no_cabecalho = _authkey(parameter="X-Chave", location="header")
    assert (no_cabecalho.parametros(), no_cabecalho.cabecalhos()) == ({}, {"X-Chave": CHAVE})
    basic = wfs_authentication(None, {"type": "wfs", "username": "leitor", "password": CHAVE})
    assert basic.parametros() == {} and basic.cabecalhos()["Authorization"].startswith("Basic ")


def test_node_declares_the_credential_and_the_injected_field():
    props = {p["name"]: p for p in wfs.WFSNode.description()["properties"]}
    assert props["credential_id"]["type"] == "credential"
    assert set(props["credential_id"]["credential_types"]) <= set(CREDENTIAL_TYPE_SCHEMAS)
    assert props["http_auth"]["type"] == "object" and props["http_auth"]["default"] == {}


# ── The secret in every request ──────────────────────────────────────────────────

def test_authkey_in_url_goes_on_every_request(servidor):
    auth = _authkey()
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, bbox=(1, 2, 3, 4), cql_filter="a = 1", auth=auth)
    assert f"authkey={CHAVE}" in servidor.construcoes[0]["url"]  # o GetCapabilities
    tipos = {"hits" if p.get("resultType") == "hits" else p.get("request") for p in servidor.pedidos}
    assert {"hits", "DescribeFeatureType", "GetFeature"} <= tipos
    for pedido in servidor.pedidos:  # probe, control, DescribeFeatureType and the page
        assert pedido.get("authkey") == CHAVE


def test_authkey_in_url_also_on_the_owslib_path(servidor):
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, auth=_authkey())
    (pagina,) = servidor.requested_pages  # owslib's getfeature, without a filter
    assert pagina.get("authkey") == CHAVE


def test_configurable_parameter_name(servidor):
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, auth=_authkey(parameter="chave"))
    (pagina,) = servidor.requested_pages
    assert pagina.get("chave") == CHAVE and "authkey" not in pagina


def _signed_headers(kw: dict) -> dict:
    """The headers the request signing adds — what `requests` would send."""
    pedido = requests.Request("GET", "http://x/ows").prepare()
    kw["auth"].auth_delegate(pedido)
    return dict(pedido.headers)


def test_authkey_in_header_goes_on_every_request_and_never_in_url(servidor):
    auth = _authkey(location="header")
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, bbox=(1, 2, 3, 4), cql_filter="a = 1", auth=auth)
    assert _signed_headers(servidor.construcoes[0])["authkey"] == CHAVE  # o GetCapabilities
    assert servidor.argumentos and all(_signed_headers(kw)["authkey"] == CHAVE for kw in servidor.argumentos)
    assert not any(CHAVE in u for u in servidor.urls + [servidor.construcoes[0]["url"]])


def test_basic_goes_through_request_signing(servidor):
    auth = wfs_authentication(None, {"type": "wfs", "username": "leitor", "password": CHAVE})
    wfs._fetch_wfs_features(URL, "ns:rodovias", 10, cql_filter="a = 1", auth=auth)
    esperado = "Basic " + base64.b64encode(f"leitor:{CHAVE}".encode()).decode()
    assert _signed_headers(servidor.construcoes[0])["Authorization"] == esperado
    assert servidor.argumentos and all(_signed_headers(kw)["Authorization"] == esperado for kw in servidor.argumentos)
    assert not any(CHAVE in u for u in servidor.urls)


def test_getcapabilities_refresh_also_carries_the_key(servidor):
    # Layer missing from GetCapabilities: the node redoes it ONCE before reporting.
    with pytest.raises(ValueError):
        wfs._fetch_wfs_features(URL, "ns:publicada_agora", 10, auth=_authkey())
    assert len(servidor.construcoes) == 2
    assert all(f"authkey={CHAVE}" in c["url"] for c in servidor.construcoes)


# ── Only to the node's address ───────────────────────────────────────────────────

@pytest.mark.parametrize("endereco_do_no", ["http://outro-host/ows", "https://x/ows"])
def test_other_advertised_origin_refuses_before_getfeature(servidor, endereco_do_no):
    # GetCapabilities advertises http://x/...: another host, or the same host without TLS.
    with pytest.raises(ValueError, match="anuncia outro endereço"):
        wfs._fetch_wfs_features(endereco_do_no, "ns:rodovias", 10, auth=_authkey())
    assert servidor.urls == []  # no GetFeature, no probe


def test_without_credential_the_advertised_host_still_applies(servidor):
    wfs._fetch_wfs_features("http://outro-host/ows", "ns:rodovias", 10)
    assert len(servidor.requested_pages) == 1


# ── The secret never in a message ────────────────────────────────────────────────

@pytest.mark.parametrize("chave", [CHAVE, "a+b/c=d&e"])
def test_secret_does_not_leak_in_message_or_traceback(servidor, chave):
    from urllib.parse import quote, quote_plus
    auth = wfs_authentication(None, {"type": "geoserver_authkey", "token": chave})
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


def test_secret_does_not_leak_in_the_attempt_log(servidor, caplog):
    import logging
    servidor.paginas = [requests.ConnectionError(f"Max retries exceeded with url: /ows?authkey={CHAVE}")]
    with caplog.at_level(logging.WARNING):
        with pytest.raises(RuntimeError):
            wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 1, 0.0, None, _authkey())
    assert "tentativa" in caplog.text and CHAVE not in caplog.text


def test_while_fetching_no_process_log_carries_the_key(monkeypatch, caplog):
    # The DEBUG of urllib3 (and of owslib) writes the URL of each request.
    import logging
    import geopandas as gpd

    def _fake_fetch(*args):
        logging.getLogger("urllib3.connectionpool").debug('"GET /ows?authkey=%s HTTP/1.1" 200', CHAVE)
        return gpd.GeoDataFrame(geometry=[])

    monkeypatch.setattr(wfs, "_tentar_com_retry", _fake_fetch)
    with caplog.at_level(logging.DEBUG):
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 0, 0.0, None, _authkey())
    assert "GET /ows?authkey=***" in caplog.text and CHAVE not in caplog.text


def test_not_even_in_the_attempt_log_of_a_server_refusal(servidor, caplog):
    # The ServiceException branch (the server's own voice) has its own log.
    import logging
    from owslib.util import ServiceException
    servidor.paginas = [ServiceException(f"<ows:ExceptionText>pool esgotado em /ows?authkey={CHAVE}</ows:ExceptionText>")]
    with caplog.at_level(logging.WARNING):
        with pytest.raises(RuntimeError):
            wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 1, 0.0, None, _authkey())
    assert "tentativa" in caplog.text and CHAVE not in caplog.text


def test_configuration_error_stays_valueerror(servidor):
    # ValueError is what the executor does NOT retry: flattening it to RuntimeError
    # during redaction would make the configuration refusal be repeated.
    with pytest.raises(ValueError, match="anuncia outro endereço"):
        wfs._fetch_with_retry("http://outro-host/ows", "ns:rodovias", 10, None, None, None, 5, 2, 0.0, None, _authkey())


def test_key_echoed_with_html_entities_is_also_redacted_before_truncation(servidor):
    # A proxy echoes the key ESCAPED (`&amp;`, `&lt;`, `&#x27;`): only after
    # html.unescape does it become the key again — and the 200-character cut fell
    # in the middle of it, leaving a fragment that no redaction recognizes.
    import html as _html
    from owslib.util import ServiceException
    chave = "seg&redo<x>'42-ABCDEFGHIJ-KLMNOP"  # pragma: allowlist secret
    auth = wfs_authentication(None, {"type": "geoserver_authkey", "token": chave})
    antes = "x" * (200 - 12 - len("Unauthorized ") - len("?authkey="))
    pagina = f"<html><body>Unauthorized {antes}?authkey={_html.escape(chave, quote=True)}</body></html>"
    servidor.paginas = [ServiceException(pagina)]
    with pytest.raises((RuntimeError, ValueError)) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 0, 0.0, None, auth)
    msg = str(ei.value)
    assert "Unauthorized" in msg and "***" in msg
    assert chave[:8] not in msg and chave[8:20] not in msg


def test_basic_password_also_disappears_in_base64_form(servidor, caplog):
    # `Authorization: Basic base64(usuario:senha)` is how the password TRAVELS — and
    # it is what a proxy or WAF that echoes headers puts on the error page.
    import logging
    from owslib.util import ServiceException
    from flow.utils.credencial_wfs import secret_forms, without_secret
    auth = wfs_authentication(None, {"type": "wfs", "username": "leitor", "password": CHAVE})
    par = base64.b64encode(f"leitor:{CHAVE}".encode()).decode()
    assert par in secret_forms(auth)
    assert without_secret(f"request headers: Authorization: Basic {par}", auth) == "request headers: Authorization: Basic ***"

    servidor.paginas = [ServiceException(f"<ows:ExceptionText>proxy error; headers: Authorization: Basic {par}</ows:ExceptionText>")]
    with caplog.at_level(logging.WARNING):
        with pytest.raises(RuntimeError) as ei:
            wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 1, 0.0, None, auth)
    assert par not in str(ei.value) and par not in caplog.text and CHAVE not in caplog.text


def test_page_echoing_the_url_leaves_no_piece_of_the_key(servidor):
    # An HTML error page (a 400 from a proxy or WAF) arrives as owslib's
    # ServiceException, with the body. The message is cut at 200 characters
    # and the cut falls in the middle of the key: the first 25 of the 36 would
    # remain — and no later redaction recognizes the fragment.
    from owslib.util import ServiceException
    chave = "SEGREDO-0123456789-abcdefghij-XYZ-42"  # pragma: allowlist secret
    auth = wfs_authentication(None, {"type": "geoserver_authkey", "token": chave})
    antes = "x" * (200 - 25 - len("Unauthorized ") - len("?authkey="))
    pagina = f"<html><body>Unauthorized {antes}?authkey={chave}</body></html>"
    servidor.paginas = [ServiceException(pagina)]
    with pytest.raises((RuntimeError, ValueError)) as ei:
        wfs._fetch_with_retry(URL, "ns:rodovias", 10, None, None, None, 5, 0, 0.0, None, auth)
    assert "Unauthorized" in str(ei.value)  # the message really is the page's
    assert chave[:12] not in str(ei.value)


# ── Cache per credential ─────────────────────────────────────────────────────────

def test_capabilities_cache_is_per_credential(servidor):
    outra = wfs_authentication(None, {"type": "geoserver_authkey", "token": "outra-chave"})
    for auth in (_authkey(), outra, None, _authkey()):
        wfs._fetch_wfs_features(URL, "ns:rodovias", 10, auth=auth)
    # The same key reuses it; another key and the anonymous one build their own.
    assert len(servidor.construcoes) == 3
    assert all(CHAVE not in repr(k) for k in wfs._caps_cache)  # the cache key does not store the secret


# ── The node ─────────────────────────────────────────────────────────────────────

async def test_execute_resolves_the_credential_and_passes_it_on(monkeypatch):
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


async def test_execute_does_not_query_with_unresolved_credential(monkeypatch):
    from unittest.mock import MagicMock
    fetch = MagicMock()
    monkeypatch.setattr(wfs, "_fetch_with_retry", fetch)
    no = wfs.WFSNode("n", {"url": URL, "typeName": "ns:rodovias",
                           "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05"})
    with pytest.raises(ValueError, match="não pôde ser resolvida"):
        await no.execute({})
    fetch.assert_not_called()
