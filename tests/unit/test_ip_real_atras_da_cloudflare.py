# tests/unit/test_ip_real_atras_da_cloudflare.py
"""
IP real do cliente atras da Cloudflare.

Producao e cliente -> Cloudflare -> Traefik -> API. A Cloudflare nao substitui
o `X-Forwarded-For` que o cliente mandou: ANEXA o IP real ao fim dele. O
Traefik confia nas faixas da Cloudflare (`forwardedHeaders.trustedIPs`) e
repassa o header como veio. Logo o PRIMEIRO elemento do XFF e o que o cliente
escreveu — e era exatamente o que `get_client_ip` usava. Qualquer cliente
trocava de identidade a cada request, anulando rate limit e auditoria.

O que vale e o lado DIREITO do header: cada elemento a direita foi escrito por
um salto em que confiamos. `get_client_ip` caminha da direita para a esquerda
pulando `TRUSTED_PROXIES` (rede do Traefik) e `EDGE_PROXIES` (Cloudflare) e
devolve o primeiro IP que sobra.

  FORJADO     lixo a esquerda e ignorado; vale o IP anexado pela Cloudflare.
  DIRETO      peer fora de TRUSTED_PROXIES: o header inteiro e ignorado.
  IPV6        as faixas IPv6 da Cloudflare tambem sao puladas.
  SO PROXIES  se todos os elementos sao proxies conhecidos, vale o mais a esquerda.
  DESLIGADO   EDGE_PROXIES="" (vazio explicito) e diferente de AUSENTE (Cloudflare).
  INVALIDO    faixa mal digitada e ignorada com log; nao derruba o import.
  ANTIGOS     os contratos anteriores de get_client_ip continuam valendo.
"""
from __future__ import annotations

import importlib
import ipaddress
import logging

import pytest

TRAEFIK = "172.18.0.5"          # peer da API: rede do Traefik (TRUSTED_PROXIES)
CF_EDGE_V4 = "104.16.1.1"       # dentro de 104.16.0.0/13
CF_EDGE_V6 = "2606:4700::1234"  # dentro de 2606:4700::/32
CLIENTE = "203.0.113.9"


