# tests/unit/test_mtls_header_trust.py
"""Trust in the mTLS cert header and in the IP forwarded by the proxy.

Regression (critical): the executor's entire identity comes from
`X-Forwarded-Tls-Client-Cert-Info`. Traefik's `passTLSClientCert` only
OVERWRITES that header when there is a client cert — it never removes a header
already present. With `clientAuthType: VerifyClientCertIfGiven`, a client with
no cert at all had the forged header passed intact to the backend.
"""
import pytest
from fastapi import HTTPException

from app.api.dependencies import (
    _parse_traefik_client_cert,
    _serial_to_int,
    assert_request_from_trusted_proxy,
)
from app.core import trusted_proxy


# ── Header parsing ────────────────────────────────────────────────────────────

def test_parse_extrai_cn_e_serial():
    cn, serial = _parse_traefik_client_cert('Subject="CN=executor-abc123";SerialNumber="42"')
    assert cn == "executor-abc123"
    assert serial == "42"


def test_parse_aceita_valor_url_encoded():
    cn, serial = _parse_traefik_client_cert('Subject%3D%22CN%3Dexecutor-abc%22%3BSerialNumber%3D%2242%22')
    assert cn == "executor-abc"
    assert serial == "42"


def test_cn_fora_do_subject_e_ignorado():
    """CN only counts inside Subject=... — never from Issuer or another field."""
    header = 'Issuer="CN=executor-vitima";Subject="CN=executor-real";SerialNumber="7"'
    cn, _ = _parse_traefik_client_cert(header)
    assert cn == "executor-real"


def test_subject_sem_aspas_tambem_e_aceito():
    """Quotes are optional in Traefik's header (the serial already had both
    variants). Requiring quotes would take down every executor at once."""
    cn, serial = _parse_traefik_client_cert('Subject=CN=executor-abc;SerialNumber=2acb673f')
    assert cn == "executor-abc"
    assert serial == "2acb673f"


def test_header_vazio_nao_produz_identidade():
    assert _parse_traefik_client_cert("") == (None, None)


# ── Serial: base explicita ────────────────────────────────────────────────────

def test_serial_hex_do_db_e_decimal_do_header_convergem():
    """DB guarda hex, Traefik manda decimal — mesmo cert, mesmo int."""
    serial_int = 56883706168065981647801696766709589867
    assert _serial_to_int(format(serial_int, "x"), source="db") == serial_int
    assert _serial_to_int(str(serial_int), source="header") == serial_int


def test_serial_hex_so_com_digitos_nao_e_confundido_com_decimal():
    """'123456' em hex != 123456 em decimal — a base vem do `source`."""
    assert _serial_to_int("123456", source="db") == 0x123456
    assert _serial_to_int("123456", source="header") == 123456


# ── Trust in the proxy ────────────────────────────────────────────────────────

@pytest.fixture
def com_proxy_confiavel(monkeypatch):
    import ipaddress
    monkeypatch.setattr(
        trusted_proxy, "TRUSTED_PROXIES", [ipaddress.ip_network("172.16.0.0/12")],
    )
    # No edge proxies: the asserts below don't depend on the default (Cloudflare).
    monkeypatch.setattr(trusted_proxy, "EDGE_PROXIES", [])


def test_header_de_origem_nao_confiavel_e_rejeitado(com_proxy_confiavel):
    with pytest.raises(HTTPException) as exc:
        assert_request_from_trusted_proxy("203.0.113.9", "/internal/send-email")
    assert exc.value.status_code == 401


def test_header_vindo_do_proxy_e_aceito(com_proxy_confiavel):
    assert_request_from_trusted_proxy("172.18.0.5", "/internal/send-email")


def test_sem_trusted_proxies_configurado_aceita_qualquer_origem(monkeypatch):
    """Dev mode: with no proxy in front, the check is disabled."""
    monkeypatch.setattr(trusted_proxy, "TRUSTED_PROXIES", [])
    assert_request_from_trusted_proxy("203.0.113.9", "/qualquer")


# ── Real IP for rate limiting ─────────────────────────────────────────────────

def test_forwarded_for_so_e_usado_se_o_peer_for_o_proxy(com_proxy_confiavel):
    assert trusted_proxy.get_client_ip("172.18.0.5", "198.51.100.7, 172.18.0.5") == "198.51.100.7"


def test_forwarded_for_forjado_por_cliente_direto_e_ignorado(com_proxy_confiavel):
    """Without this, anyone could switch identity on every request and the rate
    limit would never trigger."""
    assert trusted_proxy.get_client_ip("203.0.113.9", "1.2.3.4") == "203.0.113.9"
