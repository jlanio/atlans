# tests/unit/test_fix_ws_router.py
"""
Tests for the fixes to the executors' WS (router + connection registry).

Covers:
  B1  — orphans only fail when the executor has really gone away
  S3  — coercion/clamping of `capacity`
  S5  — allowlist and ceiling for `system_info`
  S10 — byte ceiling and rate limit for `node_event`
  P1  — run->executor authorization memo
  S6  — relay envelope bound to channel/executor/nonce/time
  B14 — presence release via CAS
"""
import asyncio
import json
import time
from unittest.mock import MagicMock

import pytest

from app.api.routers.executor_ws import inbox as IB
from app.api.routers.executor_ws import orfaos as ORF
from app.api.routers.executor_ws import protocolo as P
from app.api.routers.executor_ws import resultados as RES
from app.core.executor_connections import executor_registry
from app.core import executor_connections as C
from flow.utils.publisher.reducao import (
    HEAVY_EXTRA_KEYS,
    ERROR_CEILING,
    NODE_EVENT_BYTES_CEILING,
    shrink_node_event,
)


class _FakeConn:
    """Minimal stand-in for ExecutorConnection for the router tests."""

    def __init__(self, max_concurrent=4, max_queue=50):
        self.max_concurrent_limit = max_concurrent
        self.max_queue_limit = max_queue
        self.run_auth_cache: dict = {}
        self.db_auth_cooldown_until = 0.0


@pytest.fixture
def fake_conn(monkeypatch):
    conn = _FakeConn()
    monkeypatch.setattr(executor_registry, "get", lambda _aid: conn)
    return conn


# ── S3: capacity ──────────────────────────────────────────────────────────────

def test_capacity_dict_in_counter_is_rejected(fake_conn):
    """The payload that brought down POST /execute for the entire platform."""
    cap, errors = P._sanitize_capacity("ex-1", {
        "queued": {"n": 0}, "running": 0, "max_concurrent": 4, "max_queue": 50,
    })
    assert cap is None
    assert any("queued" in e for e in errors)


def test_negative_capacity_is_rejected(fake_conn):
    cap, errors = P._sanitize_capacity("ex-1", {
        "queued": -1, "running": 0, "max_concurrent": 4, "max_queue": 50,
    })
    assert cap is None
    assert any("negativo" in e for e in errors)


def test_boolean_capacity_does_not_become_integer(fake_conn):
    cap, errors = P._sanitize_capacity("ex-1", {
        "queued": True, "running": 0, "max_concurrent": 4, "max_queue": 50,
    })
    assert cap is None
    assert errors


def test_numeric_string_capacity_is_coerced(fake_conn):
    cap, errors = P._sanitize_capacity("ex-1", {
        "queued": "2", "running": "1", "max_concurrent": "4", "max_queue": "50",
    })
    assert errors == []
    assert cap["queued"] == 2 and cap["running"] == 1
    assert all(isinstance(cap[k], int) for k in ("queued", "running", "max_concurrent", "max_queue"))


def test_capacity_is_clamped_by_db_limits(fake_conn):
    """Declaring max_queue=10**9 must not attract every job in the pool."""
    cap, errors = P._sanitize_capacity("ex-1", {
        "queued": 0, "running": 0, "max_concurrent": 10 ** 9, "max_queue": 10 ** 9,
    })
    assert errors == []
    assert cap["max_concurrent"] == fake_conn.max_concurrent_limit
    assert cap["max_queue"] == fake_conn.max_queue_limit


def test_capacity_invalid_metrics_become_none(fake_conn):
    cap, _ = P._sanitize_capacity("ex-1", {
        "queued": 0, "running": 0, "max_concurrent": 1, "max_queue": 1,
        "disk_free_gb": "muito", "ram_available_gb": -5,
    })
    assert cap["disk_free_gb"] is None
    assert cap["ram_available_gb"] is None


def test_capacity_sanitizada_e_somavel():
    """Contrato consumido por _resolve_candidates: cap['running'] + cap['queued']."""
    cap, _ = P._sanitize_capacity("ex-1", {
        "queued": 3, "running": 2, "max_concurrent": 4, "max_queue": 50,
    })
    assert cap["running"] + cap["queued"] == 5


# ── S5: system_info ───────────────────────────────────────────────────────────

def test_string_system_info_is_dropped():
    """'pwn' persistido na coluna JSONB gerava 500 permanente em GET /executores."""
    assert P._sanitize_system_info("ex-1", "pwn") is None


def test_system_info_applies_allowlist():
    clean = P._sanitize_system_info("ex-1", {
        "hostname": "host-a", "os_name": "Linux", "cpu_cores": 8,
        "container": True, "__proto__": {"x": 1}, "secret": "abc",
    })
    assert clean == {
        "hostname": "host-a", "os_name": "Linux", "cpu_cores": 8.0, "container": True,
    }


def test_system_info_truncates_long_strings():
    clean = P._sanitize_system_info("ex-1", {"hostname": "h" * 5000})
    assert len(clean["hostname"]) == P._SYSTEM_INFO_STR_MAX


def test_bulky_system_info_is_not_persisted():
    """15 MB per reconnection: nothing outside the allowlist survives."""
    payload = {f"campo_{i}": "x" * 1000 for i in range(5000)}
    assert P._sanitize_system_info("ex-1", payload) is None
    assert len(json.dumps(P._sanitize_system_info("ex-1", {**payload, "hostname": "h"}))) < 512


# ── S10: node_event ───────────────────────────────────────────────────────────

def test_log_node_event_is_limited_in_low_band(monkeypatch):
    monkeypatch.setattr(P, "_rate_state", {})
    log_msg = {"kind": "debug", "run_id": "r", "node": "n"}
    allowed = sum(
        1 for _ in range(P._NODE_EVENT_RATE_LIMIT * 2)
        if P._node_event_allowed("ex-1", log_msg)
    )
    assert allowed == P._NODE_EVENT_RATE_LIMIT
    # A new window frees it up again (without dropping the connection).
    P._rate_state[("ex-1", "node_event:log")]["window_start"] -= P._RATE_WINDOW * 2
    assert P._node_event_allowed("ex-1", log_msg) is True


def test_lifecycle_is_not_dropped_by_log_quota(monkeypatch):
    """The bug: 300 nodes = 600 lifecycle events in a burst blew past the 200/s and the
    canvas was left with half the graph spinning forever."""
    monkeypatch.setattr(P, "_rate_state", {})
    for _ in range(P._NODE_EVENT_RATE_LIMIT * 3):
        P._node_event_allowed("ex-1", {"kind": "debug"})
    # Even with the log quota exhausted, every node `completed` gets through.
    for i in range(600):
        assert P._node_event_allowed("ex-1", {
            "kind": "lifecycle", "node": f"n{i}", "status": "completed",
        }) is True


def test_lifecycle_still_has_hard_ceiling(monkeypatch):
    monkeypatch.setattr(P, "_rate_state", {})
    msg = {"kind": "lifecycle", "status": "started"}
    allowed = sum(
        1 for _ in range(P._NODE_EVENT_LIFECYCLE_RATE_LIMIT * 2)
        if P._node_event_allowed("ex-1", msg)
    )
    assert allowed == P._NODE_EVENT_LIFECYCLE_RATE_LIMIT


def test_missing_kind_counts_as_lifecycle(monkeypatch):
    """Default do produtor (publish_event) e KIND_LIFECYCLE."""
    monkeypatch.setattr(P, "_rate_state", {})
    for _ in range(P._NODE_EVENT_RATE_LIMIT + 50):
        assert P._node_event_allowed("ex-1", {"run_id": "r", "node": "n"}) is True


def test_buckets_do_not_share_quota(monkeypatch):
    monkeypatch.setattr(P, "_rate_state", {})
    for _ in range(P._JOB_RESULT_RATE_LIMIT):
        assert P._rate_allowed("ex-1", "job_result", P._JOB_RESULT_RATE_LIMIT) is True
    assert P._rate_allowed("ex-1", "job_result", P._JOB_RESULT_RATE_LIMIT) is False
    # Another bucket of the same executor stays free.
    assert P._node_event_allowed("ex-1", {"kind": "lifecycle"}) is True


