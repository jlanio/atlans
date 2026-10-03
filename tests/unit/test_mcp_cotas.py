# tests/unit/test_mcp_cotas.py
"""
Per-token quotas: per-minute counting and a ceiling on concurrent waits.

What each test protects:

- the key is the TOKEN's, never the IP's — two clients behind the same NAT must not
  share (or steal) the same bucket;
- the deadline is born on the first call and the following ones do not push it, or the
  window would never close (each call would push the deadline forward and the bucket
  would stay full forever);
- overflowing returns `retry_after_seconds` from the real TTL, so the client waits
  instead of retrying;
- the boundary is where the real ceiling is: call number LIMIT passes and
  the next one is refused (a `<` in place of a `<=` would otherwise go
  unnoticed);
- a key left without a deadline (the `EXPIRE` got lost back when it was sent
  separately from the `INCR`) gets a deadline on the next count — otherwise the token
  would be locked forever;
- a failure between the reservation's two `INCR`s does not leave a dangling slot;
- without Redis everything degrades OPEN, with a warning at most once per minute — the
  policy already used by the logs WebSocket;
- the wait returns the reservation even when the body raises, and the refusal by ceiling
  does not leave a dangling counter.
"""
from __future__ import annotations

import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app.mcp import cotas
from tests.unit._mcp_harness import FakeRedis


@pytest.fixture(autouse=True)
def _reset_process_state():
    """The warning and the local semaphore are module globals; each test starts clean."""
    cotas._last_warning = 0.0
    cotas._local_waits.clear()
    cotas._local_waits_total = 0
    yield
    cotas._last_warning = 0.0
    cotas._local_waits.clear()
    cotas._local_waits_total = 0


def _response_body(exc: ToolError) -> dict:
    return json.loads(str(exc))


# ── verificar() ───────────────────────────────────────────────────────────────


async def test_first_call_creates_the_one_minute_window():
    redis = FakeRedis()
    await cotas.verificar(redis, "tok-1", None)
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == 1
    assert redis.ttls["ratelimit:mcp:tok-1:geral"] == 60


async def test_later_calls_do_not_push_the_expiry_so_the_window_can_close():
    redis = FakeRedis()
    chave = "ratelimit:mcp:tok-1:geral"
    await cotas.verificar(redis, "tok-1", None)
    redis.ttls[chave] = 25  # 35 s of the window have passed
    for _ in range(3):
        await cotas.verificar(redis, "tok-1", None)
    assert redis.dados[chave] == 4
    assert redis.ttls[chave] == 25


async def test_buckets_are_per_token():
    redis = FakeRedis()
    await cotas.verificar(redis, "tok-1", None)
    await cotas.verificar(redis, "tok-2", None)
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == 1
    assert redis.dados["ratelimit:mcp:tok-2:geral"] == 1


async def test_exceeding_the_general_raises_rate_limited_with_the_ttl():
    redis = FakeRedis()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.OVERALL_LIMIT
    redis.ttls["ratelimit:mcp:tok-1:geral"] = 17
    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", None)
    corpo = _response_body(exc.value)
    assert corpo["code"] == "rate_limited"
    assert corpo["retry_after_seconds"] == 17


async def test_the_exact_boundary_of_the_general_bucket():
    """Call number OVERALL_LIMIT passes; the next one is refused."""
    redis = FakeRedis()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.OVERALL_LIMIT - 1
    redis.ttls["ratelimit:mcp:tok-1:geral"] = 30

    await cotas.verificar(redis, "tok-1", None)  # call number OVERALL_LIMIT
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == cotas.OVERALL_LIMIT

    with pytest.raises(ToolError) as exc:  # a OVERALL_LIMIT + 1
        await cotas.verificar(redis, "tok-1", None)
    assert _response_body(exc.value)["code"] == "rate_limited"


