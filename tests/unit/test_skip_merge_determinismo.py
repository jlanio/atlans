# tests/unit/test_skip_merge_determinismo.py
"""
Determinism of skip in merge/diamond (F2).

A merge node with a LIVE parent (outside the branch) and a SKIPPED parent (in the
branch not taken) was skipped or not depending on the ORDER in which the batch was
processed: `_propagate_skip` zeroed `pending_parents_count` and marked it skipped
without checking whether any parent had actually executed and delivered data. If
the live parent decremented the merge first and the sibling branch's skip zeroed
it last, the merge — with real data in hand — was wiped out.

Reproduces the diamond with the real executor and a real fork node (Conditional):

    TX (trigger) ─────────────────► D (merge)      live parent, independent
    TA (trigger) ──► A (Conditional) ─true─► B      branch taken
                                     └false─► C ──► D   skipped branch → merge

With 3 features and `count > 1`, A decides `branch=True`: B runs, C is skipped. D
must RUN (it received TX's data), never be skipped.
"""

import asyncio
import geopandas as gpd
from shapely.geometry import Point
from unittest.mock import MagicMock

from flow.executor.core import WorkflowExecutor


def _publisher():
    pub = MagicMock()
    pub.publish_event = MagicMock()
    return pub


def _gdf():
    return gpd.GeoDataFrame(
        {"n": list("abc")},
        geometry=[Point(i, i) for i in range(3)],
        crs="EPSG:4326",
    )


def _trigger(nid):
    # type 'trigger' makes the executor inject initial_inputs; name 'Merge' is the
    # factory lookup (strategy first returns the 1st real value as output).
    return {"id": nid, "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}}


def _merge(nid, alias=None):
    props = {"strategy": "first"}
    if alias:
        props["alias"] = alias
    return {"id": nid, "type": "control", "name": "Merge", "properties": props}


def _branch(nid):
    return {"id": nid, "type": "control", "name": "Conditional",
            "properties": {"metric": "count", "operator": ">", "compareTo": "1"}}


def _spread(source, target):
    # no from_key/to_key → spreads the parent's dict (the skipped parent spreads {}).
    return {"source": source, "target": target}


def _cond_edge(source, target, condition):
    return {"source": source, "target": target, "condition": condition}


def _rodar(ordem_nos):
    """Builds the diamond with the nodes in the GIVEN ORDER (controls the batch
    interleaving) and runs it. Returns (final_outputs, node_stats)."""
    node_por_id = {
        "TX": _trigger("TX"),
        "TA": _trigger("TA"),
        "A": _branch("A"),
        "B": _merge("B"),
        "C": _merge("C"),
        "D": _merge("D", alias="Fim"),
    }
    definition = {
        "nodes": [node_por_id[i] for i in ordem_nos],
        "edges": [
            _spread("TX", "D"),               # pai vivo independente → merge
            _spread("TA", "A"),               # feeds the fork
            _cond_edge("A", "B", True),       # ramo tomado
            _cond_edge("A", "C", False),      # branch NOT taken → skipped
            _spread("C", "D"),                # pai skipado → merge
        ],
    }
    ex = WorkflowExecutor(definition, task_id=f"f2-{'-'.join(ordem_nos)}", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"TX": {"output": _gdf()}, "TA": {"output": _gdf()}}))
    return final, ex.node_stats


def test_merge_roda_quando_pai_vivo_decrementa_antes_do_skip():
    # Order that triggers the bug: TX (live parent) is processed BEFORE A, so C's
    # skip zeroes D's pending last. Before: D skipped. Now: D runs.
    final, stats = _rodar(["TX", "TA", "A", "B", "C", "D"])
    assert stats["C"]["status"] == "skipped", "C está no ramo não tomado — deve ser skipado"
    assert stats["D"]["status"] != "skipped", "D tem pai vivo (TX) — não pode ser skipado"
    assert "D" in final and final["D"], "D rodou e produziu saída"


def test_merge_roda_independente_da_ordem_do_batch():
    # Reverse order (A/TA before TX): C's skip decrements D first, then TX zeroes
    # it. It already worked before; here it confirms the fix is symmetric.
    final, stats = _rodar(["TA", "A", "B", "C", "TX", "D"])
    assert stats["C"]["status"] == "skipped"
    assert stats["D"]["status"] != "skipped"
    assert "D" in final and final["D"]


def test_merge_com_todos_os_pais_skipados_continua_skipado():
    # Guard against over-correction: if D has NO live parent (both in the dead
    # branch), it MUST still be skipped.
    #   TA → A ─true─► B
    #             └false─► C1 ─► D
    #             └false─► C2 ─► D
    # branch=True, so C1 and C2 (false) are skipped and D (only their child) too.
    definition = {
        "nodes": [_trigger("TA"), _branch("A"), _merge("B"),
                  _merge("C1"), _merge("C2"), _merge("D")],
        "edges": [
            _spread("TA", "A"),
            _cond_edge("A", "B", True),
            _cond_edge("A", "C1", False),
            _cond_edge("A", "C2", False),
            _spread("C1", "D"),
            _spread("C2", "D"),
        ],
    }
    ex = WorkflowExecutor(definition, task_id="f2-all-skip", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"TA": {"output": _gdf()}}))
    assert ex.node_stats["C1"]["status"] == "skipped"
    assert ex.node_stats["C2"]["status"] == "skipped"
    assert ex.node_stats["D"]["status"] == "skipped", "sem pai vivo, D deve ser skipado"
    assert "D" not in final