def test_drop_rate_state_clears_all_buckets(monkeypatch):
    monkeypatch.setattr(P, "_rate_state", {})
    P._rate_allowed("ex-1", "job_result", 10)
    P._node_event_allowed("ex-1", {"kind": "lifecycle"})
    P._node_event_allowed("ex-2", {"kind": "lifecycle"})
    P._drop_rate_state("ex-1")
    assert [k for k in P._rate_state if k[0] == "ex-1"] == []
    assert ("ex-2", "node_event:lifecycle") in P._rate_state


def test_truncation_preserves_control_fields():
    event = {
        "run_id": "run-1", "node": "n1", "status": "running", "kind": "log",
        "level": "info", "timestamp": 123.0, "payload": "x" * 100_000,
    }
    payload = json.dumps(event)
    out = json.loads(shrink_node_event(event, payload))
    assert out["run_id"] == "run-1" and out["node"] == "n1" and out["status"] == "running"
    assert out["__truncated__"] is True
    assert out["__original_size__"] == len(payload)
    assert "payload" not in out
    assert len(shrink_node_event(event, payload)) <= NODE_EVENT_BYTES_CEILING


def test_overflow_from_heavy_extra_preserves_output_columns():
    """Per-key degradation: the heavy stuff (traceback/debug/stdout/drift) goes first.

    Before, an overflow cut straight down to the control fields and the whole `extra`
    vanished — including `output_columns`, the editor's column suggestion, which is
    exactly the useful thing a wide-table `completed` carries.
    """
    colunas = {"result": [f"col_{i}" for i in range(200)]}
    event = {
        "run_id": "run-1", "node": "n1", "status": "completed", "kind": "lifecycle",
        "level": "info", "timestamp": 123.0, "duration_ms": 5.0,
        "extra": {
            "node_name": "Join", "node_type": "join", "cache_hit": False,
            "output_columns": colunas,
            "traceback": "tb" * 40_000,
            "debug_output": {"in:a": "x" * 10_000},
            "lines": ["log " * 500] * 20,
            "schema_drift": {"missing": ["m" * 5_000], "extra": []},
        },
    }
    payload = json.dumps(event)
    assert len(payload) > NODE_EVENT_BYTES_CEILING

    raw = shrink_node_event(event, payload)
    assert len(raw) <= NODE_EVENT_BYTES_CEILING
    out = json.loads(raw)
    assert out["extra"]["output_columns"] == colunas, "a sugestão de coluna tinha que sobreviver"
    assert out["extra"]["node_name"] == "Join" and out["extra"]["cache_hit"] is False
    for heavy_key in HEAVY_EXTRA_KEYS:
        assert heavy_key not in out["extra"]
    assert out["duration_ms"] == 5.0
    assert out["__truncated__"] is True
    assert out["__original_size__"] == len(payload)


def test_huge_event_error_is_truncated_preserving_the_extra():
    """`error` is also a heavy field: truncating it avoids throwing away the light extra."""
    event = {
        "run_id": "run-1", "node": "n1", "status": "failed", "kind": "lifecycle",
        "level": "error", "timestamp": 123.0, "error": "e" * 100_000,
        "extra": {"error_category": "runtime", "retryable": False},
    }
    payload = json.dumps(event)
    assert len(payload) > NODE_EVENT_BYTES_CEILING

    out = json.loads(shrink_node_event(event, payload))
    assert out["error"].endswith("…[truncado]")
    assert out["error"].startswith("e" * ERROR_CEILING)
    assert len(out["error"]) < ERROR_CEILING + 20
    assert out["extra"] == {"error_category": "runtime", "retryable": False}
    assert out["__truncated__"] is True


def test_extreme_overflow_still_falls_back_to_control_fields():
    """If not even the degraded event fits, the ceiling is still a guarantee: control only."""
    event = {
        "run_id": "run-1", "node": "n1", "status": "completed", "kind": "lifecycle",
        "level": "info", "timestamp": 123.0,
        "extra": {
            "traceback": "tb",
            # hostile output_columns, larger than the ceiling itself: preserving it
            # would make the "truncated" version larger than the original.
            "output_columns": {"r": ["c" * 60] * 3_000},
        },
    }
    payload = json.dumps(event)

    raw = shrink_node_event(event, payload)
    assert len(raw) <= NODE_EVENT_BYTES_CEILING
    out = json.loads(raw)
    assert "extra" not in out
    assert out["run_id"] == "run-1" and out["node"] == "n1" and out["status"] == "completed"
    assert out["__truncated__"] is True


async def test_huge_node_event_is_truncated_before_redis(monkeypatch, fake_conn):
    published: list[str] = []

    class _Pipe:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def rpush(self, _k, *payloads):
            published.extend(payloads)

        def ltrim(self, *a):
            pass

        def expire(self, *a):
            pass

        def publish(self, _c, payload):
            published.append(payload)

        async def execute(self):
            return []

    class _RC:
        def pipeline(self, transaction=False):
            return _Pipe()

    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_run_belongs_to_agent", _async_true)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: _RC())

    await RES._publish_node_events("ex-1", [{
        "type": "node_event", "run_id": "run-1", "node": "n1", "blob": "y" * 200_000,
    }])

    assert published, "evento deveria ter sido publicado (truncado)"
    for payload in published:
        assert len(payload) <= NODE_EVENT_BYTES_CEILING
        assert json.loads(payload)["__truncated__"] is True


async def _async_true(*_a, **_kw):
    return True


async def _async_false(*_a, **_kw):
    return False


# ── S10 (part 2): job_result also has a byte ceiling and rate limit ──────────

def test_huge_job_result_error_is_truncated():
    """15 MB went raw into WorkflowRun.error_message (Text, no limit)."""
    capped, _ = P._cap_job_result("ex-1", {
        "job_id": "j1", "status": "error", "error": "A" * 15_000_000,
    })
    assert len(capped["error"]) <= P._MAX_JOB_ERROR_CHARS + 40
    assert capped["error"].startswith("AAA")


def test_non_string_error_does_not_pass_whole():
    capped, _ = P._cap_job_result("ex-1", {
        "job_id": "j1", "status": "error", "error": {"blob": "B" * 5_000_000},
    })
    assert isinstance(capped["error"], str)
    assert len(capped["error"]) <= P._MAX_JOB_ERROR_CHARS + 40


def test_huge_stats_preserves_control_keys():
    stats = {
        "__response__": {"status": 200, "body": "ok"},
        **{f"node-{i}": {"rows": "x" * 2000} for i in range(4000)},
    }
    capped, _ = P._cap_job_result("ex-1", {"job_id": "j1", "status": "ok", "stats": stats})
    out = capped["stats"]
    assert out["__truncated__"] is True
    assert out["__response__"] == {"status": 200, "body": "ok"}
    assert "node-0" not in out
    assert len(json.dumps(out)) <= P._MAX_JOB_STATS_BYTES


def test_stats_with_huge_control_key_marks_control_dropped():
    """Without __control_dropped__ the webhook_router's BRPOP would sit until the timeout."""
    stats = {"__response__": {"body": "z" * (P._MAX_JOB_STATS_BYTES + 1000)}}
    capped, _ = P._cap_job_result("ex-1", {"job_id": "j1", "status": "ok", "stats": stats})
    assert capped["stats"]["__control_dropped__"] is True
    assert len(json.dumps(capped["stats"])) <= P._MAX_JOB_STATS_BYTES


def test_non_serializable_stats_does_not_crash_the_consumer():
    ciclo: dict = {}
    ciclo["self"] = ciclo
    capped, _ = P._cap_job_result("ex-1", {"job_id": "j1", "status": "ok", "stats": ciclo})
    assert capped["stats"]["__control_dropped__"] is True


def test_stats_of_wrong_type_is_dropped():
    capped, _ = P._cap_job_result("ex-1", {"job_id": "j1", "status": "ok", "stats": "pwn"})
    assert capped["stats"] == {}


