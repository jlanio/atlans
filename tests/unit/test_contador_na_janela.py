# tests/unit/test_contador_na_janela.py
"""
Window counter in Redis and the sites that rely on it: the WebSocket rate
limit (before and after the accept), the executor's e-mail quota, the
per-family refresh, the MCP quotas and the assistant's token quota.

The defect the repetition produced: each site did `INCR` and, only when the
counter went back to 1, `EXPIRE` — two commands. If the `EXPIRE` is lost (the
process dies between the two, the connection breaks, the SSE is canceled
midway), the key is left WITH NO EXPIRY: the counter never resets and, once it
crosses the ceiling, the IP, the executor, the refresh family or the user are
blocked forever. Only the MCP quotas had a cure, and only at refusal time.

The login lockout also counts through here, but in a SLIDING window (each
failure renews the expiry) — and it stays that way.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.websockets import WebSocketState

from app.core.redis import count_in_window
from tests.unit._mcp_harness import FakeRedis


# ── The piece ─────────────────────────────────────────────────────────────────


async def test_first_count_arms_the_window():
    redis = FakeRedis()
    assert await count_in_window("c", 60, redis=redis) == (1, 60)
    assert redis.ttls["c"] == 60


async def test_count_and_deadline_go_out_in_the_same_transaction():
    """INCRBY and EXPIRE in a single MULTI/EXEC: no two loose commands, which is
    where the EXPIRE got lost."""
    redis = FakeRedis()
    await count_in_window("c", 60, redis=redis)
    assert [c for c in redis.chamadas if c[0] in ("exec", "pipeline")] == [("exec", ["incrby", "expire", "ttl"])]


async def test_fixed_window_does_not_move_with_counts():
    redis = FakeRedis()
    await count_in_window("c", 60, redis=redis)
    redis.ttls["c"] = 7  # passaram 53 s
    assert await count_in_window("c", 60, redis=redis) == (2, 7)
    assert redis.ttls["c"] == 7


async def test_increment_adds_at_once():
    redis = FakeRedis()
    assert await count_in_window("c", 86400, increment=500, redis=redis) == (500, 86400)
    assert await count_in_window("c", 86400, increment=120, redis=redis) == (620, 86400)


async def test_sliding_renews_the_deadline_on_each_count():
    redis = FakeRedis()
    await count_in_window("c", 900, sliding=True, redis=redis)
    redis.ttls["c"] = 100
    assert await count_in_window("c", 900, sliding=True, redis=redis) == (2, 900)


async def test_without_client_uses_the_global_pool(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr("app.core.redis._pool", redis)
    assert await count_in_window("c", 60) == (1, 60)
    assert redis.dados == {"c": 1}


# ── The sites ─────────────────────────────────────────────────────────────────


def _fake_ws():
    return SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.7"),
        headers={},
        scope={},
        client_state=WebSocketState.CONNECTED,
        close=AsyncMock(),
    )


async def _ws_before_accept(redis):
    from app.api.dependencies import _ws_pre_accept_rate_check

    assert await _ws_pre_accept_rate_check(_fake_ws(), scope="teste") is True


async def _ws_after_accept(redis):
    from app.api.dependencies import check_ws_rate_limit

    ws = _fake_ws()
    assert await check_ws_rate_limit(ws, limit=30, period=60, scope="teste", identity="usr-1") is True


async def _email_quota(redis):
    from app.api.routers.internal_email_router import _enforce_agent_quota

    await _enforce_agent_quota("ex-1")


async def _refresh_per_family(redis):
    from app.core.utils.jwt_utils import refresh_rate_exceeded

    assert await refresh_rate_exceeded("fam-1") is False


async def _mcp_quotas(redis):
    from app.mcp import cotas

    await cotas.verificar(redis, "tok-1", None)


async def _assistant_billing(redis):
    from app.mcp import cotas

    await cotas.cobrar_tokens_do_assistente(redis, "usr-1", 100)


SITES = [
    pytest.param(_ws_before_accept, "ratelimit:ws_open:teste:203.0.113.7", 60, id="ws-antes-do-accept"),
    pytest.param(_ws_after_accept, "ratelimit:ws:teste:u:usr-1", 60, id="ws-depois-do-accept"),
    pytest.param(_email_quota, "ratelimit:send_email:ex-1", 3600, id="cota-de-email"),
    pytest.param(_refresh_per_family, "refresh_rate:fam-1", 60, id="refresh-por-familia"),
    pytest.param(_mcp_quotas, "ratelimit:mcp:tok-1:geral", 60, id="cotas-do-mcp"),
    pytest.param(_assistant_billing, "assistente:tokens:usr-1", 24 * 60 * 60, id="cobranca-do-assistente"),
]


@pytest.mark.parametrize("sitio, chave, janela", SITES)
async def test_key_that_lost_its_expire_gets_a_deadline_again_on_next_count(sitio, chave, janela, monkeypatch):
    """The `INCR` of the first count arrived; the `EXPIRE` did not. The next
    count has to set the expiry — otherwise the bucket never reopens."""
    redis = FakeRedis()
    redis.dados[chave] = 1       # a 1a contagem existiu...
    redis.ttls.pop(chave, None)  # ...e o EXPIRE dela se perdeu
    monkeypatch.setattr("app.core.redis._pool", redis)

    await sitio(redis)

    assert redis.ttls.get(chave) == janela, "a chave continua sem prazo: o balde nunca mais reabre"


async def test_login_lockout_keeps_sliding_window():
    """Each failure renews the attempts' expiry: the counter only resets after
    `_ATTEMPTS_TTL` seconds with no failure at all."""
    from app.api.routers import auth_router

    redis = FakeRedis()
    assert await auth_router._record_failed("admin", redis) == auth_router._MAX_ATTEMPTS - 1
    redis.ttls["login_failed:admin"] = 30  # quase vencendo
    assert await auth_router._record_failed("admin", redis) == auth_router._MAX_ATTEMPTS - 2
    assert redis.ttls["login_failed:admin"] == auth_router._ATTEMPTS_TTL
