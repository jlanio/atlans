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

from tests.unit._lacos import conferir_o_lock_do_laco
from tests.unit._mcp_harness import RedisFalso

RAIZ = Path(__file__).resolve().parents[2]


# ── O lifespan ────────────────────────────────────────────────────────────────

# The background tasks that the core's lifespan starts, by the module they come from.
TAREFAS_DE_FUNDO = [
    ("app.core.run_result_consumer", "run_consumer_loop"),
    ("app.core.artifact_cleanup", "run_cleanup_loop"),
    ("app.core.storage_reconciliation", "run_reconciliation_loop"),
    ("app.core.fontes_catalogo", "importar_catalogo_no_arranque"),
    ("app.core.fontes_catalogo", "run_verificacao_loop"),
    ("app.core.executor_connections", "overdue_acks_monitor"),
    ("app.api.routers.executor_ws_router", "orphan_runs_watchdog"),
]
# And one from an extension (app/extensoes), which starts and stops along with them.
TAREFA_DA_EXTENSAO = "tarefa_da_extensao"


@pytest.fixture
def lifespan_sem_infra(monkeypatch, registro_de_teste):
    """The lifespan of `app.main` with database, Redis, MinIO, scheduler and MCP
    stubbed, and each background task replaced by one that just waits for
    cancellation.

    `eventos` records the order of things: ("subiu", t), ("encerrou", t) and
    ("close_redis",). `lenta` picks the task that is slow to shut down — like a
    real one, which still closes a connection and logs after cancellation."""
    from app import main

    estado = SimpleNamespace(eventos=[], lenta=None, redis=MagicMock())
    estado.redis.ping = AsyncMock(return_value=True)

    def _tarefa(nome):
        async def _corre():
            estado.eventos.append(("subiu", nome))
            try:
                await asyncio.Event().wait()
            finally:
                if nome == estado.lenta:
                    await asyncio.sleep(0.05)
                estado.eventos.append(("encerrou", nome))

        return _corre

    for modulo, nome in TAREFAS_DE_FUNDO:
        monkeypatch.setattr(f"{modulo}.{nome}", _tarefa(nome))
    registro_de_teste.tarefas_de_fundo.append(("Extensão de teste", _tarefa(TAREFA_DA_EXTENSAO)))

    async def _close_redis():
        estado.eventos.append(("close_redis",))

    @asynccontextmanager
    async def _sessoes_do_mcp():
        yield

    monkeypatch.setattr(main, "_wait_for_db", AsyncMock())
    monkeypatch.setattr("app.core.redis.init_redis", AsyncMock(return_value=estado.redis))
    monkeypatch.setattr("app.core.redis.close_redis", _close_redis)
    monkeypatch.setattr("app.core.storage.ensure_bucket", MagicMock())
    monkeypatch.setattr("app.core.storage.endpoint_externo_e_local", lambda: False)
    monkeypatch.setattr("app.core.async_scheduler.scheduler", SimpleNamespace(start=AsyncMock(), stop=AsyncMock()))
    monkeypatch.setattr(main, "engine", SimpleNamespace(dispose=AsyncMock()))
    monkeypatch.setattr(main, "mcp_server", SimpleNamespace(session_manager=SimpleNamespace(run=_sessoes_do_mcp)))
    estado.lifespan = main.lifespan
    return estado


@pytest.mark.parametrize("lenta", [nome for _, nome in TAREFAS_DE_FUNDO] + [TAREFA_DA_EXTENSAO])
async def test_shutdown_aguarda_cada_tarefa_de_fundo_antes_de_fechar_o_redis(lifespan_sem_infra, lenta):
    """Cancelling is not enough: the shutdown has to AWAIT each task, otherwise it
    closes the database and Redis while the task is still mid-shutdown (and the
    loop ends with "Task was destroyed but it is pending!")."""
    estado = lifespan_sem_infra
    estado.lenta = lenta

    async with estado.lifespan(SimpleNamespace(state=SimpleNamespace())):
        await asyncio.sleep(0)  # the tasks start
        assert {e[1] for e in estado.eventos if e[0] == "subiu"} == (
            {nome for _, nome in TAREFAS_DE_FUNDO} | {TAREFA_DA_EXTENSAO}
        )

    assert ("encerrou", lenta) in estado.eventos, f"{lenta} foi cancelada e não aguardada"
    assert estado.eventos.index(("encerrou", lenta)) < estado.eventos.index(("close_redis",))


