"""Executor IP in the run metrics.

The `run_results` consumer runs in the API's four workers and looked up the IP in
the LOCAL connection registry: only the worker holding the executor's WebSocket
has it, so ~3 out of 4 runs stored an empty `workflow_run_metrics.executor_ip`.
Now the WebSocket worker writes the IP into the result it enqueues, and the
consumer reads it from there.
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


class _StoringRedis:
    def __init__(self):
        self.queues: dict[str, list[str]] = {}

    async def setex(self, *_a):
        return True

    async def lpush(self, chave, payload):
        self.queues.setdefault(chave, []).append(payload)


def _connection(ip):
    return SimpleNamespace(
        executor_ip=ip, run_auth_cache={}, db_auth_cooldown_until=0.0,
        max_concurrent_limit=4, max_queue_limit=50,
    )


@pytest.fixture
def worker_do_websocket(monkeypatch):
    rc = _StoringRedis()
    conexoes = {"ex-1": _connection("203.0.113.7")}
    monkeypatch.setattr(executor_registry, "get", conexoes.get)
    monkeypatch.setattr(P, "_rate_state", {})

    async def _snapshot(_run_id):
        return ("executor:ex-1", "running", None)

    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)
    return rc, conexoes


@pytest.mark.asyncio
async def test_queued_result_carries_connection_ip(worker_do_websocket):
    rc, _ = worker_do_websocket
    await RES._handle_job_result("ex-1", {
        "type": "job_result", "job_id": "run-1", "run_id": "run-1", "status": "ok",
        "stats": {"__metrics__": {"run": {}}},
    })

    (payload,) = [json.loads(p) for p in rc.queues["run_results"]]
    assert payload["executor_ip"] == "203.0.113.7"


@pytest.mark.asyncio
async def test_executor_does_not_declare_its_own_ip(worker_do_websocket):
    """What the executor sends in the job_result does not reach the server's key."""
    rc, _ = worker_do_websocket
    await RES._handle_job_result("ex-1", {
        "type": "job_result", "job_id": "run-1", "run_id": "run-1", "status": "ok",
        "executor_ip": "10.6.6.6",
        "stats": {"executor_ip": "10.6.6.6", "__metrics__": {"run": {"executor_ip": "10.6.6.6"}}},
    })

    (payload,) = [json.loads(p) for p in rc.queues["run_results"]]
    assert payload["executor_ip"] == "203.0.113.7"


# ── O consumer, em qualquer worker ──────────────────────────────────────────

def _from_db():
    adicionados = []
    nome = MagicMock()
    nome.scalar_one_or_none.return_value = "executor-01"
    no_metrics = MagicMock()
    no_metrics.scalar_one_or_none.return_value = None
    db = MagicMock(
        commit=AsyncMock(),
        # 1st query: metrics already stored? 2nd: the executor's name.
        execute=AsyncMock(side_effect=[no_metrics, nome]),
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


async def _stored_metrics(payload, monkeypatch, *, registro_local=None):
    """Runs the consumer in a worker whose local registry only has `registro_local`."""
    monkeypatch.setattr(executor_registry, "get", lambda _id: registro_local)
    db, adicionados = _from_db()
    await CONS._persist_metrics(db, _run(), {"run": {}}, payload)
    return next(o for o in adicionados if isinstance(o, WorkflowRunMetrics))


@pytest.mark.asyncio
async def test_consumer_on_another_worker_stores_payload_ip(monkeypatch):
    wrm = await _stored_metrics({"executor_ip": "203.0.113.7"}, monkeypatch, registro_local=None)
    assert (wrm.executor_ip, wrm.executor_name) == ("203.0.113.7", "executor-01")


@pytest.mark.asyncio
async def test_old_result_without_key_still_tries_local_registry(monkeypatch):
    """Enqueued before this field existed (mid-deploy, dead letter)."""
    wrm = await _stored_metrics({}, monkeypatch, registro_local=_connection("198.51.100.4"))
    assert wrm.executor_ip == "198.51.100.4"


INVALID_VALUES = [
    "não é ip", "10.0.0.1; DROP TABLE", "x" * 100, 12345, None,
    # IPv6 with a zone: the zone is free text and overflowed the column's VARCHAR(45).
    "fe80:1234:5678:9abc:def0:1234:5678:9abc%eeeeeeeeeeeeeee",
    "fe80::1%" + "A" * 200,
]


@pytest.mark.asyncio
@pytest.mark.parametrize("valor", INVALID_VALUES)
async def test_non_ip_never_reaches_the_column(monkeypatch, valor):
    wrm = await _stored_metrics({"executor_ip": valor}, monkeypatch, registro_local=None)
    assert wrm.executor_ip is None


@pytest.mark.asyncio
@pytest.mark.parametrize("valor", INVALID_VALUES)
async def test_without_valid_ip_in_payload_tries_local_registry(monkeypatch, valor):
    """The WebSocket worker may not have the IP (connection already out of the registry
    in a takeover): the local registry still applies when it is the same worker."""
    wrm = await _stored_metrics({"executor_ip": valor}, monkeypatch, registro_local=_connection("198.51.100.4"))
    assert wrm.executor_ip == "198.51.100.4"


@pytest.mark.asyncio
async def test_local_registry_value_is_also_validated(monkeypatch):
    wrm = await _stored_metrics({}, monkeypatch, registro_local=_connection("testclient"))
    assert wrm.executor_ip is None


def test_ip_comes_out_in_canonical_form():
    assert CONS._ip_do_payload({"executor_ip": " 2001:DB8::9 "}) == "2001:db8::9"
    assert CONS._ip_do_payload({"executor_ip": "::ffff:10.0.0.1"}) == "::ffff:10.0.0.1"


# ── The IP is that of the connection that received the frame ─────────────────

@pytest.mark.asyncio
async def test_with_connection_outside_registry_session_ip_counts(worker_do_websocket):
    """Takeover: the listener has already removed this connection from the registry
    while its queue is still draining. The IP comes from the session, not the registry."""
    rc, conexoes = worker_do_websocket
    conexoes.clear()
    await RES._handle_job_result("ex-1", {
        "type": "job_result", "job_id": "run-1", "run_id": "run-1", "status": "ok",
        "stats": {"__metrics__": {"run": {}}},
    }, executor_ip="192.0.2.10")

    (payload,) = [json.loads(p) for p in rc.queues["run_results"]]
    assert payload["executor_ip"] == "192.0.2.10"


@pytest.mark.asyncio
async def test_session_queue_delivers_its_ip_to_handler(monkeypatch):
    from app.api.routers.executor_ws import inbox as IB

    recebidos = []

    async def _handler(executor_id, msg, frame_bytes=0, executor_ip=None):
        recebidos.append(executor_ip)

    monkeypatch.setattr(IB, "_handle_job_result", _handler)
    fila = IB._InboxQueue(maxsize=10)
    fila.ip_da_conexao = "192.0.2.10"
    await fila.put(("job_result", {"job_id": "j1", "run_id": "j1"}, 10))
    await fila.put(IB._INBOX_STOP)

    await IB._drain_inbox("ex-1", fila, set())

    assert recebidos == ["192.0.2.10"]


@pytest.mark.asyncio
async def test_teardown_rescue_also_carries_session_ip(monkeypatch):
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
