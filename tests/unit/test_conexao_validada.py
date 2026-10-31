"""Connection-time SSRF check for owslib/requests (flow/utils/conexao_validada.py)."""
import socket

import pytest
import requests

from flow.utils import conexao_validada as cv


def _resolve_para(monkeypatch, ip):
    def fake(host, port, *a, **k):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
    monkeypatch.setattr(socket, "getaddrinfo", fake)


def test_a_name_that_resolves_to_an_internal_address_is_refused(monkeypatch):
    monkeypatch.setattr(cv, "_hosts_de_proxy", lambda: set())
    _resolve_para(monkeypatch, "169.254.169.254")
    with cv.conexoes_validadas():
        with pytest.raises(ValueError, match="internos"):
            requests.get("http://metadata.exemplo.org/latest", timeout=2)


def test_the_validated_address_is_the_one_connected(monkeypatch):
    import urllib3.util.connection as conexao

    chamadas = []
    # A fresh install over a recording "original" (monkeypatch restores both
    # the module attribute and the flag, so the real wrapper survives).
    monkeypatch.setattr(cv, "_instalado", False)
    monkeypatch.setattr(conexao, "create_connection", lambda address, *a, **k: chamadas.append(address) or "sock")
    monkeypatch.setattr(cv, "_hosts_de_proxy", lambda: set())
    cv._instalar()
    _resolve_para(monkeypatch, "93.184.216.34")

    with cv.conexoes_validadas():
        assert conexao.create_connection(("site.exemplo.org", 80), timeout=1) == "sock"
    assert chamadas == [("93.184.216.34", 80)]

    # Unmarked thread: the original receives the name untouched.
    conexao.create_connection(("site.exemplo.org", 80), timeout=1)
    assert chamadas[-1] == ("site.exemplo.org", 80)


def test_unmarked_threads_are_untouched(monkeypatch):
    import urllib3.util.connection as conexao

    cv._instalar()
    _resolve_para(monkeypatch, "127.0.0.1")
    # Outside the block an internal address is not refused by this layer
    # (it fails to connect or connects — but never with the SSRF ValueError).
    try:
        conexao.create_connection(("127.0.0.1", 9), timeout=0.2).close()
    except OSError:
        pass
