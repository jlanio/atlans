# tests/unit/test_observability_dispatch_tier.py
"""`dispatch_tier` sai na serialização do run (nulo em runs antigos)."""
from unittest.mock import MagicMock

from app.services.observability_service import _serialize_run


def _run(**over):
    r = MagicMock()
    r.task_id = "t-1"; r.id = 1; r.status = "success"
    r.start_time = None; r.end_time = None; r.duration_seconds = None
    r.error_message = None; r.host = "executor:abcdef12345"; r.workflow_hash = "wf-1"
    r.retry_count = 0; r.node_stats = {}
    for k, v in over.items():
        setattr(r, k, v)
    return r


def test_serializa_dispatch_tier():
    out = _serialize_run(_run(dispatch_tier="pool"), agent_names={"abcdef12345": "pool-a"})
    assert out["dispatch_tier"] == "pool"
    assert out["agent_host"] == "pool-a@12345"


def test_run_antigo_sem_tier():
    r = _run(); del r.dispatch_tier
    r.dispatch_tier = None
    assert _serialize_run(r)["dispatch_tier"] is None
