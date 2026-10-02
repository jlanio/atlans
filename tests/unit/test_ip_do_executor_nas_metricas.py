"""IP do executor nas métricas das execuções.

O consumer de `run_results` roda nos quatro workers da API e procurava o IP no
registro de conexões LOCAL: só o worker que segura o WebSocket do executor o
tem, então ~3 de cada 4 execuções gravavam `workflow_run_metrics.executor_ip`
vazio. Agora o worker do WebSocket escreve o IP no resultado que enfileira, e o
consumer o lê de lá.
"""
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.routers.executor_ws import protocolo as P
from app.api.routers.executor_ws import resultados as RES
from app.core import run_result_consumer as CONS
from app.core.executor_connections import executor_registry
from app.models.run_metrics import WorkflowRunMetrics


class _RedisQueGuarda:
    def __init__(self):
        self.filas: dict[str, list[str]] = {}

    async def setex(self, *_a):
        return True

    async def lpush(self, chave, payload):
        self.filas.setdefault(chave, []).append(payload)


def _conexao(ip):
    return SimpleNamespace(
        executor_ip=ip, run_auth_cache={}, db_auth_cooldown_until=0.0,
        max_concurrent_limit=4, max_queue_limit=50,
    )


@pytest.fixture
def worker_do_websocket(monkeypatch):
    rc = _RedisQueGuarda()
    conexoes = {"ex-1": _conexao("203.0.113.7")}
    monkeypatch.setattr(executor_registry, "get", conexoes.get)
    monkeypatch.setattr(P, "_rate_state", {})

    async def _snapshot(_run_id):
        return ("executor:ex-1", "running", None)

    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)
    return rc, conexoes


@pytest.mark.asyncio
async def test_o_resultado_enfileirado_leva_o_ip_da_conexao(worker_do_websocket):
    rc, _ = worker_do_websocket
    await RES._handle_job_result("ex-1", {
        "type": "job_result", "job_id": "run-1", "run_id": "run-1", "status": "ok",
        "stats": {"__metrics__": {"run": {}}},
    })

    (payload,) = [json.loads(p) for p in rc.filas["run_results"]]
    assert payload["executor_ip"] == "203.0.113.7"


@pytest.mark.asyncio
async def test_o_executor_nao_declara_o_proprio_ip(worker_do_websocket):
    """O que o executor manda no job_result não chega à chave do servidor."""
    rc, _ = worker_do_websocket
    await RES._handle_job_result("ex-1", {
        "type": "job_result", "job_id": "run-1", "run_id": "run-1", "status": "ok",
        "executor_ip": "10.6.6.6",
        "stats": {"executor_ip": "10.6.6.6", "__metrics__": {"run": {"executor_ip": "10.6.6.6"}}},
    })

    (payload,) = [json.loads(p) for p in rc.filas["run_results"]]
    assert payload["executor_ip"] == "203.0.113.7"


# ── O consumer, em qualquer worker ──────────────────────────────────────────

def _banco():
    adicionados = []
    nome = MagicMock()
    nome.scalar_one_or_none.return_value = "executor-01"
    sem_metricas = MagicMock()
    sem_metricas.scalar_one_or_none.return_value = None
    db = MagicMock(
        commit=AsyncMock(),
        # 1ª consulta: métricas já gravadas? 2ª: o nome do executor.
        execute=AsyncMock(side_effect=[sem_metricas, nome]),
        add=adicionados.append,
    )
    return db, adicionados


def _run():
    return MagicMock(
        task_id="run-1", workflow_hash="wf-1", workspace_id="ws-1", host="executor:ex-1",
        start_time=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 9, 27, 12, 1, tzinfo=timezone.utc),
        duration_seconds=60.0, status="success", error_message=None,
    )


async def _metricas_gravadas(payload, monkeypatch, *, registro_local=None):
    """Roda o consumer num worker cujo registro local só tem `registro_local`."""
    monkeypatch.setattr(executor_registry, "get", lambda _id: registro_local)
    db, adicionados = _banco()
    await CONS._persist_metrics(db, _run(), {"run": {}}, payload)
    return next(o for o in adicionados if isinstance(o, WorkflowRunMetrics))


@pytest.mark.asyncio
async def test_consumer_em_outro_worker_grava_o_ip_do_payload(monkeypatch):
    wrm = await _metricas_gravadas({"executor_ip": "203.0.113.7"}, monkeypatch, registro_local=None)
    assert (wrm.executor_ip, wrm.executor_name) == ("203.0.113.7", "executor-01")


