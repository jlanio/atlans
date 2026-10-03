# tests/unit/test_job_result_caracterizacao.py
"""Characterization of `_handle_job_result`: what it writes, publishes and in what order.

The handler receives results from OLD and NEW executors in the field, so the
format and order of each effect are a contract — with the `run_results` consumer,
with the synchronous webhook (BRPOP on `webhook_response:{run}`) and with the panel (the
`__workflow_complete__`). A Redis that logs each command in the order it arrives
pins down:

- the order database → Redis → webhook: run read, ephemeral result key,
  `run_results` queue, `webhook_response`, body Artifact in MinIO and,
  last, history + the `__workflow_complete__` channel;
- the exact format (keys, order, values) of each payload in the outcomes ok,
  failure with and without taxonomy, and cancelled — from the old executor (no `run_id`, no
  `error_category`) and from the new one;
- validation and truncation of `stats`/`error` on input, and the explicit error
  to the webhook when truncation took even the control keys;
- idempotency (repeated job_result for a terminal run), refusal by memo,
  rate limiting and closing the run as failed when the result is lost;
- that the failure of one destination does not prevent the following ones.
"""
import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.api.routers.executor_ws import protocolo as P
from app.api.routers.executor_ws import resultados as RES
from app.core.constants import MAX_EVENTS_IN_HISTORY, REDIS_TTL_1H, WORKFLOW_COMPLETE_NODE
from app.core.executor_connections import executor_registry
from flow.utils.protocolo_ws import (
    STATS_CONTROL_DROPPED,
    STATS_ORIGINAL_SIZE,
    STATS_TRUNCATED,
)

EX = "ex-1"
RUN = "run-1"
IP = "203.0.113.7"
HIST = f"workflow:{RUN}:history"
CANAL = f"workflow:{RUN}:events"
WEBHOOK = f"webhook_response:{RUN}"


# ── Test doubles ──────────────────────────────────────────────────────────────


class _Pipe:
    """Pipeline that only reaches the log on `execute` — all or nothing, as in Redis."""

    def __init__(self, rc):
        self._rc = rc
        self._cmds: list[tuple] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    def rpush(self, chave, *valores):
        self._cmds.append(("pipe.rpush", chave, *valores))

    def ltrim(self, chave, inicio, fim):
        self._cmds.append(("pipe.ltrim", chave, inicio, fim))

    def expire(self, chave, ttl):
        self._cmds.append(("pipe.expire", chave, ttl))

    def publish(self, canal, valor):
        self._cmds.append(("pipe.publish", canal, valor))

    def lpush(self, chave, valor):
        self._cmds.append(("pipe.lpush", chave, valor))

    async def execute(self):
        self._rc.record(*self._cmds, ("pipe.execute",))
        return []


class _Redis:
    """Logs, in order, each command that arrives. `falhar(cmd)` decides which ones raise."""

    def __init__(self, diario: list, falhar):
        self._journal = diario
        self._fail = falhar

    def record(self, *cmds):
        for cmd in cmds:
            if self._fail(cmd):
                raise ConnectionError(f"redis recusou {cmd[0]}")
        self._journal.extend(cmds)

    async def setex(self, chave, ttl, valor):
        self.record(("setex", chave, ttl, valor))

    async def lpush(self, chave, valor):
        self.record(("lpush", chave, valor))

    async def expire(self, chave, ttl):
        self.record(("expire", chave, ttl))

    def pipeline(self, transaction=True):
        assert transaction is False
        return _Pipe(self)


