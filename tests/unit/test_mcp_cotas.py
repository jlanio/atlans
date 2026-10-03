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
- the boundary is where the real ceiling is: call number LIMITE passes and
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
from tests.unit._mcp_harness import RedisFalso


@pytest.fixture(autouse=True)
def _zera_estado_do_processo():
    """The warning and the local semaphore are module globals; each test starts clean."""
    cotas._ultimo_aviso = 0.0
    cotas._esperas_locais.clear()
    cotas._esperas_locais_total = 0
    yield
    cotas._ultimo_aviso = 0.0
    cotas._esperas_locais.clear()
    cotas._esperas_locais_total = 0


def _corpo(exc: ToolError) -> dict:
    return json.loads(str(exc))


# ── verificar() ───────────────────────────────────────────────────────────────


async def test_primeira_chamada_cria_a_janela_de_um_minuto():
    redis = RedisFalso()
    await cotas.verificar(redis, "tok-1", None)
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == 1
    assert redis.ttls["ratelimit:mcp:tok-1:geral"] == 60


async def test_chamadas_seguintes_nao_empurram_o_prazo_para_a_janela_poder_fechar():
    redis = RedisFalso()
    chave = "ratelimit:mcp:tok-1:geral"
    await cotas.verificar(redis, "tok-1", None)
    redis.ttls[chave] = 25  # 35 s of the window have passed
    for _ in range(3):
        await cotas.verificar(redis, "tok-1", None)
    assert redis.dados[chave] == 4
    assert redis.ttls[chave] == 25


async def test_baldes_sao_por_token():
    redis = RedisFalso()
    await cotas.verificar(redis, "tok-1", None)
    await cotas.verificar(redis, "tok-2", None)
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == 1
    assert redis.dados["ratelimit:mcp:tok-2:geral"] == 1


async def test_estourar_o_geral_levanta_rate_limited_com_o_ttl():
    redis = RedisFalso()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.LIMITE_GERAL
    redis.ttls["ratelimit:mcp:tok-1:geral"] = 17
    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", None)
    corpo = _corpo(exc.value)
    assert corpo["code"] == "rate_limited"
    assert corpo["retry_after_seconds"] == 17


async def test_a_fronteira_exata_do_balde_geral():
    """Call number LIMITE_GERAL passes; the next one is refused."""
    redis = RedisFalso()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.LIMITE_GERAL - 1
    redis.ttls["ratelimit:mcp:tok-1:geral"] = 30

    await cotas.verificar(redis, "tok-1", None)  # call number LIMITE_GERAL
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == cotas.LIMITE_GERAL

    with pytest.raises(ToolError) as exc:  # a LIMITE_GERAL + 1
        await cotas.verificar(redis, "tok-1", None)
    assert _corpo(exc.value)["code"] == "rate_limited"


async def test_chave_estourada_sem_prazo_ganha_o_prazo_na_contagem():
    """Without the deadline back, the token would be locked forever.

    When `INCR` and `EXPIRE` were two commands, losing the second (Redis
    restarted, connection dropped) left the key without a deadline: the counter never
    reset and every call from that token started being refused — until someone
    deleted the key by hand. The count arms the deadline of a key without one, in the
    same transaction as the `INCR`, overflowed or not.
    """
    redis = RedisFalso()
    chave = "ratelimit:mcp:tok-1:geral"
    redis.dados[chave] = cotas.LIMITE_GERAL + 5  # estourado
    redis.ttls.pop(chave, None)  # and with no deadline at all (the EXPIRE got lost)

    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", None)

    assert _corpo(exc.value)["retry_after_seconds"] == cotas.JANELA_SEGUNDOS
    assert ("expire", chave, cotas.JANELA_SEGUNDOS) in redis.chamadas
    assert redis.ttls[chave] == cotas.JANELA_SEGUNDOS


async def test_cota_de_run_tem_teto_proprio_menor_que_o_geral():
    redis = RedisFalso()
    assert cotas.LIMITES_POR_COTA["run"] < cotas.LIMITE_GERAL
    redis.dados["ratelimit:mcp:tok-1:run"] = cotas.LIMITES_POR_COTA["run"]
    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", "run")
    assert _corpo(exc.value)["code"] == "rate_limited"
    # The general bucket was already consumed before the specific one refused: it is one
    # call, counted once in each bucket.
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == 1


