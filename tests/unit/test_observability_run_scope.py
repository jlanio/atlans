# tests/unit/test_observability_run_scope.py
"""Access scope for the run history.

Observability authorized runs by `Workflow.workspace_id` — the workflow's
CURRENT workspace. With the route that moves a workflow between workspaces this
becomes a leak in both directions: the members of the destination workspace
would start seeing all the history produced at the origin (error_message,
node_stats, executor host), and those who only have access to the origin would
lose their view of it.

`WorkflowRun.workspace_id` is written at dispatch and never changes — it is the
correct historical data. It is also the criterion the logs WebSocket has always
used and the one artifacts already use.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.models import WorkflowRun
from app.services.observability_service import ObservabilityService, _run_filter


def _user(role="user"):
    u = MagicMock()
    u.role = role
    return u


# ── _run_filter ──────────────────────────────────────────────────────────────

def test_filter_uses_the_run_workspace_not_the_workflow_one():
    filtros = _run_filter(_user(), ["ws-1"])

    sql = str(filtros[0])
    assert "workflow_runs.workspace_id" in sql
    # The old subquery on workflows must not come back: it followed the workflow
    # to the new workspace, taking the history along.
    assert "workflows" not in sql


def test_filter_has_no_null_workspace_escape():
    """The `OR workspace_id IS NULL` must not come back.

    It existed to preserve legacy history, but the price was handing that
    history — error_message, node_stats, executor host — to ANY authenticated
    user, from any tenant. Migration 20260828_0001 assigned the old runs to
    the right workspace and made the column NOT NULL, so there is no more
    legacy to accommodate.
    """
    sql = str(_run_filter(_user(), ["ws-1"])[0])

    assert "IS NULL" not in sql.upper()


def test_workflow_filter_also_has_no_null_escape():
    """Same regression, on the `workflows` table side (_wf_filter)."""
    from app.services.observability_service import _wf_filter

    sql = str(_wf_filter(_user(), ["ws-1"])[0])

    assert "IS NULL" not in sql.upper()
    assert "workflows.workspace_id" in sql


def test_admin_gets_no_filter_when_the_caller_asks_for_the_full_view():
    """The admin bypass is no longer inferred from `user.role` inside the service:
    the caller says `como_admin=True` (the REST router does that for a global
    admin); without the kwarg, an admin gets the same slice as a member."""
    assert _run_filter(_user("admin"), ["ws-1"], como_admin=True) == []
    assert _run_filter(_user("admin"), ["ws-1"]) != []


# ── get_run_detail ───────────────────────────────────────────────────────────

def _db_with_run(run):
    resultado = MagicMock()
    resultado.scalar_one_or_none.return_value = run
    return MagicMock(execute=AsyncMock(return_value=resultado))


def _run(workspace_id):
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
    r.host = "executor:abc"
    r.node_stats = {}
    r.exit_code = 0
    return r


def _where(db, chamada=0):
    """Only the WHERE of the executed query — the SELECT list also mentions
    `workspace_id`, and looking at the whole SQL would give a false positive."""
    return str(db.execute.await_args_list[chamada].args[0]).split("WHERE", 1)[1]


@pytest.mark.asyncio
async def test_run_from_another_workspace_is_not_accessible():
    """Move scenario: the workflow went to ws-destino, but this run happened
    in ws-origem and does not belong to someone who only reaches the destination.

    The slice goes into the query itself, via `_run_filter` — the same rule as
    the listing and the metrics. That is why the test checks the filter in the
    SQL and not just the return value: with the double returning any row, a
    check in Python would pass even if the query had stopped filtering.
    """
    from app.core.exceptions import RunNotFoundError

    db = _db_with_run(None)   # the row does not come back because the WHERE excluded it

    with pytest.raises(RunNotFoundError):
        await ObservabilityService.get_run_detail(db, "run-1", _user(), ["ws-destino"])

    sql = _where(db)
    assert "workflow_runs.workspace_id IN" in sql
    assert "workflow_runs.workspace_id IS NULL" not in sql


@pytest.mark.asyncio
async def test_run_from_own_workspace_is_accessible():
    db = _db_with_run(_run("ws-origem"))

    detalhe = await ObservabilityService.get_run_detail(db, "run-1", _user(), ["ws-origem"])

    assert detalhe["run_id"] == "run-1"




@pytest.mark.asyncio
async def test_admin_accesses_run_from_any_workspace():
    db = _db_with_run(_run("ws-origem"))

    detalhe = await ObservabilityService.get_run_detail(db, "run-1", _user("admin"), [], como_admin=True)

    assert detalhe["run_id"] == "run-1"
    # With `como_admin=True`, `_run_filter` returns an empty list: no slicing by workspace.
    assert "workspace_id" not in _where(db)