@pytest.fixture
def cenario(monkeypatch):
    """Executor connected to THIS worker, its run 'running', Redis logging everything.

    `linha` is what `_query_run_snapshot` returns (host, status, start_time);
    `falhar` receives each Redis command and says whether it raises.
    """
    diario: list[tuple] = []
    estado = SimpleNamespace(
        diario=diario,
        conn=SimpleNamespace(executor_ip=IP, run_auth_cache={}, db_auth_cooldown_until=0.0),
        linha=(f"executor:{EX}", "running", datetime.now(timezone.utc) - timedelta(seconds=10)),
        falhar=lambda _cmd: False,
        body_failure=None,
    )

    async def _snapshot(run_id):
        diario.append(("snapshot", run_id))
        if isinstance(estado.linha, Exception):
            raise estado.linha
        return estado.linha

    async def _body(run_id, executor_id, body_ref):
        diario.append(("body_artifact", run_id, executor_id, body_ref))
        if estado.body_failure is not None:
            raise estado.body_failure

    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot)
    monkeypatch.setattr(RES, "_JOB_RESULT_DB_RETRY_DELAY", 0.0)
    monkeypatch.setattr(RES, "_register_webhook_response_artifact", _body)
    monkeypatch.setattr(executor_registry, "get", lambda _id: estado.conn)
    monkeypatch.setattr(
        "app.core.redis.get_redis_pool", lambda: _Redis(diario, lambda cmd: estado.falhar(cmd)),
    )
    # The app's logger only propagates to root when root already had a handler at
    # import; here propagation is ensured so caplog can see the messages.
    monkeypatch.setattr(RES.logger, "propagate", True)
    return estado


def _names(diario) -> list[str]:
    return [cmd[0] for cmd in diario]


def _single(diario, nome, chave):
    achados = [cmd for cmd in diario if cmd[0] == nome and cmd[1] == chave]
    assert len(achados) == 1, f"{nome} {chave}: {achados}"
    return achados[0]


def _run_result(diario) -> tuple[str, dict]:
    raw = _single(diario, "lpush", "run_results")[2]
    return raw, json.loads(raw)


def _completion(diario) -> tuple[str, dict]:
    raw = _single(diario, "pipe.publish", CANAL)[2]
    return raw, json.loads(raw)


def _expected_run_result(
    obtido: dict, *, status, error_message=None, error_category=None, retryable=False,
    executor_ip=IP, stats_json="{}",
) -> str:
    """The queue envelope, byte by byte: `json.dumps` header + spliced `stats`.

    `end_time` and `duration_seconds` depend on the clock and come from the actual value;
    the rest is what the contract fixes.
    """
    head = json.dumps({
        "task_id":          RUN,
        "status":           status,
        "error_message":    error_message,
        "error_category":   error_category,
        "retryable":        retryable,
        "end_time":         obtido["end_time"],
        "duration_seconds": obtido["duration_seconds"],
        "executor_ip":      executor_ip,
    })
    return f'{head[:-1]},"stats":{stats_json}}}'


def _expected_completion(obtido: dict, *, level, status, error=None, extra=None) -> str:
    return json.dumps({
        "run_id":      RUN,
        "node":        WORKFLOW_COMPLETE_NODE,
        "kind":        "lifecycle",
        "level":       level,
        "status":      status,
        "timestamp":   obtido["timestamp"],
        "duration_ms": obtido["duration_ms"],
        "error":       error,
        "extra":       extra,
    })


def _completion_pipeline(raw: str) -> list[tuple]:
    return [
        ("pipe.rpush", HIST, raw),
        ("pipe.ltrim", HIST, -MAX_EVENTS_IN_HISTORY, -1),
        ("pipe.expire", HIST, REDIS_TTL_1H),
        ("pipe.publish", CANAL, raw),
        ("pipe.execute",),
    ]


def _ephemeral(**campos) -> str:
    base = {
        "job_id": RUN, "status": None, "run_id": None, "error": None,
        "error_category": None, "retryable": False,
    }
    base.update(campos)
    return json.dumps(base)


def _messages(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == RES.logger.name]


# ── Desfechos: formato e ordem ────────────────────────────────────────────────


