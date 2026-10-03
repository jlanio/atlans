"""
Schedule IDOR: cross-tenant delete/update.

Regression: schedules are resolved by a global `job_id`. The route only authorizes
the workflow in the path (the `workflow_com_papel` dependency), but the service did
not confirm the schedule belongs to it. A user pointed a DELETE/PUT of their own
workflow at another tenant's `job_id` and deleted/reconfigured someone else's schedule.

Fix: the methods receive `owner_workflow_hash` and require
`sch.workflow_hash == owner`, responding 404 (not 403) so as not to reveal
existence.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions import ScheduleNotFoundError
from app.services.schedule_service import ScheduleService


def _service_with(sch):
    svc = ScheduleService.__new__(ScheduleService)  # without touching the real DB
    svc.schedule_crud = MagicMock()
    svc.schedule_crud.get = AsyncMock(return_value=sch)
    svc.schedule_crud.delete = AsyncMock()
    svc.schedule_crud.update_by_id = AsyncMock(return_value=sch)
    return svc


def _schedule(job_id="job-1", workflow_hash="wf-do-dono"):
    return MagicMock(job_id=job_id, workflow_hash=workflow_hash)


# ── DELETE ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_de_outro_workflow_recusado():
    svc = _service_with(_schedule(workflow_hash="wf-DO-DONO"))

    with pytest.raises(ScheduleNotFoundError):
        await svc.delete_schedule("job-1", owner_workflow_hash="wf-do-atacante")

    svc.schedule_crud.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_do_proprio_workflow_permitido():
    svc = _service_with(_schedule(workflow_hash="wf-do-dono"))

    await svc.delete_schedule("job-1", owner_workflow_hash="wf-do-dono")

    svc.schedule_crud.delete.assert_awaited_once()


# ── UPDATE ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_de_outro_workflow_recusado():
    svc = _service_with(_schedule(workflow_hash="wf-do-dono"))
    payload = MagicMock()
    payload.dict = MagicMock(return_value={"active": False})

    with pytest.raises(ScheduleNotFoundError):
        await svc.update_schedule("job-1", payload, owner_workflow_hash="wf-do-atacante")

    svc.schedule_crud.update_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_do_proprio_workflow_permitido():
    svc = _service_with(_schedule(workflow_hash="wf-do-dono"))
    payload = MagicMock()
    payload.dict = MagicMock(return_value={"active": False})

    await svc.update_schedule("job-1", payload, owner_workflow_hash="wf-do-dono")

    svc.schedule_crud.update_by_id.assert_awaited_once()


# ── O dono e obrigatorio ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_omitir_o_dono_quebra_na_chamada():
    """It was optional, and with `None` the ownership check was SKIPPED.

    The IDOR defense was off by default — it took only a new caller (a tool of
    the MCP server, a script) forgetting the parameter to delete another
    tenant's schedule. No real caller used the shortcut: both routes always
    passed the owner. Now forgetting it is a call error.

    The `match` matters: without it any TypeError would satisfy the test.
    """
    svc = _service_with(_schedule())

    with pytest.raises(TypeError, match="owner_workflow_hash"):
        await svc.delete_schedule("job-1")


@pytest.mark.asyncio
@pytest.mark.parametrize("metodo", ["delete", "update"])
async def test_dono_None_explicito_falha_fechado(metodo):
    """The case the mandatory signature does NOT cover — and it is the dangerous one.

    Making the parameter mandatory catches whoever OMITS it. It does not catch
    whoever passes a variable that happens to be `None`, and that is how the
    defect would show up in a real caller. With the old shortcut
    (`owner_workflow_hash is not None and ...`) that SKIPPED the ownership check
    and deleted someone else's schedule; today `None` matches no `workflow_hash`
    and the refusal is a 404.

    Without this test, restoring the old shortcut while keeping the parameter
    mandatory passes the whole file — verified by mutation.
    """
    svc = _service_with(_schedule(workflow_hash="wf-do-dono"))

    with pytest.raises(ScheduleNotFoundError):
        if metodo == "delete":
            await svc.delete_schedule("job-1", owner_workflow_hash=None)
        else:
            payload = MagicMock()
            payload.dict = MagicMock(return_value={"active": False})
            await svc.update_schedule("job-1", payload, owner_workflow_hash=None)

    svc.schedule_crud.delete.assert_not_awaited()
    svc.schedule_crud.update_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_inexistente_404():
    svc = _service_with(None)

    with pytest.raises(ScheduleNotFoundError):
        await svc.delete_schedule("nao-existe", owner_workflow_hash="wf-x")
