# tests/unit/test_schedule_orfao_workflow_inativo.py
"""Active schedule pointing to a deactivated workflow — the "orphan schedule".

Symptom in production, repeated on every cron occurrence:

    AsyncScheduler: falha ao disparar workflow 'X': Workflow X esta desativado.

The "Ativado/Inativo" (enabled/inactive) switch in the project list sends
`PUT /workflows/{id}` with only `flag_ative` — without `definition`,
`apply_schedule_if_needed` did not even run, and the Schedule stayed active
pointing to a workflow that refuses to run. The same held for the admin override.

Two locks, tested here:
  1. `sync_schedules_with_workflow_state` aligns `Schedule.active` with the workflow.
  2. the scheduler's `_tick` does not even see schedules of inactive workflows.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.async_scheduler import AsyncScheduler
from app.core.scheduling.hooks import sync_schedules_with_workflow_state
from app.models.models import Schedule, Workflow, WorkflowGroup


# ── 1. Syncing Schedule.active with flag_ative ────────────────────────────────


def _definition(active: bool = True) -> dict:
    return {
        "nodes": [
            {
                "id": "n1",
                "type": "trigger",
                "name": "ScheduleTrigger",
                "properties": {
                    "strategy": "cron",
                    "cron_expression": "0 13 * * *",
                    "timezone": "America/Cuiaba",
                    "active": active,
                },
            }
        ]
    }


@pytest.fixture
def workflow():
    wf = MagicMock()
    wf.id_hash = "wf-1"
    wf.flag_ative = True
    wf.definition = _definition()
    return wf


@pytest.fixture
def crud(monkeypatch):
    fake = MagicMock()
    fake.schedule_crud = MagicMock(
        get_by_workflow_hash=AsyncMock(return_value=[]),
        update=AsyncMock(),
    )
    monkeypatch.setattr("app.core.scheduling.hooks.ScheduleService", lambda db: fake)
    return fake


def _schedule(active: bool = True) -> MagicMock:
    return MagicMock(job_id="job-1", active=active, next_run_at=datetime(2026, 1, 1))


async def test_deactivating_workflow_turns_off_the_schedule(workflow, crud):
    """The regression: this is where the orphan was born."""
    workflow.flag_ative = False
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule(active=True)]

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    crud.schedule_crud.update.assert_awaited_once()
    assert crud.schedule_crud.update.await_args.args[1] == {"active": False}


async def test_reactivating_turns_the_schedule_back_on_resetting_next_run_at(workflow, crud):
    """`next_run_at` stayed in the past while the workflow was turned off.

    Turning it back on without zeroing would fire the workflow at the instant of the click.
    """
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule(active=False)]

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    assert crud.schedule_crud.update.await_args.args[1] == {"active": True, "next_run_at": None}


async def test_reactivating_respects_the_disabled_node_on_the_canvas(workflow, crud):
    """What governs reactivation is the ScheduleTrigger's `active`, not the workflow.

    Blindly turning everything back on would resurrect the schedule the owner had
    turned off in the editor before deactivating the workflow.
    """
    workflow.definition = _definition(active=False)
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule(active=False)]

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    crud.schedule_crud.update.assert_not_awaited()


async def test_reactivating_without_node_on_canvas_keeps_it_off(workflow, crud):
    """Without a ScheduleTrigger in the definition there is no legitimate schedule."""
    workflow.definition = {"nodes": [{"id": "n1", "name": "Outro"}]}
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule(active=True)]

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    assert crud.schedule_crud.update.await_args.args[1] == {"active": False}


async def test_already_consistent_state_does_not_write(workflow, crud):
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule(active=True)]

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    crud.schedule_crud.update.assert_not_awaited()


async def test_workflow_without_schedule_is_no_op(workflow, crud):
    crud.schedule_crud.get_by_workflow_hash.return_value = []

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    crud.schedule_crud.update.assert_not_awaited()


# ── 2. The tick does not see schedules of a workflow that cannot run ──────────


@pytest_asyncio.fixture
async def session_factory():
    """In-memory SQLite shared between sessions (StaticPool).

    `_tick` opens its own session via `AsyncSessionLocal`; without StaticPool each
    connection would see a different empty database.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            Workflow.metadata.create_all,
            tables=[WorkflowGroup.__table__, Workflow.__table__, Schedule.__table__],
        )
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def _seed(factory, *, flag_ative=True, deleted_at=None, sch_active=True, vencido=True):
    passado = datetime(2020, 1, 1)
    async with factory() as db:
        db.add(Workflow(
            id_hash="wf-1", name="wf", workspace_id="ws-1", definition={},
            flag_ative=flag_ative, deleted_at=deleted_at,
        ))
        db.add(Schedule(
            id_hash="sch-1", workflow_hash="wf-1", strategy="cron",
            cron_expression="0 13 * * *", job_id="job-1", active=sch_active,
            next_run_at=passado if vencido else datetime.utcnow() + timedelta(days=1),
        ))
        await db.commit()