async def test_new_executor_ok_stores_in_usual_order_and_format(cenario, caplog):
    stats = {"n1": {"status": "completed", "rows": 3}, "__metrics__": {"run": {"duration_ms": 10}}}
    # Ownership already proven by node_events: the memo does not skip the read and exits at the end.
    cenario.conn.run_auth_cache[RUN] = (True, time.monotonic() + 60)

    with caplog.at_level("INFO"):
        await RES._handle_job_result(EX, {
            "type": "job_result", "job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats,
        })

    d = cenario.diario
    assert _names(d) == [
        "snapshot", "setex", "lpush",
        "pipe.rpush", "pipe.ltrim", "pipe.expire", "pipe.publish", "pipe.execute",
    ]
    assert d[0] == ("snapshot", RUN)
    assert d[1] == ("setex", f"executor:{EX}:results:{RUN}", 300, _ephemeral(status="ok", run_id=RUN))

    raw, res = _run_result(d)
    assert raw == _expected_run_result(res, status="success", stats_json=json.dumps(stats))
    assert 10 <= res["duration_seconds"] < 11
    fim = datetime.fromisoformat(res["end_time"])
    assert fim.utcoffset() == timedelta(0)
    assert abs((datetime.now(timezone.utc) - fim).total_seconds()) < 5

    raw_ev, ev = _completion(d)
    assert raw_ev == _expected_completion(ev, level="info", status="completed")
    assert abs(ev["duration_ms"] - res["duration_seconds"] * 1000) < 1
    assert abs(ev["timestamp"] - time.time()) < 5
    assert d[3:] == _completion_pipeline(raw_ev)

    assert RUN not in cenario.conn.run_auth_cache
    assert "Resultado do job 'run-1' recebido do executor 'ex-1': status=ok." in _messages(caplog)


async def test_old_executor_failure_without_run_id_or_taxonomy(cenario, caplog):
    """The back-pressure/shutdown format: only `job_id`, `status` and `error`."""
    erro = "Fila do executor cheia — back-pressure."
    cenario.linha = (f"executor:{EX}", "running", None)

    with caplog.at_level("INFO"):
        await RES._handle_job_result(EX, {
            "type": "job_result", "job_id": RUN, "status": "error", "error": erro,
        })

    d = cenario.diario
    assert _names(d) == [
        "snapshot", "setex", "lpush", "lpush", "expire",
        "pipe.rpush", "pipe.ltrim", "pipe.expire", "pipe.publish", "pipe.execute",
    ]
    assert d[1][3] == _ephemeral(status="error", run_id=None, error=erro)

    raw, res = _run_result(d)
    assert raw == _expected_run_result(res, status="failed", error_message=erro)
    assert res["duration_seconds"] is None

    assert d[3] == ("lpush", WEBHOOK, json.dumps({"job_status": "error", "error": erro, "response": None}))
    assert d[4] == ("expire", WEBHOOK, 300)

    raw_ev, ev = _completion(d)
    assert raw_ev == _expected_completion(
        ev, level="error", status="failed", error=erro,
        extra={"error_category": None, "retryable": False},
    )
    assert ev["duration_ms"] is None
    assert d[5:] == _completion_pipeline(raw_ev)
    assert (
        "Resultado do job 'run-1' recebido do executor 'ex-1': status=error "
        "category=internal retryable=False."
    ) in _messages(caplog)


async def test_new_executor_failure_carries_taxonomy(cenario, caplog):
    with caplog.at_level("INFO"):
        await RES._handle_job_result(EX, {
            "type": "job_result", "job_id": RUN, "run_id": RUN, "status": "error",
            "error": "coluna 'x' não existe", "error_category": "user", "retryable": True,
            "stats": {"n1": {"status": "failed"}},
        })

    d = cenario.diario
    assert d[1][3] == _ephemeral(
        status="error", run_id=RUN, error="coluna 'x' não existe",
        error_category="user", retryable=True,
    )
    raw, res = _run_result(d)
    assert raw == _expected_run_result(
        res, status="failed", error_message="coluna 'x' não existe",
        error_category="user", retryable=True,
        stats_json=json.dumps({"n1": {"status": "failed"}}),
    )
    raw_ev, ev = _completion(d)
    assert raw_ev == _expected_completion(
        ev, level="error", status="failed", error="coluna 'x' não existe",
        extra={"error_category": "user", "retryable": True},
    )
    assert (
        "Resultado do job 'run-1' recebido do executor 'ex-1': status=error "
        "category=user retryable=True."
    ) in _messages(caplog)


