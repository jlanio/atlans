# tests/unit/_lacos.py
"""A conferência dos laços periódicos com lock, para os do núcleo
(test_tarefas_de_fundo) e os das extensões (tests/extensoes)."""
import asyncio

from tests.unit._mcp_harness import RedisFalso


async def conferir_o_lock_do_laco(modulo, laco, intervalo, chave, trabalho, monkeypatch):
    """O laço pega o lock no pool global (SET NX EX), sem abrir um cliente
    Redis por volta, e roda o trabalho uma vez antes do cancelamento."""
    import importlib

    import redis.asyncio as aioredis

    mod = importlib.import_module(modulo)
    pool = RedisFalso()
    clientes_novos = []
    voltas = []

    async def _trabalho(**kw):
        voltas.append(kw)
        raise asyncio.CancelledError  # o shutdown chega na primeira volta

    monkeypatch.setattr("app.core.redis._pool", pool)
    monkeypatch.setattr(aioredis, "from_url", lambda *a, **k: clientes_novos.append(a) or RedisFalso())
    monkeypatch.setattr(mod, intervalo, 0.01)
    monkeypatch.setattr(mod, trabalho, _trabalho)

    await asyncio.wait_for(getattr(mod, laco)(), 2.0)

    assert voltas == [{}]
    assert clientes_novos == [], "o lock abriu um cliente Redis novo em vez de usar o pool"
    assert pool.dados.get(chave) == "1"
    assert ("set", chave, True, 1) in pool.chamadas  # SET NX EX, TTL = o intervalo (mínimo 1 s)
