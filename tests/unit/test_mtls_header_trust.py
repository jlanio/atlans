# tests/unit/test_mtls_header_trust.py
"""Confianca no header de cert mTLS e no IP encaminhado pelo proxy.

Regressao (critica): toda a identidade do executor vem de
`X-Forwarded-Tls-Client-Cert-Info`. O `passTLSClientCert` do Traefik apenas
SOBRESCREVE esse header quando ha client cert — ele nunca remove um header ja
presente. Com `clientAuthType: VerifyClientCertIfGiven`, um cliente sem cert
nenhum tinha o header forjado repassado intacto ao backend.
"""
import pytest
from fastapi import HTTPException

from app.api.dependencies import (
    _parse_traefik_client_cert,
    _serial_to_int,
    assert_request_from_trusted_proxy,
)
from app.core import trusted_proxy


# ── Parsing do header ─────────────────────────────────────────────────────────

def test_parse_extrai_cn_e_serial():
    cn, serial = _parse_traefik_client_cert('Subject="CN=executor-abc123";SerialNumber="42"')
    assert cn == "executor-abc123"
    assert serial == "42"


def test_parse_aceita_valor_url_encoded():
    cn, serial = _parse_traefik_client_cert('Subject%3D%22CN%3Dexecutor-abc%22%3BSerialNumber%3D%2242%22')
    assert cn == "executor-abc"
    assert serial == "42"


def test_cn_fora_do_subject_e_ignorado():
    """CN so vale dentro de Subject=... — nunca de Issuer ou outro campo."""
    header = 'Issuer="CN=executor-vitima";Subject="CN=executor-real";SerialNumber="7"'
    cn, _ = _parse_traefik_client_cert(header)
    assert cn == "executor-real"


def test_subject_sem_aspas_tambem_e_aceito():
    """As aspas sao opcionais no header do Traefik (o serial ja tinha as duas
    variantes). Exigir aspas derrubaria todos os executores de uma vez."""
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


# ── Confianca no proxy ────────────────────────────────────────────────────────

@pytest.fixture
def com_proxy_confiavel(monkeypatch):
    import ipaddress
    monkeypatch.setattr(
        trusted_proxy, "TRUSTED_PROXIES", [ipaddress.ip_network("172.16.0.0/12")],
    )
    # Sem proxies de borda: os asserts abaixo nao dependem do default (Cloudflare).
    monkeypatch.setattr(trusted_proxy, "EDGE_PROXIES", [])


def test_header_de_origem_nao_confiavel_e_rejeitado(com_proxy_confiavel):
    with pytest.raises(HTTPException) as exc:
        assert_request_from_trusted_proxy("203.0.113.9", "/internal/send-email")
    assert exc.value.status_code == 401


def test_header_vindo_do_proxy_e_aceito(com_proxy_confiavel):
    assert_request_from_trusted_proxy("172.18.0.5", "/internal/send-email")


def test_sem_trusted_proxies_configurado_aceita_qualquer_origem(monkeypatch):
    """Modo dev: sem proxy na frente, a checagem fica desativada."""
    monkeypatch.setattr(trusted_proxy, "TRUSTED_PROXIES", [])
    assert_request_from_trusted_proxy("203.0.113.9", "/qualquer")


# ── IP real para rate limit ───────────────────────────────────────────────────

def test_forwarded_for_so_e_usado_se_o_peer_for_o_proxy(com_proxy_confiavel):
    assert trusted_proxy.get_client_ip("172.18.0.5", "198.51.100.7, 172.18.0.5") == "198.51.100.7"


def test_forwarded_for_forjado_por_cliente_direto_e_ignorado(com_proxy_confiavel):
    """Sem isso, qualquer um trocaria de identidade a cada request e o rate
    limit nunca dispararia."""
    assert trusted_proxy.get_client_ip("203.0.113.9", "1.2.3.4") == "203.0.113.9"
