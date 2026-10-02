# tests/unit/test_tarefas_de_fundo.py
"""
Tarefas de fundo da API: o lifespan que as sobe e derruba, os laços periódicos
com lock no Redis e o `REDIS_URL` que todos leem.

Os defeitos que a repetição produziu:

- o lifespan subia oito tarefas à mão e as derrubava em blocos copiados; uma
  delas era cancelada e nunca aguardada — o shutdown seguia e
  fechava banco e Redis com ela ainda encerrando;
- três dos quatro laços periódicos abriam um cliente Redis NOVO a cada volta só
  para pegar o lock, em vez de usar o pool global;
- o `REDIS_URL` era lido do ambiente em cinco lugares além de `config.py`, e o
  consumer de resultados tinha outro default (`localhost`).
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

# As tarefas de fundo que o lifespan do núcleo sobe, pelo módulo de onde vêm.
TAREFAS_DE_FUNDO = [
    ("app.core.run_result_consumer", "run_consumer_loop"),
    ("app.core.artifact_cleanup", "run_cleanup_loop"),
    ("app.core.storage_reconciliation", "run_reconciliation_loop"),
    ("app.core.fontes_catalogo", "importar_catalogo_no_arranque"),
    ("app.core.fontes_catalogo", "run_verificacao_loop"),
    ("app.core.executor_connections", "overdue_acks_monitor"),
    ("app.api.routers.executor_ws_router", "orphan_runs_watchdog"),
]
# E a de uma extensão (app/extensoes), que sobe e encerra junto.
TAREFA_DA_EXTENSAO = "tarefa_da_extensao"


@pytest.fixture
def lifespan_sem_infra(monkeypatch, registro_de_teste):
    """O lifespan de `app.main` com banco, Redis, MinIO, scheduler e MCP dublados
    e cada tarefa de fundo trocada por uma que só espera o cancelamento.

    `eventos` guarda a ordem das coisas: ("subiu", t), ("encerrou", t) e
    ("close_redis",). `lenta` escolhe a tarefa que demora a encerrar — como uma
    de verdade, que ainda fecha conexão e loga depois do cancelamento."""
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
    """Cancelar não basta: o shutdown tem de AGUARDAR cada tarefa, senão fecha
    banco e Redis com ela ainda no meio do encerramento (e o loop acaba com
    "Task was destroyed but it is pending!")."""
    estado = lifespan_sem_infra
    estado.lenta = lenta

    async with estado.lifespan(SimpleNamespace(state=SimpleNamespace())):
        await asyncio.sleep(0)  # as tarefas sobem
        assert {e[1] for e in estado.eventos if e[0] == "subiu"} == (
            {nome for _, nome in TAREFAS_DE_FUNDO} | {TAREFA_DA_EXTENSAO}
        )

    assert ("encerrou", lenta) in estado.eventos, f"{lenta} foi cancelada e não aguardada"
    assert estado.eventos.index(("encerrou", lenta)) < estado.eventos.index(("close_redis",))


async def test_ping_da_subida_e_no_pool_assincrono(lifespan_sem_infra):
    """O ping de conexão sai pelo pool assíncrono — antes era um cliente Redis
    SÍNCRONO, mantido só para isso, que prendia o event loop na subida."""
    estado = lifespan_sem_infra
    async with estado.lifespan(SimpleNamespace(state=SimpleNamespace())):
        pass
    estado.redis.ping.assert_awaited_once()


# ── Os laços periódicos ───────────────────────────────────────────────────────


async def test_lock_e_set_nx_ex_no_pool_global(monkeypatch):
    from app.core import tarefas_periodicas

    pool = RedisFalso()
    monkeypatch.setattr("app.core.redis._pool", pool)
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is True
    assert ("set", "x:lock", True, 600) in pool.chamadas
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is False  # ocupado até o TTL vencer


async def test_redis_fora_ou_pool_nao_inicializado_prossegue_sem_lock(monkeypatch):
    """As rotinas protegidas são idempotentes: sem Redis, o pior caso é trabalho
    repetido, nunca trabalho a menos."""
    from app.core import tarefas_periodicas

    class RedisFora(RedisFalso):
        async def set(self, *args, **kwargs):
            raise ConnectionError("redis fora")

    monkeypatch.setattr("app.core.redis._pool", RedisFora())
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is True
    monkeypatch.setattr("app.core.redis._pool", None)  # fora do lifespan
    assert await tarefas_periodicas.adquirir_lock("x:lock", 600) is True


async def test_laco_trabalha_a_cada_volta_sobrevive_a_erro_e_encerra_no_cancelamento():
    from app.core import tarefas_periodicas

    voltas = []

    async def _trabalho():
        voltas.append(len(voltas) + 1)
        if len(voltas) == 1:
            raise RuntimeError("banco fora")  # não derruba o laço
        if len(voltas) == 3:
            raise asyncio.CancelledError  # o shutdown chega

    await asyncio.wait_for(tarefas_periodicas.laco_periodico("teste", 0.01, _trabalho), 2.0)
    assert voltas == [1, 2, 3]


async def test_laco_com_lock_ocupado_pula_as_voltas(monkeypatch):
    from app.core import tarefas_periodicas

    pool = RedisFalso()
    pool.dados["x:lock"] = "1"  # outro worker pegou
    monkeypatch.setattr("app.core.redis._pool", pool)
    voltas = []

    async def _trabalho():
        voltas.append(1)

    tarefa = asyncio.create_task(tarefas_periodicas.laco_periodico("teste", 0.01, _trabalho, lock="x:lock"))
    await asyncio.sleep(0.08)
    tarefa.cancel()
    await tarefa  # o laço trata o cancelamento e termina sozinho
    assert voltas == []
    assert len([c for c in pool.chamadas if c[:2] == ("set", "x:lock")]) >= 2

# (módulo, laço, atributo do intervalo, chave do lock, trabalho de cada volta)
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



# ── Um REDIS_URL só ───────────────────────────────────────────────────────────


async def test_consumer_de_resultados_usa_o_redis_url_da_aplicacao(monkeypatch):
    """Sem `REDIS_URL` no ambiente, o consumer caía em `localhost` enquanto o
    pool (e todo o resto) ia para `redis:6379`: dois Redis diferentes."""
    import redis.asyncio as aioredis

    from app.core import config, run_result_consumer

    urls = []

    def _from_url(url, **kw):
        urls.append(url)
        raise asyncio.CancelledError  # só interessa o endereço

    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(aioredis, "from_url", _from_url)

    await run_result_consumer.run_consumer_loop()

    assert urls == [config.REDIS_URL]


def test_so_config_le_o_redis_url_do_ambiente():
    """Um default só, em `app/core/config.py`. A exceção declarada é
    `rate_limiter.py`: ele precisa saber se a variável foi DEFINIDA (ausente =
    contadores em memória), e o default de `config.py` apagaria essa diferença."""
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
