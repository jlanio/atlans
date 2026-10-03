"""Regression tests for the security fixes applied in option C of the audit.

Each test fails WITHOUT the corresponding fix:
 - item 10: telemetry WS for admins only (require_role=ROLE_ADMIN);
 - item 13: cancel_run authorizes by the RUN's workspace, not the workflow's;
 - item 18: the 422 handler does not echo the value submitted by the client (input/ctx).

(Item 11 — idempotency covering 'cancelled' — has its regression test in
 test_fix_ws_router.py::test_job_result_of_cancelled_run_is_ignored.)
"""
import json

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.models import Workflow, WorkflowGroup, WorkflowRun
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


# ── Item 18: 422 does not leak the client's input ───────────────────────────

async def test_422_does_not_echo_client_input_or_ctx():
    from app.core.utils.error_handlers import validation_exception_handler

    exc = RequestValidationError([
        {
            "type": "string_too_short",
            "loc": ("body", "password"),
            "msg": "String should have at least 8 characters",
            "input": "senha-secreta-do-usuario",
            "ctx": {"min_length": 8},
        },
    ])

    resp = await validation_exception_handler(None, exc)
    body = json.loads(resp.body)
    detalhes = body["details"]

    # The submitted value must NOT come back in the response — neither in 'input' nor loose.
    assert all("input" not in e for e in detalhes)
    assert all("ctx" not in e for e in detalhes)
    assert "senha-secreta-do-usuario" not in resp.body.decode()

    # But what the client needs in order to fix it is still there.
    assert detalhes[0]["loc"] == ["body", "password"]
    assert detalhes[0]["msg"]
    assert detalhes[0]["type"] == "string_too_short"


# ── Item 10: telemetria exige admin ─────────────────────────────────────────

async def test_ws_telemetry_requires_admin(monkeypatch):
    from app.api.routers import telemetry_router as TR

    capturado = {}

    async def _auth(ws, *, scope=None, require_role=None):
        capturado["require_role"] = require_role
        return None  # closes the connection and makes the handler return early

    monkeypatch.setattr(TR, "ws_authenticate", _auth)

    class _WS:
        async def close(self, *a, **k):
            pass

    await TR.websocket_telemetry(_WS())
    assert capturado["require_role"] == TR.ROLE_ADMIN


# ── Item 13: cancel_run authorizes by the RUN's workspace ───────────────────

@pytest_asyncio.fixture
async def cancellation_db():
    """A MOVED workflow: the run happened in ws-A, the workflow now belongs to ws-B.

    It is the situation that separates the two authorization criteria — and, with a
    real database instead of a double, the test exercises the real role query.
    """
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(
            Workspace.metadata.create_all,
            tables=[
                Workspace.__table__,
                WorkspaceMember.__table__,
                WorkflowGroup.__table__,
                Workflow.__table__,
                WorkflowRun.__table__,
            ],
        )
    async with AsyncSession(eng) as db:
        db.add(Workspace(id_hash="ws-A", name="antigo", owner_id="dono"))
        db.add(Workspace(id_hash="ws-B", name="atual", owner_id="dono"))
        db.add(Workflow(id_hash="wf-1", name="fluxo", workspace_id="ws-B", definition={}))
        db.add(WorkflowRun(
            task_id="run-1", workflow_hash="wf-1", workspace_id="ws-A", status="running",
        ))
        # Operator in the workflow's CURRENT workspace, nothing in the run's workspace.
        db.add(WorkspaceMember(workspace_id="ws-B", user_id="u-1", role="operator"))
        await db.commit()
        yield db
    await eng.dispose()


async def test_cancel_run_refuses_role_only_in_the_current_workspace(cancellation_db):
    """An operator in TODAY's workspace does not cancel a run that executed in ANOTHER.

    A workflow can be moved from A to B after the trigger. Whoever controls B
    must not be able to cancel a run that executed — and consumed resources — in A.
    """
    from app.services.workflow_execution_service import cancel_run

    with pytest.raises(HTTPException) as exc:
        await cancel_run(cancellation_db, "run-1", user_id="u-1")

    assert exc.value.status_code == 403


