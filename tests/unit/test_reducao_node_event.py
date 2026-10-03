# tests/unit/test_reducao_node_event.py
"""Reducing a node_event above the ceiling: a single rule on both ends of the wire.

The executor and the server each had their own copy, with different rules. The
executor (before sending) kept `duration_ms` and whatever stdout lines fit, but
threw away the whole `extra`; the server (before Redis) cut only the heavy keys
of `extra` and kept `output_columns`. Since the ceiling is the same, the executor
already delivered the reduced event and the server's rule never ran for an honest
executor: a `completed` with a large traceback reached the panel without the
editor's column suggestion.
"""
import json

from app.api.routers.executor_ws import resultados as RES
from executor.connection import _dumps_event
from flow.utils.publisher.reducao import NODE_EVENT_BYTES_CEILING as TETO
from flow.utils.publisher.reducao import PER_FIELD_CEILING, shrink_node_event


def _completed_with_large_traceback() -> tuple[dict, dict]:
    colunas = {"result": [f"col_{i}" for i in range(120)]}
    evento = {
        "type": "node_event", "run_id": "run-1", "node": "n1", "status": "completed",
        "kind": "lifecycle", "level": "info", "timestamp": 123.0, "duration_ms": 42.5,
        "error": None,
        "extra": {
            "node_name": "Join", "node_type": "join", "output_keys": ["result"],
            "output_columns": colunas,
            "traceback": "Traceback (most recent call last):\n" + "  linha\n" * 12_000,
        },
    }
    assert len(json.dumps(evento)) > TETO
    return evento, colunas


# ── The bug: the executor's reduction lost output_columns ────────────────────

def test_completed_with_large_traceback_keeps_output_columns_in_executor_reduction():
    evento, colunas = _completed_with_large_traceback()

    bruto = _dumps_event(evento)

    assert len(bruto) <= TETO
    reduzido = json.loads(bruto)
    assert (reduzido.get("extra") or {}).get("output_columns") == colunas, (
        "o executor reduziu o evento e a sugestão de coluna do editor sumiu"
    )
    assert "traceback" not in reduzido["extra"], "o peso tinha que sair"
    assert reduzido["extra"]["node_name"] == "Join"
    assert reduzido["type"] == "node_event"        # without this the server does not route
    assert reduzido["duration_ms"] == 42.5
    assert reduzido["__truncated__"] is True
    assert reduzido["__original_size__"] == len(json.dumps(evento))


def test_failed_with_huge_error_arrives_with_the_shortened_error_and_the_category():
    """The executor dropped `error` and `extra` together: the node showed as failed
    in the panel with no message at all and without saying whether a retry was worth it."""
    evento = {
        "type": "node_event", "run_id": "run-1", "node": "n1", "status": "failed",
        "kind": "lifecycle", "level": "error", "timestamp": 123.0, "duration_ms": 7.0,
        "error": "E" * 100_000,
        "extra": {"node_name": "Buffer", "error_category": "runtime", "retryable": False,
                  "traceback": "tb"},
    }

    reduzido = json.loads(_dumps_event(evento))

    assert (reduzido.get("error") or "").startswith("E" * 1_000), "a mensagem de erro sumiu"
    assert len(reduzido["error"]) < 10_000
    assert reduzido["extra"]["error_category"] == "runtime"
    assert reduzido["extra"]["retryable"] is False


# ── The server reapplies it as a defense, with the rules of both sides ───────

def test_event_reduced_by_the_executor_passes_the_server_without_losing_anything_else():
    evento, colunas = _completed_with_large_traceback()
    enviado = json.loads(_dumps_event(evento))

    publicado = json.loads(RES._serialize_node_event("ex-1", enviado))

    assert publicado == {k: v for k, v in enviado.items() if k != "type"}
    assert (publicado.get("extra") or {}).get("output_columns") == colunas


def test_server_preserves_the_stdout_lines_of_an_event_that_arrives_large():
    """Buggy executor (or too old to reduce): the server threw away the whole
    `lines` as a heavy key and the node's output tab was left empty."""
    msg = {
        "type": "node_event", "run_id": "r", "node": "n", "kind": "stdout",
        "status": "log", "level": "info", "timestamp": 1.0,
        "extra": {"lines": ["y" * 500 for _ in range(400)]},
    }

    bruto = RES._serialize_node_event("ex-1", msg)

    assert len(bruto) <= TETO
    linhas = (json.loads(bruto).get("extra") or {}).get("lines") or []
    assert linhas[:3] == ["y" * 500] * 3, "as linhas que cabiam foram jogadas fora"
    assert "nao couberam" in linhas[-1], "o corte tem que ser marcado"


def test_server_reducing_to_control_fields_preserves_duration_ms():
    msg = {
        "type": "node_event", "run_id": "r", "node": "n", "kind": "lifecycle",
        "status": "completed", "level": "info", "timestamp": 1.0, "duration_ms": 12.0,
        "blob": "x" * 100_000,
    }

    reduzido = json.loads(RES._serialize_node_event("ex-1", msg))

    assert "blob" not in reduzido
    assert reduzido.get("duration_ms") == 12.0, "o painel perdia a duração do nó"


# ── Steps of the single rule ──────────────────────────────────────────────────

def test_step_1_serializes_the_light_extra_with_the_executor_default():
    """The remaining `extra` may hold Timestamp/numpy in the executor: without its
    `default` the dumps raised TypeError and the sender recycled the event in a loop."""
    from datetime import datetime

    evento = {
        "type": "node_event", "run_id": "r", "node": "n", "status": "completed",
        "kind": "lifecycle", "timestamp": 1.0,
        "extra": {"quando": datetime(2026, 9, 30, 12, 0), "traceback": "t" * 70_000},
    }

    reduzido = json.loads(_dumps_event(evento))

    assert reduzido["extra"] == {"quando": "2026-09-30T12:00:00"}


def test_event_that_fits_comes_back_intact():
    evento = {"run_id": "r", "node": "n", "status": "completed", "extra": {"branch": "a"}}
    payload = json.dumps(evento)
    assert shrink_node_event(evento, payload) is payload


def test_step_2_still_keeps_the_stdout_lines():
    """Even without the weight the event does not fit (hostile control field): it
    falls back to the coerced control fields, and the lines that fit come back with it."""
    evento = {
        "type": "node_event", "run_id": "r", "node": {"lixo": "z" * 80_000},
        "kind": "stdout", "status": "log", "level": "info", "timestamp": 1.0,
        "extra": {"lines": [f"linha {i}" for i in range(50)]},
    }

    bruto = _dumps_event(evento)

    assert len(bruto) <= TETO
    reduzido = json.loads(bruto)
    assert len(reduzido["node"]) <= PER_FIELD_CEILING
    assert reduzido["extra"]["lines"] == [f"linha {i}" for i in range(50)]


def test_safety_net_keeps_the_type_that_routes_the_message():
    """Without `type` the server does not know what to do with the message and discards it."""
    evento = {
        "type": "node_event", "run_id": "r", "node": "n", "status": "failed",
        "kind": {"k": "x" * 1_000}, "level": {"l": "y" * 1_000}, "timestamp": 1.0,
    }
    payload = json.dumps(evento)

    bruto = shrink_node_event(evento, payload, teto=800)

    assert len(bruto) <= 800
    reduzido = json.loads(bruto)
    assert reduzido["type"] == "node_event"
    assert (reduzido["run_id"], reduzido["node"], reduzido["status"]) == ("r", "n", "failed")
    assert reduzido["__truncated__"] is True
