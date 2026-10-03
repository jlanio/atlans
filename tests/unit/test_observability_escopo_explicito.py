# tests/unit/test_observability_escopo_explicito.py
"""Explicit scope in observability (docs/specs/mcp-server.md §6.12).

The observability services inferred the full view from the `User` object
itself (`role == "admin"`). For REST this was indistinguishable from an edge
rule; for the MCP server it is a hole: an admin PAT restricted to one
workspace would cross the token's scope just because the `User` carries the role.

Now the full view is an argument — `como_admin` — that only the edge that
confirmed the role turns on (the REST router, via `e_admin_global`). These
tests pin down the four sides of that:

- an admin `User` WITHOUT `como_admin` gets the workspace filter, and the
  filter goes into the query itself (the SQL is inspected, as in
  `test_observability_run_scope.py`);
- with `como_admin=True` there is no filter;
- `_serialize_run` errs on the side of not leaking: without `admin=True`, no
  `workflow_active`/`owner_username`;
- the cache key tells the full view apart from the member view and includes the user;
- the router passes `como_admin=True` only when the user is a global admin.
"""
from __future__ import annotations

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import RunNotFoundError, WorkspaceAccessDeniedError
from app.models.models import WorkflowRun
from app.services import observability_service as osvc
from app.services.observability import escopo as scope_mod
from app.services.observability_service import (
    ObservabilityService,
    _now_block,
    _executores_do_escopo,
    _metrics_cache_key,
    _resolve_scope,
    _run_filter,
    _serialize_run,
    _wf_filter,
    e_admin_global,
)


# ── Test doubles ─────────────────────────────────────────────────────────────

def _user(role="admin", id_hash="usr-1"):
    u = MagicMock()
    u.role = role
    u.id_hash = id_hash
    return u


def _resultado(*, linha=None, linhas=None, escalar=None):
    r = MagicMock()
    r.one.return_value = linha if linha is not None else SimpleNamespace(running=0, pending=0)
    r.all.return_value = list(linhas or [])
    r.scalar_one_or_none.return_value = escalar
    r.scalar.return_value = escalar
    return r


def _db(*respostas):
    """Session double: returns `respostas` in order and, once exhausted, empty
    results."""
    fila = list(respostas)

    async def _execute(stmt):
        return fila.pop(0) if fila else _resultado()

    db = MagicMock(execute=AsyncMock(side_effect=_execute))
    db.bind.dialect.name = "sqlite"
    return db


def _where(db, chamada=0) -> str:
    """Only the WHERE of the executed query — the SELECT list also mentions
    `workspace_id`, and looking at the whole SQL would give a false positive.
    With no filter at all the query has no WHERE, and that counts as "empty"."""
    partes = str(db.execute.await_args_list[chamada].args[0]).split("WHERE", 1)
    return partes[1] if len(partes) > 1 else ""


def _run(workspace_id="ws-origem"):
    r = MagicMock(spec=WorkflowRun)
    r.workspace_id = workspace_id
    r.workflow_hash = "wf-1"
    r.task_id = "run-1"
    r.id = 1
    r.status = "success"
    r.start_time = None
    r.end_time = None
    r.duration_seconds = 1.0
    r.error_message = None
    r.host = None
    r.node_stats = {}
    return r


# ── e_admin_global ───────────────────────────────────────────────────────────

def test_is_global_admin_reads_the_role():
    assert e_admin_global(_user("admin")) is True
    assert e_admin_global(_user("user")) is False
    assert e_admin_global(SimpleNamespace()) is False


# ── Filters: the User's role is not enough ───────────────────────────────────

def test_admin_without_como_admin_gets_the_workspace_filter():
    """The raw admin `User` is what MCP hands to the service; without `como_admin`
    it must be treated as a member of the workspaces in scope."""
    run_f = _run_filter(_user("admin"), ["ws-1"])
    wf_f = _wf_filter(_user("admin"), ["ws-1"])

    assert len(run_f) == 1 and "workflow_runs.workspace_id IN" in str(run_f[0])
    assert len(wf_f) == 1 and "workflows.workspace_id IN" in str(wf_f[0])


def test_with_como_admin_there_is_no_filter_even_for_regular_user():
    """The argument rules, not the role: whoever calls with `como_admin=True` has
    already confirmed the role at the edge."""
    assert _run_filter(_user("admin"), ["ws-1"], como_admin=True) == []
    assert _wf_filter(_user("admin"), ["ws-1"], como_admin=True) == []
    # Symmetrically, the service does not "downgrade" based on the object's role.
    assert _run_filter(_user("user"), ["ws-1"], como_admin=True) == []


def test_como_admin_is_keyword_only():
    with pytest.raises(TypeError):
        _run_filter(_user("admin"), ["ws-1"], True)  # type: ignore[misc]


