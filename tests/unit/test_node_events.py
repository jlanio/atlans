"""
Contract of the node execution events (flow.executor.events).

The frontend's run panel depends on `kind` (origin: lifecycle/stdout/
debug) and `level` (severity) being fields of their OWN, not inferred from `status`.
While everything lived in `status`, the UI had to filter by negation ("everything
that isn't an error or a print") and couldn't tell stdout from lifecycle.

The per-node error category is what lets the panel say "fix the input"
instead of just dumping the traceback.
"""
from unittest.mock import MagicMock

import pytest

from flow.executor import events as node_events
from flow.utils.publisher.events import publish_stdout


NODE_DEFS = {"n1": {"name": "Ler CSV", "type": "action"}}


def _publisher():
    return MagicMock(publish_event=MagicMock())


def _kwargs(pub):
    """Normaliza a chamada em kwargs — os helpers misturam posicional e nomeado."""
    args, kwargs = pub.publish_event.call_args
    names = ["run_id", "node", "status", "timestamp", "duration_ms", "error", "extra"]
    merged = dict(zip(names, args))
    merged.update(kwargs)
    return merged


def test_started_e_lifecycle_info():
    pub = _publisher()
    node_events.publish_started(pub, "run-1", "n1", NODE_DEFS)
    call = _kwargs(pub)
    assert call["kind"] == "lifecycle"
    assert call["level"] == "info"
    assert call["status"] == "started"
    assert call["extra"]["node_name"] == "Ler CSV"


def test_completed_without_drift_is_info():
    pub = _publisher()
    node_events.publish_completed(pub, "run-1", "n1", NODE_DEFS, "completed", 12.5, output_keys=["out"])
    call = _kwargs(pub)
    assert call["kind"] == "lifecycle"
    assert call["level"] == "info"
    assert call["extra"]["output_keys"] == ["out"]
    assert "error_category" not in call["extra"]


def test_schema_drift_raises_to_warn():
    """Drift is not a failure, but it isn't routine either — the panel highlights it in amber."""
    pub = _publisher()
    node_events.publish_completed(
        pub, "run-1", "n1", NODE_DEFS, "completed", 3.0,
        schema_drift={"missing": ["geometry"], "extra": []},
    )
    call = _kwargs(pub)
    assert call["level"] == "warn"
    assert call["extra"]["schema_drift"]["missing"] == ["geometry"]


@pytest.mark.parametrize("exc, category, retryable", [
    (ValueError("coluna ausente"), "user", False),
    (TimeoutError(), "timeout", True),
    (ConnectionError(), "transient", True),
    (MemoryError(), "resource", False),
])
def test_failure_publishes_category_and_retryable(exc, category, retryable):
    pub = _publisher()
    node_events.publish_completed(
        pub, "run-1", "n1", NODE_DEFS, "failed", 8.0,
        error=str(exc), traceback_str="Traceback…", exception=exc,
    )
    call = _kwargs(pub)
    assert call["level"] == "error"
    assert call["extra"]["error_category"] == category
    assert call["extra"]["retryable"] is retryable
    # The traceback ALWAYS goes in the failure event — the UI decides when to show it,
    # and now shows it by default (before, it required debug mode, which has to be
    # turned on before executing and so was never on when it was needed).
    assert call["extra"]["traceback"] == "Traceback…"


def test_debug_has_its_own_kind():
    pub = _publisher()
    node_events.publish_debug(pub, "run-1", "n1", NODE_DEFS, {"a": 1}, {"b": 2})
    call = _kwargs(pub)
    assert call["kind"] == "debug"
    assert call["status"] == "debug"
    assert "debug_output" in call["extra"]


def test_stdout_has_its_own_kind():
    """stdout travels in BATCHES and `lines` is the ONLY source of truth.

    One event per print() line overflowed the executor's 500-slot queue
    (shared by all jobs and by GeoSync) and the server's rate limit.
    And `extra['message']` no longer exists: publishing the same text twice
    doubled the payload and a batch of 200 long lines exceeded the 64 KB of
    `NODE_EVENT_BYTES_CEILING`, making the sender reduce the event to the control
    fields — without `extra` — and the panel lose the 200 lines at once.
    """
    pub = _publisher()
    publish_stdout(pub, "run-1", "n1", ["processando 1200 feições", "pronto"])
    call = _kwargs(pub)
    assert call["kind"] == "stdout"
    assert call["level"] == "info"
    assert call["extra"]["lines"] == ["processando 1200 feições", "pronto"]
    assert "message" not in call["extra"], "texto duplicado estoura o teto de 64 KB"


def test_stdout_never_brings_down_the_node():
    """A user's print() must not break the execution if the publisher fails."""
    pub = MagicMock(publish_event=MagicMock(side_effect=RuntimeError("redis fora")))
    publish_stdout(pub, "run-1", "n1", ["texto"])  # must not raise
    publish_stdout(None, "run-1", "n1", ["texto"])
    publish_stdout(pub, "", "n1", ["texto"])
    publish_stdout(pub, "run-1", "n1", [])  # an empty batch doesn't become an event
