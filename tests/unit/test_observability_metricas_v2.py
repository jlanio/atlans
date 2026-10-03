# tests/unit/test_observability_metricas_v2.py
"""History metrics v2 (docs/specs/metrics-history.md §3).

What the spec changed on purpose and these tests pin down:

- success rate = completed ÷ (completed + failed) — running and
  cancelled are left out of the denominator;
- percentiles only from completed runs with duration > 0, with the SAME
  interpolation as PostgreSQL's `percentile_cont` in the Python fallback;
- common filters (`workspace_id` → 403 outside the scope, `workflow_id` → 404,
  `tz` → 422) and a cache key that includes them;
- "stuck" = active for longer than max(3 × p50, 900 s), or 3600 s without p50;
- per-day chart with every day, cut in the requested time zone;
- new run fields for any user, admin-only ones preserved;
- "Sem executor" (no executor) row and online fleet with zeros in the per-executor view.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from app.core.exceptions import WorkflowNotFoundError, WorkspaceAccessDeniedError
from app.core.executor_connections import executor_registry
from app.core.utils.estatistica import percentil_linear
from app.services import observability_service as osvc
from app.services.observability.agregados import _execucoes_presas
from app.services.observability_service import (
    ObservabilityService,
    _now_block,
    _metrics_cache_key,
    _percentis,
    _resolve_scope,
    _serialize_run,
)


# ── Test doubles ─────────────────────────────────────────────────────────────

def _user(role="admin", id_hash="usr-1"):
    u = MagicMock()
    u.role = role
    u.id_hash = id_hash
    return u


class _EmptyRow:
    """Aggregation row with no data: any column reads as None."""

    def __getattr__(self, _nome):
        return None


def _resultado(*, linha=None, linhas=None, escalar=None):
    r = MagicMock()
    r.one.return_value = linha if linha is not None else _EmptyRow()
    r.all.return_value = list(linhas or [])
    r.scalars.return_value.all.return_value = list(linhas or [])
    r.scalar_one_or_none.return_value = escalar
    r.scalar.return_value = escalar
    return r


def _db(*respostas, sql_dialect="sqlite"):
    """Session double: returns `respostas` in order and, once exhausted, empty
    results. `sql_dialect` decides between PostgreSQL SQL and the Python fallback."""
    fila = list(respostas)

    async def _execute(stmt):
        return fila.pop(0) if fila else _resultado()

    db = MagicMock(execute=AsyncMock(side_effect=_execute))
    db.bind.dialect.name = sql_dialect
    return db


def _sql(db, chamada=0, sql_dialect=postgresql.dialect()) -> str:
    stmt = db.execute.await_args_list[chamada].args[0]
    return str(stmt.compile(dialect=sql_dialect, compile_kwargs={"literal_binds": False}))


@pytest.fixture(autouse=True)
def _no_redis():
    """Presence, capacity and ACKs come from Redis; here nothing is up."""
    with patch.object(executor_registry, "is_online", AsyncMock(return_value=False)), \
         patch.object(executor_registry, "read_capacity", AsyncMock(return_value=None)), \
         patch.object(executor_registry, "list_pending_acks", AsyncMock(return_value=[])):
        yield


AGORA = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


# ── Percentis ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("valores, p, esperado", [
    ([], 0.5, None),
    ([42.0], 0.5, 42.0),
    ([10, 20], 0.5, 15.0),                # interpolates between neighbors
    ([1, 2, 3, 4, 5], 0.5, 3.0),
    ([1, 2, 3, 4, 5], 0.95, 4.8),         # 0.95 * 4 = 3.8 → 4 + 0.8 * (5 - 4)
    ([5, 1, 3], 0.5, 3.0),                # does not depend on input order
])
def test_continuous_percentile_follows_postgres_percentile_cont(valores, p, esperado):
    assert percentil_linear(valores, p) == esperado


@pytest.mark.asyncio
async def test_python_percentiles_only_look_at_completed_with_positive_duration():
    """Outside PostgreSQL the median is computed in Python, but the slice
    (status success, duration > 0) must be in the SQL — otherwise the projected
    volume would be the whole window."""
    db = _db(_resultado(linhas=[30.0, 10.0, 20.0]))

    p50, p95 = await _percentis(db, [], [0.5, 0.95])

    assert (p50, p95) == (20.0, 29.0)
    sql = _sql(db)
    assert "workflow_runs.status = " in sql
    assert "workflow_runs.duration_seconds > " in sql
    assert "percentile_cont" not in sql


@pytest.mark.asyncio
async def test_postgres_percentiles_use_percentile_cont_within_group():
    linha = SimpleNamespace(p0=42.0, p1=190.0)
    db = _db(_resultado(linha=linha), sql_dialect="postgresql")

    assert await _percentis(db, [], [0.5, 0.95]) == [42.0, 190.0]
    sql = _sql(db)
    assert "percentile_cont(" in sql
    assert "WITHIN GROUP (ORDER BY workflow_runs.duration_seconds)" in sql


# ── Filtros comuns e cache ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_out_of_scope_workspace_is_403_for_regular_user():
    with pytest.raises(WorkspaceAccessDeniedError):
        await _resolve_scope(_db(), _user("user"), ["ws-1"], workspace_id="ws-2")


@pytest.mark.asyncio
async def test_admin_filters_any_workspace_without_querying_the_db():
    db = _db()
    run_f, wf_f = await _resolve_scope(
        db, _user("admin"), [], workspace_id="ws-qualquer", como_admin=True,
    )

    assert db.execute.await_count == 0
    assert "workflow_runs.workspace_id = " in str(run_f[0])
    assert "workflows.workspace_id = " in str(wf_f[0])


@pytest.mark.asyncio
async def test_out_of_scope_workflow_is_404():
    """"No access" and "does not exist" fall into the same 404: a 403 would confirm
    the existence of another tenant's workflows."""
    db = _db(_resultado(escalar=None))
    with pytest.raises(WorkflowNotFoundError):
        await _resolve_scope(db, _user("user"), ["ws-1"], workflow_id="wf-x")
    assert "workflows.workspace_id IN" in _sql(db)