async def test_cota_de_validate_nao_afeta_o_balde_de_run():
    redis = RedisFalso()
    await cotas.verificar(redis, "tok-1", "validate")
    assert redis.dados["ratelimit:mcp:tok-1:validate"] == 1
    assert "ratelimit:mcp:tok-1:run" not in redis.dados


async def test_ttl_ausente_cai_na_janela_cheia_em_vez_de_um_numero_negativo():
    redis = RedisFalso()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.LIMITE_GERAL + 5
    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", None)
    assert _corpo(exc.value)["retry_after_seconds"] == cotas.JANELA_SEGUNDOS


async def test_sem_redis_degrada_aberto_e_avisa_uma_vez_por_minuto(caplog):
    with caplog.at_level("WARNING", logger="app.mcp.cotas"):
        for _ in range(5):
            await cotas.verificar(None, "tok-1", "run")
    avisos = [r for r in caplog.records if r.name == "app.mcp.cotas"]
    assert len(avisos) == 1


async def test_falha_do_redis_nao_derruba_a_chamada():
    class RedisQuebrado(RedisFalso):
        async def incrby(self, chave, quanto):
            raise ConnectionError("sem rede")

    await cotas.verificar(RedisQuebrado(), "tok-1", None)  # does not raise


# ── espera() ──────────────────────────────────────────────────────────────────


async def test_espera_reserva_nos_dois_contadores_e_devolve_no_fim():
    redis = RedisFalso()
    async with cotas.espera(redis, "tok-1", ttl_s=120):
        assert redis.dados["mcp:wait:token:tok-1"] == 1
        assert redis.dados["mcp:wait:global"] == 1
    assert redis.dados["mcp:wait:token:tok-1"] == 0
    assert redis.dados["mcp:wait:global"] == 0


async def test_ttl_da_reserva_cobre_o_prazo_maximo_mais_folga():
    redis = RedisFalso()
    async with cotas.espera(redis, "tok-1", ttl_s=120):
        pass
    assert redis.ttls["mcp:wait:token:tok-1"] == 180


async def test_espera_devolve_a_reserva_mesmo_com_erro_no_corpo():
    redis = RedisFalso()
    with pytest.raises(RuntimeError):
        async with cotas.espera(redis, "tok-1", ttl_s=60):
            raise RuntimeError("a execução falhou")
    assert redis.dados["mcp:wait:token:tok-1"] == 0


async def test_quarta_espera_do_mesmo_token_e_recusada_sem_deixar_contador_pendurado():
    redis = RedisFalso()
    redis.dados["mcp:wait:token:tok-1"] = cotas.MAX_ESPERAS_POR_TOKEN
    redis.dados["mcp:wait:global"] = 1
    with pytest.raises(ToolError) as exc:
        async with cotas.espera(redis, "tok-1", ttl_s=60):
            pass
    corpo = _corpo(exc.value)
    assert corpo["code"] == "wait_limit"
    assert "wait=false" in corpo["hint"]
    assert redis.dados["mcp:wait:token:tok-1"] == cotas.MAX_ESPERAS_POR_TOKEN
    assert redis.dados["mcp:wait:global"] == 1


async def test_teto_global_recusa_mesmo_token_dentro_do_proprio_limite():
    redis = RedisFalso()
    redis.dados["mcp:wait:global"] = cotas.MAX_ESPERAS_GLOBAL
    with pytest.raises(ToolError) as exc:
        async with cotas.espera(redis, "tok-novo", ttl_s=60):
            pass
    assert _corpo(exc.value)["code"] == "wait_limit"
    assert redis.dados["mcp:wait:token:tok-novo"] == 0