async def _triggered(factory, monkeypatch) -> list[str]:
    """Runs a tick and returns the job_ids that reached `_process_schedule`."""
    vistos: list[str] = []
    sched = AsyncScheduler()
    monkeypatch.setattr("app.core.async_scheduler.AsyncSessionLocal", factory)
    monkeypatch.setattr(
        sched, "_process_schedule",
        AsyncMock(side_effect=lambda s, now: vistos.append(s.job_id)),
    )
    await sched._tick()
    return vistos


async def test_tick_processes_schedule_of_active_workflow(session_factory, monkeypatch):
    await _seed(session_factory)

    assert await _triggered(session_factory, monkeypatch) == ["job-1"]


async def test_tick_respects_the_limit_and_orders_by_next_run_at(session_factory, monkeypatch):
    """The tick drains in batches: with the ceiling at 2, only the 2 most overdue
    (lowest next_run_at) reach _process_schedule; the 3rd waits for the next cycle.
    The schedules are inserted OUT of time order on purpose, to tell the
    ORDER BY apart from a plain scan by rowid."""
    monkeypatch.setattr("app.core.async_scheduler.TICK_MAX_SCHEDULES", 2)

    base = datetime(2020, 1, 1)
    async with session_factory() as db:
        db.add(Workflow(id_hash="wf-1", name="wf", workspace_id="ws-1", definition={}))
        for i, (job, atraso) in enumerate([("job-c", 2), ("job-b", 1), ("job-a", 0)]):
            db.add(Schedule(
                id_hash=f"sch-{i}", workflow_hash="wf-1", strategy="cron",
                cron_expression="0 13 * * *", job_id=job, active=True,
                next_run_at=base + timedelta(minutes=atraso),
            ))
        await db.commit()

    assert await _triggered(session_factory, monkeypatch) == ["job-a", "job-b"]


async def test_tick_ignores_schedule_of_deactivated_workflow(session_factory, monkeypatch):
    """The final lock: even with the orphan already in the database, the scheduler does not touch it."""
    await _seed(session_factory, flag_ative=False)

    assert await _triggered(session_factory, monkeypatch) == []


async def test_tick_ignores_schedule_of_soft_deleted_workflow(session_factory, monkeypatch):
    await _seed(session_factory, deleted_at=datetime(2026, 1, 1))

    assert await _triggered(session_factory, monkeypatch) == []


async def test_tick_ignores_disabled_schedule(session_factory, monkeypatch):
    await _seed(session_factory, sch_active=False)

    assert await _triggered(session_factory, monkeypatch) == []


async def test_tick_processes_new_schedule_without_next_run_at(session_factory, monkeypatch):
    """`next_run_at IS NULL` is the signal for "compute the first run".

    The new JOIN must not have left these schedules stuck forever.
    """
    async with session_factory() as db:
        db.add(Workflow(id_hash="wf-1", name="wf", workspace_id="ws-1", definition={}))
        db.add(Schedule(
            id_hash="sch-1", workflow_hash="wf-1", strategy="cron",
            cron_expression="0 13 * * *", job_id="job-1", active=True, next_run_at=None,
        ))
        await db.commit()

    assert await _triggered(session_factory, monkeypatch) == ["job-1"]