def test_cache_key_includes_the_filters():
    """Without the filters in the key, "all workspaces" would be served to whoever
    asked for "only workspace X" for the next 45 s."""
    base = _metrics_cache_key("metrics", _user("admin"), [], 30, como_admin=True)
    with_ws = _metrics_cache_key("metrics", _user("admin"), [], 30, como_admin=True, workspace_id="ws-1")
    with_wf = _metrics_cache_key(
        "metrics", _user("admin"), [], 30, como_admin=True, workspace_id="ws-1", workflow_id="wf-1",
    )

    assert len({base, with_ws, with_wf}) == 3
    assert _metrics_cache_key("metrics", _user("admin"), [], 30, como_admin=True, workspace_id=None) == base


# ── /metrics: formulas ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_success_rate_ignores_in_progress_and_cancelled():
    principal = SimpleNamespace(
        total=17, success=8, failed=2, running=5, pending=1, cancelled=1,
        avg_duration=12.0, last_24h=3, last_7d=9, prev_7d=4, prev_7d_success=3, prev_7d_failed=1,
    )
    anterior = SimpleNamespace(total=10, success=6, failed=4)
    db = _db(
        _resultado(linha=SimpleNamespace(total=3, ativos=2)),
        _resultado(linha=principal),
        _resultado(linha=anterior),
    )

    m = await ObservabilityService.get_metrics(db, _user("admin"), [], days=7, force=True, como_admin=True)

    assert m["success_rate"] == 0.8                    # 8 / (8 + 2), not 8 / 17
    assert m["success_rate_prev_7d"] == 0.75           # 3 / (3 + 1)
    assert m["by_status"] == {
        "success": 8, "failed": 2, "running": 5, "pending": 1, "cancelled": 1, "other": 0,
    }
    assert (m["success_runs"], m["running_runs"], m["pending_runs"], m["cancelled_runs"]) == (8, 5, 1, 1)
    assert m["prev_period"] == {
        "total_runs": 10, "success_runs": 6, "failed_runs": 4, "success_rate": 0.6, "p50_seconds": None,
    }
    assert m["duration"] == {"p50_seconds": None, "p95_seconds": None}
    # Fields the Overview still uses.
    assert (m["total_workflows"], m["active_workflows"], m["runs_last_24h"], m["runs_last_7d"], m["runs_prev_7d"]) == (3, 2, 3, 9, 4)
    assert m["avg_duration_seconds"] == 12.0


