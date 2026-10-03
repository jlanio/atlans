# tests/unit/test_ip_real_atras_da_cloudflare.py
"""
Real client IP behind Cloudflare.

Production is client -> Cloudflare -> Traefik -> API. Cloudflare does not replace
the `X-Forwarded-For` the client sent: it APPENDS the real IP to its end. Traefik
trusts Cloudflare's ranges (`forwardedHeaders.trustedIPs`) and passes the header
on as it came. So the FIRST element of the XFF is what the client wrote — and
that was exactly what `get_client_ip` used. Any client could switch identity on
every request, defeating rate limiting and auditing.

What counts is the RIGHT side of the header: each element on the right was written
by a hop we trust. `get_client_ip` walks from right to left skipping
`TRUSTED_PROXIES` (Traefik's network) and `EDGE_PROXIES` (Cloudflare) and
returns the first IP left over.

  FORJADO     (forged) junk on the left is ignored; the IP appended by Cloudflare wins.
  DIRETO      (direct) peer outside TRUSTED_PROXIES: the whole header is ignored.
  IPV6        Cloudflare's IPv6 ranges are skipped too.
  SO PROXIES  (only proxies) if every element is a known proxy, the leftmost wins.
  DESLIGADO   (off) EDGE_PROXIES="" (explicitly empty) differs from ABSENT (Cloudflare).
  INVALIDO    (invalid) a mistyped range is ignored with a log; it does not break the import.
  ANTIGOS     (old) the previous contracts of get_client_ip still hold.
"""
from __future__ import annotations

import importlib
import ipaddress
import logging

import pytest

TRAEFIK = "172.18.0.5"          # the API's peer: Traefik's network (TRUSTED_PROXIES)
CF_EDGE_V4 = "104.16.1.1"       # within 104.16.0.0/13
CF_EDGE_V6 = "2606:4700::1234"  # within 2606:4700::/32
CLIENTE = "203.0.113.9"


@pytest.fixture
def recarrega(monkeypatch):
    """
    Reloads trusted_proxy with controlled TRUSTED_PROXIES/EDGE_PROXIES and
    restores the module at the end (same technique as test_ip_de_auditoria_atras_do_proxy).

    `edge=None` is the ABSENT variable (Cloudflare default); `edge=""` is the
    explicit empty value (off).
    """
    import app.core.trusted_proxy as tp

    def _reload(edge: str | None = None, trusted: str = "172.16.0.0/12"):
        monkeypatch.setenv("TRUSTED_PROXIES", trusted)
        if edge is None:
            monkeypatch.delenv("EDGE_PROXIES", raising=False)
        else:
            monkeypatch.setenv("EDGE_PROXIES", edge)
        importlib.reload(tp)
        return tp

    yield _reload
    monkeypatch.undo()    # original env back...
    importlib.reload(tp)  # ...and the module reloaded with it


# ── FORJADO ──────────────────────────────────────────────────────────────────

def test_lixo_a_esquerda_e_ignorado_vale_o_ip_anexado_pela_cloudflare(recarrega):
    """The bug scenario: the client sends its own XFF, Cloudflare appends the
    real IP and Traefik appends the edge. Before, the 1st element was the key."""
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"forjado, {CLIENTE}, {CF_EDGE_V4}") == CLIENTE
    assert tp.get_client_ip(TRAEFIK, f"1.2.3.4, {CLIENTE}, {CF_EDGE_V4}") == CLIENTE


# ── DIRETO ───────────────────────────────────────────────────────────────────

def test_direto_ao_origin_o_header_inteiro_e_ignorado(recarrega):
    """Peer outside TRUSTED_PROXIES: not even the right side of the header counts."""
    tp = recarrega()
    assert tp.get_client_ip("198.51.100.7", "forjado") == "198.51.100.7"
    assert tp.get_client_ip("198.51.100.7", f"forjado, {CLIENTE}, {CF_EDGE_V4}") == "198.51.100.7"


# ── IPV6 ─────────────────────────────────────────────────────────────────────

def test_edge_ipv6_da_cloudflare_tambem_e_pulado(recarrega):
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"2001:db8::9, {CF_EDGE_V6}") == "2001:db8::9"


# ── SO PROXIES ───────────────────────────────────────────────────────────────

def test_todos_proxies_conhecidos_vale_o_mais_a_esquerda(recarrega):
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"{TRAEFIK}, {CF_EDGE_V4}") == TRAEFIK


# ── DESLIGADO / AUSENTE ──────────────────────────────────────────────────────

def test_edge_proxies_vazio_desliga_o_default(recarrega):
    """Without Cloudflare in front, the last IP of the header IS the client."""
    tp = recarrega(edge="")
    assert tp.EDGE_PROXIES == []
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, {CF_EDGE_V4}") == CF_EDGE_V4


def test_edge_proxies_ausente_e_a_lista_da_cloudflare(recarrega):
    tp = recarrega(edge=None)
    esperadas = [p.strip() for p in tp.CLOUDFLARE_RANGES.split(",") if p.strip()]
    # no entry of the constant was discarded as invalid
    assert len(tp.EDGE_PROXIES) == len(esperadas)
    assert ipaddress.ip_network("104.16.0.0/13") in tp.EDGE_PROXIES
    assert ipaddress.ip_network("2606:4700::/32") in tp.EDGE_PROXIES