async def test_cancelled_is_not_failure_nor_carries_taxonomy(cenario):
    """Cancelling is a user request: info level, no category, no retryable."""
    erro = "Cancelado pelo usuário."
    await RES._handle_job_result(EX, {
        "type": "job_result", "job_id": RUN, "run_id": RUN, "status": "cancelled",
        "error": erro, "error_category": "user", "retryable": True,
    })

    d = cenario.diario
    assert d[1][3] == _ephemeral(status="cancelled", run_id=RUN, error=erro)
    raw, res = _run_result(d)
    assert raw == _expected_run_result(res, status="cancelled", error_message=erro)
    # The synchronous webhook is unblocked with the executor's raw status.
    assert _single(d, "lpush", WEBHOOK)[2] == json.dumps(
        {"job_status": "cancelled", "error": erro, "response": None},
    )
    raw_ev, ev = _completion(d)
    assert raw_ev == _expected_completion(ev, level="info", status="cancelled", error=erro)


async def test_naive_start_time_is_read_as_utc(cenario):
    inicio = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=30)
    cenario.linha = (f"executor:{EX}", "running", inicio)

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})

    _, res = _run_result(cenario.diario)
    assert 30 <= res["duration_seconds"] < 31
    _, ev = _completion(cenario.diario)
    assert 30_000 <= ev["duration_ms"] < 31_000


async def test_explicitly_passed_connection_ip_wins_over_registry(cenario):
    await RES._handle_job_result(
        EX, {"job_id": RUN, "run_id": RUN, "status": "ok"}, executor_ip="198.51.100.9",
    )
    _, res = _run_result(cenario.diario)
    assert res["executor_ip"] == "198.51.100.9"


async def test_without_connection_on_this_worker_ip_is_null(cenario):
    cenario.conn = None
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})
    raw, res = _run_result(cenario.diario)
    assert raw == _expected_run_result(res, status="success", executor_ip=None)


# ── Synchronous webhook and body in MinIO ────────────────────────────────────


async def test_inline_response_goes_to_webhook_before_completion(cenario):
    resposta = {"status": 201, "headers": {"X-Id": "7"}, "body": {"id": 7}}
    stats = {"n1": {"status": "completed"}, "__response__": resposta}

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    d = cenario.diario
    assert _names(d) == [
        "snapshot", "setex", "lpush", "lpush", "expire",
        "pipe.rpush", "pipe.ltrim", "pipe.expire", "pipe.publish", "pipe.execute",
    ]
    assert d[2][1] == "run_results"
    assert d[3] == ("lpush", WEBHOOK, json.dumps({"job_status": "ok", "error": None, "response": resposta}))
    assert d[4] == ("expire", WEBHOOK, 300)


async def test_ok_without_response_node_does_not_touch_webhook(cenario):
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": {"n1": {}}})
    assert not [cmd for cmd in cenario.diario if WEBHOOK in cmd]


async def test_body_in_minio_registers_artifact_between_webhook_and_completion(cenario):
    body_ref = {"s3_key": f"webhook-responses/ws-1/{RUN}/body.json", "size": 2048}
    resposta = {"status": 200, "body_ref": body_ref}

    await RES._handle_job_result(EX, {
        "job_id": RUN, "run_id": RUN, "status": "ok", "stats": {"__response__": resposta},
    })

    d = cenario.diario
    assert _names(d) == [
        "snapshot", "setex", "lpush", "lpush", "expire", "body_artifact",
        "pipe.rpush", "pipe.ltrim", "pipe.expire", "pipe.publish", "pipe.execute",
    ]
    assert d[5] == ("body_artifact", RUN, EX, body_ref)


async def test_body_ref_without_s3_key_does_not_register_artifact(cenario):
    await RES._handle_job_result(EX, {
        "job_id": RUN, "run_id": RUN, "status": "ok",
        "stats": {"__response__": {"status": 200, "body_ref": {"size": 1}}},
    })
    assert "body_artifact" not in _names(cenario.diario)


