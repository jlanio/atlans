# tests/unit/test_schedule_religar_zera_proxima.py
"""Turning a paused schedule back on ZEROES `next_run_at`.

The bug: while the schedule was paused, `next_run_at` stayed stuck at a past
time. On turning it back on (`active=true`) without zeroing, `_process_schedule`
sees `now >= next_run_at` and fires the workflow right away — an invisible side
effect of flipping the switch. The fix lives in `ScheduleService.update_schedule`,
on the path that the REST route (`PUT /workflows/{id}/schedules/{job}`) and the
MCP tool `update_schedule` share.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.models import Schedule, Workflow
from app.schemas.schedule import ScheduleUpdate
from app.services.schedule_service import ScheduleService, activation_fields

WF = "wf-1"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Workflow.metadata.create_all,
            tables=[Workflow.__table__, Schedule.__table__],
        )
    async with AsyncSession(engine) as sessao:
        yield sessao
    await engine.dispose()


async def _seed(db, *, active, next_run_at):
    job_id = f"job-{uuid4()}"
    db.add(Schedule(
        workflow_hash=WF, strategy="cron", cron_expression="0 6 * * *",
        timezone="America/Cuiaba", active=active, next_run_at=next_run_at,
        job_id=job_id, workspace_id="ws-1",
    ))
    await db.commit()
    return job_id


PAST = datetime(2020, 1, 1, 6, 0)  # long before now, naive (as the database stores it)


@pytest.mark.asyncio
async def test_resuming_paused_resets_next_run_at(db):
    job = await _seed(db, active=False, next_run_at=PAST)
    atualizado = await ScheduleService(db).update_schedule(
        job, ScheduleUpdate(active=True), owner_workflow_hash=WF,
    )
    assert atualizado.active is True
    # The point: the time stuck in the past does NOT survive reactivation.
    assert atualizado.next_run_at is None


@pytest.mark.asyncio
async def test_changing_the_time_while_active_resets_next_run_at(db):
    """Already active, but the TIME changed: the stored `next_run_at` was computed
    from the OLD cron, so keeping it would make the next occurrence fire at the old
    time once. Zeroing forces `_process_schedule` to recompute from the new cron
    (and `None` does not fire right away — it recomputes the next FUTURE occurrence)."""
    futuro = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
    job = await _seed(db, active=True, next_run_at=futuro)
    atualizado = await ScheduleService(db).update_schedule(
        job, ScheduleUpdate(active=True, cron_expression="30 7 * * *"), owner_workflow_hash=WF,
    )
    assert atualizado.active is True
    assert atualizado.next_run_at is None


@pytest.mark.asyncio
async def test_reediting_active_without_changing_the_time_does_not_reset(db):
    """Already active and the time did NOT change (re-saving the same cron): the
    computed next occurrence is preserved — only a real timing change, or the
    paused→active transition, zeroes it."""
    futuro = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
    job = await _seed(db, active=True, next_run_at=futuro)
    atualizado = await ScheduleService(db).update_schedule(
        # Same cron that `_seed` stores ("0 6 * * *").
        job, ScheduleUpdate(active=True, cron_expression="0 6 * * *"), owner_workflow_hash=WF,
    )
    assert atualizado.active is True
    assert atualizado.next_run_at == futuro


@pytest.mark.asyncio
async def test_pausing_does_not_touch_next_run_at(db):
    """Desligar preserva o `next_run_at` (nada a recalcular ao pausar)."""
    job = await _seed(db, active=True, next_run_at=PAST)
    atualizado = await ScheduleService(db).update_schedule(
        job, ScheduleUpdate(active=False), owner_workflow_hash=WF,
    )
    assert atualizado.active is False
    assert atualizado.next_run_at == PAST


def test_activation_fields_are_the_canonical_source():
    """The semantics the hook and update_schedule share, in a single place."""
    assert activation_fields(True) == {"active": True, "next_run_at": None}
    assert activation_fields(False) == {"active": False}