async def test_exceeded_key_without_expiry_gets_the_expiry_on_count():
    """Without the deadline back, the token would be locked forever.

    When `INCR` and `EXPIRE` were two commands, losing the second (Redis
    restarted, connection dropped) left the key without a deadline: the counter never
    reset and every call from that token started being refused — until someone
    deleted the key by hand. The count arms the deadline of a key without one, in the
    same transaction as the `INCR`, overflowed or not.
    """
    redis = FakeRedis()
    chave = "ratelimit:mcp:tok-1:geral"
    redis.dados[chave] = cotas.OVERALL_LIMIT + 5  # estourado
    redis.ttls.pop(chave, None)  # and with no deadline at all (the EXPIRE got lost)

    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", None)

    assert _response_body(exc.value)["retry_after_seconds"] == cotas.WINDOW_SECONDS
    assert ("expire", chave, cotas.WINDOW_SECONDS) in redis.chamadas
    assert redis.ttls[chave] == cotas.WINDOW_SECONDS


async def test_run_quota_has_its_own_ceiling_lower_than_the_general():
    redis = FakeRedis()
    assert cotas.LIMITS_PER_QUOTA["run"] < cotas.OVERALL_LIMIT
    redis.dados["ratelimit:mcp:tok-1:run"] = cotas.LIMITS_PER_QUOTA["run"]
    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", "run")
    assert _response_body(exc.value)["code"] == "rate_limited"
    # The general bucket was already consumed before the specific one refused: it is one
    # call, counted once in each bucket.
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == 1


async def test_validate_quota_does_not_affect_the_run_bucket():
    redis = FakeRedis()
    await cotas.verificar(redis, "tok-1", "validate")
    assert redis.dados["ratelimit:mcp:tok-1:validate"] == 1
    assert "ratelimit:mcp:tok-1:run" not in redis.dados


async def test_missing_ttl_falls_back_to_full_window_instead_of_a_negative_number():
    redis = FakeRedis()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.OVERALL_LIMIT + 5
    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", None)
    assert _response_body(exc.value)["retry_after_seconds"] == cotas.WINDOW_SECONDS


async def test_without_redis_degrades_open_and_warns_once_per_minute(caplog):
    with caplog.at_level("WARNING", logger="app.mcp.cotas"):
        for _ in range(5):
            await cotas.verificar(None, "tok-1", "run")
    avisos = [r for r in caplog.records if r.name == "app.mcp.cotas"]
    assert len(avisos) == 1


async def test_redis_failure_does_not_break_the_call():
    class BrokenRedis(FakeRedis):
        async def incrby(self, chave, quanto):
            raise ConnectionError("sem rede")

    await cotas.verificar(BrokenRedis(), "tok-1", None)  # does not raise


# ── espera() ──────────────────────────────────────────────────────────────────


async def test_wait_reserves_in_both_counters_and_releases_at_the_end():
    redis = FakeRedis()
    async with cotas.espera(redis, "tok-1", ttl_s=120):
        assert redis.dados["mcp:wait:token:tok-1"] == 1
        assert redis.dados["mcp:wait:global"] == 1
    assert redis.dados["mcp:wait:token:tok-1"] == 0
    assert redis.dados["mcp:wait:global"] == 0


async def test_reservation_ttl_covers_the_max_deadline_plus_slack():
    redis = FakeRedis()
    async with cotas.espera(redis, "tok-1", ttl_s=120):
        pass
    assert redis.ttls["mcp:wait:token:tok-1"] == 180


async def test_wait_releases_the_reservation_even_with_error_in_the_body():
    redis = FakeRedis()
    with pytest.raises(RuntimeError):
        async with cotas.espera(redis, "tok-1", ttl_s=60):
            raise RuntimeError("a execução falhou")
    assert redis.dados["mcp:wait:token:tok-1"] == 0


async def test_fourth_wait_of_the_same_token_is_refused_without_leaving_a_dangling_counter():
    redis = FakeRedis()
    redis.dados["mcp:wait:token:tok-1"] = cotas.MAX_WAITS_PER_TOKEN
    redis.dados["mcp:wait:global"] = 1
    with pytest.raises(ToolError) as exc:
        async with cotas.espera(redis, "tok-1", ttl_s=60):
            pass
    corpo = _response_body(exc.value)
    assert corpo["code"] == "wait_limit"
    assert "wait=false" in corpo["hint"]
    assert redis.dados["mcp:wait:token:tok-1"] == cotas.MAX_WAITS_PER_TOKEN
    assert redis.dados["mcp:wait:global"] == 1