@pytest.fixture
def recarrega(monkeypatch):
    """
    Recarrega trusted_proxy com TRUSTED_PROXIES/EDGE_PROXIES controladas e
    restaura o modulo ao final (mesma tecnica de test_ip_de_auditoria_atras_do_proxy).

    `edge=None` e a variavel AUSENTE (default Cloudflare); `edge=""` e o vazio
    explicito (desligado).
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
    monkeypatch.undo()    # env original de volta...
    importlib.reload(tp)  # ...e o modulo recarregado com ela


# ── FORJADO ──────────────────────────────────────────────────────────────────

def test_lixo_a_esquerda_e_ignorado_vale_o_ip_anexado_pela_cloudflare(recarrega):
    """O cenario do bug: o cliente manda um XFF proprio, a Cloudflare anexa o
    IP real e o Traefik anexa o edge. Antes, o 1o elemento era a chave."""
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"forjado, {CLIENTE}, {CF_EDGE_V4}") == CLIENTE
    assert tp.get_client_ip(TRAEFIK, f"1.2.3.4, {CLIENTE}, {CF_EDGE_V4}") == CLIENTE


# ── DIRETO ───────────────────────────────────────────────────────────────────

def test_direto_ao_origin_o_header_inteiro_e_ignorado(recarrega):
    """Peer fora de TRUSTED_PROXIES: nem o lado direito do header vale."""
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
    """Sem Cloudflare na frente, o ultimo IP do header E o cliente."""
    tp = recarrega(edge="")
    assert tp.EDGE_PROXIES == []
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, {CF_EDGE_V4}") == CF_EDGE_V4


def test_edge_proxies_ausente_e_a_lista_da_cloudflare(recarrega):
    tp = recarrega(edge=None)
    esperadas = [p.strip() for p in tp.CLOUDFLARE_RANGES.split(",") if p.strip()]
    # nenhuma entrada da constante foi descartada como invalida
    assert len(tp.EDGE_PROXIES) == len(esperadas)
    assert ipaddress.ip_network("104.16.0.0/13") in tp.EDGE_PROXIES
    assert ipaddress.ip_network("2606:4700::/32") in tp.EDGE_PROXIES


def test_edge_proxies_customizado_substitui_o_default(recarrega):
    tp = recarrega(edge="198.51.100.0/24")
    assert tp.EDGE_PROXIES == [ipaddress.ip_network("198.51.100.0/24")]
    # a Cloudflare deixou de ser pulada...
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, {CF_EDGE_V4}") == CF_EDGE_V4
    # ...e a faixa customizada passou a ser
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, 198.51.100.7") == CLIENTE


# ── INVALIDO ─────────────────────────────────────────────────────────────────

def test_edge_proxies_invalido_e_ignorado_com_log_sem_derrubar_o_import(
    recarrega, monkeypatch, caplog,
):
    # O logger da app pode ter propagate=False (handlers proprios) dependendo
    # de quem o criou primeiro; garante que o record chegue ao caplog.
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
    """Assimetria preservada: is_trusted_proxy() e True (checagem desligada),
    mas o XFF nao e lido — em dev sem proxy, o peer E o cliente."""
    tp = recarrega(trusted="")
    assert tp.is_trusted_proxy("203.0.113.9") is True
    assert tp.get_client_ip("203.0.113.9", f"1.2.3.4, {CF_EDGE_V4}") == "203.0.113.9"


# ── Decisoes documentadas na docstring de get_client_ip ─────────────────────

def test_elementos_que_nao_sao_ip_sao_pulados_e_sem_nenhum_valido_vale_o_peer(recarrega):
    tp = recarrega()
    # `unknown` e `ip:porta` nao contam; o IP valido seguinte a esquerda vale
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, unknown, 10.0.0.1:8080, {CF_EDGE_V4}") == CLIENTE
    # nenhum elemento valido: peer
    assert tp.get_client_ip(TRAEFIK, "unknown, , lixo") == TRAEFIK


def test_ip_devolvido_na_forma_canonica(recarrega):
    """Mesmo cliente, mesmo balde — independente de como o IPv6 foi escrito."""
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"2001:DB8:0000::0009, {CF_EDGE_V6}") == "2001:db8::9"


def test_is_trusted_proxy_nao_avaliza_a_cloudflare(recarrega):
    """EDGE_PROXIES nao autoriza o header de cert mTLS: so TRUSTED_PROXIES."""
    tp = recarrega()
    assert tp.is_trusted_proxy(CF_EDGE_V4) is False
    assert tp.is_trusted_proxy(TRAEFIK) is True


# ── WORKER DA CLOUDFLARE ─────────────────────────────────────────────────────
# Um Worker que chama a atlans.example.org chega à Cloudflare com o IP de saída dos
# Workers (2a06:98c0:3600::103, dentro das faixas dela) e manda o XFF que
# quiser; a Cloudflare anexa aquele IP e o Traefik anexa o edge. Pulando TODOS
# os saltos da Cloudflare, o valor escrito pelo Worker virava a identidade.

WORKER_EGRESS = "2a06:98c0:3600::103"
CF_EDGE_2 = "172.70.1.2"  # dentro de 172.64.0.0/13


def test_worker_da_cloudflare_nao_escolhe_a_propria_identidade(recarrega):
    tp = recarrega()
    for forjado in ("6.6.6.6", "7.7.7.7", "203.0.113.9"):
        assert tp.get_client_ip(TRAEFIK, f"{forjado}, {WORKER_EGRESS}, {CF_EDGE_2}") == WORKER_EGRESS


def test_so_um_salto_de_borda_e_pulado(recarrega):
    """Dois edges seguidos: o segundo (da direita para a esquerda) é quem se
    conectou à Cloudflare, e é ele o cliente — mesmo estando nas faixas dela."""
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"{CLIENTE}, {CF_EDGE_V4}, {CF_EDGE_2}") == CF_EDGE_V4


def test_infra_interna_a_direita_e_pulada_antes_do_edge(recarrega):
    tp = recarrega()
    assert tp.get_client_ip(TRAEFIK, f"forjado, {CLIENTE}, {CF_EDGE_V4}, {TRAEFIK}") == CLIENTE
