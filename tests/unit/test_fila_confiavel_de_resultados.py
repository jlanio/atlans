"""
Reliable run_results queue (app/core/run_result_consumer.py): an item is moved
to the consumer's processing list and only removed after it was handled.
"""
import asyncio
import fnmatch
import json
from unittest.mock import patch

import pytest

from app.core import run_result_consumer as rrc


class _RedisDeListas:
    """The handful of list commands the consumer uses, in memory."""

    def __init__(self):
        self.listas: dict[str, list[str]] = {}
        self.chaves: dict[str, str] = {}

    def _l(self, k):
        return self.listas.setdefault(k, [])

    async def lpush(self, k, v):
        self._l(k).insert(0, v)

    async def rpush(self, k, v):
        self._l(k).append(v)

    async def blmove(self, origem, destino, _timeout, de, para):
        lst = self._l(origem)
        if not lst:
            return None
        v = lst.pop() if de == "RIGHT" else lst.pop(0)
        (self._l(destino).insert(0, v) if para == "LEFT" else self._l(destino).append(v))
        return v

    async def lmove(self, origem, destino, de, para):
        return await self.blmove(origem, destino, 0, de, para)

    async def lrem(self, k, _n, v):
        lst = self._l(k)
        if v in lst:
            lst.remove(v)
            return 1
        return 0

    async def exists(self, k):
        return int(k in self.chaves)

    async def set(self, k, v, ex=None, nx=False):
        self.chaves[k] = v

    async def scan_iter(self, match="*", count=None):
        for k in list(self.listas):
            if fnmatch.fnmatch(k, match) and self.listas[k]:
                yield k


class _Ctx:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *a):
        return False


@pytest.fixture
def _sessao():
    with patch.object(rrc, "AsyncSessionLocal", lambda: _Ctx()):
        yield


async def test_a_handled_item_leaves_the_processing_list(_sessao):
    r = _RedisDeListas()
    await r.lpush("run_results", json.dumps({"task_id": "t1"}))

    async def _ok(_db, _p):
        return True

    await rrc._consume_one(r, "run_results", _ok, "run_results:processando:eu")
    assert r.listas["run_results"] == [] and r.listas["run_results:processando:eu"] == []


async def test_a_shutdown_mid_item_hands_it_back(_sessao):
    r = _RedisDeListas()
    item = json.dumps({"task_id": "t1"})
    await r.lpush("run_results", item)

    async def _lento(_db, _p):
        await asyncio.sleep(10)

    tarefa = asyncio.create_task(rrc._consume_one(r, "run_results", _lento, "run_results:processando:eu"))
    await asyncio.sleep(0.05)
    tarefa.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tarefa
    assert r.listas["run_results"] == [item]
    assert r.listas["run_results:processando:eu"] == []


async def test_the_items_of_a_dead_consumer_go_back_to_the_queue():
    r = _RedisDeListas()
    r.listas["run_results:processando:morto"] = ["b", "a"]     # a is the oldest
    r.listas["run_results:processando:vivo"] = ["c"]
    await r.set("run_results:consumidor:vivo", "1")

    devolvidos = await rrc._reclaim_abandoned(r, "run_results", "run_results:processando:eu")

    assert devolvidos == 2
    # The consumer takes from the right: "a" (the oldest) comes out first.
    assert r.listas["run_results"] == ["b", "a"]
    assert r.listas["run_results:processando:vivo"] == ["c"]   # a live one is left alone