async def test_global_ceiling_refuses_even_a_token_within_its_own_limit():
    redis = FakeRedis()
    redis.dados["mcp:wait:global"] = cotas.MAX_GLOBAL_WAITS
    with pytest.raises(ToolError) as exc:
        async with cotas.espera(redis, "tok-novo", ttl_s=60):
            pass
    assert _response_body(exc.value)["code"] == "wait_limit"
    assert redis.dados["mcp:wait:token:tok-novo"] == 0


async def test_failure_between_the_two_incr_leaves_no_dangling_reservation():
    """The first bucket has already been incremented when the second one fails.

    Without returning what was counted, each attempt during a Redis outage
    would eat one of the token's slots, and the ceiling would lock as soon as the network came back.
    """

    class RedisFailingOnGlobal(FakeRedis):
        async def incr(self, chave):
            if chave == "mcp:wait:global":
                raise ConnectionError("caiu no meio da reserva")
            return await super().incr(chave)

    redis = RedisFailingOnGlobal()
    async with cotas.espera(redis, "tok-1", ttl_s=60):
        # It degraded to the local semaphore, as the no-Redis policy dictates.
        assert cotas._local_waits["tok-1"] == 1
    assert redis.dados["mcp:wait:token:tok-1"] == 0


async def test_without_redis_the_wait_uses_a_process_local_semaphore():
    import contextlib

    async with contextlib.AsyncExitStack() as pilha:
        for _ in range(cotas.MAX_WAITS_PER_TOKEN):
            await pilha.enter_async_context(cotas.espera(None, "tok-1", ttl_s=60))
        with pytest.raises(ToolError) as exc:
            async with cotas.espera(None, "tok-1", ttl_s=60):
                pass
    assert _response_body(exc.value)["code"] == "wait_limit"
    # Popped off the stack: the semaphore is back at zero and the next request passes.
    async with cotas.espera(None, "tok-1", ttl_s=60):
        pass


async def test_local_semaphore_has_global_ceiling_and_returns_to_zero():
    """Without Redis the global ceiling also applies — and the counter unwinds down to zero."""
    import contextlib

    cotas._local_waits_total = cotas.MAX_GLOBAL_WAITS
    with pytest.raises(ToolError) as exc:
        async with cotas.espera(None, "tok-novo", ttl_s=60):
            pass
    assert _response_body(exc.value)["code"] == "wait_limit"
    # The refusal does not consume a slot: the total stays where it was.
    assert cotas._local_waits_total == cotas.MAX_GLOBAL_WAITS
    assert "tok-novo" not in cotas._local_waits

    cotas._local_waits_total = 0
    async with contextlib.AsyncExitStack() as pilha:
        for numero in range(cotas.MAX_WAITS_PER_TOKEN):
            await pilha.enter_async_context(cotas.espera(None, f"tok-{numero}", ttl_s=60))
        assert cotas._local_waits_total == cotas.MAX_WAITS_PER_TOKEN
    assert cotas._local_waits_total == 0
    assert cotas._local_waits == {}


# ── verificar_tokens_do_assistente() ────────────────────────────────────────────


async def test_the_token_ceiling_is_the_CALLERS_and_the_default_is_the_installations():
    """The ceiling now depends on the plan, and the one who resolves it is the caller.

    This module is Redis only: if it went fetching the subscription, the assistant loop
    (which runs inside an SSE generator, without a request session) would drag the database
    into a check that exists to be cheap.
    """
    redis = FakeRedis()
    redis.dados["assistente:tokens:usr-1"] = cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA

    # Without `teto`, the behavior from before plans: the installation's ceiling.
    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1")
    assert _response_body(exc.value)["code"] == "rate_limited"

    # With a higher ceiling (a plan's, when there is an extension), the SAME spending passes.
    await cotas.verificar_tokens_do_assistente(
        redis, "usr-1", teto=10 * cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    )


async def test_the_injected_ceiling_boundary_is_the_ceiling_itself():
    """A `<=` in place of the `<` would give a free turn to every plan — and the
    boundary is precisely where nobody looks."""
    redis = FakeRedis()
    teto = 22_500_000

    redis.dados["assistente:tokens:usr-1"] = teto - 1
    await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=teto)

    redis.dados["assistente:tokens:usr-1"] = teto
    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=teto)
    assert _response_body(exc.value)["code"] == "rate_limited"