@pytest.mark.asyncio
async def test_without_runs_the_rate_is_zero_and_the_previous_7d_is_null():
    """0.0 (spec) for the window rate; `null` for the 7-day one, which is what
    hides the Overview's trend arrow instead of showing "dropped to 0%"."""
    db = _db(_resultado(linha=SimpleNamespace(total=0, ativos=0)))

    m = await ObservabilityService.get_metrics(db, _user("admin"), [], days=30, force=True, como_admin=True)

    assert m["success_rate"] == 0.0
    assert m["success_rate_prev_7d"] is None
    assert m["prev_period"]["success_rate"] == 0.0
    assert m["now"]["overdue_acks"] == 0          # admin: contado
    assert m["now"]["executors"] == {"online": 0, "total": 0}
    assert m["now"]["queued_on_executors"] is None


@pytest.mark.asyncio
async def test_previous_period_has_its_own_window_of_same_size():
    """The comparison is against [now-2d, now-d): it lives in its own query instead
    of widening the main WHERE (which the window tests pin at max(days, 14))."""
    db = _db(_resultado(linha=SimpleNamespace(total=0, ativos=0)))

    await ObservabilityService.get_metrics(db, _user("admin"), [], days=30, force=True, como_admin=True)

    stmt = db.execute.await_args_list[2].args[0]
    instants = sorted(v for v in stmt.compile().params.values() if isinstance(v, datetime))
    assert len(instants) == 2
    assert all(m.tzinfo is not None for m in instants)
    assert timedelta(days=29, hours=23) < instants[1] - instants[0] < timedelta(days=30, hours=1)
    assert timedelta(days=59) < datetime.now(timezone.utc) - instants[0] < timedelta(days=61)


@pytest.mark.asyncio
async def test_top_failures_brings_name_rate_and_summarized_last_error():
    agregado = SimpleNamespace(workflow_hash="wf-1", total_runs=20, failure_count=5)
    ultima = SimpleNamespace(
        workflow_hash="wf-1", status="failed", error_message="x" * 300,
        error_category="timeout", start_time=AGORA,
    )
    meta = SimpleNamespace(
        id_hash="wf-1", name="Integração SICAR", flag_ative=True, workspace_id="ws-1",
        owner_username="ana", workspace_name="Cadastro", origem="usuario",
    )
    db = _db(_resultado(linhas=[agregado]), _resultado(linhas=[ultima]), _resultado(linhas=[meta]))

    (item,) = await osvc._top_failures(db, [], AGORA - timedelta(days=30))

    assert item["workflow_name"] == "Integração SICAR"
    assert item["failure_rate"] == 0.25
    assert len(item["last_error"]) == 200 and item["last_error"].endswith("…")
    assert item["last_error_category"] == "timeout"
    assert item["last_failed_at"] == AGORA.isoformat()
    # Each workflow's "last failure" comes from ONE query with a window function.
    assert "row_number() OVER (PARTITION BY workflow_runs.workflow_hash" in _sql(db, 1)


# ── Stuck runs ───────────────────────────────────────────────────────────────

def _candidate(task_id, wf, minutos, host="executor:ex-2"):
    return SimpleNamespace(
        task_id=task_id, id=1, workflow_hash=wf, host=host,
        start_time=AGORA - timedelta(minutes=minutos),
    )


@pytest.mark.asyncio
async def test_stuck_uses_3x_the_median_with_900s_floor_and_3600s_without_median():
    candidates = [
        _candidate("lenta-sem-p50", "wf-a", 70),   # 4200 s > 3600 (no p50)    → stuck
        _candidate("curta-sem-p50", "wf-a", 50),   # 3000 s < 3600             → no
        _candidate("piso", "wf-b", 16),            # p50 100 → max(300, 900) = 900 < 960 → presa
        _candidate("multiplo", "wf-c", 40),        # p50 1000 → 3000 > 2400    → no
        _candidate("multiplo-2", "wf-c", 60),      # 3600 > 3000               → presa
    ]
    nomes = [SimpleNamespace(id_hash="ex-2", name="geo-02")]
    db = _db(_resultado(linhas=candidates), _resultado(), _resultado(linhas=nomes))

    with patch("app.services.observability.agregados._p50_por_workflow", AsyncMock(return_value={"wf-b": 100.0, "wf-c": 1000.0})):
        quantas, presas = await _execucoes_presas(db, [], AGORA)

    assert quantas == 3
    assert [p["run_id"] for p in presas] == ["lenta-sem-p50", "piso", "multiplo-2"]
    assert presas[0]["elapsed_seconds"] == 4200 and presas[0]["typical_seconds"] is None
    assert presas[1]["typical_seconds"] == 100.0
    assert presas[0]["executor_name"] == "geo-02"
    # The query already cuts at the floor: nothing below 900 s can be stuck.
    sql = _sql(db, 0)
    assert "workflow_runs.status IN" in sql and "workflow_runs.start_time <= " in sql


