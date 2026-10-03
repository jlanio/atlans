# tests/unit/test_job_executor_teto_de_stats.py
"""Steps of the 8 KB ceiling per node stat (executor/job_executor.py).

`output_columns` feeds the editor's column-name suggestion. The old cut
discarded it ENTIRELY on the first overflow — the wider the table, the more
certain the loss, exactly where the suggestion is worth the most. The tests
pin the degradation ladder: error message truncated → each column list
truncated to the first _MAX_STAT_COLUNAS_POR_PORTA → columns
discarded → only the essential fields. Each step only runs if the previous one
was not enough.
"""
import json

from executor.job_executor import (
    _MAX_NODE_STAT_BYTES,
    _MAX_STAT_COLUNAS_POR_PORTA,
    _MAX_STAT_ERROR_CHARS,
    _STAT_CAMPOS_ESSENCIAIS,
    _limitar_node_stats,
    _reduzir_stat_de_no,
)


def _tamanho(obj) -> int:
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


def test_colunas_largas_sao_truncadas_e_nao_descartadas():
    """Census table: the stat overflows from column names alone.

    The old behavior discarded output_columns entirely; now the
    first _MAX_STAT_COLUNAS_POR_PORTA of EACH port survive.
    """
    colunas = [f"variavel_censitaria_{i:04d}" for i in range(200)]
    stat = _stat_base(output_columns={"result": list(colunas), "aux": list(colunas)})
    assert _tamanho(stat) > _MAX_NODE_STAT_BYTES, "cenário precisa estourar o teto"

    reduzido = _reduzir_stat_de_no(stat)

    assert _tamanho(reduzido) <= _MAX_NODE_STAT_BYTES
    assert reduzido["__truncated__"] is True, "o corte usa a flag por stat existente"
    assert reduzido["output_columns"]["result"] == colunas[:_MAX_STAT_COLUNAS_POR_PORTA]
    assert reduzido["output_columns"]["aux"] == colunas[:_MAX_STAT_COLUNAS_POR_PORTA]
    # No marker item inside the list: each entry becomes a clickable suggestion.
    assert all(c in colunas for c in reduzido["output_columns"]["result"])
    # The executor's original stat must not be mutated by the cut.
    assert len(stat["output_columns"]["result"]) == 200


def test_erro_gigante_e_truncado_sem_custar_as_colunas():
    """Step 1: if truncating the error message is enough, the columns stay intact."""
    colunas = [f"col_{i}" for i in range(30)]
    stat = _stat_base(error="x" * 20_000, output_columns={"result": list(colunas)})
    assert _tamanho(stat) > _MAX_NODE_STAT_BYTES

    reduzido = _reduzir_stat_de_no(stat)

    assert _tamanho(reduzido) <= _MAX_NODE_STAT_BYTES
    assert reduzido["error"] == "x" * _MAX_STAT_ERROR_CHARS + "…[truncado]"
    assert reduzido["output_columns"] == {"result": colunas}, "colunas não podiam cair aqui"
    assert reduzido["__truncated__"] is True


def test_colunas_caem_por_inteiro_so_quando_nem_truncadas_cabem():
    """Step 3: unrelated ballast takes up almost the whole ceiling — truncating is not enough, discarding is."""
    colunas = [f"col_{i:04d}" for i in range(_MAX_STAT_COLUNAS_POR_PORTA * 2)]
    stat = _stat_base(output_columns={"result": colunas})
    sem_colunas = dict(stat)
    sem_colunas.pop("output_columns")
    # Sized so that: without columns it fits (with ~200 bytes of slack for the
    # ballast key and the flag), but not even the first 50 columns (~550 bytes) fit.
    stat["lastro"] = "z" * (_MAX_NODE_STAT_BYTES - _tamanho(sem_colunas) - 200)
    assert _tamanho(stat) > _MAX_NODE_STAT_BYTES

    reduzido = _reduzir_stat_de_no(stat)

    assert _tamanho(reduzido) <= _MAX_NODE_STAT_BYTES
    assert "output_columns" not in reduzido
    assert reduzido["__truncated__"] is True
    # Stopped at the discard step: did not collapse to the essential fields.
    assert "lastro" in reduzido


def test_ultimo_recurso_continua_sendo_so_os_campos_essenciais():
    """Step 4: not even the pop solves it — what remains is the minimum that draws the row in the panel."""
    stat = _stat_base(
        lastro="z" * (_MAX_NODE_STAT_BYTES * 2),
        output_columns={"result": [f"col_{i}" for i in range(120)]},
    )

    reduzido = _reduzir_stat_de_no(stat)

    assert _tamanho(reduzido) <= _MAX_NODE_STAT_BYTES
    assert "lastro" not in reduzido and "output_columns" not in reduzido
    assert reduzido["__truncated__"] is True
    esperados = {k for k in _STAT_CAMPOS_ESSENCIAIS if k in stat} | {"__truncated__"}
    assert set(reduzido) == esperados


def test_limitar_node_stats_entrega_as_colunas_truncadas_ao_resultado():
    """The real path (job_result → server) receives the degraded stat, not a pruned one."""
    colunas = [f"variavel_censitaria_{i:04d}" for i in range(200)]
    node_stats = {"n1": _stat_base(
        output_columns={"result": list(colunas), "aux": list(colunas)},
    )}
    assert _tamanho(node_stats["n1"]) > _MAX_NODE_STAT_BYTES

    limitado = _limitar_node_stats(node_stats)

    assert limitado["n1"]["output_columns"]["result"] == colunas[:_MAX_STAT_COLUNAS_POR_PORTA]
    assert limitado["n1"]["__truncated__"] is True
