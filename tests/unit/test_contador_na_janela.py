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

from app.core.redis import contar_na_janela
from tests.unit._mcp_harness import RedisFalso


# ── The piece ─────────────────────────────────────────────────────────────────


async def test_primeira_contagem_arma_a_janela():
    redis = RedisFalso()
    assert await contar_na_janela("c", 60, redis=redis) == (1, 60)
    assert redis.ttls["c"] == 60


async def test_contagem_e_prazo_saem_na_mesma_transacao():
    """INCRBY and EXPIRE in a single MULTI/EXEC: no two loose commands, which is
    where the EXPIRE got lost."""
    redis = RedisFalso()
    await contar_na_janela("c", 60, redis=redis)
    assert [c for c in redis.chamadas if c[0] in ("exec", "pipeline")] == [("exec", ["incrby", "expire", "ttl"])]


async def test_janela_fixa_nao_anda_com_as_contagens():
    redis = RedisFalso()
    await contar_na_janela("c", 60, redis=redis)
    redis.ttls["c"] = 7  # passaram 53 s
    assert await contar_na_janela("c", 60, redis=redis) == (2, 7)
    assert redis.ttls["c"] == 7


async def test_incremento_soma_de_uma_vez():
    redis = RedisFalso()
    assert await contar_na_janela("c", 86400, incremento=500, redis=redis) == (500, 86400)
    assert await contar_na_janela("c", 86400, incremento=120, redis=redis) == (620, 86400)


async def test_deslizante_renova_o_prazo_a_cada_contagem():
    redis = RedisFalso()
    await contar_na_janela("c", 900, deslizante=True, redis=redis)
    redis.ttls["c"] = 100
    assert await contar_na_janela("c", 900, deslizante=True, redis=redis) == (2, 900)


async def test_sem_cliente_usa_o_pool_global(monkeypatch):
    redis = RedisFalso()
    monkeypatch.setattr("app.core.redis._pool", redis)
    assert await contar_na_janela("c", 60) == (1, 60)
    assert redis.dados == {"c": 1}


# ── The sites ─────────────────────────────────────────────────────────────────


def _ws_falso():
    return SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.7"),
        headers={},
        scope={},
        client_state=WebSocketState.CONNECTED,
        close=AsyncMock(),
    )


async def _ws_antes_do_accept(redis):
    from app.api.dependencies import _ws_pre_accept_rate_check

    assert await _ws_pre_accept_rate_check(_ws_falso(), scope="teste") is True


async def _ws_depois_do_accept(redis):
    from app.api.dependencies import check_ws_rate_limit

    ws = _ws_falso()
    assert await check_ws_rate_limit(ws, limit=30, period=60, scope="teste", identity="usr-1") is True


async def _cota_de_email(redis):
    from app.api.routers.internal_email_router import _enforce_agent_quota

    await _enforce_agent_quota("ex-1")


async def _refresh_por_familia(redis):
    from app.core.utils.jwt_utils import refresh_rate_exceeded

    assert await refresh_rate_exceeded("fam-1") is False


async def _cotas_do_mcp(redis):
    from app.mcp import cotas

    await cotas.verificar(redis, "tok-1", None)


async def _cobranca_do_assistente(redis):
    from app.mcp import cotas

    await cotas.cobrar_tokens_do_assistente(redis, "usr-1", 100)


SITIOS = [
    pytest.param(_ws_antes_do_accept, "ratelimit:ws_open:teste:203.0.113.7", 60, id="ws-antes-do-accept"),
    pytest.param(_ws_depois_do_accept, "ratelimit:ws:teste:u:usr-1", 60, id="ws-depois-do-accept"),
    pytest.param(_cota_de_email, "ratelimit:send_email:ex-1", 3600, id="cota-de-email"),
    pytest.param(_refresh_por_familia, "refresh_rate:fam-1", 60, id="refresh-por-familia"),
    pytest.param(_cotas_do_mcp, "ratelimit:mcp:tok-1:geral", 60, id="cotas-do-mcp"),
    pytest.param(_cobranca_do_assistente, "assistente:tokens:usr-1", 24 * 60 * 60, id="cobranca-do-assistente"),
]


@pytest.mark.parametrize("sitio, chave, janela", SITIOS)
async def test_chave_que_perdeu_o_expire_volta_a_ter_prazo_na_contagem_seguinte(sitio, chave, janela, monkeypatch):
    """The `INCR` of the first count arrived; the `EXPIRE` did not. The next
    count has to set the expiry — otherwise the bucket never reopens."""
    redis = RedisFalso()
    redis.dados[chave] = 1       # a 1a contagem existiu...
    redis.ttls.pop(chave, None)  # ...e o EXPIRE dela se perdeu
    monkeypatch.setattr("app.core.redis._pool", redis)

    await sitio(redis)

    assert redis.ttls.get(chave) == janela, "a chave continua sem prazo: o balde nunca mais reabre"


async def test_bloqueio_de_login_continua_com_janela_deslizante():
    """Each failure renews the attempts' expiry: the counter only resets after
    `_ATTEMPTS_TTL` seconds with no failure at all."""
    from app.api.routers import auth_router

    redis = RedisFalso()
    assert await auth_router._record_failed("admin", redis) == auth_router._MAX_ATTEMPTS - 1
    redis.ttls["login_failed:admin"] = 30  # quase vencendo
    assert await auth_router._record_failed("admin", redis) == auth_router._MAX_ATTEMPTS - 2
    assert redis.ttls["login_failed:admin"] == auth_router._ATTEMPTS_TTL