def test_small_job_result_passes_intact():
    msg = {"job_id": "j1", "status": "ok", "stats": {"n1": {"rows": 3}}, "error": None}
    capped, _ = P._cap_job_result("ex-1", msg)
    assert capped == msg


def test_stats_serialized_once_and_reused():
    """The returned JSON must be the SAME one that goes to the run_results queue —
    without that the caller redid a dumps of up to 4 MB, synchronously, on the event loop."""
    stats = {"n1": {"rows": 3}, "__response__": {"status": 200}}
    capped, stats_json = P._cap_job_result("ex-1", {
        "job_id": "j1", "status": "ok", "stats": stats,
    })
    assert json.loads(stats_json) == capped["stats"]


def test_missing_stats_returns_empty_object():
    _capped, stats_json = P._cap_job_result("ex-1", {"job_id": "j1", "status": "ok"})
    assert json.loads(stats_json) == {}


class _FakeRedis:
    """Captures everything the handler sends to Redis."""

    def __init__(self):
        self.writes: list[str] = []

    async def setex(self, _k, _ttl, payload):
        self.writes.append(payload)

    async def lpush(self, _k, payload):
        self.writes.append(payload)

    async def expire(self, *_a):
        return True

    def pipeline(self, transaction=False):
        outer = self

        class _Pipe:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_a):
                return False

            def rpush(self, _k, *payloads):
                outer.writes.extend(payloads)

            def lpush(self, _k, payload):
                outer.writes.append(payload)

            def ltrim(self, *_a):
                pass

            def expire(self, *_a):
                pass

            def publish(self, _c, payload):
                outer.writes.append(payload)

            async def execute(self):
                return []

        return _Pipe()


@pytest.fixture
def without_db(monkeypatch):
    """The duration calculation opens a real session; in the tests it fails fast and
    the handler continues (the block is already tolerant of DB errors)."""

    class _NoDB:
        async def __aenter__(self):
            raise RuntimeError("sem banco no teste")

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(RES, "get_session_async", lambda: _NoDB())


def _snapshot_de(executor_id="ex-1", status="running", start_time=None):
    """Linha (host, status, start_time) devolvida por _query_run_snapshot."""

    async def _query(_run_id):
        return (f"executor:{executor_id}", status, start_time)

    return _query


async def test_huge_job_result_does_not_reach_redis_raw(monkeypatch, fake_conn):
    """All durable destinations (results, run_results, history, publish)
    must receive the already-contained payload."""
    rc = _FakeRedis()
    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot_de())
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_job_result("ex-1", {
        "type": "job_result", "job_id": "run-1", "run_id": "run-1",
        "status": "error", "error": "A" * 15_000_000,
        "stats": {f"node-{i}": {"rows": "x" * 2000} for i in range(4000)},
    })

    assert rc.writes, "nada foi publicado"
    for payload in rc.writes:
        assert len(payload) < 1_000_000, f"payload de {len(payload)} bytes foi para o Redis"
        json.loads(payload)  # splicing in `stats` must produce valid JSON
    juntos = "".join(rc.writes)
    assert "A" * (P._MAX_JOB_ERROR_CHARS + 100) not in juntos


async def test_job_result_reads_the_run_only_once(monkeypatch, fake_conn):
    """Posse, idempotencia e duracao saem da MESMA linha: eram 3 sessions."""
    leituras = []

    async def _query(run_id):
        leituras.append(run_id)
        return ("executor:ex-1", "running", None)

    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_query_run_snapshot", _query)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: _FakeRedis())

    await RES._handle_job_result("ex-1", {
        "job_id": "run-1", "run_id": "run-1", "status": "ok", "stats": {"n1": {}},
    })
    assert leituras == ["run-1"]


async def test_job_result_of_foreign_run_is_rejected(monkeypatch, fake_conn):
    """Cross-tenant fail-closed: another executor's host must not be overwritten."""
    rc = _FakeRedis()
    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot_de("ex-2"))
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_job_result("ex-1", {
        "job_id": "run-1", "run_id": "run-1", "status": "ok",
    })
    assert rc.writes == []
    # The refusal is memoized so the flood does not turn into one SELECT per attempt.
    assert fake_conn.run_auth_cache["run-1"][0] is False


async def test_job_result_without_host_is_rejected(monkeypatch, fake_conn):
    """NULL host (nonexistent run or not yet dispatched) stays fail-closed."""
    rc = _FakeRedis()

    async def _no_row(_run_id):
        return None

    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_query_run_snapshot", _no_row)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_job_result("ex-1", {"job_id": "run-1", "status": "ok"})
    assert rc.writes == []


async def test_job_result_of_terminal_run_is_ignored(monkeypatch, fake_conn):
    """An outbox replay must not turn a 'failed' into a 'success'."""
    rc = _FakeRedis()
    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot_de(status="failed"))
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_job_result("ex-1", {
        "job_id": "run-1", "run_id": "run-1", "status": "ok",
    })
    assert rc.writes == []


async def test_job_result_of_cancelled_run_is_ignored(monkeypatch, fake_conn):
    """A run cancelled by the user is already terminal: a later job_result
    (redelivery or compromised executor) must not resurrect it as success."""
    rc = _FakeRedis()
    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot_de(status="cancelled"))
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_job_result("ex-1", {
        "job_id": "run-1", "run_id": "run-1", "status": "ok",
    })
    assert rc.writes == []


async def test_job_result_with_db_down_opens_cooldown(monkeypatch, fake_conn):
    """A Postgres blip must not turn into one checkout attempt per event."""
    rc = _FakeRedis()

    async def _explode(_run_id):
        raise RuntimeError("pool esgotado")

    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_query_run_snapshot", _explode)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_job_result("ex-1", {"job_id": "run-1", "status": "ok"})
    assert rc.writes == []
    assert fake_conn.db_auth_cooldown_until > time.monotonic()


async def test_job_result_has_rate_limit(monkeypatch, fake_conn):
    monkeypatch.setattr(P, "_rate_state", {})
    vistos = []

    async def _query(run_id):
        vistos.append(run_id)
        return ("executor:ex-1", "running", None)

    monkeypatch.setattr(RES, "_query_run_snapshot", _query)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: _FakeRedis())

    for _ in range(P._JOB_RESULT_RATE_LIMIT + 20):
        await RES._handle_job_result("ex-1", {
            "job_id": "run-1", "run_id": "run-1", "status": "error", "error": "x",
        })
    # The discard happens BEFORE authorization: the cost in SELECTs is what the
    # flood exploits.
    assert len(vistos) == P._JOB_RESULT_RATE_LIMIT


# ── P1: memo de autorizacao run -> executor ──────────────────────────────────

async def test_run_auth_queries_the_db_once_per_run(monkeypatch, fake_conn):
    calls = []

    async def _fake_query(executor_id, run_id):
        calls.append((executor_id, run_id))
        return True

    monkeypatch.setattr(RES, "_query_run_belongs_to_agent", _fake_query)

    for _ in range(50):
        assert await RES._run_belongs_to_agent("ex-1", "run-1") is True
    assert len(calls) == 1


async def test_run_auth_memoizes_denial(monkeypatch, fake_conn):
    calls = []

    async def _fake_query(executor_id, run_id):
        calls.append(run_id)
        return False

    monkeypatch.setattr(RES, "_query_run_belongs_to_agent", _fake_query)

    for _ in range(20):
        assert await RES._run_belongs_to_agent("ex-1", "run-alheio") is False
    assert len(calls) == 1