@pytest.mark.asyncio
async def test_stuck_limits_to_five_oldest_but_counts_all():
    candidates = [_candidate(f"r{i}", "wf-a", 120 - i) for i in range(7)]
    db = _db(_resultado(linhas=candidates))

    with patch("app.services.observability.agregados._p50_por_workflow", AsyncMock(return_value={})):
        quantas, presas = await _execucoes_presas(db, [], AGORA)

    assert quantas == 7
    assert [p["run_id"] for p in presas] == ["r0", "r1", "r2", "r3", "r4"]


# ── "Now" block ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_now_counts_online_fleet_published_queue_and_acks_only_for_admin():
    frota = [
        SimpleNamespace(id_hash="ex-1", name="a", executor_type="dedicated", is_default=False, status="active"),
        SimpleNamespace(id_hash="ex-2", name="b", executor_type="dedicated", is_default=False, status="active"),
        SimpleNamespace(id_hash="ex-3", name="c", executor_type="default", is_default=True, status="active"),
    ]
    ativos = SimpleNamespace(running=2, pending=1)
    capacities = {"ex-1": {"running": 2, "queued": 5, "max_concurrent": 4, "max_queue": 50, "extra": 1}, "ex-2": None}
    acks = [{"job_id": "j1", "elapsed_seconds": 20.0}, {"job_id": "j2", "elapsed_seconds": 3.0}]

    with patch.object(executor_registry, "is_online", AsyncMock(side_effect=lambda eid: eid in ("ex-1", "ex-2"))), \
         patch.object(executor_registry, "read_capacity", AsyncMock(side_effect=lambda eid: capacities.get(eid))), \
         patch.object(executor_registry, "list_pending_acks", AsyncMock(return_value=acks)):
        db = _db(_resultado(linha=ativos), _resultado(), _resultado(linhas=frota))
        admin = await _now_block(db, _user("admin"), [], AGORA, como_admin=True)

        db = _db(_resultado(linha=ativos), _resultado(), _resultado(linhas=frota))
        with patch("app.services.user_executor_service.get_user_accessible_agents",
                   AsyncMock(return_value=[{"id_hash": "ex-1", "name": "a", "status": "active"},
                                           {"id_hash": "ex-9", "name": "z", "status": "inactive"}])):
            comum = await _now_block(db, _user("user"), [], AGORA)

    assert (admin["running"], admin["pending"], admin["stuck_count"]) == (2, 1, 0)
    assert admin["executors"] == {"online": 2, "total": 3}
    assert admin["queued_on_executors"] == 5          # only those that publish; ex-2 online without capacity does not zero it
    assert admin["overdue_acks"] == 1                  # 20 s ≥ JOB_ACK_WARN_SECONDS; 3 s is not
    # Regular user: accessible fleet (inactive ones left out) and null ACKs.
    assert comum["executors"] == {"online": 1, "total": 1}
    assert comum["overdue_acks"] is None


