# tests/unit/test_wfs_authkey_rede.py
"""The WFS node with a credential through the real path: owslib → requests → network.

Only the `requests` send is stubbed (`HTTPAdapter.send`): URL building, the
headers, the request signing and redirect following are the libraries' own.
That is where two defects lived that the `openURL` stub (in
test_wfs_authkey.py) had no way of seeing:
- `requests` follows redirects, and only strips `Authorization` when the host
  changes — the key in a custom header went along to the other host;
- the refused password (401) was repeated on every attempt, which locks out
  LDAP/AD accounts behind the GeoServer.
"""
import io

import pytest
import requests
from requests.adapters import HTTPAdapter

import flow.nodes.datasource.wfs as wfs
from flow.utils.credencial_wfs import wfs_authentication

from .test_wfs_cql import _CAPS

URL = "http://x/ows"
CHAVE = "c0ffee-SEGREDO-42"

_MODES = {
    "url": {"type": "geoserver_authkey", "token": CHAVE},
    "cabecalho": {"type": "geoserver_authkey", "token": CHAVE, "location": "header"},
    "basic": {"type": "wfs", "username": "leitor", "password": CHAVE},
}


class _FakeNetwork:
    """Responds by the first URL fragment that matches; records each request sent."""

    def __init__(self):
        self.pedidos: list[requests.PreparedRequest] = []
        self._rules: list[tuple[str, int, bytes, dict]] = []

    def responder(self, trecho: str, status: int = 200, corpo: bytes = b"", cabecalhos: dict | None = None):
        self._rules.append((trecho, status, corpo, cabecalhos or {}))

    def enviar(self, pedido, **_):
        self.pedidos.append(pedido)
        for trecho, status, corpo, cabecalhos in self._rules:
            if trecho in pedido.url:
                return _response(pedido, status, corpo, cabecalhos)
        return _response(pedido, 404, b"", {})

    def hosts(self) -> list[str]:
        return [requests.utils.urlparse(p.url).netloc for p in self.pedidos]


def _response(pedido, status, corpo, cabecalhos):
    r = requests.Response()
    r.status_code = status
    r.headers.update(cabecalhos)
    r._content = corpo
    r._content_consumed = True
    r.raw = io.BytesIO(corpo)
    r.url = pedido.url
    r.request = pedido
    r.encoding = "utf-8"
    return r


@pytest.fixture
def rede(monkeypatch):
    falsa = _FakeNetwork()
    monkeypatch.setattr(HTTPAdapter, "send", lambda self, pedido, **kw: falsa.enviar(pedido, **kw))
    monkeypatch.setattr(wfs, "_caps_cache", {})
    monkeypatch.setattr("time.sleep", lambda s: None)
    return falsa


def _fetch_text(auth, url=URL, retries=2):
    return wfs._fetch_with_retry(url, "ns:rodovias", 10, None, None, None, 5, retries, 0.0, None, auth)


# ── Redirecionamento ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("modo", sorted(_MODES))
def test_redirect_to_another_host_is_refused_before_following(rede, modo):
    # Including nginx's `return 301 https://novo$request_uri`, which repeats the
    # query — and with it the URL key — at the new address.
    rede.responder("x/ows?", 302, cabecalhos={"Location": f"http://outro-host/ows?service=WFS&authkey={CHAVE}"})
    with pytest.raises(ValueError, match="redirecionou o pedido para outro endereço") as ei:
        _fetch_text(wfs_authentication(None, _MODES[modo]))
    assert rede.hosts() == ["x"]  # nobody went to the other host, and nothing was repeated
    assert CHAVE not in str(ei.value)


def test_redirect_to_the_same_host_on_another_port_is_refused(rede):
    rede.responder("x/ows?", 302, cabecalhos={"Location": "http://x:8443/ows?service=WFS&request=GetCapabilities"})
    with pytest.raises(ValueError, match="redirecionou"):
        _fetch_text(wfs_authentication(None, _MODES["cabecalho"]))
    assert rede.hosts() == ["x"]


