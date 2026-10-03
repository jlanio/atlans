"""Success rate and percentile: a single calculation for every screen.

The spec's success rate (docs/specs/metrics-history.md §3) is completed ÷
(completed + failed): in-progress and canceled runs stay out of the
denominator. History, the per-workflow view and the per-executor view already
used this calculation; the workflow detail rewrote it as
`(total - failed) / total`, counting every in-progress or canceled run as a
success — the same workflow showed two different rates depending on the screen.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.utils.estatistica import percentil_linear, success_rate
from app.services.observability_service import ObservabilityService


def _resultado(*, linhas=None, escalar=None):
    r = MagicMock()
    r.all.return_value = list(linhas or [])
    r.scalars.return_value.all.return_value = list(linhas or [])
    r.scalar_one_or_none.return_value = escalar
    r.__iter__.return_value = iter([])
    return r


def _db(*respostas):
    """Devolve `respostas` na ordem e, esgotadas, resultados vazios."""
    fila = list(respostas)

    async def _execute(_stmt):
        return fila.pop(0) if fila else _resultado()

    db = MagicMock(execute=AsyncMock(side_effect=_execute))
    db.bind.dialect.name = "sqlite"
    return db


def _run(status: str, n: int):
    return SimpleNamespace(
        task_id=f"run-{n}", id=n, status=status,
        start_time=datetime(2026, 9, 6, 12, n, tzinfo=timezone.utc), end_time=None,
        duration_seconds=10.0 if status == "success" else None, error_message=None,
        host=None, dispatch_tier=None, workflow_hash="wf-1", workspace_id="ws-1",
        trigger_source="manual", triggered_by=None, error_category=None,
        schedule_id=None, retry_count=0,
    )


@pytest.mark.asyncio
async def test_workflow_detail_uses_the_rate_of_the_other_screens():
    runs = [_run(s, i) for i, s in enumerate(["success", "success", "failed", "running", "cancelled"])]
    db = _db(_resultado(escalar="Bacia"), _resultado(linhas=runs))

    m = await ObservabilityService.get_workflow_metrics(db, "wf-1", MagicMock(role="user"), ["ws-1"])

    assert (m["total_runs"], m["failed_runs"]) == (5, 1)
    # 2 / (2 + 1). The old calculation gave (5 - 1) / 5 = 0.8: the in-progress
    # run and the canceled one counted as successes.
    assert m["success_rate"] == 0.6667


@pytest.mark.asyncio
async def test_detail_with_only_in_progress_runs_does_not_show_100_percent():
    runs = [_run("running", 0), _run("pending", 1)]
    db = _db(_resultado(escalar="Bacia"), _resultado(linhas=runs))

    m = await ObservabilityService.get_workflow_metrics(db, "wf-1", MagicMock(role="user"), ["ws-1"])

    assert m["success_rate"] == 0.0     # no denominator, as on the other screens (before: 1.0)


# ── The single pieces ────────────────────────────────────────────────────────

def test_success_rate_only_looks_at_completed_and_failed():
    assert success_rate(8, 2) == 0.8
    assert success_rate(2, 1) == 0.6667          # 4 decimal places, as the screen receives it
    assert success_rate(0, 0) == 0.0             # no denominator does not blow up


def test_linear_percentile_without_values_is_absence_not_zero():
    """History shows "—" with no completed run; whoever wants zero (the cost
    per plan) decides that on their own screen."""
    assert percentil_linear([], 0.5) is None
    assert percentil_linear([1, 2, 3, 4, 5], 0.95) == 4.8
