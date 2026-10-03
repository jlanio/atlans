"""The webhook trigger limit counts per client, not per proxy.

The (IP, workflow) key used slowapi's `get_remote_address`, which behind
Traefik returns the proxy's IP for every caller: a single bucket per workflow,
shared by the whole world. With the global counters in Redis, anyone who
knew a webhook's URL would exhaust the workflow's 20/min for everyone else.
"""
import importlib
from types import SimpleNamespace

import pytest


@pytest.fixture
def atras_do_traefik(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXIES", "172.16.0.0/12")
    import app.core.trusted_proxy as tp
    importlib.reload(tp)
    yield
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    importlib.reload(tp)


def _pedido(xff: str, workflow: str = "wf-1"):
    return SimpleNamespace(
        client=SimpleNamespace(host="172.18.0.5"),            # o Traefik
        headers={"x-forwarded-for": xff},
        path_params={"id_hash": workflow},
    )


def test_a_chave_e_o_ip_real_de_quem_chama(atras_do_traefik):
    from app.api.routers.webhook_router import _webhook_rate_key

    assert _webhook_rate_key(_pedido("203.0.113.9, 172.18.0.5")) == "203.0.113.9:wf-1"


def test_dois_chamadores_do_mesmo_workflow_nao_dividem_o_balde(atras_do_traefik):
    from app.api.routers.webhook_router import _webhook_rate_key

    assert _webhook_rate_key(_pedido("203.0.113.9")) != _webhook_rate_key(_pedido("198.51.100.4"))


def test_o_mesmo_chamador_em_workflows_diferentes_tambem_nao(atras_do_traefik):
    from app.api.routers.webhook_router import _webhook_rate_key

    assert _webhook_rate_key(_pedido("203.0.113.9", "wf-1")) != _webhook_rate_key(_pedido("203.0.113.9", "wf-2"))
