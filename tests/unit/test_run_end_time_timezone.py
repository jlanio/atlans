# tests/unit/test_run_end_time_timezone.py
"""The run's `end_time` must reach the database with an explicit time zone.

The producer used `utcnow().isoformat()`, which yields a string WITHOUT an offset.
The consumer did fromisoformat and handed a naive datetime to WorkflowRun.end_time,
which is timestamptz: Postgres assumed the session time zone (TZ=America/Cuiaba in
the containers) and stored the end 4h in the future. Every run showed a duration
of ~4h when the UI computed end_time - start_time.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.core.run_result_consumer import _update_run_status


def _payload(end_time: str) -> dict:
    return {
        "task_id": "run-1",
        "status": "success",
        "error_message": None,
        "stats": {},
        "end_time": end_time,
        "duration_seconds": 42.0,
    }


async def test_end_time_with_offset_is_preserved():
    run, db = MagicMock(), MagicMock(commit=AsyncMock())

    await _update_run_status(db, run, _payload("2026-08-04T17:01:34+00:00"))

    assert run.end_time == datetime(2026, 8, 4, 17, 1, 34, tzinfo=timezone.utc)


async def test_naive_end_time_is_assumed_utc():
    """An old payload in the queue must not turn into a 4h offset in the database."""
    run, db = MagicMock(), MagicMock(commit=AsyncMock())

    await _update_run_status(db, run, _payload("2026-08-04T17:01:34"))

    assert run.end_time.tzinfo is not None
    assert run.end_time == datetime(2026, 8, 4, 17, 1, 34, tzinfo=timezone.utc)


async def test_end_time_in_another_offset_is_converted_correctly():
    run, db = MagicMock(), MagicMock(commit=AsyncMock())

    await _update_run_status(db, run, _payload("2026-08-04T13:01:34-04:00"))

    assert run.end_time.astimezone(timezone.utc) == datetime(
        2026, 8, 4, 17, 1, 34, tzinfo=timezone.utc
    )
