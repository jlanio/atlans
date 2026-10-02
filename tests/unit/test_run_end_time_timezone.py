# tests/unit/test_run_end_time_timezone.py
"""`end_time` do run precisa chegar ao banco com fuso explícito.

O produtor usava `utcnow().isoformat()`, que gera string SEM offset. O consumer
fazia fromisoformat e entregava um datetime naive para WorkflowRun.end_time, que
e timestamptz: o Postgres assumia o fuso da sessao (TZ=America/Cuiaba nos
containers) e gravava o fim 4h no futuro. Toda execucao aparecia com ~4h de
duracao quando a UI subtraia end_time - start_time.
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


async def test_end_time_com_offset_e_preservado():
    run, db = MagicMock(), MagicMock(commit=AsyncMock())

    await _update_run_status(db, run, _payload("2026-08-04T17:01:34+00:00"))

    assert run.end_time == datetime(2026, 8, 4, 17, 1, 34, tzinfo=timezone.utc)


async def test_end_time_naive_e_assumido_como_utc():
    """Payload antigo na fila não pode virar 4h de deslocamento no banco."""
    run, db = MagicMock(), MagicMock(commit=AsyncMock())

    await _update_run_status(db, run, _payload("2026-08-04T17:01:34"))

    assert run.end_time.tzinfo is not None
    assert run.end_time == datetime(2026, 8, 4, 17, 1, 34, tzinfo=timezone.utc)


async def test_end_time_em_outro_offset_e_convertido_corretamente():
    run, db = MagicMock(), MagicMock(commit=AsyncMock())

    await _update_run_status(db, run, _payload("2026-08-04T13:01:34-04:00"))

    assert run.end_time.astimezone(timezone.utc) == datetime(
        2026, 8, 4, 17, 1, 34, tzinfo=timezone.utc
    )