@pytest.mark.parametrize("body_ref", ["webhook-responses/ws-1/body.json", ["s3_key"], 7])
async def test_malformed_body_ref_does_not_prevent_completion(cenario, body_ref):
    """A faulty (or compromised) executor that sends a malformed `body_ref`
    does not take the end of the run away from the panel: the body is not
    registered, and the completion goes out as always."""
    await RES._handle_job_result(EX, {
        "job_id": RUN, "run_id": RUN, "status": "ok",
        "stats": {"__response__": {"status": 200, "body_ref": body_ref}},
    })
    nomes = _names(cenario.diario)
    assert "body_artifact" not in nomes
    assert nomes[-1] == "pipe.execute"


async def test_body_registration_failure_does_not_prevent_completion(cenario, caplog):
    cenario.body_failure = RuntimeError("banco fora")
    body_ref = {"s3_key": f"webhook-responses/ws-1/{RUN}/body.json"}

    with caplog.at_level("ERROR"):
        await RES._handle_job_result(EX, {
            "job_id": RUN, "run_id": RUN, "status": "ok",
            "stats": {"__response__": {"status": 200, "body_ref": body_ref}},
        })

    assert _names(cenario.diario)[-1] == "pipe.execute"
    assert (
        "Falha ao registrar Artifact de webhook response (run=run-1): banco fora"
        in _messages(caplog)
    )


# ── Validation and truncation of stats/error ─────────────────────────────────


async def test_truncation_that_took_control_keys_becomes_webhook_error(cenario):
    """A (new) executor that truncated `stats` down to without `__response__`: the webhook
    receives an explicit error instead of waiting for the timeout."""
    stats = {STATS_TRUNCATED: True, STATS_ORIGINAL_SIZE: 20_000_000, STATS_CONTROL_DROPPED: True}

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    d = cenario.diario
    raw, res = _run_result(d)
    assert raw == _expected_run_result(res, status="success", stats_json=json.dumps(stats))
    assert _single(d, "lpush", WEBHOOK)[2] == json.dumps({
        "job_status": "error",
        "error": (
            "Resposta do workflow excedeu o limite de 20000000 bytes no transporte "
            "executor→servidor. Reduza o tamanho do body (ex: compactar geometria, "
            "paginar resultados) ou consuma via runner assíncrono."
        ),
        "response": None,
    })
    # The RUN's outcome is still success: only the body did not fit.
    raw_ev, ev = _completion(d)
    assert raw_ev == _expected_completion(ev, level="info", status="completed")


async def test_truncation_that_kept_response_delivers_body(cenario):
    resposta = {"status": 200, "body": "ok"}
    stats = {STATS_TRUNCATED: True, STATS_ORIGINAL_SIZE: 99, "__response__": resposta}

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    assert _single(cenario.diario, "lpush", WEBHOOK)[2] == json.dumps(
        {"job_status": "ok", "error": None, "response": resposta},
    )


async def test_stats_over_ceiling_is_reduced_before_all_destinations(cenario):
    """The server reapplies the protocol's truncation: the per-node stats go, the
    control keys stay — the webhook still receives the response."""
    resposta = {"status": 200, "body": "ok"}
    stats = {f"node-{i}": {"rows": "x" * 2000} for i in range(2500)}
    stats["__response__"] = resposta
    tamanho = len(json.dumps(stats, default=str))
    assert tamanho > P._MAX_JOB_STATS_BYTES

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    raw, res = _run_result(cenario.diario)
    reduzido = {"__response__": resposta, STATS_TRUNCATED: True, STATS_ORIGINAL_SIZE: tamanho}
    assert raw == _expected_run_result(res, status="success", stats_json=json.dumps(reduzido, default=str))
    assert _single(cenario.diario, "lpush", WEBHOOK)[2] == json.dumps(
        {"job_status": "ok", "error": None, "response": resposta},
    )