# ── /runs-by-day ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_runs_per_day_brings_all_days_cut_in_the_timezone():
    """In São Paulo (UTC-3), 01:00 UTC is still the previous day; `pending` adds
    into `running`, `cancelled` stays separate and the rest goes to `other`."""
    hoje = datetime.now(timezone.utc)
    yesterday_0100_utc = (hoje - timedelta(days=1)).replace(hour=1, minute=0, second=0, microsecond=0)
    linhas = [
        SimpleNamespace(start_time=yesterday_0100_utc, status="success"),
        SimpleNamespace(start_time=hoje - timedelta(hours=2) if hoje.hour >= 5 else hoje, status="pending"),
        SimpleNamespace(start_time=hoje, status="running"),
        SimpleNamespace(start_time=hoje, status="cancelled"),
        SimpleNamespace(start_time=hoje, status="cached"),
        SimpleNamespace(start_time=hoje.replace(tzinfo=None), status="failed"),   # naive (SQLite) → UTC
    ]
    db = _db(_resultado(linhas=linhas))

    saida = await ObservabilityService.get_runs_by_day(
        db, _user("admin"), [], 7, tz="America/Sao_Paulo", como_admin=True,
    )

    dias = saida["days"]
    assert len(dias) == 7
    assert [d["day"] for d in dias] == sorted(d["day"] for d in dias)
    assert all(set(d) == {"day", "total", "success", "failed", "running", "cancelled", "other"} for d in dias)
    # Yesterday's 01:00 UTC run falls on "the day before yesterday" in the SP time
    # zone (−3h crosses midnight). Find the bucket by DATE in the requested time
    # zone, not by a fixed index: when the test runs between 00:00–03:00 UTC,
    # "today in SP" is still the previous day and `dias[-3]` slipped by one day
    # (it failed only in that window).
    success_day = yesterday_0100_utc.astimezone(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    balde = next(d for d in dias if d["day"] == success_day)
    assert balde["success"] == 1 and balde["total"] == 1
    assert sum(d["total"] for d in dias) == 6
    assert sum(d["running"] for d in dias) == 2
    assert sum(d["cancelled"] for d in dias) == 1
    assert sum(d["other"] for d in dias) == 1
    assert sum(d["failed"] for d in dias) == 1
    # Fallback: only (start_time, status) of the window go to Python.
    sql = _sql(db)
    assert "count(" not in sql and "workflow_runs.start_time >= " in sql


@pytest.mark.asyncio
async def test_postgres_runs_per_day_cuts_the_day_with_at_time_zone():
    db = _db(_resultado(linhas=[SimpleNamespace(day="2026-09-06", status="success", count=2)]), sql_dialect="postgresql")

    with patch.object(osvc, "_agora_utc", return_value=AGORA):
        saida = await ObservabilityService.get_runs_by_day(
            db, _user("admin"), [], 3, tz="America/Sao_Paulo", como_admin=True,
        )

    sql = _sql(db)
    assert "timezone(" in sql and "GROUP BY" in sql
    assert [d["day"] for d in saida["days"]] == ["2026-09-04", "2026-09-05", "2026-09-06"]
    assert saida["days"][-1] == {
        "day": "2026-09-06", "total": 2, "success": 2, "failed": 0, "running": 0, "cancelled": 0, "other": 0,
    }


@pytest.mark.asyncio
async def test_invalid_tz_is_422_in_the_router(client):
    """Validation stays at the edge: an invalid name would become an SQL error in
    `AT TIME ZONE` (500) instead of a 422 the web app understands."""
    from app.api.dependencies import get_db
    from app.main import app

    async def _fake_db():
        yield _db()

    app.dependency_overrides[get_db] = _fake_db
    try:
        resp = await client.get("/observability/runs-by-day", params={"days": 7, "tz": "Marte/Olimpo"})
        assert resp.status_code == 422
        resp = await client.get("/observability/metrics", params={"workspace_id": "ws-de-outro"})
        assert resp.status_code == 403
        assert resp.json()["error"] == "workspace_access_denied"
        resp = await client.get("/observability/runs", params={"tier": "xyz"})
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── /runs and /runs/{id}: serialization and filters ──────────────────────────

def _run_row(**over):
    base = dict(
        task_id="t-1", id=1, status="failed", start_time=AGORA, end_time=None, duration_seconds=None,
        error_message="boom", host="executor:abcdef12345", dispatch_tier="pool", workflow_hash="wf-1",
        workspace_id="ws-antigo", trigger_source="schedule", triggered_by="usr-9",
        error_category="timeout", schedule_id=7, retry_count=0, node_stats={},
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_serialization_brings_the_new_fields_and_reserves_the_admin_only():
    meta = {"wf-1": {
        "workflow_name": "Integração", "workflow_active": True, "owner_username": "ana",
        "workspace_id": "ws-novo", "workspace_name": "Novo", "origem": "assistente",
    }}
    kwargs = dict(
        agent_names={"abcdef12345": "geo-02"}, workflow_meta=meta,  # pragma: allowlist secret
        workspace_names={"ws-antigo": "Antigo"}, user_names={"usr-9": "bia"},
    )

    comum = _serialize_run(_run_row(), admin=False, **kwargs)
    admin = _serialize_run(_run_row(), admin=True, **kwargs)

    assert comum["executor_id"] == "abcdef12345" and comum["executor_name"] == "geo-02"
    assert comum["agent_host"] == "geo-02@12345"
    assert (comum["trigger_source"], comum["triggered_by"], comum["triggered_by_username"]) == ("schedule", "usr-9", "bia")
    assert (comum["error_category"], comum["schedule_id"]) == ("timeout", 7)
    assert comum["workflow_name"] == "Integração"
    # The workspace is the RUN'S (where the run happened), not the workflow's current one.
    assert (comum["workspace_id"], comum["workspace_name"]) == ("ws-antigo", "Antigo")
    assert "workflow_active" not in comum and "owner_username" not in comum
    assert admin["workflow_active"] is True and admin["owner_username"] == "ana"
    # The WORKFLOW's origin (who created it) goes to ANY user: it is the
    # assistant badge in the list, not administrative data.
    assert comum["workflow_origem"] == "assistente"


def test_serialization_without_host_and_meta_returns_nulls():
    out = _serialize_run(_run_row(host=None, triggered_by=None, workspace_id=None))
    assert out["executor_id"] is None and out["executor_name"] is None and out["agent_host"] is None
    assert out["triggered_by_username"] is None and out["workspace_name"] is None
    assert "workflow_name" not in out
    # Workflow deleted for good: no meta, no origin — the screen paints no badge.
    assert out["workflow_origem"] is None


@pytest.mark.asyncio
async def test_workflow_origin_filter_joins_workflows_and_is_not_the_trigger():
    """The History's "Assistente" chip slices by the WORKFLOW (`workflows.origem`),
    not by the trigger (`workflow_runs.trigger_source`) — they are different and
    combinable axes."""
    db = _db()
    await ObservabilityService.list_runs(
        db, _user("admin"), [], workflow_origem="assistente", como_admin=True,
    )
    sql = _sql(db, 0)
    assert "JOIN workflows" in sql, "o recorte por origem precisa do join, como a busca"
    assert "workflows.origem = " in sql
    # `trigger_source` stays in the projection, but does NOT become a slice: the
    # chip does not hide manual runs of an assistant workflow.
    assert "workflow_runs.trigger_source = " not in sql

    # Combined with the status chip and with search, without a duplicate join.
    db = _db()
    await ObservabilityService.list_runs(
        db, _user("admin"), [], workflow_origem="assistente", status="failed", q="GDAL", como_admin=True,
    )
    sql = _sql(db, 0)
    assert sql.count("JOIN workflows") == 1
    assert "workflow_runs.status = " in sql and "workflows.name ILIKE" in sql


@pytest.mark.asyncio
async def test_list_only_joins_workflows_when_there_is_a_search():
    db = _db()
    await ObservabilityService.list_runs(
        db, _user("admin"), [], q="GDAL", tier="pool", trigger_source="schedule", como_admin=True,
    )
    with_search = _sql(db, 0)
    assert "JOIN workflows" in with_search
    assert "workflow_runs.error_message ILIKE" in with_search and "workflows.name ILIKE" in with_search
    assert "workflow_runs.dispatch_tier = " in with_search and "workflow_runs.trigger_source = " in with_search
    padrao = [v for v in db.execute.await_args_list[0].args[0].compile().params.values() if v == "%GDAL%"]
    assert padrao, "o termo vira %termo% nos dois ILIKE"

    db = _db()
    await ObservabilityService.list_runs(db, _user("user"), ["ws-1"], workspace_id="ws-1")
    without_search = _sql(db, 0)
    assert "JOIN workflows" not in without_search
    assert "workflow_runs.workspace_id = " in without_search


@pytest.mark.asyncio
async def test_search_escapes_user_wildcards():
    db = _db()
    await ObservabilityService.list_runs(db, _user("admin"), [], q="100%_a", como_admin=True)
    params = db.execute.await_args_list[0].args[0].compile().params.values()
    assert "%100\\%\\_a%" in params


@pytest.mark.asyncio
async def test_list_resolves_names_in_batch_not_per_row():
    """A page of N runs costs the listing + 4 SELECT ... IN (executors,
    workflows, workspaces, users), regardless of N."""
    linhas = [_run_row(task_id=f"t-{i}", triggered_by=f"usr-{i}", workspace_id=f"ws-{i}") for i in range(10)]
    db = _db(_resultado(linhas=linhas))

    saida = await ObservabilityService.list_runs(db, _user("user"), ["ws-1"], limit=50)

    assert len(saida["runs"]) == 10
    assert db.execute.await_count == 5
    assert "workflow_active" not in saida["runs"][0]


@pytest.mark.asyncio
async def test_detail_brings_the_workflow_typical_seconds():
    run = _run_row()
    db = _db(_resultado(escalar=run))

    with patch.object(osvc, "_p50_por_workflow", AsyncMock(return_value={"wf-1": 38.5})):
        detalhe = await ObservabilityService.get_run_detail(db, "t-1", _user("user"), ["ws-antigo"])

    assert detalhe["typical_seconds"] == 38.5
    assert detalhe["trigger_source"] == "schedule"
    assert "owner_username" not in detalhe


@pytest.mark.asyncio
async def test_active_run_detail_does_not_recompute_the_median():
    """While the run is RUNNING (the frequent poll that run_workflow instructs), the
    90-day median makes no sense — it is not computed. Mutation: removing the gate
    on `_ACTIVE_STATUSES` makes `_p50_por_workflow` run on every poll."""
    p50 = AsyncMock(return_value={"wf-1": 38.5})
    for estado in ("running", "pending"):
        run = _run_row(status=estado, end_time=None)
        db = _db(_resultado(escalar=run))
        with patch.object(osvc, "_p50_por_workflow", p50):
            detalhe = await ObservabilityService.get_run_detail(db, "t-1", _user("user"), ["ws-antigo"])
        assert detalhe["typical_seconds"] is None, estado
    p50.assert_not_called()


# ── /metrics/executores ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_executors_include_no_executor_and_online_fleet_with_zeros():
    linhas = [
        SimpleNamespace(host="executor:ex-1", total_runs=4, success_runs=3, failed_runs=1, avg_duration=10.0, last_run_at=AGORA),
        SimpleNamespace(host=None, total_runs=2, success_runs=0, failed_runs=2, avg_duration=None, last_run_at=AGORA),
    ]
    frota = [
        SimpleNamespace(id_hash="ex-1", name="geo-01", executor_type="dedicated", is_default=False, status="active"),
        SimpleNamespace(id_hash="ex-2", name="geo-02", executor_type="default", is_default=True, status="active"),
        SimpleNamespace(id_hash="ex-3", name="geo-03", executor_type="dedicated", is_default=False, status="active"),
    ]
    cap = {"ex-1": {"running": 1, "queued": 2, "max_concurrent": 4, "max_queue": 50}}
    db = _db(_resultado(linhas=linhas), _resultado(), _resultado(linhas=frota))

    with patch.object(executor_registry, "is_online", AsyncMock(side_effect=lambda eid: eid in ("ex-1", "ex-2"))), \
         patch.object(executor_registry, "read_capacity", AsyncMock(side_effect=lambda eid: cap.get(eid))):
        saida = await ObservabilityService.get_executor_metrics(
            db, _user("admin"), [], days=30, force=True, como_admin=True,
        )

    by_host = {e["agent_host"]: e for e in saida["executores"]}
    assert set(by_host) == {"executor:ex-1", None, "executor:ex-2"}   # ex-3 offline and without runs is left out

    sem = by_host[None]
    assert sem["display_name"] == "Sem executor" and sem["unassigned"] is True
    assert (sem["executor_id"], sem["online"], sem["capacity"], sem["p50_seconds"]) == (None, False, None, None)

    ex1 = by_host["executor:ex-1"]
    assert (ex1["executor_id"], ex1["executor_type"], ex1["is_default"], ex1["status"]) == ("ex-1", "dedicated", False, "active")
    assert ex1["online"] is True and ex1["capacity"] == cap["ex-1"]
    assert ex1["success_rate"] == 0.75 and ex1["unassigned"] is False

    ex2 = by_host["executor:ex-2"]
    assert ex2["total_runs"] == 0 and ex2["online"] is True and ex2["last_run_at"] is None
    assert ex2["display_name"] == "geo-02@ex-2"


# ── /metrics/workflows ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_per_workflow_view_lists_all_with_zeros_and_sorts():
    inventario = [
        SimpleNamespace(id_hash="wf-b", name="Beta", flag_ative=True, workspace_id="ws-1", workspace_name="Um", origem="usuario"),
        SimpleNamespace(id_hash="wf-a", name="alfa", flag_ative=False, workspace_id="ws-1", workspace_name="Um", origem="assistente"),
        SimpleNamespace(id_hash="wf-c", name="Gama", flag_ative=True, workspace_id="ws-2", workspace_name="Dois", origem="usuario"),
    ]
    agregados = [
        SimpleNamespace(workflow_hash="wf-c", total=5, success=3, failed=1, running=1),
    ]
    # The last run completed; the last ERROR is the one from the last failure (a
    # separate query, only for those with a failure in the window).
    ultimas = [SimpleNamespace(workflow_hash="wf-c", status="success", error_message=None, error_category=None, start_time=AGORA)]
    last_failures = [SimpleNamespace(workflow_hash="wf-c", status="failed", error_message="Timeout", error_category="timeout", start_time=AGORA)]
    db = _db(
        _resultado(linhas=inventario), _resultado(linhas=agregados),
        _resultado(linhas=[SimpleNamespace(grupo="wf-c", duration_seconds=170.0)]),
        _resultado(linhas=ultimas), _resultado(linhas=last_failures),
    )

    saida = await ObservabilityService.get_workflows_metrics(
        db, _user("admin"), [], days=30, force=True, como_admin=True,
    )

    assert [w["workflow_hash"] for w in saida["workflows"]] == ["wf-c", "wf-a", "wf-b"]   # runs desc, nome asc (sem caixa)
    gama = saida["workflows"][0]
    assert gama["success_rate"] == 0.75 and gama["p50_seconds"] == 170.0 and gama["running_runs"] == 1
    assert (gama["last_status"], gama["last_error"], gama["last_error_category"]) == ("success", "Timeout", "timeout")
    assert gama["last_run_at"] == AGORA.isoformat()
    alfa = saida["workflows"][1]
    assert alfa["total_runs"] == 0 and alfa["active"] is False and alfa["last_run_at"] is None
    assert alfa["p50_seconds"] is None and alfa["success_rate"] == 0.0
    # Each row says who created the workflow: the "Por workflow" view paints the
    # assistant badge and filters by it without a second call.
    assert (alfa["origem"], gama["origem"]) == ("assistente", "usuario")
    assert "workflows.deleted_at IS NULL" in _sql(db, 0)


# ══════════════════════════════════════════════════════════════════════════════
# Review regressions: date_from with a Z suffix (Python 3.10) and a per-user
# cache key (the executor fleet is not a function of the workspaces alone)
# ══════════════════════════════════════════════════════════════════════════════

def test_parse_iso_accepts_the_z_suffix_the_web_sends():
    from app.services.observability_service import _parse_iso
    d = _parse_iso("2026-08-07T22:05:13.123Z")
    assert d.tzinfo is not None and d.utcoffset().total_seconds() == 0
    assert _parse_iso("2026-08-07T22:05:13+00:00") == d.replace(microsecond=0)


@pytest.mark.asyncio
async def test_list_runs_accepts_date_from_in_iso_with_z():
    """`toISOString()` ends in Z; 3.10's `fromisoformat` rejected it and the History
    table never loaded in production."""
    db = _db()
    await ObservabilityService.list_runs(
        db, _user("admin"), [], date_from="2026-08-07T22:05:13.123Z", como_admin=True,
    )
    assert "start_time >=" in _sql(db, 0)


def test_cache_key_distinguishes_users_with_the_same_workspaces():
    ana = _metrics_cache_key("metrics", _user("user", "ana"), ["ws-1"], 30)
    bia = _metrics_cache_key("metrics", _user("user", "bia"), ["ws-1"], 30)
    assert ana != bia
    # The full view is also keyed by user: the same admin with and without
    # `como_admin` (REST × MCP) cannot share the cached response.
    assert _metrics_cache_key("metrics", _user("admin", "a"), [], 30, como_admin=True) \
        != _metrics_cache_key("metrics", _user("admin", "b"), [], 30, como_admin=True)