@pytest.mark.asyncio
async def test_resultado_antigo_sem_a_chave_ainda_tenta_o_registro_local(monkeypatch):
    """Enfileirado antes deste campo existir (deploy no meio, dead letter)."""
    wrm = await _metricas_gravadas({}, monkeypatch, registro_local=_conexao("198.51.100.4"))
    assert wrm.executor_ip == "198.51.100.4"


INVALIDOS = [
    "não é ip", "10.0.0.1; DROP TABLE", "x" * 100, 12345, None,
    # IPv6 com zona: a zona é texto livre e estourava o VARCHAR(45) da coluna.
    "fe80:1234:5678:9abc:def0:1234:5678:9abc%eeeeeeeeeeeeeee",
    "fe80::1%" + "A" * 200,
]


@pytest.mark.asyncio
@pytest.mark.parametrize("valor", INVALIDOS)
async def test_o_que_nao_e_ip_nunca_chega_a_coluna(monkeypatch, valor):
    wrm = await _metricas_gravadas({"executor_ip": valor}, monkeypatch, registro_local=None)
    assert wrm.executor_ip is None


@pytest.mark.asyncio
@pytest.mark.parametrize("valor", INVALIDOS)
async def test_sem_ip_valido_no_payload_tenta_o_registro_local(monkeypatch, valor):
    """O worker do WebSocket pode não ter o IP (conexão já fora do registro
    num takeover): o registro local ainda vale quando for o mesmo worker."""
    wrm = await _metricas_gravadas({"executor_ip": valor}, monkeypatch, registro_local=_conexao("198.51.100.4"))
    assert wrm.executor_ip == "198.51.100.4"


@pytest.mark.asyncio
async def test_o_valor_do_registro_local_tambem_e_validado(monkeypatch):
    wrm = await _metricas_gravadas({}, monkeypatch, registro_local=_conexao("testclient"))
    assert wrm.executor_ip is None


def test_ip_sai_na_forma_canonica():
    assert CONS._ip_do_payload({"executor_ip": " 2001:DB8::9 "}) == "2001:db8::9"
    assert CONS._ip_do_payload({"executor_ip": "::ffff:10.0.0.1"}) == "::ffff:10.0.0.1"


# ── O IP é o da conexão que recebeu o frame ──────────────────────────────────

@pytest.mark.asyncio
async def test_com_a_conexao_fora_do_registro_vale_o_ip_da_sessao(worker_do_websocket):
    """Takeover: o listener já tirou esta conexão do registro enquanto a fila
    dela ainda esvazia. O IP vem da sessão, não do registro."""
    rc, conexoes = worker_do_websocket
    conexoes.clear()
    await RES._handle_job_result("ex-1", {
        "type": "job_result", "job_id": "run-1", "run_id": "run-1", "status": "ok",
        "stats": {"__metrics__": {"run": {}}},
    }, executor_ip="192.0.2.10")

    (payload,) = [json.loads(p) for p in rc.filas["run_results"]]
    assert payload["executor_ip"] == "192.0.2.10"


@pytest.mark.asyncio
async def test_a_fila_da_sessao_entrega_o_ip_dela_ao_handler(monkeypatch):
    from app.api.routers.executor_ws import inbox as IB

    recebidos = []

    async def _handler(executor_id, msg, frame_bytes=0, executor_ip=None):
        recebidos.append(executor_ip)

    monkeypatch.setattr(IB, "_handle_job_result", _handler)
    fila = IB._InboxQueue(maxsize=10)
    fila.ip_da_conexao = "192.0.2.10"
    await fila.put(("job_result", {"job_id": "j1", "run_id": "j1"}, 10))
    await fila.put(IB._INBOX_STOP)

    await IB._drenar_inbox("ex-1", fila, set())

    assert recebidos == ["192.0.2.10"]


@pytest.mark.asyncio
async def test_o_resgate_do_teardown_tambem_leva_o_ip_da_sessao(monkeypatch):
    from app.api.routers.executor_ws import inbox as IB

    recebidos = []

    async def _handler(executor_id, msg, frame_bytes=0, executor_ip=None):
        recebidos.append(executor_ip)

    monkeypatch.setattr(IB, "_handle_job_result", _handler)
    fila = IB._InboxQueue(maxsize=10)
    fila.ip_da_conexao = "192.0.2.10"
    fila.put_nowait(("job_result", {"job_id": "j1", "run_id": "j1"}, 10))

    await IB._resgatar_job_results_pendentes("ex-1", fila)

    assert recebidos == ["192.0.2.10"]