async def test_db_error_denies_without_repeating_the_query(monkeypatch, fake_conn):
    """A DB error still DENIES and does NOT become a memo (the verdict is transient),
    but during the cooldown no new session is opened per event — that is how a
    1-minute hiccup in Postgres turned into a mass disconnection of executors."""
    calls = []

    async def _fake_query(executor_id, run_id):
        calls.append(run_id)
        return None  # DB failure

    monkeypatch.setattr(RES, "_query_run_belongs_to_agent", _fake_query)

    for _ in range(50):
        assert await RES._run_belongs_to_agent("ex-1", "run-1") is False
    assert len(calls) == 1
    assert "run-1" not in fake_conn.run_auth_cache

    # Once the cooldown passes, it tries again — recovery has to be fast.
    fake_conn.db_auth_cooldown_until = 0.0
    assert await RES._run_belongs_to_agent("ex-1", "run-1") is False
    assert len(calls) == 2


async def test_authorization_query_has_timeout(monkeypatch, fake_conn):
    """Waiting POOL_TIMEOUT (30s) on the WS hot path leaves the heartbeat unread
    and the server drops a healthy executor."""
    monkeypatch.setattr(RES, "_RUN_AUTH_QUERY_TIMEOUT", 0.01)

    async def _stuck(executor_id, run_id):
        await asyncio.sleep(5)
        return True

    monkeypatch.setattr(RES, "_query_run_belongs_to_agent", _stuck)

    assert await RES._run_belongs_to_agent("ex-1", "run-1") is False
    assert fake_conn.db_auth_cooldown_until > time.monotonic()


async def test_run_auth_does_not_cross_executors(monkeypatch):
    """The memo lives on the connection: an executor never inherits another's verdict."""
    conns = {"ex-1": _FakeConn(), "ex-2": _FakeConn()}
    monkeypatch.setattr(executor_registry, "get", conns.get)

    asked = []

    async def _fake_query(executor_id, run_id):
        asked.append(executor_id)
        return executor_id == "ex-1"

    monkeypatch.setattr(RES, "_query_run_belongs_to_agent", _fake_query)

    assert await RES._run_belongs_to_agent("ex-1", "run-1") is True
    assert await RES._run_belongs_to_agent("ex-2", "run-1") is False
    assert asked == ["ex-1", "ex-2"]


def test_run_auth_cache_has_ceiling(fake_conn):
    now = time.monotonic()
    for i in range(RES._RUN_AUTH_CACHE_MAX + 100):
        RES._store_run_auth(fake_conn.run_auth_cache, f"run-{i}", False, now)
    assert len(fake_conn.run_auth_cache) <= RES._RUN_AUTH_CACHE_MAX


def test_forget_run_auth_clears_the_memo(fake_conn):
    fake_conn.run_auth_cache["run-1"] = (True, time.monotonic() + 999)
    RES._forget_run_auth("ex-1", "run-1")
    assert "run-1" not in fake_conn.run_auth_cache


# ── B1: orphans only fail if the executor really went away ───────────────────

@pytest.fixture
def no_wait(monkeypatch):
    async def _no_sleep(_s):
        return None

    monkeypatch.setattr(ORF.asyncio, "sleep", _no_sleep)


async def test_network_blip_does_not_fail_in_flight_runs(monkeypatch, no_wait):
    """Reconnection on the SAME worker: in-flight runs must survive."""
    chamou = []
    monkeypatch.setattr(ORF, "_fail_orphan_runs", lambda aid: chamou.append(aid))
    monkeypatch.setattr(executor_registry, "get", lambda _aid: _FakeConn())

    await ORF._fail_orphan_runs_if_gone("ex-1")
    assert chamou == []


async def test_reconnection_on_another_worker_does_not_fail_runs(monkeypatch, no_wait):
    chamou = []

    async def _fail(aid):
        chamou.append(aid)

    async def _present(_aid):
        return True

    monkeypatch.setattr(ORF, "_fail_orphan_runs", _fail)
    monkeypatch.setattr(executor_registry, "get", lambda _aid: None)
    monkeypatch.setattr(C, "_redis_presence_or_unknown", _present)

    await ORF._fail_orphan_runs_if_gone("ex-1")
    assert chamou == []


async def test_redis_unavailable_during_check_does_not_destroy_runs(monkeypatch, no_wait):
    """'I don't know' != 'gone'. A pool blip at the moment of the check destroyed
    precisely the runs the grace period exists to save."""
    chamou = []

    async def _fail(aid):
        chamou.append(aid)

    async def _unknown(_aid):
        return None

    monkeypatch.setattr(ORF, "_fail_orphan_runs", _fail)
    monkeypatch.setattr(executor_registry, "get", lambda _aid: None)
    monkeypatch.setattr(C, "_redis_presence_or_unknown", _unknown)

    await ORF._fail_orphan_runs_if_gone("ex-1")
    assert chamou == []


async def test_tri_state_presence_returns_none_on_redis_error(monkeypatch):
    async def _boom():
        raise RuntimeError("pool saturado")

    async def _noop():
        return None

    monkeypatch.setattr(C, "_get_redis", _boom)
    monkeypatch.setattr(C, "_reset_redis_singleton", _noop)
    assert await C._redis_presence_or_unknown("ex-1") is None
    # The boolean wrapper stays fail-closed for whoever decides on dispatch.
    assert await C._redis_check_presence("ex-1") is False


async def test_truly_gone_executor_fails_the_runs(monkeypatch, no_wait):
    chamou = []

    async def _fail(aid):
        chamou.append(aid)

    async def _absent(_aid):
        return False

    monkeypatch.setattr(ORF, "_fail_orphan_runs", _fail)
    monkeypatch.setattr(executor_registry, "get", lambda _aid: None)
    monkeypatch.setattr(C, "_redis_presence_or_unknown", _absent)

    await ORF._fail_orphan_runs_if_gone("ex-1")
    assert chamou == ["ex-1"]


# ── S6: relay envelope ───────────────────────────────────────────────────────

def test_relay_envelope_opens_on_the_right_channel():
    env = C.build_relay_envelope('{"type":"job"}', executor_id="ex-1")
    out = C.open_signed_envelope(
        env, channel_label="Relay", executor_id="ex-1", audience=C._AUDIENCE_RELAY,
    )
    assert out == '{"type":"job"}'


def test_envelope_cannot_be_replayed_on_another_executor():
    """Republishing a control/revoked on every executor's channel took down the fleet."""
    env = C.build_relay_envelope('{"type":"control","action":"revoked"}', executor_id="ex-1")
    assert C.open_signed_envelope(
        env, channel_label="Relay", executor_id="ex-2", audience=C._AUDIENCE_RELAY,
    ) is None


def test_drive_envelope_is_not_valid_on_relay_channel():
    env = C.build_signed_envelope('{"type":"drive_event"}')
    assert C.open_signed_envelope(
        env, channel_label="Relay", executor_id="ex-1", audience=C._AUDIENCE_RELAY,
    ) is None


def test_drive_envelope_accepts_fan_out():
    env = C.build_signed_envelope('{"type":"drive_event"}')
    for aid in ("ex-1", "ex-2"):
        assert C.open_signed_envelope(
            env, channel_label="Drive event", executor_id=aid, audience=C._AUDIENCE_DRIVE,
        ) == '{"type":"drive_event"}'


def test_envelope_cannot_be_presented_again():
    env = C.build_relay_envelope('{"type":"job"}', executor_id="ex-1")
    assert C.open_signed_envelope(
        env, channel_label="Relay", executor_id="ex-1", audience=C._AUDIENCE_RELAY,
    ) is not None
    assert C.open_signed_envelope(
        env, channel_label="Relay", executor_id="ex-1", audience=C._AUDIENCE_RELAY,
    ) is None


def test_stale_envelope_is_refused():
    """An envelope captured yesterday must not stay valid (legitimate signature)."""
    payload = '{"type":"control","action":"revoked"}'
    ts = f"{time.time() - (C._RELAY_FRESHNESS_WINDOW + 10):.3f}"
    nonce = "n" * 32
    env = json.dumps({
        "payload": payload, "aud": C._AUDIENCE_RELAY, "executor_id": "ex-1",
        "nonce": nonce, "ts": ts,
        "hmac": C._relay_mac(
            payload=payload, audience=C._AUDIENCE_RELAY, executor_id="ex-1",
            nonce=nonce, ts=ts,
        ),
    })
    assert C.open_signed_envelope(
        env, channel_label="Relay", executor_id="ex-1", audience=C._AUDIENCE_RELAY,
    ) is None