async def test_resolve_scope_refuses_out_of_scope_workspace_for_raw_admin():
    """Before, the admin filtered any workspace without querying the database; now
    that requires `como_admin=True`. Without it, a `workspace_id` outside the list
    is the same 403 any member gets."""
    with pytest.raises(WorkspaceAccessDeniedError):
        await _resolve_scope(_db(), _user("admin"), ["ws-1"], workspace_id="ws-2")

    db = _db()
    run_f, wf_f = await _resolve_scope(
        db, _user("admin"), ["ws-1"], workspace_id="ws-2", como_admin=True,
    )
    assert db.execute.await_count == 0
    assert "workflow_runs.workspace_id = " in str(run_f[0])
    assert "workflows.workspace_id = " in str(wf_f[0])


async def test_run_detail_filters_by_workspace_for_admin_without_como_admin():
    """The slice goes into the query itself: with the double returning any row,
    a check in Python would pass even if the WHERE had stopped filtering."""
    db = _db(_resultado(escalar=None))

    with pytest.raises(RunNotFoundError):
        await ObservabilityService.get_run_detail(db, "run-1", _user("admin"), ["ws-destino"])

    assert "workflow_runs.workspace_id IN" in _where(db)


async def test_run_detail_with_como_admin_does_not_filter():
    db = _db(_resultado(escalar=_run()))

    detalhe = await ObservabilityService.get_run_detail(
        db, "run-1", _user("admin"), [], como_admin=True,
    )

    assert detalhe["run_id"] == "run-1"
    assert "workspace_id" not in _where(db)


async def test_run_list_filters_for_admin_without_como_admin():
    db = _db()
    await ObservabilityService.list_runs(db, _user("admin"), ["ws-1"])
    assert "workflow_runs.workspace_id IN" in _where(db)

    db = _db()
    await ObservabilityService.list_runs(db, _user("admin"), ["ws-1"], como_admin=True)
    assert "workspace_id" not in _where(db)


async def test_run_events_pass_como_admin_to_the_detail():
    """`get_run_events` reuses the detail's access check; the argument
    has to reach it, or the REST admin would lose the log of runs from
    workspaces that are not theirs."""
    with patch.object(ObservabilityService, "get_run_detail", AsyncMock(return_value={})) as detalhe, \
         patch("app.core.redis.get_redis_pool") as pool:
        pool.return_value.lrange = AsyncMock(return_value=[])
        await ObservabilityService.get_run_events(_db(), "run-1", _user("admin"), [], como_admin=True)

    assert detalhe.await_args.kwargs["como_admin"] is True


# ── Fleet and the "now" block ────────────────────────────────────────────────

async def test_raw_admin_fleet_is_the_accessible_one_not_all_active():
    """Without `como_admin`, even the admin sees only the accessible executors
    (default pool + their workspaces + assigned) — the whole fleet is not
    queried in the database."""
    acessiveis = [{"id_hash": "ex-1", "name": "a", "status": "active"}]
    db = _db()
    with patch("app.services.user_executor_service.get_user_accessible_agents",
               AsyncMock(return_value=acessiveis)) as acesso:
        frota = await _executores_do_escopo(db, _user("admin"))

    acesso.assert_awaited_once_with(db, "usr-1")
    assert [e["id_hash"] for e in frota] == ["ex-1"]
    assert db.execute.await_count == 0


async def test_fleet_with_como_admin_comes_whole_from_the_db():
    toda = [
        SimpleNamespace(id_hash="ex-1", name="a", executor_type="dedicated", is_default=False, status="active"),
        SimpleNamespace(id_hash="ex-2", name="b", executor_type="default", is_default=True, status="active"),
    ]
    db = _db(_resultado(linhas=toda))
    with patch("app.services.user_executor_service.get_user_accessible_agents",
               AsyncMock(return_value=[])) as acesso:
        frota = await _executores_do_escopo(db, _user("user"), como_admin=True)

    acesso.assert_not_awaited()
    assert [e["id_hash"] for e in frota] == ["ex-1", "ex-2"]


async def test_now_block_only_counts_late_acks_with_como_admin():
    from app.services.observability import agregados
    with patch.object(agregados, "_execucoes_presas", AsyncMock(return_value=(0, []))), \
         patch.object(agregados, "_executores_do_escopo", AsyncMock(return_value=[])), \
         patch.object(agregados, "_presenca", AsyncMock(return_value=({}, {}))), \
         patch.object(agregados, "_confirmacoes_atrasadas", AsyncMock(return_value=2)) as acks:
        cru = await _now_block(_db(), _user("admin"), [], osvc._agora_utc())
        total = await _now_block(_db(), _user("admin"), [], osvc._agora_utc(), como_admin=True)

    assert cru["overdue_acks"] is None
    assert total["overdue_acks"] == 2
    assert acks.await_count == 1


# ── _serialize_run ───────────────────────────────────────────────────────────

