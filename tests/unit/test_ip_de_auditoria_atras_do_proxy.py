# tests/unit/test_ip_de_auditoria_atras_do_proxy.py
"""
IP real do cliente nos registros de auditoria e telemetria.

Dois campos gravavam `client.host` cru:

  consumed_from_ip     trilha de auditoria do enrollment de executor
  RunMetrics.executor_ip  telemetria de qual maquina rodou o job

Atras do Traefik, `client.host` e o IP do PROXY para todo mundo. Os dois campos
registravam sempre o mesmo endereco — a trilha de auditoria do enrollment nao
distinguia nada, e a telemetria dizia que a frota inteira vinha de uma maquina
so. `app/core/trusted_proxy.get_client_ip` ja existia e a docstring dele nomeia
exatamente esse problema.

Duas propriedades importam, e a segunda e a que impede a correcao de virar um
buraco novo:

  RESOLVE     atras de proxy CONFIAVEL, vale o primeiro IP do X-Forwarded-For.
  NAO FORJA   vindo de peer NAO confiavel, o header e ignorado — senao qualquer
              cliente trocaria de identidade a cada request e a "auditoria"
              passaria a registrar o que o auditado quisesse.

E uma terceira, especifica da coluna:

  NULL        `executor_ip` e nullable. Sem peer, o valor tem de continuar NULL
              e nao virar a string "unknown", que parece um dado e nao e.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def proxy_confiavel(monkeypatch):
    """Recarrega trusted_proxy com uma rede confiavel configurada."""
    monkeypatch.setenv("TRUSTED_PROXIES", "172.16.0.0/12")
    import app.core.trusted_proxy as tp
    importlib.reload(tp)
    yield tp
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    importlib.reload(tp)


# ── RESOLVE / NAO FORJA ──────────────────────────────────────────────────────

def test_atras_de_proxy_confiavel_usa_o_forwarded_for(proxy_confiavel):
    ip = proxy_confiavel.get_client_ip("172.18.0.5", "203.0.113.9, 172.18.0.5")
    assert ip == "203.0.113.9"


def test_peer_nao_confiavel_nao_pode_forjar_o_header(proxy_confiavel):
    """Sem esta guarda, o auditado escolheria o que a auditoria registra."""
    ip = proxy_confiavel.get_client_ip("198.51.100.7", "203.0.113.9")
    assert ip == "198.51.100.7"


def test_sem_forwarded_for_cai_no_peer(proxy_confiavel):
    assert proxy_confiavel.get_client_ip("172.18.0.5", None) == "172.18.0.5"


# ── Os dois sitios de fato usam o helper ─────────────────────────────────────

def test_enrollment_resolve_o_ip_pelo_helper():
    """`consumed_from_ip` nao pode voltar a ser o IP do Traefik."""
    import inspect
    from app.api.routers import executores_router as mod

    fonte = inspect.getsource(mod)
    assert "get_client_ip(" in fonte, "executores_router deixou de resolver o IP real"
    assert 'from_ip = request.client.host' not in fonte, (
        "from_ip voltou a usar client.host cru — grava o IP do proxy"
    )


def test_registro_de_executor_resolve_o_ip_pelo_helper():
    import inspect
    from app.core import executor_connections as mod

    fonte = inspect.getsource(mod.ExecutorConnectionRegistry.register)
    assert "ip_do_websocket(ws)" in fonte, "register() deixou de resolver o IP real"
    assert "get_client_ip(" in inspect.getsource(mod.ip_do_websocket)


# ── NULL ─────────────────────────────────────────────────────────────────────

def test_executor_ip_continua_NULL_quando_nao_ha_peer(proxy_confiavel):
    """A coluna e nullable de proposito: 'unknown' parece um valor e nao e."""
    import inspect
    from app.core import executor_connections as mod

    fonte = inspect.getsource(mod.ip_do_websocket)
    assert "if ws.client else None" in fonte, (
        "o ramo que preserva o NULL de executor_ip sumiu"
    )


def test_helper_devolve_unknown_apenas_sem_host(proxy_confiavel):
    """Documenta por que o `if ws.client` externo e necessario."""
    assert proxy_confiavel.get_client_ip(None, None) == "unknown"


def test_ipv6_com_zona_no_forwarded_for_e_pulado(proxy_confiavel):
    """A zona (`%eth0`) é texto livre, sem limite de tamanho: estourava o
    VARCHAR(45) das colunas de IP. Não é endereço de cliente na internet."""
    ip = proxy_confiavel.get_client_ip("172.18.0.5", "203.0.113.9, fe80::1%" + "A" * 200)
    assert ip == "203.0.113.9"