async def test_cancel_run_refuses_insufficient_role_in_the_run_workspace(cancellation_db):
    """Being a member of the run's workspace is not enough: the minimum is `operator`.

    Without this case, the 403 above could come from "not a member" and the ROLE
    requirement — which is the other half of the rule — would go uncovered.
    """
    from app.services.workflow_execution_service import cancel_run

    cancellation_db.add(
        WorkspaceMember(workspace_id="ws-A", user_id="u-3", role="viewer")
    )
    await cancellation_db.commit()

    with pytest.raises(HTTPException) as exc:
        await cancel_run(cancellation_db, "run-1", user_id="u-3")

    assert exc.value.status_code == 403


async def test_cancel_run_accepts_role_in_the_run_workspace(cancellation_db, monkeypatch):
    """The other side: with the role in the right workspace, the cancellation proceeds.

    Without this pair, the test above would pass with a refusal that refuses everyone.

    The run gets a `host` and the executor registry is doubled on purpose: without
    that the outcome would be `already_finished` — the "has no associated
    executor" branch —, and the assertion would only prove that nobody raised 403.
    This way it proves that the cancellation REALLY went out after authorization.
    """
    from app.services import workflow_execution_service as WES

    cancellation_db.add(
        WorkspaceMember(workspace_id="ws-A", user_id="u-2", role="operator")
    )
    run = (await cancellation_db.execute(
        select(WorkflowRun).where(WorkflowRun.task_id == "run-1")
    )).scalar_one()
    run.host = "executor:ag-1"
    await cancellation_db.commit()

    enviados = []

    async def _send(executor_id, payload):
        enviados.append((executor_id, payload))
        return True

    monkeypatch.setattr(WES.executor_registry, "send_json", _send)

    outcome = await WES.cancel_run(cancellation_db, "run-1", user_id="u-2")

    assert outcome == "requested"
    assert enviados == [("ag-1", {"type": "cancel", "job_id": "run-1"})]


async def test_cancel_run_requires_user_id(cancellation_db):
    """The signature is the guard: forgetting the parameter breaks at the call.

    That was the defect — `cancel_run(db, run_id)` had no authorization at all, and
    any caller outside the route crossed tenants silently.

    The `match` matters: without it, any TypeError from any source (a badly
    built double, for example) would satisfy the test.
    """
    from app.services.workflow_execution_service import cancel_run

    with pytest.raises(TypeError, match="user_id"):
        await cancel_run(cancellation_db, "run-1")


# ── Item 13b: the route passes the right identity to the service ────────────

async def test_cancel_route_passes_the_user_and_the_admin_shortcut(monkeypatch):
    """The rule lives in the service; the WIRING lives in the route, and that is what regresses.

    Moving authorization into the service left the route with no test at all: swapping
    `como_admin=...` for `como_admin=True` — that is, waiving authorization for
    everyone — passed the whole suite. This test is what makes that swap
    visible.
    """
    from app.api.routers import workflows_router as WR

    recebido = {}

    async def _cancel(db, run_id, *, user_id, como_admin=False):
        recebido.update(run_id=run_id, user_id=user_id, como_admin=como_admin)
        return "requested"

    monkeypatch.setattr(
        "app.services.workflow_execution_service.cancel_run", _cancel,
    )
    # The route is decorated with @limiter.limit, which requires a real Request before
    # the body runs. Disabling the limiter (reverted by monkeypatch) lets us call
    # the coroutine directly with request=None, which the body does not use.
    monkeypatch.setattr(WR.limiter, "enabled", False)

    class _FakeUser:
        def __init__(self, role):
            self.role = role
            self.id_hash = "u-1"

    out = await WR.cancel_run(
        request=None, run_id="run-1", db=None, current_user=_FakeUser(None),
    )
    assert out == {"run_id": "run-1", "outcome": "requested"}
    assert recebido["user_id"] == "u-1"
    assert recebido["como_admin"] is False       # non-admin does NOT skip the check

    await WR.cancel_run(
        request=None, run_id="run-1", db=None, current_user=_FakeUser(WR.ROLE_ADMIN),
    )
    assert recebido["como_admin"] is True        # admin global, sim