async def test_ping_da_subida_e_no_pool_assincrono(lifespan_sem_infra):
    """The connection ping goes through the async pool — it used to be a
    SYNCHRONOUS Redis client, kept only for this, which blocked the event loop
    at startup."""
    estado = lifespan_sem_infra
    async with estado.lifespan(SimpleNamespace(state=SimpleNamespace())):
        pass
    estado.redis.ping.assert_awaited_once()


# ── The periodic loops ────────────────────────────────────────────────────────


async def test_lock_e_set_nx_ex_no_pool_global(monkeypatch):
    from app.core import tarefas_periodicas

    pool = RedisFalso()
    monkeypatch.setattr("app.core.redis._pool", pool)
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is True
    assert ("set", "x:lock", True, 600) in pool.chamadas
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is False  # held until the TTL expires


async def test_redis_fora_ou_pool_nao_inicializado_prossegue_sem_lock(monkeypatch):
    """The protected routines are idempotent: without Redis, the worst case is
    repeated work, never missing work."""
    from app.core import tarefas_periodicas

    class RedisFora(RedisFalso):
        async def set(self, *args, **kwargs):
            raise ConnectionError("redis fora")

    monkeypatch.setattr("app.core.redis._pool", RedisFora())
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is True
    monkeypatch.setattr("app.core.redis._pool", None)  # outside the lifespan
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is True


async def test_laco_trabalha_a_cada_volta_sobrevive_a_erro_e_encerra_no_cancelamento():
    from app.core import tarefas_periodicas

    voltas = []

    async def _trabalho():
        voltas.append(len(voltas) + 1)
        if len(voltas) == 1:
            raise RuntimeError("banco fora")  # does not bring down the loop
        if len(voltas) == 3:
            raise asyncio.CancelledError  # o shutdown chega

    await asyncio.wait_for(tarefas_periodicas.laco_periodico("teste", 0.01, _trabalho), 2.0)
    assert voltas == [1, 2, 3]


async def test_laco_com_lock_ocupado_pula_as_voltas(monkeypatch):
    from app.core import tarefas_periodicas

    pool = RedisFalso()
    pool.dados["x:lock"] = "1"  # another worker took it
    monkeypatch.setattr("app.core.redis._pool", pool)
    voltas = []

    async def _trabalho():
        voltas.append(1)

    tarefa = asyncio.create_task(tarefas_periodicas.laco_periodico("teste", 0.01, _trabalho, lock="x:lock"))
    await asyncio.sleep(0.08)
    tarefa.cancel()
    await tarefa  # the loop handles the cancellation and finishes on its own
    assert voltas == []
    assert len([c for c in pool.chamadas if c[:2] == ("set", "x:lock")]) >= 2

# (module, loop, interval attribute, lock key, work done on each turn)
LACOS = [
    ("app.core.artifact_cleanup", "run_cleanup_loop", "_CLEANUP_INTERVAL", "artifact_cleanup:lock", "purge_expired_artifacts"),
    ("app.core.storage_reconciliation", "run_reconciliation_loop", "_RECONCILE_INTERVAL", "storage_reconcile:lock", "run_full_reconciliation"),
    ("app.core.fontes_catalogo", "run_verificacao_loop", "FONTES_VERIFICACAO_INTERVAL", "fontes_verificacao:lock", "verificar_endpoints"),
]


@pytest.mark.parametrize(
    "modulo, laco, intervalo, chave, trabalho", [pytest.param(*c, id=c[1]) for c in LACOS]
)
async def test_laco_pega_o_lock_no_pool_global_sem_abrir_cliente_por_volta(
    modulo, laco, intervalo, chave, trabalho, monkeypatch
):
    await conferir_o_lock_do_laco(modulo, laco, intervalo, chave, trabalho, monkeypatch)



# ── A single REDIS_URL ────────────────────────────────────────────────────────


async def test_consumer_de_resultados_usa_o_redis_url_da_aplicacao(monkeypatch):
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


def test_so_config_le_o_redis_url_do_ambiente():
    """A single default, in `app/core/config.py`. The declared exception is
    `rate_limiter.py`: it needs to know whether the variable was SET (absent =
    in-memory counters), and the `config.py` default would erase that difference."""
    excecoes = {"app/core/config.py", "app/core/rate_limiter.py"}
    leitores = sorted(
        str(arquivo.relative_to(RAIZ))
        for arquivo in (RAIZ / "app").rglob("*.py")
        if str(arquivo.relative_to(RAIZ)) not in excecoes
        and any(
            forma in arquivo.read_text(encoding="utf-8")
            for forma in ('getenv("REDIS_URL"', 'environ["REDIS_URL"]', 'environ.get("REDIS_URL"')
        )
    )
    assert leitores == []