async def test_too_large_response_drops_control_and_notifies_webhook(cenario):
    stats = {"__response__": {"status": 200, "body": "x" * (P._MAX_JOB_STATS_BYTES + 10)}}
    tamanho = len(json.dumps(stats, default=str))

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    raw, res = _run_result(cenario.diario)
    badges = {STATS_TRUNCATED: True, STATS_ORIGINAL_SIZE: tamanho, STATS_CONTROL_DROPPED: True}
    assert raw == _expected_run_result(res, status="success", stats_json=json.dumps(badges))
    webhook = json.loads(_single(cenario.diario, "lpush", WEBHOOK)[2])
    assert webhook["job_status"] == "error"
    assert webhook["response"] is None
    assert f"limite de {tamanho} bytes" in webhook["error"]


async def test_non_object_stats_becomes_empty(cenario):
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": [1, 2]})
    raw, res = _run_result(cenario.diario)
    assert raw == _expected_run_result(res, status="success", stats_json="{}")
    assert not [cmd for cmd in cenario.diario if WEBHOOK in cmd]


async def test_recursive_stats_marks_control_dropped(cenario):
    stats: dict = {"n1": {}}
    stats["n1"]["eu"] = stats

    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats})

    raw, res = _run_result(cenario.diario)
    badges = {STATS_TRUNCATED: True, STATS_CONTROL_DROPPED: True}
    assert raw == _expected_run_result(res, status="success", stats_json=json.dumps(badges))
    assert "limite de ? bytes" in json.loads(_single(cenario.diario, "lpush", WEBHOOK)[2])["error"]


async def test_huge_non_text_error_is_contained_in_all_destinations(cenario):
    erro = {"trace": "y" * 20_000}
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "error", "error": erro})

    contained = repr(erro)[:P._MAX_JOB_ERROR_CHARS] + "…[truncado pelo servidor]"
    d = cenario.diario
    assert json.loads(d[1][3])["error"] == contained[:500]
    _, res = _run_result(d)
    assert res["error_message"] == contained
    assert json.loads(_single(d, "lpush", WEBHOOK)[2])["error"] == contained
    _, ev = _completion(d)
    assert ev["error"] == contained


async def test_large_frame_serializes_off_loop_with_same_result(cenario, monkeypatch):
    """Above the threshold, the containment of `stats` and the webhook dumps go to a
    thread — and what reaches Redis is the same."""
    real = asyncio.to_thread
    em_thread: list[str] = []

    async def _spy(fn, *a, **kw):
        em_thread.append(fn.__name__)
        return await real(fn, *a, **kw)

    monkeypatch.setattr(asyncio, "to_thread", _spy)
    resposta = {"status": 200, "body": {"id": 1}}
    stats = {"n1": {}, "__response__": resposta}

    await RES._handle_job_result(
        EX, {"job_id": RUN, "run_id": RUN, "status": "ok", "stats": stats},
        frame_bytes=RES._JSON_OFFLOAD_THRESHOLD + 1,
    )

    assert em_thread == ["_cap_job_result", "dumps"]
    raw, res = _run_result(cenario.diario)
    assert raw == _expected_run_result(res, status="success", stats_json=json.dumps(stats))
    assert _single(cenario.diario, "lpush", WEBHOOK)[2] == json.dumps(
        {"job_status": "ok", "error": None, "response": resposta},
    )


async def test_small_frame_does_not_use_thread(cenario, monkeypatch):
    em_thread: list = []

    async def _spy(fn, *a, **kw):  # pragma: no cover - must not be called
        em_thread.append(fn)
        return fn(*a, **kw)

    monkeypatch.setattr(asyncio, "to_thread", _spy)
    await RES._handle_job_result(EX, {
        "job_id": RUN, "run_id": RUN, "status": "ok", "stats": {"__response__": {"status": 200}},
    }, frame_bytes=10)
    assert em_thread == []


# ── Idempotency, ownership and limits ────────────────────────────────────────