def _run_row():
    return SimpleNamespace(
        task_id="t-1", id=1, status="success", start_time=None, end_time=None,
        duration_seconds=1.0, error_message=None, host=None, workflow_hash="wf-1",
        triggered_by=None, workspace_id="ws-1", retry_count=0, node_stats={},
    )


def test_serialize_run_by_default_does_not_return_admin_only_fields():
    """A caller that forgets the argument errs on the side of not leaking."""
    meta = {"wf-1": {
        "workflow_name": "Integração", "workflow_active": True, "owner_username": "ana",
        "workspace_id": "ws-1", "workspace_name": "Um",
    }}

    padrao = _serialize_run(_run_row(), workflow_meta=meta)
    admin = _serialize_run(_run_row(), workflow_meta=meta, admin=True)

    assert padrao["workflow_name"] == "Integração"
    assert "workflow_active" not in padrao and "owner_username" not in padrao
    assert admin["workflow_active"] is True and admin["owner_username"] == "ana"


# ── Cache key ────────────────────────────────────────────────────────────────

def test_cache_key_distinguishes_full_view_from_member_and_includes_the_user():
    """The same admin with and without `como_admin` (REST × MCP) cannot share
    the cached response: the full view would sit 45 s in the cache and be served
    to a PAT restricted to one workspace. And the user goes into the key in both
    views — there is no longer a global "admin" bucket."""
    membro = _metrics_cache_key("metrics", _user("admin", "a"), ["ws-1"], 30)
    total = _metrics_cache_key("metrics", _user("admin", "a"), ["ws-1"], 30, como_admin=True)
    total_for_other = _metrics_cache_key("metrics", _user("admin", "b"), ["ws-1"], 30, como_admin=True)

    assert membro != total
    assert total != total_for_other
    # Deterministic for the same scope, and the object's role does not go in.
    assert total == _metrics_cache_key("metrics", _user("user", "a"), ["ws-1"], 30, como_admin=True)


def test_what_goes_into_the_key_hash_is_the_scope_and_the_user():
    """There is no longer a global "admin" bucket.

    The key itself is hexadecimal — asserting on its text proves nothing.
    What is pinned down here is the hash INPUT: `todos:<user_id>:<workspaces>`.
    """
    vistos: list[str] = []
    sha256_real = hashlib.sha256

    def _spy(dados: bytes):
        vistos.append(dados.decode())
        return sha256_real(dados)

    with patch.object(scope_mod.hashlib, "sha256", _spy):
        _metrics_cache_key("metrics", _user("admin", "a"), ["ws-2", "ws-1"], 30, como_admin=True)
        _metrics_cache_key("metrics", _user("admin", "a"), ["ws-2", "ws-1"], 30)

    assert vistos == ["todos:a:ws-1,ws-2", "membro:a:ws-1,ws-2"]


def test_cache_key_como_admin_is_keyword_only():
    with pytest.raises(TypeError):
        _metrics_cache_key("metrics", _user("admin"), [], 30, True)  # type: ignore[misc]


# ── Router: `como_admin` only for global admin ───────────────────────────────

_ROUTES = [
    ("get_metrics", "/observability/metrics", {}),
    ("get_workflows_metrics", "/observability/metrics/workflows", {}),
    ("get_workflow_metrics", "/observability/metrics/workflow/wf-1", {}),
    ("get_executor_metrics", "/observability/metrics/executores", {}),
    ("list_runs", "/observability/runs", {}),
    ("get_run_detail", "/observability/runs/run-1", {}),
    ("get_run_events", "/observability/runs/run-1/events", {}),
    ("get_runs_by_day", "/observability/runs-by-day", {"tz": "UTC"}),
]


@pytest.fixture
def api(client):
    """Client with a double `get_db`; each test picks the authenticated user."""
    from app.api.dependencies import get_current_user, get_db
    from app.main import app

    db = MagicMock()

    async def _db_dep():
        yield db

    app.dependency_overrides[get_db] = _db_dep

    def _as_user(usuario):
        async def _current_user():
            return usuario

        app.dependency_overrides[get_current_user] = _current_user
        return client

    yield _as_user
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize("metodo, caminho, params", _ROUTES)
@pytest.mark.parametrize("papel, esperado", [("admin", True), ("user", False)])
async def test_router_passes_como_admin_only_for_global_admin(api, metodo, caminho, params, papel, esperado):
    """REST stays identical — a global admin sees everything — because it is the
    ROUTER that declares the view, in all eight routes."""
    from app.api.routers import observability_router as R

    usuario = _user(papel, "usr-test-001")
    usuario.is_active = True
    cliente = api(usuario)

    with patch.object(R._svc, metodo, AsyncMock(return_value={})) as chamada:
        resp = await cliente.get(caminho, params=params)

    assert resp.status_code == 200, resp.text
    chamada.assert_awaited_once()
    assert chamada.await_args.kwargs["como_admin"] is esperado
