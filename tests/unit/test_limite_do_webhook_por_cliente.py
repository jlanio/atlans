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
def behind_traefik(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXIES", "172.16.0.0/12")
    import app.core.trusted_proxy as tp
    importlib.reload(tp)
    yield
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    importlib.reload(tp)


def _email_request(xff: str, workflow: str = "wf-1"):
    return SimpleNamespace(
        client=SimpleNamespace(host="172.18.0.5"),            # o Traefik
        headers={"x-forwarded-for": xff},
        path_params={"id_hash": workflow},
    )


def test_key_is_callers_real_ip(behind_traefik):
    from app.api.routers.webhook_router import _webhook_rate_key

    assert _webhook_rate_key(_email_request("203.0.113.9, 172.18.0.5")) == "203.0.113.9:wf-1"


def test_two_callers_of_same_workflow_do_not_share_bucket(behind_traefik):
    from app.api.routers.webhook_router import _webhook_rate_key

    assert _webhook_rate_key(_email_request("203.0.113.9")) != _webhook_rate_key(_email_request("198.51.100.4"))


def test_same_caller_on_different_workflows_does_not_either(behind_traefik):
    from app.api.routers.webhook_router import _webhook_rate_key

    assert _webhook_rate_key(_email_request("203.0.113.9", "wf-1")) != _webhook_rate_key(_email_request("203.0.113.9", "wf-2"))