@pytest.mark.parametrize("terminal", ["success", "failed", "cancelled"])
async def test_repeated_job_result_of_closed_run_stores_nothing(cenario, caplog, terminal):
    """Redelivery via the outbox (old or new executor): the first one closes the run,
    the second finds the terminal row and exits without touching Redis."""
    msg = {"type": "job_result", "job_id": RUN, "run_id": RUN, "status": "ok", "stats": {"n1": {}}}
    await RES._handle_job_result(EX, dict(msg))
    primeira = list(cenario.diario)
    assert "lpush" in _names(primeira)

    cenario.diario.clear()
    cenario.linha = (f"executor:{EX}", terminal, None)
    with caplog.at_level("INFO"):
        await RES._handle_job_result(EX, dict(msg))

    assert cenario.diario == [("snapshot", RUN)]
    assert (
        "Job 'run-1' (run 'run-1'): run já está em estado terminal — resultado "
        "ignorado (idempotência)."
    ) in _messages(caplog)


async def test_rejection_memo_denies_without_reading_db(cenario, caplog):
    cenario.conn.run_auth_cache[RUN] = (False, time.monotonic() + 60)

    with caplog.at_level("WARNING"):
        await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})

    assert cenario.diario == []
    assert (
        "Executor 'ex-1' tentou reportar job_result para run 'run-1' que não lhe "
        "pertence — rejeitado."
    ) in _messages(caplog)


async def test_expired_rejection_memo_reads_db_again(cenario):
    cenario.conn.run_auth_cache[RUN] = (False, time.monotonic() - 1)
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})
    assert cenario.diario[0] == ("snapshot", RUN)
    assert "lpush" in _names(cenario.diario)


@pytest.mark.parametrize("host", ["executor:ex-2", None])
async def test_run_not_from_this_executor_is_rejected_and_memoized(cenario, caplog, host):
    cenario.linha = (host, "running", None) if host else None

    with caplog.at_level("WARNING"):
        await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})

    assert cenario.diario == [("snapshot", RUN)]
    ok, prazo = cenario.conn.run_auth_cache[RUN]
    assert ok is False
    assert 0 < prazo - time.monotonic() <= RES._RUN_AUTH_TTL_DENY
    assert (
        f"Executor 'ex-1' tentou reportar job_result para run 'run-1' que não lhe "
        f"pertence (host={host}) — rejeitado."
    ) in _messages(caplog)


async def test_without_job_id_touches_nothing(cenario, caplog):
    with caplog.at_level("WARNING"):
        await RES._handle_job_result(EX, {"run_id": RUN, "status": "ok"})
    assert cenario.diario == []
    assert "Executor 'ex-1' enviou job_result sem job_id." in _messages(caplog)


def _inconclusive_close(diario, motivo: str) -> None:
    """The single pipeline of `_close_inconclusive_run`, checked byte by byte."""
    mensagem = f"Resultado do executor não pôde ser processado: {motivo}"
    assert _names(diario)[-8:] == [
        "pipe.lpush", "pipe.rpush", "pipe.ltrim", "pipe.expire", "pipe.publish",
        "pipe.lpush", "pipe.expire", "pipe.execute",
    ]
    cmds = diario[-8:]
    assert cmds[0][1] == "run_results"
    resultado = json.loads(cmds[0][2])
    assert cmds[0][2] == json.dumps({
        "task_id":          RUN,
        "status":           "failed",
        "error_message":    mensagem,
        "error_category":   "internal",
        "retryable":        True,
        "end_time":         resultado["end_time"],
        "duration_seconds": None,
        "stats":            {},
    })
    evento = json.loads(cmds[1][2])
    assert cmds[1][2] == json.dumps({
        "run_id":      RUN,
        "node":        WORKFLOW_COMPLETE_NODE,
        "kind":        "lifecycle",
        "level":       "error",
        "status":      "failed",
        "timestamp":   evento["timestamp"],
        "duration_ms": None,
        "error":       mensagem,
        "extra":       {"error_category": "internal", "retryable": True},
    })
    # The event stamps the SAME instant as the end stored in the result.
    assert evento["timestamp"] == datetime.fromisoformat(resultado["end_time"]).timestamp()
    assert cmds[1:5] == _completion_pipeline(cmds[1][2])[:4]
    assert cmds[5] == ("pipe.lpush", WEBHOOK, json.dumps(
        {"job_status": "error", "error": mensagem, "response": None},
    ))
    assert cmds[6] == ("pipe.expire", WEBHOOK, 300)


