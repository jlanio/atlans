# tests/unit/test_tarefas_de_fundo.py
"""
API background tasks: the lifespan that starts and stops them, the periodic
loops with a Redis lock, and the `REDIS_URL` they all read.

The defects the repetition produced:

- the lifespan started eight tasks by hand and stopped them in copy-pasted
  blocks; one of them was cancelled and never awaited — the shutdown went on
  and closed the database and Redis while it was still shutting down;
- three of the four periodic loops opened a NEW Redis client on every turn just
  to take the lock, instead of using the global pool;
- `REDIS_URL` was read from the environment in five places besides `config.py`,
  and the results consumer had a different default (`localhost`).
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit._lacos import check_loop_lock
from tests.unit._mcp_harness import FakeRedis

RAIZ = Path(__file__).resolve().parents[2]


# ── O lifespan ────────────────────────────────────────────────────────────────

# The background tasks that the core's lifespan starts, by the module they come from.
BACKGROUND_TASKS = [
    ("app.core.run_result_consumer", "run_consumer_loop"),
    ("app.core.artifact_cleanup", "run_cleanup_loop"),
    ("app.core.storage_reconciliation", "run_reconciliation_loop"),
    ("app.core.fontes_catalogo", "importar_catalogo_no_arranque"),
    ("app.core.fontes_catalogo", "run_verificacao_loop"),
    ("app.core.executor_connections", "overdue_acks_monitor"),
    ("app.api.routers.executor_ws_router", "orphan_runs_watchdog"),
]
# And one from an extension (app/extensoes), which starts and stops along with them.
EXTENSION_TASK = "tarefa_da_extensao"


@pytest.fixture
def lifespan_without_infra(monkeypatch, empty_registry):
    """The lifespan of `app.main` with database, Redis, MinIO, scheduler and MCP
    stubbed, and each background task replaced by one that just waits for
    cancellation.

    `eventos` records the order of things: ("subiu", t), ("encerrou", t) and
    ("close_redis",). `lenta` picks the task that is slow to shut down — like a
    real one, which still closes a connection and logs after cancellation."""
    from app import main

    estado = SimpleNamespace(eventos=[], lenta=None, redis=MagicMock())
    estado.redis.ping = AsyncMock(return_value=True)

    def _task(nome):
        async def _runs():
            estado.eventos.append(("subiu", nome))
            try:
                await asyncio.Event().wait()
            finally:
                if nome == estado.lenta:
                    await asyncio.sleep(0.05)
                estado.eventos.append(("encerrou", nome))

        return _runs

    for modulo, nome in BACKGROUND_TASKS:
        monkeypatch.setattr(f"{modulo}.{nome}", _task(nome))
    empty_registry.tarefas_de_fundo.append(("Extensão de teste", _task(EXTENSION_TASK)))

    async def _close_redis():
        estado.eventos.append(("close_redis",))

    @asynccontextmanager
    async def _mcp_sessions():
        yield

    monkeypatch.setattr(main, "_wait_for_db", AsyncMock())
    monkeypatch.setattr("app.core.redis.init_redis", AsyncMock(return_value=estado.redis))
    monkeypatch.setattr("app.core.redis.close_redis", _close_redis)
    monkeypatch.setattr("app.core.storage.ensure_bucket", MagicMock())
    monkeypatch.setattr("app.core.storage.endpoint_externo_e_local", lambda: False)
    monkeypatch.setattr("app.core.async_scheduler.scheduler", SimpleNamespace(start=AsyncMock(), stop=AsyncMock()))
    monkeypatch.setattr(main, "engine", SimpleNamespace(dispose=AsyncMock()))
    monkeypatch.setattr(main, "mcp_server", SimpleNamespace(session_manager=SimpleNamespace(run=_mcp_sessions)))
    estado.lifespan = main.lifespan
    return estado


@pytest.mark.parametrize("lenta", [nome for _, nome in BACKGROUND_TASKS] + [EXTENSION_TASK])
async def test_shutdown_awaits_each_background_task_before_closing_redis(lifespan_without_infra, lenta):
    """Cancelling is not enough: the shutdown has to AWAIT each task, otherwise it
    closes the database and Redis while the task is still mid-shutdown (and the
    loop ends with "Task was destroyed but it is pending!")."""
    estado = lifespan_without_infra
    estado.lenta = lenta

    async with estado.lifespan(SimpleNamespace(state=SimpleNamespace())):
        await asyncio.sleep(0)  # the tasks start
        assert {e[1] for e in estado.eventos if e[0] == "subiu"} == (
            {nome for _, nome in BACKGROUND_TASKS} | {EXTENSION_TASK}
        )

    assert ("encerrou", lenta) in estado.eventos, f"{lenta} foi cancelada e não aguardada"
    assert estado.eventos.index(("encerrou", lenta)) < estado.eventos.index(("close_redis",))


async def test_startup_ping_is_on_the_async_pool(lifespan_without_infra):
    """The connection ping goes through the async pool — it used to be a
    SYNCHRONOUS Redis client, kept only for this, which blocked the event loop
    at startup."""
    estado = lifespan_without_infra
    async with estado.lifespan(SimpleNamespace(state=SimpleNamespace())):
        pass
    estado.redis.ping.assert_awaited_once()


# ── The periodic loops ────────────────────────────────────────────────────────


async def test_lock_e_set_nx_ex_no_pool_global(monkeypatch):
    from app.core import tarefas_periodicas

    pool = FakeRedis()
    monkeypatch.setattr("app.core.redis._pool", pool)
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is True
    assert ("set", "x:lock", True, 600) in pool.chamadas
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is False  # held until the TTL expires


async def test_redis_down_or_pool_not_initialized_proceeds_without_lock(monkeypatch):
    """The protected routines are idempotent: without Redis, the worst case is
    repeated work, never missing work."""
    from app.core import tarefas_periodicas

    class RedisDown(FakeRedis):
        async def set(self, *args, **kwargs):
            raise ConnectionError("redis fora")

    monkeypatch.setattr("app.core.redis._pool", RedisDown())
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is True
    monkeypatch.setattr("app.core.redis._pool", None)  # outside the lifespan
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is True


async def test_loop_works_each_turn_survives_errors_and_ends_on_cancellation():
    from app.core import tarefas_periodicas

    voltas = []

    async def _job():
        voltas.append(len(voltas) + 1)
        if len(voltas) == 1:
            raise RuntimeError("banco fora")  # does not bring down the loop
        if len(voltas) == 3:
            raise asyncio.CancelledError  # o shutdown chega

    await asyncio.wait_for(tarefas_periodicas.periodic_loop("teste", 0.01, _job), 2.0)
    assert voltas == [1, 2, 3]


async def test_loop_with_busy_lock_skips_the_turns(monkeypatch):
    from app.core import tarefas_periodicas

    pool = FakeRedis()
    pool.dados["x:lock"] = "1"  # another worker took it
    monkeypatch.setattr("app.core.redis._pool", pool)
    voltas = []

    async def _job():
        voltas.append(1)

    tarefa = asyncio.create_task(tarefas_periodicas.periodic_loop("teste", 0.01, _job, lock="x:lock"))
    await asyncio.sleep(0.08)
    tarefa.cancel()
    await tarefa  # the loop handles the cancellation and finishes on its own
    assert voltas == []
    assert len([c for c in pool.chamadas if c[:2] == ("set", "x:lock")]) >= 2

# (module, loop, interval attribute, lock key, work done on each turn)
LOOPS = [
    ("app.core.artifact_cleanup", "run_cleanup_loop", "_CLEANUP_INTERVAL", "artifact_cleanup:lock", "purge_expired_artifacts"),
    ("app.core.storage_reconciliation", "run_reconciliation_loop", "_RECONCILE_INTERVAL", "storage_reconcile:lock", "run_full_reconciliation"),
    ("app.core.fontes_catalogo", "run_verificacao_loop", "FONTES_VERIFICACAO_INTERVAL", "fontes_verificacao:lock", "verificar_endpoints"),
]


@pytest.mark.parametrize(
    "modulo, laco, intervalo, chave, trabalho", [pytest.param(*c, id=c[1]) for c in LOOPS]
)
async def test_loop_takes_the_lock_on_the_global_pool_without_opening_a_client_per_turn(
    modulo, laco, intervalo, chave, trabalho, monkeypatch
):
    await check_loop_lock(modulo, laco, intervalo, chave, trabalho, monkeypatch)



# ── A single REDIS_URL ────────────────────────────────────────────────────────


async def test_results_consumer_uses_the_application_redis_url(monkeypatch):
    """Without `REDIS_URL` in the environment, the consumer fell back to
    `localhost` while the pool (and everything else) went to `redis:6379`: two
    different Redis instances."""
    import redis.asyncio as aioredis

    from app.core import config, run_result_consumer

    urls = []

    def _from_url(url, **kw):
        urls.append(url)
        raise asyncio.CancelledError  # only the address matters

    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(aioredis, "from_url", _from_url)

    await run_result_consumer.run_consumer_loop()

    assert urls == [config.REDIS_URL]


def test_only_config_reads_the_redis_url_from_the_environment():
    """A single default, in `app/core/config.py`. The declared exception is
    `rate_limiter.py`: it needs to know whether the variable was SET (absent =
    in-memory counters), and the `config.py` default would erase that difference."""
    exempt_files = {"app/core/config.py", "app/core/rate_limiter.py"}
    leitores = sorted(
        str(arquivo.relative_to(RAIZ))
        for arquivo in (RAIZ / "app").rglob("*.py")
        if str(arquivo.relative_to(RAIZ)) not in exempt_files
        and any(
            forma in arquivo.read_text(encoding="utf-8")
            for forma in ('getenv("REDIS_URL"', 'environ["REDIS_URL"]', 'environ.get("REDIS_URL"')
        )
    )
    assert leitores == []
