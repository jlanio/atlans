# tests/unit/_lacos.py
"""The check of the periodic loops with a lock, for the core ones
(test_tarefas_de_fundo) and the extensions' ones (tests/extensoes)."""
import asyncio

from tests.unit._mcp_harness import FakeRedis


async def check_loop_lock(modulo, laco, intervalo, chave, trabalho, monkeypatch):
    """The loop takes the lock in the global pool (SET NX EX), without opening a
    Redis client per iteration, and runs the job once before cancellation."""
    import importlib

    import redis.asyncio as aioredis

    mod = importlib.import_module(modulo)
    pool = FakeRedis()
    new_clients = []
    voltas = []

    async def _job(**kw):
        voltas.append(kw)
        raise asyncio.CancelledError  # o shutdown chega na primeira volta

    monkeypatch.setattr("app.core.redis._pool", pool)
    monkeypatch.setattr(aioredis, "from_url", lambda *a, **k: new_clients.append(a) or FakeRedis())
    monkeypatch.setattr(mod, intervalo, 0.01)
    monkeypatch.setattr(mod, trabalho, _job)

    await asyncio.wait_for(getattr(mod, laco)(), 2.0)

    assert voltas == [{}]
    assert new_clients == [], "o lock abriu um cliente Redis novo em vez de usar o pool"
    assert pool.dados.get(chave) == "1"
    assert ("set", chave, True, 1) in pool.chamadas  # SET NX EX, TTL = the interval (minimum 1 s)
