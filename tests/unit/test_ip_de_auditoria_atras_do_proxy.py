# tests/unit/test_ip_de_auditoria_atras_do_proxy.py
"""
Real client IP in the audit and telemetry records.

Two fields stored the raw `client.host`:

  consumed_from_ip     audit trail of the executor enrollment
  RunMetrics.executor_ip  telemetry of which machine ran the job

Behind Traefik, `client.host` is the PROXY's IP for everyone. Both fields
always recorded the same address — the enrollment audit trail distinguished
nothing, and the telemetry said the whole fleet came from a single machine.
`app/core/trusted_proxy.get_client_ip` already existed and its docstring names
exactly this problem.

Two properties matter, and the second is the one that keeps the fix from
becoming a new hole:

  RESOLVE     behind a TRUSTED proxy, the first IP of X-Forwarded-For wins.
  NAO FORJA   (no forging) from an UNtrusted peer, the header is ignored — otherwise
              any client would switch identity on every request and the "audit"
              would record whatever the audited party wanted.

And a third, specific to the column:

  NULL        `executor_ip` is nullable. Without a peer, the value must stay NULL
              and not become the string "unknown", which looks like data and isn't.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def proxy_confiavel(monkeypatch):
    """Reloads trusted_proxy with a trusted network configured."""
    monkeypatch.setenv("TRUSTED_PROXIES", "172.16.0.0/12")
    import app.core.trusted_proxy as tp
    importlib.reload(tp)
    yield tp
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    importlib.reload(tp)


# ── RESOLVE / NAO FORJA (no forging) ─────────────────────────────────────────

def test_behind_trusted_proxy_uses_forwarded_for(proxy_confiavel):
    ip = proxy_confiavel.get_client_ip("172.18.0.5", "203.0.113.9, 172.18.0.5")
    assert ip == "203.0.113.9"


def test_untrusted_peer_cannot_forge_the_header(proxy_confiavel):
    """Without this guard, the audited party would choose what the audit records."""
    ip = proxy_confiavel.get_client_ip("198.51.100.7", "203.0.113.9")
    assert ip == "198.51.100.7"


def test_without_forwarded_for_falls_back_to_peer(proxy_confiavel):
    assert proxy_confiavel.get_client_ip("172.18.0.5", None) == "172.18.0.5"


# ── Both call sites actually use the helper ──────────────────────────────────

def test_enrollment_resolves_ip_via_helper():
    """`consumed_from_ip` must not go back to being Traefik's IP."""
    import inspect
    from app.api.routers import executores_router as mod

    fonte = inspect.getsource(mod)
    assert "get_client_ip(" in fonte, "executores_router deixou de resolver o IP real"
    assert 'from_ip = request.client.host' not in fonte, (
        "from_ip voltou a usar client.host cru — grava o IP do proxy"
    )


def test_executor_registration_resolves_ip_via_helper():
    import inspect
    from app.core import executor_connections as mod

    fonte = inspect.getsource(mod.ExecutorConnectionRegistry.register)
    assert "ip_do_websocket(ws)" in fonte, "register() deixou de resolver o IP real"
    assert "get_client_ip(" in inspect.getsource(mod.ip_do_websocket)


# ── NULL ─────────────────────────────────────────────────────────────────────

def test_executor_ip_stays_NULL_when_there_is_no_peer(proxy_confiavel):
    """The column is nullable on purpose: 'unknown' looks like a value and isn't."""
    import inspect
    from app.core import executor_connections as mod

    fonte = inspect.getsource(mod.ip_do_websocket)
    assert "if ws.client else None" in fonte, (
        "o ramo que preserva o NULL de executor_ip sumiu"
    )


def test_helper_returns_unknown_only_without_host(proxy_confiavel):
    """Documents why the outer `if ws.client` is necessary."""
    assert proxy_confiavel.get_client_ip(None, None) == "unknown"


def test_ipv6_with_zone_in_forwarded_for_is_skipped(proxy_confiavel):
    """The zone (`%eth0`) is free text, with no size limit: it overflowed the
    VARCHAR(45) of the IP columns. It is not a client address on the internet."""
    ip = proxy_confiavel.get_client_ip("172.18.0.5", "203.0.113.9, fe80::1%" + "A" * 200)
    assert ip == "203.0.113.9"