def test_explicit_default_port_is_the_same_origin(rede):
    # The canned GetCapabilities advertises http://x/geoserver/ows; the node says http://x:80/ows.
    rede.responder("x:80/ows?", 200, _CAPS)
    cliente = wfs._wfs_client("http://x:80/ows", "2.0.0", 5, auth=wfs_authentication(None, _MODES["url"]))
    wfs._check_destination(cliente, "http://x:80/ows")  # does not refuse
    (metodo,) = [m for m in cliente.getOperationByName("GetFeature").methods if m["type"].lower() == "get"]
    assert f"authkey={CHAVE}" in metodo["url"]  # and the key was attached to the advertised address


def test_same_origin_redirect_that_drops_the_query_restores_the_url_key(rede):
    # nginx's `rewrite … ?` drops the query — and the key with it. In the header
    # and Basic modes the credential survives the hop; in the URL, the next
    # request went out ANONYMOUS.
    rede.responder("x/geoserver/ows?", 200, _CAPS)
    rede.responder("x/ows?", 302, cabecalhos={"Location": "/geoserver/ows?service=WFS&request=GetCapabilities&version=2.0.0"})
    cliente = wfs._wfs_client(URL, "2.0.0", 5, auth=wfs_authentication(None, _MODES["url"]))
    assert "ns:rodovias" in cliente.contents
    assert [f"authkey={CHAVE}" in p.url for p in rede.pedidos] == [True, True]
    assert rede.pedidos[1].url.startswith("http://x/geoserver/ows?service=WFS")


def test_https_to_http_on_the_same_host_is_also_refused(rede):
    rede.responder("x/ows?", 301, cabecalhos={"Location": "http://x/ows?service=WFS&request=GetCapabilities"})
    with pytest.raises(ValueError, match="redirecionou"):
        _fetch_text(wfs_authentication(None, _MODES["cabecalho"]), url="https://x/ows")
    assert [p.url.split(":")[0] for p in rede.pedidos] == ["https"]


def test_same_origin_redirect_keeps_the_key(rede):
    rede.responder("x/geoserver/ows?", 200, _CAPS)
    rede.responder("x/ows?", 302, cabecalhos={"Location": "/geoserver/ows?service=WFS&request=GetCapabilities"})
    cliente = wfs._wfs_client(URL, "2.0.0", 5, auth=wfs_authentication(None, _MODES["cabecalho"]))
    assert "ns:rodovias" in cliente.contents
    assert [p.headers.get("authkey") for p in rede.pedidos] == [CHAVE, CHAVE]


def test_without_credential_the_redirect_follows_as_always(rede):
    rede.responder("outro-host/ows?", 200, _CAPS)
    rede.responder("x/ows?", 302, cabecalhos={"Location": "http://outro-host/ows?service=WFS&request=GetCapabilities"})
    cliente = wfs._wfs_client(URL, "2.0.0", 5)
    assert "ns:rodovias" in cliente.contents and rede.hosts() == ["x", "outro-host"]


# ── Credencial recusada ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("status", [401, 403])
@pytest.mark.parametrize("modo", sorted(_MODES))
def test_refused_credential_is_not_repeated(rede, modo, status):
    rede.responder("x/ows?", status, b"<html><body>Unauthorized</body></html>")
    with pytest.raises(ValueError, match=f"recusou a credencial \\(HTTP {status}\\)") as ei:
        _fetch_text(wfs_authentication(None, _MODES[modo]), retries=2)
    assert len(rede.pedidos) == 1  # no new attempt with the wrong password
    assert CHAVE not in str(ei.value)


def test_what_actually_goes_out_in_each_mode(rede):
    rede.responder("x/ows?", 200, _CAPS)
    for modo, http_auth in _MODES.items():
        wfs._wfs_client(URL, "2.0.0", 5, auth=wfs_authentication(None, http_auth))
    url, cabecalho, basic = rede.pedidos  # in the order of _MODES
    assert f"authkey={CHAVE}" in url.url and "authkey" not in url.headers
    assert cabecalho.headers["authkey"] == CHAVE and CHAVE not in cabecalho.url
    assert basic.headers["Authorization"].startswith("Basic ") and CHAVE not in basic.url