def test_tampered_envelope_is_refused():
    env = json.loads(C.build_relay_envelope('{"type":"job"}', executor_id="ex-1"))
    env["payload"] = '{"type":"control","action":"shutdown"}'
    assert C.open_signed_envelope(
        json.dumps(env), channel_label="Relay", executor_id="ex-1", audience=C._AUDIENCE_RELAY,
    ) is None


def test_expired_nonces_leave_without_evicting_valid_ones(monkeypatch):
    """Prefix purge: with a fixed TTL, the expired entries are always the start of the dict."""
    monkeypatch.setattr(C, "_seen_relay_nonces", {})
    agora = time.monotonic()
    for i in range(10):
        C._seen_relay_nonces[f"velho-{i}|ex-1"] = agora - 1  # already expired
    assert C._nonce_already_seen("novo", "ex-1") is False
    assert not [k for k in C._seen_relay_nonces if k.startswith("velho-")]
    assert "novo|ex-1" in C._seen_relay_nonces


def test_eviction_of_valid_nonce_screams(monkeypatch, caplog):
    """The executor's sibling cache logs; this one discarded in absolute silence and
    the operator had no way of knowing that anti-replay was off."""
    monkeypatch.setattr(C, "_RELAY_NONCE_MAX", 8)
    monkeypatch.setattr(C, "_seen_relay_nonces", {})
    monkeypatch.setattr(
        C, "_relay_nonce_evictions", {"total": 0.0, "since_log": 0.0, "last_log": 0.0},
    )
    agora = time.monotonic()
    for i in range(8):
        C._seen_relay_nonces[f"vivo-{i}|ex-1"] = agora + 999  # all still valid

    with caplog.at_level("ERROR"):
        assert C._nonce_already_seen("novo", "ex-1") is False

    assert C._relay_nonce_evictions["total"] == 1
    assert "vivo-0|ex-1" not in C._seen_relay_nonces
    assert any("anti-replay do relay cheio" in r.getMessage() for r in caplog.records)


def test_unsigned_envelope_is_refused():
    raw = json.dumps({"payload": '{"type":"job"}'})
    assert C.open_signed_envelope(
        raw, channel_label="Relay", executor_id="ex-1", audience=C._AUDIENCE_RELAY,
    ) is None


# ── B14: presence via CAS ────────────────────────────────────────────────────

async def test_release_presence_respects_the_current_owner(monkeypatch):
    """A losing worker must not delete the presence of another worker's live session."""
    store = {
        C._presence_key("ex-1"): "1",
        C._conn_owner_key("ex-1"): "token-do-worker-B",
    }

    class _RC:
        async def eval(self, script, _n, presence_key, owner_key, token):
            owner = store.get(owner_key)
            if owner and owner != token:
                return 0
            store.pop(presence_key, None)
            store.pop(owner_key, None)
            return 1

    async def _get_rc():
        return _RC()

    monkeypatch.setattr(C, "_get_redis", _get_rc)

    await C._redis_release_presence("ex-1", "token-do-worker-A")
    assert C._presence_key("ex-1") in store, "presenca da sessao viva foi apagada"

    await C._redis_release_presence("ex-1", "token-do-worker-B")
    assert C._presence_key("ex-1") not in store


async def test_renew_presence_signals_ownership_loss(monkeypatch):
    class _RC:
        async def eval(self, *_a):
            return 0

    async def _get_rc():
        return _RC()

    monkeypatch.setattr(C, "_get_redis", _get_rc)
    assert await C._redis_renew_presence("ex-1", "token-antigo") is False


async def test_renew_presence_is_fail_open_on_redis_error(monkeypatch):
    async def _boom():
        raise RuntimeError("redis fora")

    async def _noop():
        return None

    monkeypatch.setattr(C, "_get_redis", _boom)
    monkeypatch.setattr(C, "_reset_redis_singleton", _noop)
    # Tri-state: None = "could not ask". Still fail-open where it
    # matters (a healthy executor's WS does not drop over a Redis blip), but it no
    # longer passes for "renewed" — the caller reschedules the attempt.
    assert await C._redis_renew_presence("ex-1", "tok") is None


def test_connection_starts_with_its_own_memo_and_token():
    a = C.ExecutorConnection(executor_id="ex-1", websocket=None)
    b = C.ExecutorConnection(executor_id="ex-1", websocket=None)
    assert a.owner_token != b.owner_token
    assert a.run_auth_cache is not b.run_auth_cache


def test_initial_capacity_respects_the_default():
    conn = C.ExecutorConnection(executor_id="ex-1", websocket=None)
    assert conn.capacity["running"] + conn.capacity["queued"] == 0
    assert conn.is_full() is False


# Sanity: the handler should no longer depend on a real asyncio.sleep in the tests.
def test_configured_grace_period():
    assert ORF._DISCONNECT_GRACE_SECONDS > 0
    assert isinstance(asyncio.Queue, type)


# ── P0: per-connection queue, coalescing and flush on teardown ───────────────

class _RecordingPipe:
    """Pipeline that records the enqueued commands and how many times it executed."""

    def __init__(self, log: list, execucoes: list):
        self.log = log
        self.execucoes = execucoes

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    def rpush(self, key, *payloads):
        self.log.append(("rpush", key, list(payloads)))

    def lpush(self, key, payload):
        self.log.append(("lpush", key, payload))

    def ltrim(self, *a):
        self.log.append(("ltrim",))

    def expire(self, *a):
        self.log.append(("expire",))

    def publish(self, channel, payload):
        self.log.append(("publish", channel, payload))

    def hset(self, key, mapping=None):
        self.log.append(("hset", key, mapping))

    async def execute(self):
        self.execucoes.append(len(self.log))
        return []


class _RecordingRedis:
    def __init__(self):
        self.log: list = []
        self.execucoes: list = []

    def pipeline(self, transaction=False):
        return _RecordingPipe(self.log, self.execucoes)


async def test_node_events_batch_becomes_a_single_pipeline(monkeypatch, fake_conn):
    """64 events cost 64 serialized Redis round-trips in the receive
    loop — that is what held the final job_result behind the telemetry."""
    rc = _RecordingRedis()
    monkeypatch.setattr(RES, "_run_belongs_to_agent", _async_true)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    msgs = [
        {"type": "node_event", "run_id": "run-1", "node": f"n{i}", "status": "completed"}
        for i in range(64)
    ]
    await RES._publish_node_events("ex-1", msgs)

    assert rc.execucoes == [len(rc.log)], "o lote inteiro tem que sair num pipeline so"
    rpushes = [c for c in rc.log if c[0] == "rpush"]
    assert len(rpushes) == 1 and len(rpushes[0][2]) == 64
    publishes = [c for c in rc.log if c[0] == "publish"]
    assert len(publishes) == 64
    # The order within the run is arrival order — the canvas rebuilds the graph from it.
    assert [json.loads(p[2])["node"] for p in publishes] == [f"n{i}" for i in range(64)]


async def test_batch_groups_by_run_without_mixing(monkeypatch, fake_conn):
    rc = _RecordingRedis()
    monkeypatch.setattr(RES, "_run_belongs_to_agent", _async_true)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._publish_node_events("ex-1", [
        {"run_id": "a", "node": "n1"}, {"run_id": "b", "node": "n2"},
        {"run_id": "a", "node": "n3"},
    ])
    rpushes = {c[1]: c[2] for c in rc.log if c[0] == "rpush"}
    assert len(rpushes["workflow:a:history"]) == 2
    assert len(rpushes["workflow:b:history"]) == 1


async def test_batch_does_not_publish_foreign_run(monkeypatch, fake_conn):
    """Authorization is per run, once per batch — grouping must not loosen it."""
    rc = _RecordingRedis()

    async def _belongs(_aid, run_id):
        return run_id == "meu"

    monkeypatch.setattr(RES, "_run_belongs_to_agent", _belongs)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._publish_node_events("ex-1", [
        {"run_id": "meu", "node": "n1"}, {"run_id": "alheio", "node": "n2"},
    ])
    assert all("alheio" not in str(c) for c in rc.log)
    assert any(c[1] == "workflow:meu:history" for c in rc.log if c[0] == "rpush")