async def test_rate_limit_with_proven_ownership_closes_run_as_failed(cenario, monkeypatch, caplog):
    monkeypatch.setattr(RES, "_rate_allowed", lambda *_a: False)
    cenario.conn.run_auth_cache[RUN] = (True, time.monotonic() + 60)

    with caplog.at_level("ERROR"):
        await RES._handle_job_result(EX, {"job_id": "job-x", "run_id": RUN, "status": "ok"})

    # It does not even read the database: the discard comes before authorization.
    assert "snapshot" not in _names(cenario.diario)
    _inconclusive_close(cenario.diario, "rate limit de job_result")
    assert (
        f"Executor 'ex-1': job_result do job 'job-x' descartado por rate limit "
        f"(>{P._JOB_RESULT_RATE_LIMIT}/{P._RATE_WINDOW:.0f}s)."
    ) in _messages(caplog)


async def test_rate_limit_without_proven_ownership_only_discards(cenario, monkeypatch):
    monkeypatch.setattr(RES, "_rate_allowed", lambda *_a: False)
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})
    assert cenario.diario == []


async def test_db_down_retries_and_closes_run_with_proven_ownership(cenario, caplog):
    cenario.linha = RuntimeError("pool esgotado")
    cenario.conn.run_auth_cache[RUN] = (True, time.monotonic() + 60)

    with caplog.at_level("ERROR"):
        await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})

    assert _names(cenario.diario)[:RES._JOB_RESULT_DB_RETRIES] == ["snapshot"] * RES._JOB_RESULT_DB_RETRIES
    assert "setex" not in _names(cenario.diario)
    _inconclusive_close(cenario.diario, "banco indisponível (pool esgotado)")
    assert cenario.conn.db_auth_cooldown_until > time.monotonic()
    assert (
        "Não foi possível ler o run 'run-1' para o job_result do executor 'ex-1': "
        "pool esgotado — resultado descartado (fail-closed)."
    ) in _messages(caplog)


async def test_db_down_without_proven_ownership_closes_nothing(cenario):
    cenario.linha = RuntimeError("pool esgotado")
    await RES._handle_job_result(EX, {"job_id": RUN, "run_id": RUN, "status": "ok"})
    assert set(_names(cenario.diario)) == {"snapshot"}
    assert cenario.conn.db_auth_cooldown_until > time.monotonic()


# ── A failing destination does not bring down the following ones ─────────────


@pytest.mark.parametrize(
    ("falha", "mensagem", "sobram"),
    [
        (
            lambda cmd: cmd[0] == "setex",
            "Erro ao persistir resultado do job 'run-1' no Redis: redis recusou setex",
            ["snapshot", "lpush", "lpush", "expire", "pipe.rpush"],
        ),
        (
            lambda cmd: cmd[0] == "lpush" and cmd[1] == "run_results",
            "Erro ao publicar run_results para run 'run-1': redis recusou lpush",
            ["snapshot", "setex", "lpush", "expire", "pipe.rpush"],
        ),
        (
            lambda cmd: cmd[0] == "lpush" and cmd[1] == WEBHOOK,
            "Erro ao publicar webhook_response para run 'run-1': redis recusou lpush",
            ["snapshot", "setex", "lpush", "pipe.rpush"],
        ),
        (
            lambda cmd: cmd[0] == "pipe.execute",
            "Erro ao publicar __workflow_complete__ para run 'run-1': redis recusou pipe.execute",
            ["snapshot", "setex", "lpush", "lpush", "expire"],
        ),
    ],
)
async def test_failure_of_one_destination_does_not_prevent_the_next(cenario, caplog, falha, mensagem, sobram):
    cenario.falhar = falha
    with caplog.at_level("ERROR"):
        await RES._handle_job_result(EX, {
            "job_id": RUN, "run_id": RUN, "status": "error", "error": "boom",
        })
    assert _names(cenario.diario)[:len(sobram)] == sobram
    assert mensagem in _messages(caplog)