# ── The assistant quota key must not become immortal (PR 5, #3) ─────────────────
#
# When the charge did INCRBY and, only on the window's 1st write, EXPIRE — two
# commands —, losing the second (Redis restarted, connection dropped, SSE cancelled
# midway) left the key without a deadline: on crossing the ceiling, the user lost
# the assistant FOREVER. Today the deadline goes out in the same transaction as the
# INCRBY (`count_in_window`); whatever remains of an old key without a deadline is
# armed on the next charge, on the refusal or on reading `/estado` (`spent_and_reset`).


async def test_below_the_ceiling_the_charge_sets_the_expiry_of_a_key_left_without_one():
    """Below the ceiling the turn goes on, and its charge sets the missing deadline —
    otherwise the immortal key would only be noticed too late, already locked."""
    redis = FakeRedis()
    chave = cotas.tokens_key("usr-1")
    redis.dados[chave] = 10  # below the ceiling, but WITHOUT a deadline (the EXPIRE got lost)

    await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=1000)  # does not refuse
    assert await cotas.cobrar_tokens_do_assistente(redis, "usr-1", 5) == 15

    assert redis.ttls[chave] == cotas.ASSISTANT_WINDOW_SECONDS
    assert await cotas.spent_and_reset(redis, "usr-1") == (15, cotas.ASSISTANT_WINDOW_SECONDS)


async def test_the_refusal_sets_the_expiry_of_an_exceeded_key_left_without_one():
    """Once overflowed, the turn is refused BEFORE the charge — which is what arms the
    deadline. If the refusal did not arm it, whoever crossed the ceiling with such a key
    would never have the assistant again; and it also says when the window reopens."""
    redis = FakeRedis()
    chave = cotas.tokens_key("usr-1")
    redis.dados[chave] = 1000  # at the ceiling, and WITHOUT a deadline

    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=1000)

    assert _response_body(exc.value)["retry_after_seconds"] == cotas.ASSISTANT_WINDOW_SECONDS
    assert redis.ttls[chave] == cotas.ASSISTANT_WINDOW_SECONDS


async def test_charge_and_refuse_do_not_reopen_a_window_with_live_expiry():
    """Only the key WITHOUT a deadline gets one; a live window is NOT reopened — reopening
    would extend the ceiling for free on every turn."""
    redis = FakeRedis()
    chave = cotas.tokens_key("usr-1")
    redis.dados[chave] = 10
    redis.ttls[chave] = 3600  # prazo vivo

    await cotas.cobrar_tokens_do_assistente(redis, "usr-1", 5)
    assert redis.ttls[chave] == 3600

    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=15)
    assert _response_body(exc.value)["retry_after_seconds"] == 3600
    assert redis.ttls[chave] == 3600


async def test_the_state_sets_the_expiry_of_an_exceeded_key_left_without_one():
    """With the quota full, the interface reads `/estado` (which comes from here) and locks
    sending: the refusal, which would also arm the deadline, never runs. Without the cure
    here, the old key without a deadline would never expire, and the person would lose the
    assistant forever, with the meter saying "sem prazo" (no deadline)."""
    redis = FakeRedis()
    chave = cotas.tokens_key("usr-1")
    redis.dados[chave] = 1_600_000  # above the ceiling, and WITHOUT a deadline

    assert await cotas.spent_and_reset(redis, "usr-1") == (1_600_000, cotas.ASSISTANT_WINDOW_SECONDS)
    assert redis.ttls[chave] == cotas.ASSISTANT_WINDOW_SECONDS


async def test_the_state_does_not_reopen_a_window_with_live_expiry():
    """Reading the meter does not extend the ceiling: a live window stays as it is."""
    redis = FakeRedis()
    chave = cotas.tokens_key("usr-1")
    redis.dados[chave] = 10
    redis.ttls[chave] = 3600

    assert await cotas.spent_and_reset(redis, "usr-1") == (10, 3600)
    assert redis.ttls[chave] == 3600


async def test_usage_and_expiry_of_missing_key_does_not_invent_expiry():
    """Without a key (nothing spent), there is no deadline to show, and the read does not
    create the key."""
    redis = FakeRedis()
    gasto, prazo = await cotas.spent_and_reset(redis, "usr-1")

    assert gasto == 0
    assert prazo is None
    assert not any(c[0] == "expire" for c in redis.chamadas)
    assert redis.dados == {}