async def test_drainer_preserves_order_between_node_event_and_job_result(monkeypatch, fake_conn):
    """If both paths drained in parallel, __workflow_complete__ could
    overtake the last node events."""
    ordem: list[str] = []

    async def _publish(_aid, msgs):
        ordem.extend(f"evento:{m['node']}" for m in msgs)

    async def _resultado(_aid, _msg, _bytes, **_kw):
        ordem.append("job_result")

    monkeypatch.setattr(IB, "_publish_node_events", _publish)
    monkeypatch.setattr(IB, "_handle_job_result", _resultado)

    inbox: asyncio.Queue = asyncio.Queue(maxsize=100)
    inbox.put_nowait(("node_event", {"run_id": "r", "node": "n1"}, 10))
    inbox.put_nowait(("job_result", {"job_id": "r"}, 10))
    inbox.put_nowait(("node_event", {"run_id": "r", "node": "n2"}, 10))
    inbox.put_nowait(IB._INBOX_STOP)

    await IB._drain_inbox("ex-1", inbox)
    assert ordem == ["evento:n1", "job_result", "evento:n2"]


async def test_drainer_flushes_before_exiting(monkeypatch, fake_conn):
    """Without the flush on WS teardown, the run's last events are lost and the
    user's panel spins forever on a run that has already finished."""
    publicados: list[dict] = []

    async def _publish(_aid, msgs):
        publicados.extend(msgs)

    monkeypatch.setattr(IB, "_publish_node_events", _publish)

    inbox: asyncio.Queue = asyncio.Queue(maxsize=100)
    task = asyncio.create_task(IB._drain_inbox("ex-1", inbox))
    inbox.put_nowait(("node_event", {"run_id": "r", "node": "n1"}, 10))
    await IB._encerrar_drenagem(inbox, task)
    assert [m["node"] for m in publicados] == ["n1"]


