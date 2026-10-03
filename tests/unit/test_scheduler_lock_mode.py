# tests/unit/test_scheduler_lock_mode.py
"""
Regression of a SELF-DEADLOCK invisible to Postgres.

`_process_schedule` opens a transaction and keeps it open while
`_fire_workflow` runs ON ANOTHER connection. That trigger inserts a `WorkflowRun`
with an FK to `schedules.id` (schedule_id) — and every INSERT with an FK takes a
`FOR KEY SHARE` on the referenced row. `FOR UPDATE` conflicts with `FOR KEY
SHARE`: the trigger's connection blocks waiting for the row the outer
transaction holds, but that transaction is `await`-ing the trigger to finish.
Mutual lock — and since the outer connection sits idle-in-transaction (not
waiting on any lock at the database level), PG's deadlock detector never sees it.

`FOR NO KEY UPDATE` does NOT conflict with `FOR KEY SHARE` and keeps the
"one worker per schedule" exclusivity. The bug did not show up in CI (SQLite
ignores the clause), so this test pins the MODE in the SQL compiled for the
Postgres dialect.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql


def _session(db):
    @asynccontextmanager
    async def _ctx():
        yield db
    return _ctx


@pytest.mark.asyncio
async def test_process_schedule_locks_with_for_no_key_update_skip_locked():
    from app.core.async_scheduler import AsyncScheduler

    capturado: dict = {}

    resultado = MagicMock()
    resultado.scalar_one_or_none = MagicMock(return_value=None)  # exits early, no trigger

    db = MagicMock()

    async def _execute(stmt):
        capturado["stmt"] = stmt
        return resultado

    db.execute = _execute
    db.commit = AsyncMock()

    sched = MagicMock()
    sched.id = 1
    sched.job_id = "job-1"

    with patch("app.core.async_scheduler.AsyncSessionLocal", _session(db)):
        await AsyncScheduler()._process_schedule(sched, datetime(2026, 1, 1))

    sql = str(capturado["stmt"].compile(dialect=postgresql.dialect()))
    assert "FOR NO KEY UPDATE" in sql, sql
    assert "SKIP LOCKED" in sql, sql
    # The old mode — the one that conflicted with the run INSERT's FOR KEY SHARE.
    # ("FOR NO KEY UPDATE" does not contain the substring "FOR UPDATE".)
    assert "FOR UPDATE" not in sql, sql
    db.commit.assert_not_awaited()  # scalar_one_or_none None → nenhum commit/disparo
