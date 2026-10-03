# tests/unit/test_job_executor_teto_de_stats.py
"""Steps of the 8 KB ceiling per node stat (executor/job_executor.py).

`output_columns` feeds the editor's column-name suggestion. The old cut
discarded it ENTIRELY on the first overflow — the wider the table, the more
certain the loss, exactly where the suggestion is worth the most. The tests
pin the degradation ladder: error message truncated → each column list
truncated to the first _MAX_STAT_COLUMNS_PER_PORT → columns
discarded → only the essential fields. Each step only runs if the previous one
was not enough.
"""
import json

from executor.job_executor import (
    _MAX_NODE_STAT_BYTES,
    _MAX_STAT_COLUMNS_PER_PORT,
    _MAX_STAT_ERROR_CHARS,
    _STAT_ESSENTIAL_FIELDS,
    _cap_node_stats,
    _shrink_node_stat,
)


def _size(obj) -> int:
    return len(json.dumps(obj, default=str))


def _stat_base(**extras) -> dict:
    stat = {
        "node_name": "No de Teste",
        "duration_ms": 12.5,
        "status": "completed",
        "cache_hit": False,
        "input_features": 10,
        "output_features": 10,
        "error": None,
        "started_at": "2026-01-01T00:00:00",
        "output_keys": ["result"],
    }
    stat.update(extras)
    return stat


def test_wide_columns_are_truncated_not_discarded():
    """Census table: the stat overflows from column names alone.

    The old behavior discarded output_columns entirely; now the
    first _MAX_STAT_COLUMNS_PER_PORT of EACH port survive.
    """
    colunas = [f"variavel_censitaria_{i:04d}" for i in range(200)]
    stat = _stat_base(output_columns={"result": list(colunas), "aux": list(colunas)})
    assert _size(stat) > _MAX_NODE_STAT_BYTES, "cenário precisa estourar o teto"

    reduzido = _shrink_node_stat(stat)

    assert _size(reduzido) <= _MAX_NODE_STAT_BYTES
    assert reduzido["__truncated__"] is True, "o corte usa a flag por stat existente"
    assert reduzido["output_columns"]["result"] == colunas[:_MAX_STAT_COLUMNS_PER_PORT]
    assert reduzido["output_columns"]["aux"] == colunas[:_MAX_STAT_COLUMNS_PER_PORT]
    # No marker item inside the list: each entry becomes a clickable suggestion.
    assert all(c in colunas for c in reduzido["output_columns"]["result"])
    # The executor's original stat must not be mutated by the cut.
    assert len(stat["output_columns"]["result"]) == 200


def test_huge_error_is_truncated_without_costing_the_columns():
    """Step 1: if truncating the error message is enough, the columns stay intact."""
    colunas = [f"col_{i}" for i in range(30)]
    stat = _stat_base(error="x" * 20_000, output_columns={"result": list(colunas)})
    assert _size(stat) > _MAX_NODE_STAT_BYTES

    reduzido = _shrink_node_stat(stat)

    assert _size(reduzido) <= _MAX_NODE_STAT_BYTES
    assert reduzido["error"] == "x" * _MAX_STAT_ERROR_CHARS + "…[truncado]"
    assert reduzido["output_columns"] == {"result": colunas}, "colunas não podiam cair aqui"
    assert reduzido["__truncated__"] is True


def test_columns_dropped_entirely_only_when_not_even_truncated_fit():
    """Step 3: unrelated ballast takes up almost the whole ceiling — truncating is not enough, discarding is."""
    colunas = [f"col_{i:04d}" for i in range(_MAX_STAT_COLUMNS_PER_PORT * 2)]
    stat = _stat_base(output_columns={"result": colunas})
    without_columns = dict(stat)
    without_columns.pop("output_columns")
    # Sized so that: without columns it fits (with ~200 bytes of slack for the
    # ballast key and the flag), but not even the first 50 columns (~550 bytes) fit.
    stat["lastro"] = "z" * (_MAX_NODE_STAT_BYTES - _size(without_columns) - 200)
    assert _size(stat) > _MAX_NODE_STAT_BYTES

    reduzido = _shrink_node_stat(stat)

    assert _size(reduzido) <= _MAX_NODE_STAT_BYTES
    assert "output_columns" not in reduzido
    assert reduzido["__truncated__"] is True
    # Stopped at the discard step: did not collapse to the essential fields.
    assert "lastro" in reduzido


def test_last_resort_is_still_only_essential_fields():
    """Step 4: not even the pop solves it — what remains is the minimum that draws the row in the panel."""
    stat = _stat_base(
        lastro="z" * (_MAX_NODE_STAT_BYTES * 2),
        output_columns={"result": [f"col_{i}" for i in range(120)]},
    )

    reduzido = _shrink_node_stat(stat)

    assert _size(reduzido) <= _MAX_NODE_STAT_BYTES
    assert "lastro" not in reduzido and "output_columns" not in reduzido
    assert reduzido["__truncated__"] is True
    esperados = {k for k in _STAT_ESSENTIAL_FIELDS if k in stat} | {"__truncated__"}
    assert set(reduzido) == esperados


def test_limit_node_stats_delivers_truncated_columns_to_result():
    """The real path (job_result → server) receives the degraded stat, not a pruned one."""
    colunas = [f"variavel_censitaria_{i:04d}" for i in range(200)]
    node_stats = {"n1": _stat_base(
        output_columns={"result": list(colunas), "aux": list(colunas)},
    )}
    assert _size(node_stats["n1"]) > _MAX_NODE_STAT_BYTES

    limitado = _cap_node_stats(node_stats)

    assert limitado["n1"]["output_columns"]["result"] == colunas[:_MAX_STAT_COLUMNS_PER_PORT]
    assert limitado["n1"]["__truncated__"] is True