async def test_drainer_survives_a_handler_error(monkeypatch, fake_conn):
    """A problematic job_result must not kill the draining of the rest of the connection."""
    publicados: list[dict] = []

    async def _publish(_aid, msgs):
        publicados.extend(msgs)

    async def _explode(*_a, **_kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(IB, "_publish_node_events", _publish)
    monkeypatch.setattr(IB, "_handle_job_result", _explode)

    inbox: asyncio.Queue = asyncio.Queue(maxsize=100)
    inbox.put_nowait(("job_result", {"job_id": "r"}, 10))
    inbox.put_nowait(("node_event", {"run_id": "r", "node": "n1"}, 10))
    inbox.put_nowait(IB._INBOX_STOP)

    await IB._drain_inbox("ex-1", inbox)
    assert [m["node"] for m in publicados] == ["n1"]


# ── S: sync_event ganha rate limit e teto de bytes ───────────────────────────

def test_sync_event_has_rate_limit(monkeypatch):
    monkeypatch.setattr(P, "_rate_state", {})
    permitidos = sum(
        P._sync_event_allowed("ex-1", {"event": "file_uploaded"})
        for _ in range(P._SYNC_EVENT_RATE_LIMIT + 50)
    )
    assert permitidos == P._SYNC_EVENT_RATE_LIMIT


def test_terminal_sync_event_is_not_dropped(monkeypatch):
    """Losing sync_complete leaves the progress bar stuck forever."""
    monkeypatch.setattr(P, "_rate_state", {})
    for _ in range(P._SYNC_EVENT_RATE_LIMIT + 50):
        P._sync_event_allowed("ex-1", {"event": "file_uploaded"})
    assert P._sync_event_allowed("ex-1", {"event": "sync_complete"}) is True


def test_sync_error_is_not_exempt_from_rate_limit(monkeypatch):
    """`sync_error`/`conflict_detected` are emitted PER FILE.

    Exempting them brought back in full the flood the ceiling exists to contain:
    a GeoSync of thousands of files with MinIO down turned into thousands of
    exempt messages, which filled the connection's queue.
    """
    monkeypatch.setattr(P, "_rate_state", {})
    permitidos = sum(
        P._sync_event_allowed("ex-1", {"event": "sync_error", "dataset": f"d{i}"})
        for i in range(P._SYNC_PROBLEM_RATE_LIMIT + 200)
    )
    assert permitidos == P._SYNC_PROBLEM_RATE_LIMIT
    assert "conflict_detected" in P._SYNC_PROBLEM_EVENTS
    assert P._SYNC_TERMINAL_EVENTS == frozenset({"sync_complete"})


def test_problem_bucket_does_not_consume_progress_quota(monkeypatch):
    """A burst of errors must not stop the progress bar, nor the other way around."""
    monkeypatch.setattr(P, "_rate_state", {})
    for i in range(P._SYNC_PROBLEM_RATE_LIMIT + 200):
        P._sync_event_allowed("ex-1", {"event": "sync_error", "dataset": f"d{i}"})
    assert P._sync_event_allowed("ex-1", {"event": "file_uploaded"}) is True


async def test_huge_sync_event_is_reduced_and_goes_out_in_a_pipeline(monkeypatch):
    rc = _RecordingRedis()
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_sync_event("ex-1", {
        "type": "sync_event", "event": "file_uploaded", "dataset": "d1",
        "blob": "z" * 200_000,
    })

    assert rc.execucoes == [len(rc.log)], "publish+hset+expire tem que sair num RTT so"
    publicado = [c for c in rc.log if c[0] == "publish"][0][2]
    assert len(publicado) <= P._MAX_SYNC_EVENT_BYTES
    assert json.loads(publicado)["__truncated__"] is True


# ── P: ACK compara-e-apaga num unico EVAL ────────────────────────────────────

class _RedisEval:
    """Simula o _LUA_CLEAR_PENDING_ACK, inclusive o modo curinga (ARGV[1] vazio)."""

    def __init__(self, valor):
        self.valor = valor
        self.chamadas = 0

    async def eval(self, _script, _nkeys, _k1, _k2, esperado, job_id):
        self.chamadas += 1
        if self.valor is None:
            return None
        dono = self.valor.split("|", 1)[0]
        if esperado != "" and dono != esperado:
            return [0, dono]
        return [1, self.valor]


def _fixed_rc(monkeypatch, rc):
    async def _get_rc():
        return rc

    monkeypatch.setattr(C, "_get_redis", _get_rc)
    # Own registry: another test in the suite replaces the module's singleton.
    return C.ExecutorConnectionRegistry()


async def test_ack_cleans_up_in_one_round_trip(monkeypatch):
    rc = _RedisEval("ex-1|123.4")
    reg = _fixed_rc(monkeypatch, rc)
    assert await reg.clear_pending_ack(
        "j1", expected_executor_id="ex-1",
    ) == "ex-1"
    assert rc.chamadas == 1


async def test_impostor_ack_is_still_refused(monkeypatch):
    """SEC: the ACK only clears jobs dispatched to THIS executor."""
    rc = _RedisEval("ex-2|123.4")
    reg = _fixed_rc(monkeypatch, rc)
    assert await reg.clear_pending_ack(
        "j1", expected_executor_id="ex-1",
    ) is None


async def test_ack_of_unknown_job_returns_none(monkeypatch):
    rc = _RedisEval(None)
    reg = _fixed_rc(monkeypatch, rc)
    assert await reg.clear_pending_ack(
        "j1", expected_executor_id="ex-1",
    ) is None


# ── P: throttled presence renewal ────────────────────────────────────────────

async def test_presence_does_not_renew_on_every_message(monkeypatch):
    """There were 2 EVALs per capacity (every 10s) for a 120s TTL."""
    renewals = []

    async def _renew(executor_id, token):
        renewals.append(executor_id)
        return True

    monkeypatch.setattr(C, "_redis_renew_presence", _renew)
    reg = C.ExecutorConnectionRegistry()
    conn = C.ExecutorConnection(executor_id="ex-1", websocket=None)
    reg._connections["ex-1"] = conn

    for _ in range(12):  # ~2 minutes of capacity every 10s
        await reg.update_capacity("ex-1", dict(C._DEFAULT_CAPACITY))
    assert renewals == []

    conn.last_presence_renew -= C._PRESENCE_RENEW_INTERVAL + 1
    await reg.update_capacity("ex-1", dict(C._DEFAULT_CAPACITY))
    assert renewals == ["ex-1"]


async def test_redis_failure_does_not_count_as_renewal(monkeypatch):
    """A12: a Redis blip turned into 'renewed' for an entire interval.

    Combined with the fail-open of `_redis_renew_presence`, the presence key
    (TTL 120s) expired with the WebSocket alive and `orphan_runs_watchdog` killed
    runs that were making progress.
    """
    tentativas = []

    async def _renew(executor_id, token):
        tentativas.append(executor_id)
        return None  # Redis down: could not ask

    monkeypatch.setattr(C, "_redis_renew_presence", _renew)
    reg = C.ExecutorConnectionRegistry()
    conn = C.ExecutorConnection(executor_id="ex-1", websocket=None)
    reg._connections["ex-1"] = conn

    conn.last_presence_renew -= C._PRESENCE_RENEW_INTERVAL + 1
    await reg.update_capacity("ex-1", dict(C._DEFAULT_CAPACITY))
    assert tentativas == ["ex-1"]

    # The failure did NOT stamp a renewal: a few seconds later we already try
    # again, instead of waiting the whole interval with the key aging.
    conn.last_presence_renew -= C._PRESENCE_RENEW_RETRY_INTERVAL
    await reg.update_capacity("ex-1", dict(C._DEFAULT_CAPACITY))
    assert tentativas == ["ex-1", "ex-1"]


async def test_confirmed_renewal_stamps_the_throttle(monkeypatch):
    """The throttle still applies when the renewal actually happened."""
    tentativas = []

    async def _renew(executor_id, token):
        tentativas.append(executor_id)
        return True

    monkeypatch.setattr(C, "_redis_renew_presence", _renew)
    reg = C.ExecutorConnectionRegistry()
    conn = C.ExecutorConnection(executor_id="ex-1", websocket=None)
    reg._connections["ex-1"] = conn

    conn.last_presence_renew -= C._PRESENCE_RENEW_INTERVAL + 1
    await reg.update_capacity("ex-1", dict(C._DEFAULT_CAPACITY))
    # A confirmed renewal resets the clock: the next message does not repeat it.
    await reg.update_capacity("ex-1", dict(C._DEFAULT_CAPACITY))
    assert tentativas == ["ex-1"]


async def test_ownership_loss_still_drops_the_duplicate_ws(monkeypatch):
    """False (another worker is the owner) still closes this session."""
    async def _renew(_executor_id, _token):
        return False

    fechados = []

    monkeypatch.setattr(C, "_redis_renew_presence", _renew)
    reg = C.ExecutorConnectionRegistry()
    ws = MagicMock()
    conn = C.ExecutorConnection(executor_id="ex-1", websocket=ws)
    reg._connections["ex-1"] = conn

    async def _unregister(executor_id, expected_ws=None):
        fechados.append(executor_id)

    monkeypatch.setattr(reg, "unregister", _unregister)
    conn.last_presence_renew -= C._PRESENCE_RENEW_INTERVAL + 1
    await reg.update_capacity("ex-1", dict(C._DEFAULT_CAPACITY))
    assert fechados == ["ex-1"]
    C.encerrar_saida(ws)


def test_renewal_slack_covers_more_than_one_failure():
    """With TTL/3 a single missed renewal already brushed up against expiry."""
    assert C._PRESENCE_TTL / C._PRESENCE_RENEW_INTERVAL >= 4


# -- A1: job_result is never discarded by the connection queue ----------------

def _node_event(i):
    """No `kind` — the producer's default, which counts as LIFECYCLE."""
    return ("node_event", {"run_id": "run-1", "node": f"n{i}"}, 10)


def _stdout_event(i):
    """Telemetry: this is the only thing that may be sacrificed when the queue fills up."""
    return ("node_event", {"run_id": "run-1", "node": f"n{i}", "kind": "stdout"}, 10)


async def test_job_result_is_not_dropped_with_full_queue(monkeypatch):
    """job_result is NEVER discarded: with the queue full it goes INLINE right away. Before,
    it tried to open a slot by sacrificing telemetry; now it goes straight inline —
    simpler and equally lossless. Losing it would leave the run hanging in 'running'."""
    inbox = IB._InboxQueue(maxsize=4)
    for i in range(4):
        inbox.put_nowait(_stdout_event(i))
    processed = []

    async def _fake_handle(executor_id, msg, frame_bytes=0, **_kw):
        processed.append(msg["job_id"])

    monkeypatch.setattr(IB, "_handle_job_result", _fake_handle)
    descartes = IB._new_drop_counter()

    await IB._enfileirar_mensagem(
        "ex-1", inbox, descartes, "job_result", {"job_id": "j1"}, 10,
    )

    # Processed inline; not enqueued, and the queue's telemetry stays intact
    # (we do not sacrifice telemetry to open a slot — inline already solves it).
    assert processed == ["j1"]
    assert inbox.qsize() == 4
    assert descartes["total"] == 0


async def test_telemetry_is_still_dropped_with_full_queue():
    """The optimization is not undone: STDOUT on a full queue is still dropped.

    Before, this test sent a node_event WITHOUT `kind` and required it to be
    discarded — that is, it encoded the bug itself: a missing `kind` is the producer's
    default for lifecycle, and that is how a node's `completed`
    vanished. Now the discard only applies to whoever declares itself telemetry.
    """
    inbox = IB._InboxQueue(maxsize=2)
    for i in range(2):
        inbox.put_nowait(_stdout_event(i))
    descartes = IB._new_drop_counter()

    await IB._enfileirar_mensagem(
        "ex-1", inbox, descartes, "node_event",
        {"run_id": "run-1", "node": "novo", "kind": "stdout"}, 10,
    )
    assert descartes["total"] == 1
    assert [m[1]["node"] for m in inbox._queue] == ["n0", "n1"]


async def test_job_result_without_telemetry_to_drop_goes_inline(monkeypatch):
    """The contract's last resort: blocking the loop costs less than losing the run."""
    inbox = IB._InboxQueue(maxsize=2)
    inbox.put_nowait(("job_result", {"job_id": "a"}, 10))
    inbox.put_nowait(("job_result", {"job_id": "b"}, 10))
    processed = []

    async def _fake_handle(executor_id, msg, frame_bytes=0, **_kw):
        processed.append(msg["job_id"])

    monkeypatch.setattr(IB, "_handle_job_result", _fake_handle)
    await IB._enfileirar_mensagem(
        "ex-1", inbox, IB._new_drop_counter(), "job_result", {"job_id": "c"}, 10,
    )
    assert processed == ["c"]
    assert inbox.qsize() == 2  # the two previous ones are still in the queue


# -- A38: cancelling the drainer must not cut a split commit ------------------

async def test_cancelling_the_drainer_does_not_cut_job_result_midway(monkeypatch):
    """A38: a cancel between the lpush to `run_results` and the publish of
    `__workflow_complete__` left the run terminal in the database and the canvas spinning
    forever."""
    phases = []
    entrou = asyncio.Event()
    libera = asyncio.Event()

    async def _handle(executor_id, msg, frame_bytes=0, **_kw):
        phases.append("inicio")
        entrou.set()
        await libera.wait()
        phases.append("fim")

    monkeypatch.setattr(IB, "_handle_job_result", _handle)
    inbox = IB._InboxQueue(maxsize=10)
    inbox.put_nowait(("job_result", {"job_id": "j1"}, 10))
    inflight: set = set()
    task = asyncio.create_task(IB._drain_inbox("ex-1", inbox, inflight))

    await entrou.wait()
    task.cancel()          # teardown desistindo de esperar a drenagem
    await asyncio.sleep(0)
    assert phases == ["inicio"]

    # The write stays alive and shielded: the teardown waits for it.
    assert inflight
    libera.set()
    await asyncio.wait(set(inflight), timeout=1)
    assert phases == ["inicio", "fim"]


# -- A39: a database cooldown must not eat job_result -------------------------

async def test_db_cooldown_does_not_drop_job_result(monkeypatch, fake_conn):
    """A39: a transient DB error armed a 2s cooldown and ALL the
    job_results in that window vanished — each one leaving a run hanging."""
    rc = _FakeRedis()
    fake_conn.db_auth_cooldown_until = time.monotonic() + 60
    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_query_run_snapshot", _snapshot_de())
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_job_result("ex-1", {
        "job_id": "run-1", "run_id": "run-1", "status": "ok", "stats": {"n1": {}},
    })
    assert rc.writes, "job_result foi descartado por um cooldown de telemetria"


async def test_run_read_retries_transient_failure(monkeypatch, fake_conn):
    """A pgbouncer restart (~200ms) must not cost the run's result."""
    rc = _FakeRedis()
    tentativas = []

    async def _flaky(run_id):
        tentativas.append(run_id)
        if len(tentativas) == 1:
            raise RuntimeError("connection reset")
        return ("executor:ex-1", "running", None)

    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_JOB_RESULT_DB_RETRY_DELAY", 0.0)
    monkeypatch.setattr(RES, "_query_run_snapshot", _flaky)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_job_result("ex-1", {
        "job_id": "run-1", "run_id": "run-1", "status": "ok",
    })
    assert len(tentativas) == 2
    assert rc.writes


async def test_lost_job_result_closes_the_run_instead_of_hanging_it(monkeypatch, fake_conn):
    """Contract: if the result is actually lost, the run becomes failed — it never
    stays in 'running' forever."""
    rc = _FakeRedis()

    async def _explode(_run_id):
        raise RuntimeError("pool esgotado")

    # Ownership already proven by earlier node_events of this same run.
    fake_conn.run_auth_cache["run-1"] = (True, time.monotonic() + 60)
    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_JOB_RESULT_DB_RETRY_DELAY", 0.0)
    monkeypatch.setattr(RES, "_query_run_snapshot", _explode)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_job_result("ex-1", {"job_id": "run-1", "status": "ok"})

    juntos = [json.loads(w) for w in rc.writes]
    assert any(p.get("task_id") == "run-1" and p.get("status") == "failed" for p in juntos)
    # And the canvas receives the completion, otherwise the panel spins forever.
    assert any(p.get("node") == "__workflow_complete__" for p in juntos)


async def test_foreign_run_is_not_closed_with_db_down(monkeypatch, fake_conn):
    """SEC: without proven ownership, a database outage stays fail-closed — a compromised
    executor must not fail another tenant's runs during the incident."""
    rc = _FakeRedis()

    async def _explode(_run_id):
        raise RuntimeError("pool esgotado")

    monkeypatch.setattr(P, "_rate_state", {})
    monkeypatch.setattr(RES, "_JOB_RESULT_DB_RETRY_DELAY", 0.0)
    monkeypatch.setattr(RES, "_query_run_snapshot", _explode)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await RES._handle_job_result("ex-1", {"job_id": "run-alheio", "status": "ok"})
    assert rc.writes == []


async def test_teardown_rescues_job_result_left_in_queue(monkeypatch):
    """The cancelled drainer leaves the queue full: telemetry may vanish, the
    result may not — it is the run's last message."""
    inbox = IB._InboxQueue(maxsize=10)
    inbox.put_nowait(("node_event", {"run_id": "run-1", "node": "n1"}, 10))
    inbox.put_nowait(("job_result", {"job_id": "run-1", "run_id": "run-1"}, 10))
    processed = []

    async def _fake_handle(executor_id, msg, frame_bytes=0, **_kw):
        processed.append(msg["job_id"])

    monkeypatch.setattr(IB, "_handle_job_result", _fake_handle)
    await IB._resgatar_job_results_pendentes("ex-1", inbox)
    assert processed == ["run-1"]


async def test_failing_rescue_closes_the_run(monkeypatch, fake_conn):
    """If not even the rescue works, the run becomes failed — it never stays in 'running'."""
    rc = _FakeRedis()
    inbox = IB._InboxQueue(maxsize=10)
    inbox.put_nowait(("job_result", {"job_id": "run-1", "run_id": "run-1"}, 10))
    fake_conn.run_auth_cache["run-1"] = (True, time.monotonic() + 60)

    async def _explode(_executor_id, _msg, _frame_bytes=0, **_kw):
        raise RuntimeError("redis fora")

    monkeypatch.setattr(IB, "_handle_job_result", _explode)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: rc)

    await IB._resgatar_job_results_pendentes("ex-1", inbox)
    juntos = [json.loads(w) for w in rc.writes]
    assert any(p.get("task_id") == "run-1" and p.get("status") == "failed" for p in juntos)