async def test_falha_entre_os_dois_incr_nao_deixa_reserva_pendurada():
    """The first bucket has already been incremented when the second one fails.

    Without returning what was counted, each attempt during a Redis outage
    would eat one of the token's slots, and the ceiling would lock as soon as the network came back.
    """

    class RedisQueCaiNoGlobal(RedisFalso):
        async def incr(self, chave):
            if chave == "mcp:wait:global":
                raise ConnectionError("caiu no meio da reserva")
            return await super().incr(chave)

    redis = RedisQueCaiNoGlobal()
    async with cotas.espera(redis, "tok-1", ttl_s=60):
        # It degraded to the local semaphore, as the no-Redis policy dictates.
        assert cotas._esperas_locais["tok-1"] == 1
    assert redis.dados["mcp:wait:token:tok-1"] == 0


async def test_sem_redis_a_espera_usa_semaforo_local_ao_processo():
    import contextlib

    async with contextlib.AsyncExitStack() as pilha:
        for _ in range(cotas.MAX_ESPERAS_POR_TOKEN):
            await pilha.enter_async_context(cotas.espera(None, "tok-1", ttl_s=60))
        with pytest.raises(ToolError) as exc:
            async with cotas.espera(None, "tok-1", ttl_s=60):
                pass
    assert _corpo(exc.value)["code"] == "wait_limit"
    # Popped off the stack: the semaphore is back at zero and the next request passes.
    async with cotas.espera(None, "tok-1", ttl_s=60):
        pass


async def test_semaforo_local_tem_teto_global_e_volta_ao_zero():
    """Without Redis the global ceiling also applies — and the counter unwinds down to zero."""
    import contextlib

    cotas._esperas_locais_total = cotas.MAX_ESPERAS_GLOBAL
    with pytest.raises(ToolError) as exc:
        async with cotas.espera(None, "tok-novo", ttl_s=60):
            pass
    assert _corpo(exc.value)["code"] == "wait_limit"
    # The refusal does not consume a slot: the total stays where it was.
    assert cotas._esperas_locais_total == cotas.MAX_ESPERAS_GLOBAL
    assert "tok-novo" not in cotas._esperas_locais

    cotas._esperas_locais_total = 0
    async with contextlib.AsyncExitStack() as pilha:
        for numero in range(cotas.MAX_ESPERAS_POR_TOKEN):
            await pilha.enter_async_context(cotas.espera(None, f"tok-{numero}", ttl_s=60))
        assert cotas._esperas_locais_total == cotas.MAX_ESPERAS_POR_TOKEN
    assert cotas._esperas_locais_total == 0
    assert cotas._esperas_locais == {}


# ── verificar_tokens_do_assistente() ────────────────────────────────────────────


async def test_o_teto_de_tokens_e_do_CHAMADOR_e_o_default_e_o_da_instalacao():
    """The ceiling now depends on the plan, and the one who resolves it is the caller.

    This module is Redis only: if it went fetching the subscription, the assistant loop
    (which runs inside an SSE generator, without a request session) would drag the database
    into a check that exists to be cheap.
    """
    redis = RedisFalso()
    redis.dados["assistente:tokens:usr-1"] = cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA

    # Without `teto`, the behavior from before plans: the installation's ceiling.
    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1")
    assert _corpo(exc.value)["code"] == "rate_limited"

    # With a higher ceiling (a plan's, when there is an extension), the SAME spending passes.
    await cotas.verificar_tokens_do_assistente(
        redis, "usr-1", teto=10 * cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    )


async def test_a_fronteira_do_teto_injetado_e_o_proprio_teto():
    """A `<=` in place of the `<` would give a free turn to every plan — and the
    boundary is precisely where nobody looks."""
    redis = RedisFalso()
    teto = 22_500_000

    redis.dados["assistente:tokens:usr-1"] = teto - 1
    await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=teto)

    redis.dados["assistente:tokens:usr-1"] = teto
    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=teto)
    assert _corpo(exc.value)["code"] == "rate_limited"


# ── The assistant quota key must not become immortal (PR 5, #3) ─────────────────
#
# When the charge did INCRBY and, only on the window's 1st write, EXPIRE — two
# commands —, losing the second (Redis restarted, connection dropped, SSE cancelled
# midway) left the key without a deadline: on crossing the ceiling, the user lost
# the assistant FOREVER. Today the deadline goes out in the same transaction as the
# INCRBY (`contar_na_janela`); whatever remains of an old key without a deadline is
# armed on the next charge, on the refusal or on reading `/estado` (`gasto_e_prazo`).