def test_edge_proxies_customizado_substitui_o_default(recarrega):
    tp = recarrega(edge="198.51.100.0/24")
    assert tp.EDGE_PROXIES == [ipaddress.ip_network("198.51.100.0/24")]
    # Cloudflare is no longer skipped...
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, {CF_EDGE_V4}") == CF_EDGE_V4
    # ...e a faixa customizada passou a ser
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, 198.51.100.7") == CLIENTE


# ── INVALIDO ─────────────────────────────────────────────────────────────────

def test_edge_proxies_invalido_e_ignorado_com_log_sem_derrubar_o_import(
    recarrega, monkeypatch, caplog,
):
    # The app's logger may have propagate=False (its own handlers) depending
    # on who created it first; ensures the record reaches caplog.
    monkeypatch.setattr(logging.getLogger("app.core.trusted_proxy"), "propagate", True)
    with caplog.at_level(logging.ERROR, logger="app.core.trusted_proxy"):
        tp = recarrega(edge="banana, 104.16.0.0/13")
    assert tp.EDGE_PROXIES == [ipaddress.ip_network("104.16.0.0/13")]
    assert any(
        "EDGE_PROXIES" in r.getMessage() and "banana" in r.getMessage()
        for r in caplog.records
    ), "entrada invalida tem de ser logada com o nome da variavel"
    # a parte valida continua funcionando
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, {CF_EDGE_V4}") == CLIENTE


# ── ANTIGOS ──────────────────────────────────────────────────────────────────

def test_proxy_interno_a_direita_continua_sendo_pulado(recarrega):
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, {TRAEFIK}") == CLIENTE


def test_peer_nao_confiavel_continua_nao_podendo_forjar(recarrega):
    tp = recarrega()
    assert tp.get_client_ip("198.51.100.7", CLIENTE) == "198.51.100.7"


def test_sem_forwarded_for_continua_caindo_no_peer(recarrega):
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, None) == TRAEFIK
    assert tp.get_client_ip(TRAEFIK, "") == TRAEFIK


def test_sem_peer_continua_unknown(recarrega):
    tp = recarrega()
    assert tp.get_client_ip(None, None) == "unknown"


def test_trusted_proxies_vazio_continua_ignorando_o_header(recarrega):
    """Asymmetry preserved: is_trusted_proxy() is True (check disabled),
    but the XFF is not read — in dev without a proxy, the peer IS the client."""
    tp = recarrega(trusted="")
    assert tp.is_trusted_proxy("203.0.113.9") is True
    assert tp.get_client_ip("203.0.113.9", f"1.2.3.4, {CF_EDGE_V4}") == "203.0.113.9"


# ── Decisions documented in get_client_ip's docstring ───────────────────────

def test_elementos_que_nao_sao_ip_sao_pulados_e_sem_nenhum_valido_vale_o_peer(recarrega):
    tp = recarrega()
    # `unknown` e `ip:porta` nao contam; o IP valido seguinte a esquerda vale
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, unknown, 10.0.0.1:8080, {CF_EDGE_V4}") == CLIENTE
    # no valid element: peer
    assert tp.get_client_ip(TRAEFIK, "unknown, , lixo") == TRAEFIK


def test_ip_devolvido_na_forma_canonica(recarrega):
    """Same client, same bucket — regardless of how the IPv6 was written."""
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"2001:DB8:0000::0009, {CF_EDGE_V6}") == "2001:db8::9"


def test_is_trusted_proxy_nao_avaliza_a_cloudflare(recarrega):
    """EDGE_PROXIES does not authorize the mTLS cert header: only TRUSTED_PROXIES."""
    tp = recarrega()
    assert tp.is_trusted_proxy(CF_EDGE_V4) is False
    assert tp.is_trusted_proxy(TRAEFIK) is True


# ── CLOUDFLARE WORKER ────────────────────────────────────────────────────────
# A Worker that calls atlans.example.org reaches Cloudflare with the Workers'
# egress IP (2a06:98c0:3600::103, within its ranges) and sends whatever XFF it
# wants; Cloudflare appends that IP and Traefik appends the edge. By skipping ALL
# of Cloudflare's hops, the value written by the Worker became the identity.

WORKER_EGRESS = "2a06:98c0:3600::103"
CF_EDGE_2 = "172.70.1.2"  # within 172.64.0.0/13


def test_worker_da_cloudflare_nao_escolhe_a_propria_identidade(recarrega):
    tp = recarrega()
    for forjado in ("6.6.6.6", "7.7.7.7", "203.0.113.9"):
        assert tp.get_client_ip(TRAEFIK, f"{forjado}, {WORKER_EGRESS}, {CF_EDGE_2}") == WORKER_EGRESS


def test_so_um_salto_de_borda_e_pulado(recarrega):
    """Two edges in a row: the second (from right to left) is the one that
    connected to Cloudflare, and it is the client — even though it is within its ranges."""
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, {CF_EDGE_V4}, {CF_EDGE_2}") == CF_EDGE_V4


def test_infra_interna_a_direita_e_pulada_antes_do_edge(recarrega):
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"forjado, {CLIENTE}, {CF_EDGE_V4}, {TRAEFIK}") == CLIENTE
