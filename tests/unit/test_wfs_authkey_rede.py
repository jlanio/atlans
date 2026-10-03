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
from flow.utils.credencial_wfs import autenticacao_wfs

from .test_wfs_cql import _CAPS

URL = "http://x/ows"
CHAVE = "c0ffee-SEGREDO-42"

_MODOS = {
    "url": {"type": "geoserver_authkey", "token": CHAVE},
    "cabecalho": {"type": "geoserver_authkey", "token": CHAVE, "location": "header"},
    "basic": {"type": "wfs", "username": "leitor", "password": CHAVE},
}


class _Rede:
    """Responds by the first URL fragment that matches; records each request sent."""

    def __init__(self):
        self.pedidos: list[requests.PreparedRequest] = []
        self._regras: list[tuple[str, int, bytes, dict]] = []

    def responder(self, trecho: str, status: int = 200, corpo: bytes = b"", cabecalhos: dict | None = None):
        self._regras.append((trecho, status, corpo, cabecalhos or {}))

    def enviar(self, pedido, **_):
        self.pedidos.append(pedido)
        for trecho, status, corpo, cabecalhos in self._regras:
            if trecho in pedido.url:
                return _resposta(pedido, status, corpo, cabecalhos)
        return _resposta(pedido, 404, b"", {})

    def hosts(self) -> list[str]:
        return [requests.utils.urlparse(p.url).netloc for p in self.pedidos]


def _resposta(pedido, status, corpo, cabecalhos):
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
    falsa = _Rede()
    monkeypatch.setattr(HTTPAdapter, "send", lambda self, pedido, **kw: falsa.enviar(pedido, **kw))
    monkeypatch.setattr(wfs, "_caps_cache", {})
    monkeypatch.setattr("time.sleep", lambda s: None)
    return falsa


def _buscar(auth, url=URL, retries=2):
    return wfs._fetch_with_retry(url, "ns:rodovias", 10, None, None, None, 5, retries, 0.0, None, auth)


# ── Redirecionamento ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("modo", sorted(_MODOS))
def test_redirecionamento_para_outro_host_e_recusado_antes_de_seguir(rede, modo):
    # Including nginx's `return 301 https://novo$request_uri`, which repeats the
    # query — and with it the URL key — at the new address.
    rede.responder("x/ows?", 302, cabecalhos={"Location": f"http://outro-host/ows?service=WFS&authkey={CHAVE}"})
    with pytest.raises(ValueError, match="redirecionou o pedido para outro endereço") as ei:
        _buscar(autenticacao_wfs(None, _MODOS[modo]))
    assert rede.hosts() == ["x"]  # nobody went to the other host, and nothing was repeated
    assert CHAVE not in str(ei.value)


def test_redirecionamento_para_o_mesmo_host_em_outra_porta_e_recusado(rede):
    rede.responder("x/ows?", 302, cabecalhos={"Location": "http://x:8443/ows?service=WFS&request=GetCapabilities"})
    with pytest.raises(ValueError, match="redirecionou"):
        _buscar(autenticacao_wfs(None, _MODOS["cabecalho"]))
    assert rede.hosts() == ["x"]


def test_a_porta_padrao_explicita_e_a_mesma_origem(rede):
    # The canned GetCapabilities advertises http://x/geoserver/ows; the node says http://x:80/ows.
    rede.responder("x:80/ows?", 200, _CAPS)
    cliente = wfs._wfs_client("http://x:80/ows", "2.0.0", 5, auth=autenticacao_wfs(None, _MODOS["url"]))
    wfs._conferir_destino(cliente, "http://x:80/ows")  # does not refuse
    (metodo,) = [m for m in cliente.getOperationByName("GetFeature").methods if m["type"].lower() == "get"]
    assert f"authkey={CHAVE}" in metodo["url"]  # and the key was attached to the advertised address


def test_redirecionamento_na_mesma_origem_que_perde_a_query_repoe_a_chave_da_url(rede):
    # nginx's `rewrite … ?` drops the query — and the key with it. In the header
    # and Basic modes the credential survives the hop; in the URL, the next
    # request went out ANONYMOUS.
    rede.responder("x/geoserver/ows?", 200, _CAPS)
    rede.responder("x/ows?", 302, cabecalhos={"Location": "/geoserver/ows?service=WFS&request=GetCapabilities&version=2.0.0"})
    cliente = wfs._wfs_client(URL, "2.0.0", 5, auth=autenticacao_wfs(None, _MODOS["url"]))
    assert "ns:rodovias" in cliente.contents
    assert [f"authkey={CHAVE}" in p.url for p in rede.pedidos] == [True, True]
    assert rede.pedidos[1].url.startswith("http://x/geoserver/ows?service=WFS")


def test_https_para_http_no_mesmo_host_tambem_e_recusado(rede):
    rede.responder("x/ows?", 301, cabecalhos={"Location": "http://x/ows?service=WFS&request=GetCapabilities"})
    with pytest.raises(ValueError, match="redirecionou"):
        _buscar(autenticacao_wfs(None, _MODOS["cabecalho"]), url="https://x/ows")
    assert [p.url.split(":")[0] for p in rede.pedidos] == ["https"]


def test_redirecionamento_na_mesma_origem_segue_com_a_chave(rede):
    rede.responder("x/geoserver/ows?", 200, _CAPS)
    rede.responder("x/ows?", 302, cabecalhos={"Location": "/geoserver/ows?service=WFS&request=GetCapabilities"})
    cliente = wfs._wfs_client(URL, "2.0.0", 5, auth=autenticacao_wfs(None, _MODOS["cabecalho"]))
    assert "ns:rodovias" in cliente.contents
    assert [p.headers.get("authkey") for p in rede.pedidos] == [CHAVE, CHAVE]


def test_sem_credencial_o_redirecionamento_segue_como_sempre(rede):
    rede.responder("outro-host/ows?", 200, _CAPS)
    rede.responder("x/ows?", 302, cabecalhos={"Location": "http://outro-host/ows?service=WFS&request=GetCapabilities"})
    cliente = wfs._wfs_client(URL, "2.0.0", 5)
    assert "ns:rodovias" in cliente.contents and rede.hosts() == ["x", "outro-host"]


# ── Credencial recusada ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("status", [401, 403])
@pytest.mark.parametrize("modo", sorted(_MODOS))
def test_credencial_recusada_nao_e_repetida(rede, modo, status):
    rede.responder("x/ows?", status, b"<html><body>Unauthorized</body></html>")
    with pytest.raises(ValueError, match=f"recusou a credencial \\(HTTP {status}\\)") as ei:
        _buscar(autenticacao_wfs(None, _MODOS[modo]), retries=2)
    assert len(rede.pedidos) == 1  # no new attempt with the wrong password
    assert CHAVE not in str(ei.value)


def test_o_que_sai_de_verdade_em_cada_modo(rede):
    rede.responder("x/ows?", 200, _CAPS)
    for modo, http_auth in _MODOS.items():
        wfs._wfs_client(URL, "2.0.0", 5, auth=autenticacao_wfs(None, http_auth))
    url, cabecalho, basic = rede.pedidos  # in the order of _MODOS
    assert f"authkey={CHAVE}" in url.url and "authkey" not in url.headers
    assert cabecalho.headers["authkey"] == CHAVE and CHAVE not in cabecalho.url
    assert basic.headers["Authorization"].startswith("Basic ") and CHAVE not in basic.url