# ── Back-pressure: lifecycle is never discarded ─────────────────────────────
#
# The performance MR replaced the inline `await _handle_node_event(...)` with a
# queue with discarding. Under pressure, a node's `completed` started falling into the
# SAME `return` as a stdout line — and the node kept spinning forever on the canvas,
# with the run already completed in the database and in the executor's log. These
# tests lock in the rule that restores the guarantee: only telemetry may be lost.

def _ev(node: str, *, kind: str = "lifecycle", status: str = "completed") -> tuple:
    return ("node_event", {"run_id": "r", "node": node, "kind": kind, "status": status}, 10)


def _queued_nodes(inbox) -> list:
    return [m.get("node") for _t, m, _b in list(inbox._queue)]


async def test_lifecycle_is_dropped_with_full_queue():
    """NEW contract: under a full queue, lifecycle is discardable just like
    telemetry. Losing a `completed` degrades honestly — the node becomes 'unknown'
    at the end of the run (completeExecution) and the client's watchdog recovers the channel.
    Back-pressure does not apply here: the real cause of the hang was transport
    (Safari), now covered by heartbeat+watchdog."""
    inbox = IB._InboxQueue(maxsize=2)
    inbox.put_nowait(_ev("n1", kind="stdout", status="log"))
    inbox.put_nowait(_ev("n2", kind="stdout", status="log"))
    descartes = IB._new_drop_counter()

    await IB._enfileirar_mensagem(
        "ex-1", inbox, descartes, "node_event",
        {"run_id": "r", "node": "n3", "kind": "lifecycle", "status": "completed"}, 10,
    )

    # Discarded: did not jump the queue or wait for a slot.
    assert _queued_nodes(inbox) == ["n1", "n2"]
    assert descartes["total"] == 1


async def test_stdout_stays_droppable_with_full_queue():
    """The queue exists to absorb telemetry — it is still what gets dropped."""
    inbox = IB._InboxQueue(maxsize=2)
    inbox.put_nowait(_ev("n1"))
    inbox.put_nowait(_ev("n2"))
    descartes = IB._new_drop_counter()

    await IB._enfileirar_mensagem(
        "ex-1", inbox, descartes, "node_event",
        {"run_id": "r", "node": "n3", "kind": "stdout", "status": "log"}, 10,
    )

    assert _queued_nodes(inbox) == ["n1", "n2"]
    assert descartes["total"] == 1


# ── sync_complete: the only one that still pays back-pressure ───────────────

async def test_sync_complete_waits_for_slot_instead_of_being_dropped():
    inbox = IB._InboxQueue(maxsize=1)
    inbox.put_nowait(_ev("n1"))
    descartes = IB._new_drop_counter()

    tarefa = asyncio.create_task(IB._enfileirar_mensagem(
        "ex-1", inbox, descartes, "sync_event", {"event": "sync_complete"}, 10,
    ))
    await asyncio.sleep(0)
    assert not tarefa.done()
    assert descartes["total"] == 0

    inbox.get_nowait()
    await asyncio.wait_for(tarefa, timeout=1)