async def test_abaixo_do_teto_a_cobranca_arma_o_prazo_de_uma_chave_que_ficou_sem():
    """Below the ceiling the turn goes on, and its charge sets the missing deadline —
    otherwise the immortal key would only be noticed too late, already locked."""
    redis = RedisFalso()
    chave = cotas.chave_de_tokens("usr-1")
    redis.dados[chave] = 10  # below the ceiling, but WITHOUT a deadline (the EXPIRE got lost)

    await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=1000)  # does not refuse
    assert await cotas.cobrar_tokens_do_assistente(redis, "usr-1", 5) == 15

    assert redis.ttls[chave] == cotas.JANELA_DO_ASSISTENTE_SEGUNDOS
    assert await cotas.gasto_e_prazo(redis, "usr-1") == (15, cotas.JANELA_DO_ASSISTENTE_SEGUNDOS)


async def test_a_recusa_arma_o_prazo_de_uma_chave_estourada_que_ficou_sem():
    """Once overflowed, the turn is refused BEFORE the charge — which is what arms the
    deadline. If the refusal did not arm it, whoever crossed the ceiling with such a key
    would never have the assistant again; and it also says when the window reopens."""
    redis = RedisFalso()
    chave = cotas.chave_de_tokens("usr-1")
    redis.dados[chave] = 1000  # at the ceiling, and WITHOUT a deadline

    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=1000)

    assert _corpo(exc.value)["retry_after_seconds"] == cotas.JANELA_DO_ASSISTENTE_SEGUNDOS
    assert redis.ttls[chave] == cotas.JANELA_DO_ASSISTENTE_SEGUNDOS


async def test_cobrar_e_recusar_nao_reabrem_uma_janela_com_prazo_vivo():
    """Only the key WITHOUT a deadline gets one; a live window is NOT reopened — reopening
    would extend the ceiling for free on every turn."""
    redis = RedisFalso()
    chave = cotas.chave_de_tokens("usr-1")
    redis.dados[chave] = 10
    redis.ttls[chave] = 3600  # prazo vivo

    await cotas.cobrar_tokens_do_assistente(redis, "usr-1", 5)
    assert redis.ttls[chave] == 3600

    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=15)
    assert _corpo(exc.value)["retry_after_seconds"] == 3600
    assert redis.ttls[chave] == 3600


async def test_o_estado_arma_o_prazo_de_uma_chave_estourada_que_ficou_sem():
    """With the quota full, the interface reads `/estado` (which comes from here) and locks
    sending: the refusal, which would also arm the deadline, never runs. Without the cure
    here, the old key without a deadline would never expire, and the person would lose the
    assistant forever, with the meter saying "sem prazo" (no deadline)."""
    redis = RedisFalso()
    chave = cotas.chave_de_tokens("usr-1")
    redis.dados[chave] = 1_600_000  # above the ceiling, and WITHOUT a deadline

    assert await cotas.gasto_e_prazo(redis, "usr-1") == (1_600_000, cotas.JANELA_DO_ASSISTENTE_SEGUNDOS)
    assert redis.ttls[chave] == cotas.JANELA_DO_ASSISTENTE_SEGUNDOS


async def test_o_estado_nao_reabre_uma_janela_com_prazo_vivo():
    """Reading the meter does not extend the ceiling: a live window stays as it is."""
    redis = RedisFalso()
    chave = cotas.chave_de_tokens("usr-1")
    redis.dados[chave] = 10
    redis.ttls[chave] = 3600

    assert await cotas.gasto_e_prazo(redis, "usr-1") == (10, 3600)
    assert redis.ttls[chave] == 3600


async def test_gasto_e_prazo_de_chave_ausente_nao_inventa_prazo():
    """Without a key (nothing spent), there is no deadline to show, and the read does not
    create the key."""
    redis = RedisFalso()
    gasto, prazo = await cotas.gasto_e_prazo(redis, "usr-1")

    assert gasto == 0
    assert prazo is None
    assert not any(c[0] == "expire" for c in redis.chamadas)
    assert redis.dados == {}
