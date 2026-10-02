"""O limite do gatilho por webhook conta por cliente, não pelo proxy.

A chave (IP, workflow) usava o `get_remote_address` do slowapi, que atrás do
Traefik devolve o IP do proxy para todo chamador: um balde só por workflow,
dividido pelo mundo inteiro. Com os contadores globais no Redis, quem
soubesse a URL de um webhook esgotaria os 20/min do workflow para os demais.
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
